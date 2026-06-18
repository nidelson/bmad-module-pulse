"""Invariant tests for the v0.6 'invert the speedometer' milestone.

v0.6 makes predictability/accuracy the hero metric and demotes leverage to
context. The dashboard math is agent instructions (no Python compute layer),
so these pin the *math and ordering the workflow tells the agent to use* — a
future edit cannot silently re-promote leverage to the headline.

Phase 1 scope: hero metric only (median estimate-error + trend, leverage
demoted). Convergence signal (Phase 2), regime detection (Phase 3) and the
celebration inversion (Phase 4) get their own invariants when they land.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
DASHBOARD = REPO_ROOT / "skills/bmad-pulse-dashboard/workflow.md"
TRACK_DONE = REPO_ROOT / "skills/bmad-pulse-track-done/workflow.md"
TRACK_BACKFILL = REPO_ROOT / "skills/bmad-pulse-track-backfill/workflow.md"
BCP_DOC = REPO_ROOT / "docs/integration/bcp.md"


def test_predictability_score_is_defined_as_hero():
    """The aggregation must define predictability_score and call it the hero."""
    text = DASHBOARD.read_text()
    assert "predictability_score" in text
    assert "hero metric" in text.lower()


def test_predictability_is_median_estimate_error():
    """Hero = median of per-story |actual - estimated| / estimated; median (not
    mean) to resist outliers, consistent with the v0.5 geometric choice."""
    text = DASHBOARD.read_text()
    assert "|actual_hours - estimated_hours| / estimated_hours" in text
    assert "median" in text.lower()
    assert "lower is better" in text.lower()


def test_predictability_is_method_agnostic():
    """Works with or without BCP: for BCP stories it equals |drift_pct|."""
    text = DASHBOARD.read_text()
    assert "method-agnostic" in text.lower()
    assert "|bcp_recorded.drift_pct|" in text


def test_predictability_has_trend_arrow():
    """The hero carries a convergence trend (first half vs second half)."""
    text = DASHBOARD.read_text()
    assert "trend_arrow" in text
    assert "converging" in text and "diverging" in text


def test_predictability_leads_table_before_leverage():
    """Ordering invariant: in General Statistics the Predictability row must
    appear BEFORE the leverage row — leverage is no longer the headline."""
    text = DASHBOARD.read_text()
    pred_idx = text.find("| **Previsibilidade**")
    lev_idx = text.find("| AI Leverage (vs PLANO")
    assert pred_idx != -1 and lev_idx != -1, "both rows must be present"
    assert pred_idx < lev_idx, "Predictability must lead; leverage comes after"


def test_leverage_demoted_to_context():
    """Leverage must be labelled vs PLAN and explicitly marked as context, not
    a target — and the old 'Avg AI Leverage' headline row must be gone."""
    text = DASHBOARD.read_text()
    assert "AI Leverage (vs PLANO" in text
    assert "contexto, não meta" in text
    assert "| Avg AI Leverage         | {avg}x             |" not in text, (
        "the pre-v0.6 leverage headline row must be replaced"
    )


# --- Phase 2: self-referential h/BCP convergence ----------------------------


def test_convergence_signal_is_defined():
    """h_per_bcp_convergence must be a defined self-referential drift signal."""
    text = DASHBOARD.read_text()
    assert "h_per_bcp_convergence" in text
    assert "self-referential" in text.lower()
    assert "stabiliz" in text.lower()


def test_convergence_uses_half_split_of_drift_trend():
    """The reading compares median |drift| of the first vs second half of
    drift_trend — falling = converging, rising = diverging."""
    text = DASHBOARD.read_text()
    assert "first half" in text and "second half" in text
    assert "converging" in text and "diverging" in text and "stable" in text


def test_convergence_corroborated_by_band():
    """The v0.5 confidence band narrowing is reported as corroborating evidence
    — Phase 2 consumes v0.5 data, it does not recompute raw ratios."""
    text = DASHBOARD.read_text()
    assert "h_per_bcp_band" in text and "narrow" in text.lower()
    assert "does not recompute raw ratios" in text


def test_convergence_needs_min_4_stories():
    """A trend needs >=4 BCP stories; fewer is an explicit thin-sample no-read,
    not a fabricated label."""
    text = DASHBOARD.read_text()
    assert ">= 4" in text or "≥4" in text
    assert "insufficient data" in text.lower() or "thin sample" in text.lower()


# --- Phase 3: regime detection via estimated_hours_basis --------------------


def test_regime_read_from_estimated_hours_basis():
    """The regime label is read read-only from the story's
    estimated_hours_basis frontmatter field."""
    text = DASHBOARD.read_text()
    assert "estimate_regime" in text
    assert "estimated_hours_basis" in text
    assert "read-only" in text.lower() or "read **read-only**" in text


def test_regime_falls_back_to_global_method():
    """When estimated_hours_basis is absent, regime falls back to the global
    pulse_estimation_method."""
    text = DASHBOARD.read_text()
    assert "pulse_estimation_method" in text
    assert "fall" in text.lower() and "absent" in text.lower()


def test_regime_labels_leverage_vs_plan_regime():
    """The leverage context line must carry the regime: 'vs PLAN ({regime})'."""
    text = DASHBOARD.read_text()
    assert "vs PLANO, {dominant_regime}" in text or "vs PLANO ({dominant_regime})" in text


def test_regime_read_is_zero_write_coupled():
    """v0.6 starts READING estimated_hours_basis but the zero-WRITE-coupling
    invariant holds: PULSE never writes it (recording workflows don't mention
    it) and never derives hours from it."""
    for wf in (TRACK_DONE, TRACK_BACKFILL):
        assert "estimated_hours_basis" not in wf.read_text(), (
            f"{wf.name} must never write estimated_hours_basis"
        )
    assert "never derives hours from it" in DASHBOARD.read_text()


def test_integration_doc_flips_basis_to_read_only():
    """docs/integration/bcp.md must reflect the reversal: estimated_hours_basis
    is now read read-only (not 'ignores'), while estimated_hours_pre_bcp stays
    ignored and zero-coupling language remains."""
    text = BCP_DOC.read_text()
    assert "reads it read-only" in text
    assert "| `estimated_hours_basis`     | BCP (audit — PULSE ignores)" not in text, (
        "the old 'PULSE ignores' row for estimated_hours_basis must be gone"
    )
    assert "estimated_hours_pre_bcp`   | BCP (audit — PULSE ignores)" in text, (
        "estimated_hours_pre_bcp must remain ignored"
    )
    assert "zero-coupled" in text or "zero coupling" in text


# --- Phase 4: vs-PLAN labels + inverted celebration -------------------------


def test_estimate_error_pct_computed_in_both_recorders():
    """track-done and track-backfill must compute the per-story estimate error
    (|actual - estimated| / estimated) that drives the inverted celebration."""
    for wf in (TRACK_DONE, TRACK_BACKFILL):
        text = wf.read_text()
        assert "estimate_error_pct = round(abs(actual_hours - estimated_hours)" in text


def test_celebration_triggers_on_accuracy_not_leverage():
    """The track-done celebration must trigger on estimate accuracy (on-plan),
    and the old leverage-magnitude trophy must be gone."""
    text = TRACK_DONE.read_text()
    assert "🎯 On-plan" in text
    assert "estimate_error_pct <= 15 ?" in text
    assert "🔥 Exceptional!" not in text, "the leverage-magnitude trophy must be retired"
    assert "leverage_ratio >= pulse_leverage_threshold_exceptional ?" not in text, (
        "leverage thresholds must no longer drive the celebration"
    )


def test_backfill_celebration_inverted_too():
    """The backfill card must invert the same way for consistency."""
    text = TRACK_BACKFILL.read_text()
    assert "🎯 On-plan" in text and "estimate_error_pct <= 15 ?" in text
    assert "🔥 Exceptional!" not in text


def test_leverage_thresholds_marked_legacy():
    """The leverage thresholds stay for back-compat but are flagged legacy —
    they no longer drive any celebration."""
    text = TRACK_DONE.read_text()
    assert "legacy since v0.6" in text


def test_leverage_labeled_vs_plan_in_cards_and_tables():
    """Every leverage display reads 'vs PLAN', never 'vs human' as a target."""
    done = TRACK_DONE.read_text()
    assert "AI Leverage: {leverage_ratio}x (vs PLAN" in done  # track-done card stays EN
    dash = DASHBOARD.read_text()
    assert "Leverage médio (vs PLANO)" in dash
    assert "Leverage (vs PLANO) | Qualidade" in dash
