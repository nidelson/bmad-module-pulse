"""Invariant tests for the v0.5 honest-measurement-engine (h/BCP baseline).

The dashboard h/BCP baseline is computed by the agent following the
instructions in ``skills/bmad-pulse-dashboard/workflow.md`` — there is no
Python compute layer to unit-test. These are meta/invariant tests in the same
spirit as ``test_bcp_integration.py``: they pin the *math the workflow tells
the agent to use* so a future edit cannot silently regress the geometric mean
back to an arithmetic mean (which is biased high and outlier-fragile for
multiplicative ratios).

Phase 1 scope: geometric mean only. Segmentation (Phase 2) and the confidence
band (Phase 3) get their own invariants when they land.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
DASHBOARD = REPO_ROOT / "skills/bmad-pulse-dashboard/workflow.md"
TRACK_DONE = REPO_ROOT / "skills/bmad-pulse-track-done/workflow.md"
TRACK_BACKFILL = REPO_ROOT / "skills/bmad-pulse-track-backfill/workflow.md"


def test_baseline_uses_geometric_mean():
    """h_per_bcp_by_category must instruct the agent to use the geometric mean,
    with the formula spelled out so the computation is deterministic."""
    text = DASHBOARD.read_text()
    assert "h_per_bcp_by_category" in text
    assert "geometric mean" in text, (
        "the per-category h/BCP baseline must use the geometric mean (v0.5)"
    )
    assert "exp(mean(ln(" in text, (
        "the geometric-mean formula must be inlined so the agent computes it "
        "deterministically"
    )


def test_baseline_is_not_arithmetic_mean():
    """Regression guard: the pre-0.5 arithmetic phrasing must be gone, so an
    edit cannot quietly revert to the biased arithmetic mean."""
    text = DASHBOARD.read_text()
    assert "the mean of `bcp_recorded.h_per_bcp_actual`" not in text, (
        "found the pre-0.5 arithmetic-mean phrasing — baseline regressed"
    )


def test_estimated_baseline_is_geometric_too():
    """The estimated-side baseline must use the same geometric mean so the
    drift comparison is apples-to-apples."""
    text = DASHBOARD.read_text()
    # The estimated line references the same geometric mean over the estimated
    # ratios; assert both the field and the geometric framing co-occur.
    assert "h_per_bcp_estimated_by_category" in text
    assert text.count("geometric mean") >= 2, (
        "both actual and estimated per-category baselines must be geometric"
    )


def test_outlier_rationale_documented():
    """The 'why' must live next to the instruction: ratios are multiplicative
    and the geometric mean resists outliers. Keeps the choice from being
    'cleaned up' by a future editor who reads it as gratuitous."""
    text = DASHBOARD.read_text().lower()
    assert "multiplicative" in text
    assert "outlier" in text


def test_v050_semantics_change_is_flagged():
    """Dashboard authors must be warned that baselines shift under the new
    math (arithmetic -> geometric), mirroring the existing 'pre-0.5.0' marker
    style used elsewhere in the workflow."""
    text = DASHBOARD.read_text()
    assert "v0.5.0" in text and "geometric" in text
    assert "pre-0.5.0" in text, (
        "the semantics-change note must contrast against pre-0.5.0 behavior"
    )


# --- Phase 2: micro vs story-size segmentation -----------------------------


def test_segmentation_splits_by_observed_median():
    """The micro/story split must be the observed median of bcp_recorded.total,
    not a fixed threshold (which would assume the BCP scale)."""
    text = DASHBOARD.read_text()
    assert "segment_split" in text
    assert "median" in text and "bcp_recorded.total" in text, (
        "the split must be the median of the observed BCP totals"
    )
    assert "micro" in text and "story" in text


def test_split_is_data_driven_no_config_knob():
    """Zero-coupling guard: no pulse_bcp_micro_threshold config key — a fixed
    threshold would bake in an assumption about the BCP point scale."""
    text = DASHBOARD.read_text()
    assert "pulse_bcp_micro_threshold" not in text, (
        "segmentation must be data-driven (observed median), not a config knob"
    )


def test_median_guarded_against_empty():
    """The independence invariant: median is only computed when bcp_stories is
    non-empty — median([]) must never be evaluated."""
    text = DASHBOARD.read_text()
    assert "non-empty" in text and "median([])" in text, (
        "the workflow must state median is skipped on empty bcp_stories"
    )


def test_thin_segment_falls_back_to_pooled():
    """A segment with n<3 must fold into the category pooled baseline rather
    than emit a thin/untrustworthy row."""
    text = DASHBOARD.read_text()
    assert "n < 3" in text or "n >= 3" in text
    assert "pooled" in text.lower() and "fallback" in text.lower()


def test_pooled_all_row_still_emitted():
    """Continuity with pre-0.5 dashboards: an `all` (pooled) row is always
    rendered per category."""
    text = DASHBOARD.read_text()
    assert "| {category} | all |" in text, (
        "the per-category pooled `all` row must remain for backward continuity"
    )


def test_no_persisted_segment_tag():
    """Segmentation happens at dashboard read time; the recording workflows
    must not write a derived `segment` tag into bcp_recorded (which would
    freeze the split and write a BCP-derived judgment into pulse_metrics)."""
    for wf in (TRACK_DONE, TRACK_BACKFILL):
        text = wf.read_text()
        assert "segment:" not in text, (
            f"{wf.name} must not persist a derived segment tag on bcp_recorded"
        )


# --- Phase 3: confidence band ----------------------------------------------


def test_baseline_carries_confidence_band():
    """Each baseline must report a typical range (band), not a bare point."""
    text = DASHBOARD.read_text()
    assert "h_per_bcp_band" in text
    assert "[geo_mean / GSD, geo_mean * GSD]" in text, (
        "the band must be the geometric mean divided/multiplied by the GSD"
    )


def test_band_uses_sample_gsd_n_minus_1():
    """The geometric standard deviation must be the *sample* GSD (n-1), since
    we estimate from a sample, not enumerate a population."""
    text = DASHBOARD.read_text()
    assert "sample_std(ln(h_per_bcp_actual))" in text
    assert "n-1" in text and "sample, not population" in text


def test_band_is_k1_typical_range_not_95ci():
    """k=1 (~68%, 'typical range') — explicitly not a 95% CI, which would be
    too wide to act on at PULSE's small n."""
    text = DASHBOARD.read_text()
    assert "k = 1" in text or "`k = 1`" in text
    assert "typical range" in text.lower()
    assert "not a 95% CI" in text or "not a 95%" in text


def test_no_band_when_n_lt_3():
    """A band requires n>=3; n<3 shows the bare point with an (n=2)/(n=1)
    marker — a 2-sample GSD has 1 degree of freedom and is unstable."""
    text = DASHBOARD.read_text()
    assert "n >= 3" in text
    assert "(n=2)" in text and "degree of freedom" in text


def test_band_render_shows_range_only_for_segment_rows():
    """The rendered table must show the [low–high] range for segment rows
    (n>=3 by construction) and gate the pooled row's range on n_all>=3."""
    text = DASHBOARD.read_text()
    assert "[{band.low}–{band.high}]" in text
    assert "{if n_all >= 3} [{pooled band.low}–{pooled band.high}]{end}" in text
