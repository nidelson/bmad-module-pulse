"""Tests for the core dashboard aggregations (issue #111, slice 2).

Fixtures are hand-built so every expected number can be checked on paper. Where
a test asserts a guardrail, it also asserts the *counterfactual* — what the
number would be without the guardrail — so a future reader can see what the rule
is buying.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "skills/bmad-pulse-dashboard/scripts")
)

from pulse_aggregations import (  # noqa: E402
    EFFORT_FLOOR_HOURS,
    MIN_N_FOR_SEGMENT,
    Story,
    avg_leverage_vs_reference,
    h_per_bcp_by_category,
    load_stories,
    predictability,
    reference_regime_breaks,
    segment_split,
)


def story(key="s", **kw):
    """Build one pulse_metrics entry; nested blocks assembled from flat kwargs."""
    raw = {}
    for k in ("actual_hours", "estimated_hours", "category", "estimate_error_pct",
              "leverage_vs_reference", "estimated_hours_reference"):
        if k in kw:
            raw[k] = kw[k]
    rec = {k: kw[k] for k in ("h_per_bcp_actual", "total", "drift_pct") if k in kw}
    if rec:
        raw["bcp_recorded"] = rec
    if "start_total" in kw:
        raw["bcp_at_start"] = {"total": kw["start_total"]}
    return Story(key, raw)


class TestLoadStories:
    def test_preserves_file_order(self):
        """Order is the chronological proxy every trend splits on."""
        pm = {"c": {"actual_hours": 1}, "a": {"actual_hours": 2}, "b": {"actual_hours": 3}}
        assert [s.key for s in load_stories(pm)] == ["c", "a", "b"]

    def test_skips_malformed_entries_without_crashing(self):
        pm = {"ok": {"actual_hours": 1}, "bad": "not a dict", "none": None}
        assert [s.key for s in load_stories(pm)] == ["ok"]

    def test_empty_input(self):
        assert load_stories({}) == [] and load_stories(None) == []


class TestStoryFields:
    def test_prefers_persisted_error_over_recompute(self):
        """Persisted and recomputed are identical by definition; prefer persisted."""
        s = story(actual_hours=2.0, estimated_hours=1.0, estimate_error_pct=42.0)
        assert s.estimate_error_pct == 42.0

    def test_recomputes_when_absent(self):
        """|2 - 1| / 1 * 100 = 100%."""
        assert story(actual_hours=2.0, estimated_hours=1.0).estimate_error_pct == 100.0

    def test_error_is_absolute(self):
        """Underestimating by 50% is as imprecise as overestimating by 50%."""
        assert story(actual_hours=0.5, estimated_hours=1.0).estimate_error_pct == 50.0
        assert story(estimate_error_pct=-30.0).estimate_error_pct == 30.0

    def test_zero_estimate_does_not_divide_by_zero(self):
        s = story(actual_hours=1.0, estimated_hours=0.0)
        assert s.estimate_error_pct == pytest.approx(10000.0)  # floored at 0.01

    def test_bcp_prefers_final_over_start_snapshot(self):
        """A rescore makes the snapshot report a rate that was never in force."""
        assert story(total=13, start_total=15).bcp_total == 13
        assert story(start_total=15).bcp_total == 15  # fallback only

    def test_rescored_is_detected_for_labelling(self):
        assert story(total=13, start_total=15).is_rescored is True
        assert story(total=13, start_total=13).is_rescored is False
        assert story(total=13).is_rescored is False

    def test_unknown_hours_does_not_pass_the_effort_floor(self):
        """Unmeasured is not free — admitting it would poison a cost baseline."""
        assert story(actual_hours=1.0).above_effort_floor is True
        assert story(actual_hours=0.05).above_effort_floor is False
        assert story().above_effort_floor is False

    def test_boolean_is_not_read_as_a_number(self):
        """`True` would otherwise arrive as 1.0 and pass the floor."""
        assert Story("s", {"actual_hours": True}).actual_hours is None


class TestPredictability:
    def test_median_not_mean(self):
        """One catastrophic story must not define the project's accuracy.

        errors [10, 10, 10, 400] → median 10 → 90%. The mean would be 107.5,
        clamping the score to 0% on the strength of a single outlier.
        """
        stories = [story(f"s{i}", estimate_error_pct=e)
                   for i, e in enumerate([10, 10, 10, 400])]
        assert predictability(stories)["score"] == 90.0

    def test_effort_floor_does_NOT_apply_here(self):
        """A 2-minute story that was predicted as 2 minutes was predicted well.

        The floor guards ratios with actual_hours in the denominator; accuracy
        is not one, so excluding these would discard real signal.
        """
        stories = [
            story("tiny", actual_hours=0.01, estimate_error_pct=0.0),
            story("a", actual_hours=1.0, estimate_error_pct=100.0),
            story("b", actual_hours=1.0, estimate_error_pct=100.0),
        ]
        assert predictability(stories)["n"] == 3
        assert predictability(stories)["score"] == 0.0  # median 100 → clamped

    def test_reports_trend_direction(self):
        rising = [story(f"s{i}", estimate_error_pct=e) for i, e in enumerate([5, 5, 60, 60])]
        assert predictability(rising)["trend"] == "diverging"

    def test_no_data_is_none_not_zero(self):
        """0% predictable is a measurement; absent is not."""
        assert predictability([])["score"] is None
        assert predictability([story(actual_hours=1.0)])["score"] is None


class TestSegmentSplit:
    def test_is_the_median_bcp_total(self):
        stories = [story(f"s{i}", total=t) for i, t in enumerate([2, 4, 6, 100])]
        assert segment_split(stories) == 5.0

    def test_includes_low_effort_stories(self):
        """Size and effort are different axes — filtering here moves the boundary."""
        stories = [story("tiny", total=2, actual_hours=0.01),
                   story("a", total=10, actual_hours=5),
                   story("b", total=12, actual_hours=5)]
        assert segment_split(stories) == 10.0

    def test_none_when_nothing_is_scored(self):
        assert segment_split([story(actual_hours=1)]) is None


class TestHPerBcpByCategory:
    def test_geometric_mean_and_pooled_band(self):
        """geo_mean(0.05, 0.10, 0.20) = (0.001)^(1/3) = 0.1 exactly."""
        stories = [story(f"s{i}", category="backend", actual_hours=1.0,
                         h_per_bcp_actual=h, total=10)
                   for i, h in enumerate([0.05, 0.10, 0.20])]
        pooled = h_per_bcp_by_category(stories)["by_category"]["backend"]["pooled"]
        assert pooled["geo_mean"] == pytest.approx(0.1)
        assert pooled["n"] == 3 and pooled["band"] is not None

    def test_effort_floor_excludes_and_reports_the_count(self):
        """The counterfactual: without the floor the baseline drops ~5x."""
        stories = [
            story("bump", category="backend", actual_hours=0.02, h_per_bcp_actual=0.001, total=1),
            story("a", category="backend", actual_hours=1.0, h_per_bcp_actual=0.10, total=10),
            story("b", category="backend", actual_hours=1.0, h_per_bcp_actual=0.10, total=10),
        ]
        out = h_per_bcp_by_category(stories)
        assert out["excluded_below_effort_floor"] == 1
        assert out["by_category"]["backend"]["pooled"]["geo_mean"] == pytest.approx(0.10)
        assert out["by_category"]["backend"]["pooled"]["n"] == 2

    def test_thin_segment_folds_into_pooled_instead_of_vanishing(self):
        """2 micro stories: no segment of their own, but still counted."""
        stories = [story(f"m{i}", category="backend", actual_hours=1.0,
                         h_per_bcp_actual=0.10, total=2) for i in range(2)]
        stories += [story(f"s{i}", category="backend", actual_hours=1.0,
                          h_per_bcp_actual=0.10, total=50) for i in range(3)]
        cat = h_per_bcp_by_category(stories)["by_category"]["backend"]
        assert "micro" not in cat["segments"]        # below MIN_N_FOR_SEGMENT
        assert cat["segments"]["story"]["n"] == 3
        assert cat["pooled"]["n"] == 5               # nothing was lost
        assert MIN_N_FOR_SEGMENT == 3

    def test_thin_category_reports_point_without_band(self):
        stories = [story("only", category="mobile", actual_hours=1.0,
                         h_per_bcp_actual=0.07, total=10)]
        pooled = h_per_bcp_by_category(stories)["by_category"]["mobile"]["pooled"]
        assert pooled["geo_mean"] == pytest.approx(0.07)
        assert pooled["band"] is None and pooled["n"] == 1


class TestAvgLeverageVsReference:
    def test_mean_matches_the_published_spec(self):
        """Ported as specified: arithmetic mean of (10, 20, 60) = 30."""
        stories = [story(f"s{i}", category="backend", actual_hours=1.0,
                         leverage_vs_reference=v) for i, v in enumerate([10.0, 20.0, 60.0])]
        out = avg_leverage_vs_reference(stories)
        assert out["mean"] == pytest.approx(30.0)

    def test_geometric_mean_reported_alongside_for_comparison(self):
        """geo_mean(10, 20, 60) = 12000^(1/3) ≈ 22.89 — visibly lower.

        The gap is the point: the arithmetic mean of a ratio is pulled upward by
        outliers, on a metric explicitly labelled "the number that sells".
        """
        stories = [story(f"s{i}", category="backend", actual_hours=1.0,
                         leverage_vs_reference=v) for i, v in enumerate([10.0, 20.0, 60.0])]
        out = avg_leverage_vs_reference(stories)
        assert out["geo_mean"] == pytest.approx(12000 ** (1 / 3))
        assert out["geo_mean"] < out["mean"]

    def test_degenerate_effort_excluded_from_the_headline(self):
        """Without the floor a 2-minute patch reads as 500x and owns the average."""
        stories = [
            story("patch", category="backend", actual_hours=0.02, leverage_vs_reference=500.0),
            story("a", category="backend", actual_hours=1.0, leverage_vs_reference=10.0),
        ]
        out = avg_leverage_vs_reference(stories)
        assert out["mean"] == pytest.approx(10.0)
        assert out["excluded_below_effort_floor"] == 1
        assert (500.0 + 10.0) / 2 == 255.0  # what it would have published

    def test_absent_not_zero_when_no_story_carries_a_reference(self):
        stories = [story("a", category="backend", actual_hours=1.0)]
        assert avg_leverage_vs_reference(stories)["mean"] is None

    def test_best_per_category_is_identified(self):
        stories = [
            story("small", category="frontend", actual_hours=1.0, leverage_vs_reference=10.0),
            story("big", category="frontend", actual_hours=1.0, leverage_vs_reference=85.6),
        ]
        assert avg_leverage_vs_reference(stories)["by_category"]["frontend"]["best"] == ("big", 85.6)

    def test_effort_floor_constant_is_six_minutes(self):
        assert EFFORT_FLOOR_HOURS == 0.1


class TestReferenceRegimeBreaks:
    def test_single_rate_is_one_regime(self):
        """65/13 = 5.0 for both — the governed rate never changed."""
        stories = [story(f"s{i}", estimated_hours_reference=65.0, total=13) for i in range(2)]
        out = reference_regime_breaks(stories)
        assert out["single_regime"] is True and list(out["rates"]) == [5.0]

    def test_two_rates_are_flagged(self):
        stories = [story("old", estimated_hours_reference=65.0, total=13),
                   story("new", estimated_hours_reference=52.0, total=13)]
        out = reference_regime_breaks(stories)
        assert out["single_regime"] is False and sorted(out["rates"]) == [4.0, 5.0]

    def test_rescored_story_uses_final_bcp_and_is_labelled(self):
        """The phantom regime this prevents: 65/15 = 4.33 vs the real 65/13 = 5.0."""
        stories = [story("rescored", estimated_hours_reference=65.0, total=13, start_total=15)]
        out = reference_regime_breaks(stories)
        assert list(out["rates"]) == [5.0]
        assert out["rescored_stories"] == ["rescored"]
