"""Tests for the process-health aggregations (issue #111, slice 3).

The `halts` field has three valid shapes in the wild; most of these tests exist
because the shapes are NOT interchangeable and the failure mode is silent — a
missing duration read as zero understates approval friction instead of crashing.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "skills/bmad-pulse-dashboard/scripts")
)

from pulse_aggregations import Story  # noqa: E402
from pulse_process import (  # noqa: E402
    first_pass_rate,
    halt_aggregations,
    normalize_halts,
    process_health_summary,
    review_cycle_stats,
    vs_plano_leverage,
)


def story(key="s", halts=None, **kw):
    raw = dict(kw)
    if halts is not None:
        raw.setdefault("process_health", {})["halts"] = halts
    return Story(key, raw)


class TestNormalizeHalts:
    def test_shape_a_is_an_opaque_count_not_invented_entries(self):
        """An integer records HOW MANY, never of what kind."""
        entries, opaque, legacy = normalize_halts(3)
        assert entries == [] and opaque == 3 and legacy == 0

    def test_shape_b_reads_the_structured_fields(self):
        entries, opaque, legacy = normalize_halts(
            [{"kind": "approval_wait", "duration_min": 45, "pre_approved_batch": False}]
        )
        assert opaque == 0 and legacy == 0 and len(entries) == 1
        assert entries[0].kind == "approval_wait" and entries[0].duration_min == 45.0

    def test_shape_c_infers_kind_and_leaves_duration_unknown(self):
        """Legacy strings carry a kind in the prefix but never a duration."""
        entries, _, legacy = normalize_halts(["approval_wait_human_review", "something_else"])
        assert legacy == 2
        assert entries[0].kind == "approval_wait"
        assert entries[0].duration_min is None  # unknown, NOT zero
        assert entries[1].kind == "unknown"

    def test_unknown_duration_is_none_never_zero(self):
        """Zero would silently pull the approval-wait total down."""
        entries, _, _ = normalize_halts([{"kind": "approval_wait"}])
        assert entries[0].duration_min is None
        assert entries[0].counts_toward_minutes is False

    def test_true_is_not_counted_as_one_halt(self):
        """`True` is an int in Python — it must not become a halt count."""
        assert normalize_halts(True) == ([], 0, 0)

    def test_degrades_on_garbage_instead_of_crashing(self):
        for junk in (None, "a string", {"not": "a list"}, 3.7, [], [None, 42]):
            entries, opaque, legacy = normalize_halts(junk)
            assert isinstance(entries, list)

    def test_negative_count_is_floored(self):
        assert normalize_halts(-5)[1] == 0

    def test_non_numeric_duration_is_unknown(self):
        entries, _, _ = normalize_halts([{"kind": "approval_wait", "duration_min": "45min"}])
        assert entries[0].duration_min is None


class TestFirstPassRate:
    def test_missing_field_is_not_counted_as_failure(self):
        """Absence would invent rework that never happened."""
        stories = [story("a", first_pass=True), story("b", first_pass=True), story("c")]
        out = first_pass_rate(stories)
        assert out["total"] == 2 and out["rate"] == 100.0

    def test_reports_the_raw_counts_beside_the_rate(self):
        """27/33 says what a bare 81.8% hides."""
        stories = [story(f"p{i}", first_pass=True) for i in range(9)]
        stories.append(story("f", first_pass=False))
        out = first_pass_rate(stories)
        assert (out["rate"], out["passed"], out["total"]) == (90.0, 9, 10)

    def test_names_the_stories_that_needed_rework(self):
        stories = [story("ok", first_pass=True), story("redo", first_pass=False)]
        assert first_pass_rate(stories)["not_first_pass"] == ["redo"]

    def test_no_data_is_none_not_zero(self):
        assert first_pass_rate([story("a")])["rate"] is None


class TestReviewCycleStats:
    def test_distribution_shows_what_a_mean_hides(self):
        """{1: 3, 3: 1} — most pass once, one needed three. Mean says 1.5."""
        stories = [story(f"s{i}", review_cycles=c) for i, c in enumerate([1, 1, 1, 3])]
        rc = review_cycle_stats(stories)["review_cycles"]
        assert rc["distribution"] == {1: 3, 3: 1}
        assert rc["mean"] == 1.5 and rc["max"] == 3

    def test_booleans_are_not_counted_as_cycles(self):
        stories = [story("a", review_cycles=True), story("b", review_cycles=2)]
        assert review_cycle_stats(stories)["review_cycles"]["n"] == 1

    def test_empty_is_none(self):
        assert review_cycle_stats([])["review_cycles"]["mean"] is None


class TestHaltAggregations:
    def test_total_counts_every_shape(self):
        """2 (int) + 1 (object) + 1 (string) = 4."""
        stories = [story("a", halts=2),
                   story("b", halts=[{"kind": "approval_wait", "duration_min": 10}]),
                   story("c", halts=["approval_wait_x"])]
        assert halt_aggregations(stories)["total_halts"] == 4

    def test_minutes_come_only_from_shape_b(self):
        """Shape C contributes 0 minutes and is reported as unknown."""
        stories = [story("b", halts=[{"kind": "approval_wait", "duration_min": 30}]),
                   story("c", halts=["approval_wait_legacy"])]
        out = halt_aggregations(stories)
        assert out["approval_wait_minutes"] == 30.0
        assert out["approval_wait_count"] == 2
        assert out["approval_wait_unknown_minutes"] == 1  # the gap is explicit

    def test_pre_approved_batch_excluded_from_minutes(self):
        """Waiting on an already-authorised batch is not process friction."""
        stories = [story("a", halts=[
            {"kind": "approval_wait", "duration_min": 500, "pre_approved_batch": True},
            {"kind": "approval_wait", "duration_min": 20, "pre_approved_batch": False},
        ])]
        out = halt_aggregations(stories)
        assert out["approval_wait_minutes"] == 20.0
        assert out["pre_approved_batch_count"] == 1
        assert 500 + 20 == 520  # what it would have reported without the rule

    def test_legacy_strings_counted_for_the_migration_hint(self):
        stories = [story("c", halts=["approval_wait_a", "other"])]
        assert halt_aggregations(stories)["legacy_halt_string_count"] == 2

    def test_groups_by_kind(self):
        stories = [story("a", halts=[{"kind": "incident"}, {"kind": "approval_wait"}]),
                   story("b", halts=[{"kind": "incident"}])]
        assert halt_aggregations(stories)["by_kind"]["incident"] == 2

    def test_shape_a_contributes_no_kinds(self):
        """An opaque count cannot say what kind of halt it was."""
        assert halt_aggregations([story("a", halts=5)])["by_kind"] == {}

    def test_per_story_breakdown_marks_unknown_minutes(self):
        stories = [story("known", halts=[{"kind": "approval_wait", "duration_min": 15}]),
                   story("legacy", halts=["approval_wait_x"])]
        per = dict(halt_aggregations(stories)["stories_with_approval_wait"])
        assert per["known"] == 15.0
        assert per["legacy"] is None  # renders as "?min", not "0min"


class TestVsPlanoLeverage:
    def test_computed_but_flagged_not_to_render(self):
        """The anti-Goodhart invariant, enforced in the return shape."""
        stories = [story("a", estimated_hours=2.0, actual_hours=1.0)]
        out = vs_plano_leverage(stories)
        assert out["mean"] == 2.0
        assert out["render"] is False
        assert out["collapses_to"] == 1.0
        assert "calibrated" in out["why_not_rendered"]

    def test_calibrated_basis_collapses_to_one(self):
        """The invariant made visible: perfect estimates give exactly 1.0x."""
        stories = [story(f"s{i}", estimated_hours=h, actual_hours=h)
                   for i, h in enumerate([1.0, 2.0, 5.0])]
        assert vs_plano_leverage(stories)["mean"] == 1.0

    def test_effort_floor_applies_here_too(self):
        stories = [story("tiny", estimated_hours=5.0, actual_hours=0.02),
                   story("real", estimated_hours=2.0, actual_hours=2.0)]
        out = vs_plano_leverage(stories)
        assert out["n"] == 1 and out["mean"] == 1.0

    def test_no_data_is_none(self):
        assert vs_plano_leverage([])["mean"] is None


class TestProcessHealthSummary:
    def test_assembles_every_section(self):
        stories = [story("a", first_pass=True, review_cycles=1, actual_hours=1.0,
                         estimated_hours=1.0, halts=[{"kind": "approval_wait", "duration_min": 5}])]
        out = process_health_summary(stories)
        assert set(out) == {"first_pass", "cycles", "halts", "vs_plano",
                            "flow_complete", "most_unused_skills"}
        assert out["first_pass"]["rate"] == 100.0
        assert out["halts"]["approval_wait_minutes"] == 5.0

    def test_counts_unused_skills_across_stories(self):
        stories = [Story("a", {"process_health": {"unused_skills": ["x", "y"]}}),
                   Story("b", {"process_health": {"unused_skills": ["x"]}})]
        assert process_health_summary(stories)["most_unused_skills"]["x"] == 2

    def test_survives_malformed_process_health(self):
        stories = [Story("a", {"process_health": "not a dict"}), Story("b", {})]
        out = process_health_summary(stories)
        assert out["halts"]["total_halts"] == 0
