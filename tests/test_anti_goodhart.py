"""Anti-Goodhart contract test for the v0.5 honest-measurement-engine.

The whole v0.5 north-star shift rests on one mathematical fact: leverage
(`estimated_hours / actual_hours`) collapses to ~1.0x once the estimate basis
is calibrated. Therefore a *leverage target* would reward inflating estimates
(never calibrating) — the textbook Goodhart trap.

This file locks that invariant two ways:
  1. **Premise lock (markdown invariant):** the leverage formula the workflow
     tells the agent to use must stay `estimated_hours / actual_hours`, and the
     dashboard must carry the anti-Goodhart note. If either drifts, these tests
     break and force a conscious re-examination.
  2. **Property lock (executable math):** using that exact formula, calibration
     drives leverage to 1.0 and estimate inflation drives it up. These encode,
     in runnable form, *why* leverage must never be promoted to a KPI.

There is no Python compute layer in PULSE (the dashboard math is agent
instructions), so part 2 re-implements the documented formula and asserts its
properties — a contract, not a test of internal code.
"""
from __future__ import annotations

import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
TRACK_DONE = REPO_ROOT / "skills/bmad-pulse-track-done/workflow.md"
DASHBOARD = REPO_ROOT / "skills/bmad-pulse-dashboard/workflow.md"


# --- the documented formulas, re-implemented for the property locks ---------


def leverage(estimated_hours: float, actual_hours: float) -> float:
    """The formula PULSE documents at track-done: leverage = est / act."""
    return estimated_hours / max(0.01, actual_hours)


def geometric_mean(ratios: list[float]) -> float:
    """The v0.5 baseline estimator: geometric mean of h/BCP ratios."""
    return statistics.geometric_mean(ratios)


# --- Part 1: premise locks (markdown invariants) ----------------------------


def test_leverage_formula_is_estimated_over_actual():
    """The premise of the whole invariant: leverage stays est/actual. If this
    formula changes, the anti-Goodhart reasoning must be re-derived."""
    text = TRACK_DONE.read_text()
    assert "leverage_ratio = estimated_hours / actual_hours" in text


def test_dashboard_carries_anti_goodhart_note():
    """The 'why' must live next to the leverage number on the dashboard."""
    text = DASHBOARD.read_text()
    assert "Invariante anti-Goodhart" in text
    assert "leverage não é meta" in text.lower()
    assert "~1.0x por construção" in text
    assert "vs PLANO" in text and "nunca" in text and "vs humano" in text


def test_predictability_is_named_the_durable_signal():
    """The note must point to predictability (drift→0), not the multiplier, as
    the signal that matters (PT-BR rendered output: previsibilidade)."""
    text = DASHBOARD.read_text().lower()
    assert "previsibilidade" in text
    assert "drift" in text and "converg" in text


# --- Part 2: property locks (executable math) -------------------------------


def test_calibrated_baseline_drives_leverage_to_one():
    """When the estimate basis is calibrated — i.e. estimated_hours is derived
    from a baseline (geometric mean of past h/BCP) that matches the realized
    h/BCP — leverage collapses to ~1.0x. A healthy state is NOT a big number."""
    bcp_total = 20
    past_ratios = [3.8, 4.2, 4.0, 4.1, 3.9]  # realized h/BCP history
    calibrated_baseline = geometric_mean(past_ratios)  # ~4.0
    estimated_hours = calibrated_baseline * bcp_total
    actual_hours = geometric_mean(past_ratios) * bcp_total  # reality matches
    lev = leverage(estimated_hours, actual_hours)
    assert abs(lev - 1.0) < 1e-9, (
        f"calibrated baseline must drive leverage to ~1.0, got {lev}"
    )


def test_inflated_estimate_inflates_leverage():
    """Same actuals, an inflated (uncalibrated) estimate → leverage spikes.
    This is the Goodhart trap made explicit: a leverage *goal* would reward
    exactly this inflation, not real speed."""
    bcp_total = 20
    actual_hours = 4.0 * bcp_total  # 80h realized
    calibrated = leverage(4.0 * bcp_total, actual_hours)
    inflated = leverage(8.0 * bcp_total, actual_hours)  # estimate doubled
    assert calibrated < inflated, "inflating the estimate must raise leverage"
    assert abs(inflated - 2.0) < 1e-9, "doubled estimate → 2.0x, pure artifact"


def test_leverage_target_would_reward_not_calibrating():
    """Direct statement of the perverse incentive: across a calibration path
    where estimates converge on reality, leverage monotonically falls toward
    1.0 — so maximizing leverage means refusing to calibrate."""
    actual = 4.0
    # estimate basis improving from 3x-inflated down to calibrated
    estimate_bases = [12.0, 8.0, 6.0, 4.8, 4.0]
    levs = [leverage(e, actual) for e in estimate_bases]
    assert levs == sorted(levs, reverse=True), (
        "as calibration improves, leverage must fall — a leverage goal fights it"
    )
    assert abs(levs[-1] - 1.0) < 1e-9, "fully calibrated endpoint is 1.0x"
