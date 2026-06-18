"""Invariant tests for the v0.7 'action that matters' milestone.

v0.7 surfaces drift at the *commitment gate* (track-start) so a bad estimate is
interrupted before it becomes a promise. The math lives in agent instructions
(no Python compute layer), so these pin the cohort-drift primitive and, in later
phases, the advisory-only invariant of the alert itself.

Phase 1 scope: the shared cohort_drift aggregation. The track-start alert
(Phase 2), the dashboard watch-list (Phase 3) and the advisory-only contract
(Phase 4) get their own invariants when they land.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
DASHBOARD = REPO_ROOT / "skills/bmad-pulse-dashboard/workflow.md"
TRACK_START = REPO_ROOT / "skills/bmad-pulse-track-start/workflow.md"


def test_cohort_drift_primitive_is_defined():
    """cohort_drift(category, segment) must be defined as the shared v0.7
    primitive over the per-story estimate error."""
    text = DASHBOARD.read_text()
    assert "cohort_drift(category, segment)" in text
    assert "|actual_hours - estimated_hours| / estimated_hours" in text
    assert "median" in text.lower()


def test_cohort_drift_uses_last_k5():
    """The window is the last K=5 completed stories in the cohort."""
    text = DASHBOARD.read_text()
    assert "K = 5" in text
    assert "last `K = 5` completed stories" in text


def test_cohort_key_is_category_segment_with_category_fallback():
    """Cohort key = (category, segment) when the story carries BCP, else
    (category) — so non-BCP projects still cohort by category."""
    text = DASHBOARD.read_text()
    assert "(category, segment)` when the story carries BCP" in text
    assert "(category)` alone" in text


def test_cohort_drift_insufficient_below_3():
    """n<3 must be 'insufficient' and callers must stay silent — no false
    alarm on a thin cohort."""
    text = DASHBOARD.read_text()
    assert "n >= 3" in text
    assert "insufficient" in text.lower()
    assert "no false alarm" in text.lower()


def test_cohort_drift_is_read_only():
    """The primitive reads pulse_metrics; it never writes or alters an
    estimate (sets up the advisory-only invariant locked in Phase 4)."""
    text = DASHBOARD.read_text()
    assert "read-only over `pulse_metrics`" in text
    assert "never writes or alters any estimate" in text


def test_cohort_drift_equals_drift_pct_for_bcp():
    """For BCP stories the per-story error equals |bcp_recorded.drift_pct|, so
    the primitive is consistent with the v0.5/v0.6 drift data, not a new metric."""
    text = DASHBOARD.read_text()
    assert "equals `|bcp_recorded.drift_pct|`" in text


# --- Phase 2: drift alert at the track-start commitment gate -----------------


def test_alert_fires_at_track_start():
    """track-start must have an estimation drift check step and surface the
    advisory in the Confirm card."""
    text = TRACK_START.read_text()
    assert "Estimation drift check" in text
    assert "cohort_drift(category, segment)" in text
    assert "re-estimate before committing" in text


def test_alert_threshold_t25_window_k5():
    """The alert fires only when n>=3 and the cohort median exceeds T=25% over
    the last K=5 — quantifying the '+N%' the roadmap asks for."""
    text = TRACK_START.read_text()
    assert "n >= 3" in text and "T = 25%" in text and "K = 5" in text


def test_alert_silent_when_healthy_or_thin():
    """No false alarm: stay silent on a healthy or thin cohort."""
    text = TRACK_START.read_text()
    assert "silent" in text.lower()
    assert "no false alarm" in text.lower()


def test_alert_is_non_blocking():
    """The advisory must be non-blocking — the start is recorded regardless."""
    text = TRACK_START.read_text()
    assert "non-blocking" in text.lower()
    assert "start is recorded regardless" in text.lower() or "never halts the start" in text.lower()


def test_alert_never_changes_the_estimate():
    """Advisory-only invariant at the source: track-start never writes or
    changes estimated_hours via the alert."""
    text = TRACK_START.read_text()
    assert "never changes `estimated_hours`" in text or "never writes or changes `estimated_hours`" in text
    assert "advisory-only" in text.lower()


# --- Phase 3: dashboard estimation-drift watch-list -------------------------


def test_watchlist_aggregation_defined():
    """drift_watchlist keeps only cohorts with n>=3 and median > T, sorted desc."""
    text = DASHBOARD.read_text()
    assert "drift_watchlist" in text
    assert "median_abs_drift_pct > T = 25%" in text
    assert "sorted by `median_abs_drift_pct` desc" in text


def test_watchlist_section_rendered():
    """The dashboard must render the 'Monitor de drift de estimativa' section
    (PT-BR rendered output)."""
    text = DASHBOARD.read_text()
    assert "Monitor de drift de estimativa" in text
    assert "| Coorte |" in text and "Tendência" in text


def test_watchlist_omits_healthy_and_has_empty_default():
    """Healthy cohorts are omitted; an empty watch-list shows the healthy
    default message, not a blank/alarming table (PT-BR rendered output)."""
    text = DASHBOARD.read_text()
    assert "Coortes saudáveis são omitidas" in text
    assert "Nenhuma coorte derivando — estimativas no rumo" in text


def test_watchlist_is_additive_outside_bcp_gate():
    """The watch-list works for non-BCP projects too — it must sit OUTSIDE the
    BCP conditional block (after END CONDITIONAL bcp)."""
    text = DASHBOARD.read_text()
    end_bcp = text.find("<!-- END CONDITIONAL bcp -->")
    watch = text.find("## 🚦 Monitor de drift de estimativa")
    assert end_bcp != -1 and watch != -1
    assert watch > end_bcp, "watch-list must be outside the BCP-gated section"


# --- Phase 4: advisory-only contract (consolidating lock) -------------------


def test_advisory_invariant_note_present():
    """The 'why' must live next to the code: track-start carries an explicit
    advisory-invariant note (estimation is upstream; the alert informs, never
    drives)."""
    text = TRACK_START.read_text()
    assert "Advisory invariant" in text
    assert "informs, it never drives" in text
    assert "owned **upstream**" in text


def test_v07_never_writes_estimates_or_frontmatter():
    """Cross-cutting lock: the v0.7 surfaces never mutate an estimate or the
    story frontmatter. track-start states it for the alert; the dashboard
    cohort primitive is read-only over pulse_metrics."""
    ts = TRACK_START.read_text()
    assert "never writes the story frontmatter" in ts
    assert "never writes or adjusts `estimated_hours`" in ts
    dash = DASHBOARD.read_text()
    assert "read-only over `pulse_metrics`" in dash
    assert "never writes or alters any estimate" in dash


def test_alert_quantifies_plus_n_percent():
    """Roadmap promise: the alert quantifies '+N%' (a number), not a vague
    'drifting' label."""
    ts = TRACK_START.read_text()
    assert "+{median_abs_drift}%" in ts


def test_alert_and_watchlist_share_one_primitive():
    """Both the track-start alert and the dashboard watch-list must derive from
    the same cohort_drift primitive — no divergent thresholds or definitions."""
    assert "cohort_drift(category, segment)" in TRACK_START.read_text()
    dash = DASHBOARD.read_text()
    assert "cohort_drift(category, segment)" in dash and "drift_watchlist" in dash
    # the threshold T=25% is stated once per consumer, identical value
    assert "T = 25%" in TRACK_START.read_text() and "T = 25%" in dash
