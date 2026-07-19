"""Invariant tests for the issue #65 'stable leverage vs frozen reference'.

v0.6 made predictability the hero and labelled leverage "vs PLAN". That
vs-plan leverage collapses to ~1.0x by construction once the estimate basis
calibrates — which is exactly the predictability signal. Issue #65 adds a
THIRD framing: leverage **vs a frozen REFERENCE** (`estimated_hours_reference`,
written upstream by bmad-module-bcp). Its denominator is frozen, so it does
NOT collapse — an honest, stable ROI number vs a fixed external benchmark.

Like the rest of the BCP integration, PULSE stays passive and zero-coupled:
it only READS `estimated_hours_reference` (file convention) and divides. It
never imports BCP, never reads the baseline, never converts BCP→hours, and
never writes the story frontmatter.

The dashboard math is agent instructions (no Python compute layer), so these
pin the math/labels/ordering the workflow markdown tells the agent to use.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
TRACK_START = REPO_ROOT / "skills/bmad-pulse-track-start/workflow.md"
TRACK_DONE = REPO_ROOT / "skills/bmad-pulse-track-done/workflow.md"
DASHBOARD = REPO_ROOT / "skills/bmad-pulse-dashboard/workflow.md"
BCP_DOC = REPO_ROOT / "docs/integration/bcp.md"

FIELD = "estimated_hours_reference"
METRIC = "leverage_vs_reference"


# --- track-start: snapshot the frozen reference read-only -------------------


def test_track_start_reads_reference_field_read_only():
    text = TRACK_START.read_text()
    assert FIELD in text, "track-start must read estimated_hours_reference"
    assert "read-only" in text.lower()


def test_track_start_snapshots_reference_only_when_present():
    """Mirror of bcp_at_start: snapshot the field into pulse_metrics, and only
    when present (graceful — absence is normal, not an error)."""
    text = TRACK_START.read_text()
    assert FIELD in text
    assert "only" in text.lower() and "present" in text.lower()


# --- track-done: compute stable leverage vs the frozen reference ------------


def test_track_done_computes_leverage_vs_reference():
    text = TRACK_DONE.read_text()
    assert METRIC in text
    assert f"{FIELD} / actual_hours" in text, (
        "leverage_vs_reference must be estimated_hours_reference / actual_hours"
    )


def test_track_done_keeps_vs_plan_leverage():
    """The existing vs-PLAN leverage line must remain intact — vs-reference is
    additive, not a replacement (predictability stays the hero)."""
    text = TRACK_DONE.read_text()
    assert "leverage_ratio = estimated_hours / actual_hours" in text
    assert "AI Leverage: {leverage_ratio}x (vs PLAN" in text


def test_track_done_reference_is_graceful_when_absent():
    """No estimated_hours_reference → omit vs-reference, keep today's behavior."""
    text = TRACK_DONE.read_text()
    assert METRIC in text
    lowered = text.lower()
    assert "absent" in lowered or "when available" in lowered or "omit" in lowered


def test_track_done_card_labels_reference_as_frozen_stable():
    text = TRACK_DONE.read_text()
    assert "vs REFERENCE" in text or "vs REFERÊNCIA" in text
    assert "frozen" in text.lower()


def test_track_done_never_writes_basis_or_frontmatter():
    """Zero-write coupling holds: track-done reads the reference field but never
    writes story frontmatter and never touches estimated_hours_basis."""
    text = TRACK_DONE.read_text()
    assert "estimated_hours_basis" not in text, (
        "track-done must never write/mention estimated_hours_basis (locked by "
        "test_invert_speedometer too)"
    )
    assert "read-only" in text.lower()


# --- dashboard: render the stable leverage, labelled, not the hero ----------


def test_dashboard_aggregates_leverage_vs_reference():
    text = DASHBOARD.read_text()
    assert METRIC in text


def test_dashboard_labels_reference_leverage_frozen_and_stable():
    text = DASHBOARD.read_text()
    assert "vs REFERÊNCIA frozen" in text or "vs REFERENCIA frozen" in text
    # the whole point: it does NOT collapse (distinct from vs-plan)
    assert "não colapsa" in text.lower() or "does not collapse" in text.lower()


def test_dashboard_predictability_still_leads_over_reference_leverage():
    """Issue #65 is additive: predictability stays the hero, the stable leverage
    is board/ROI context — it must appear AFTER the predictability row."""
    text = DASHBOARD.read_text()
    pred_idx = text.find("| **Previsibilidade**")
    ref_idx = text.find("REFERÊNCIA frozen")
    assert pred_idx != -1 and ref_idx != -1, "both must be present"
    assert pred_idx < ref_idx, "predictability must still lead"


def test_dashboard_reference_leverage_is_conditional():
    """The vs-reference row/line must be gated on the field existing — stories
    without estimated_hours_reference must not fabricate it."""
    text = DASHBOARD.read_text()
    assert METRIC in text
    assert "CONDITIONAL" in text  # the file uses CONDITIONAL gating markers


# --- docs: ownership + read-only contract -----------------------------------


def test_bcp_doc_documents_reference_field():
    text = BCP_DOC.read_text()
    assert FIELD in text
    assert "leverage" in text.lower() and "frozen" in text.lower()


def test_bcp_doc_reference_is_pulse_read_only():
    """The ownership table must mark estimated_hours_reference BCP-owned /
    PULSE-read-only, same contract as the other bcp.* fields."""
    text = BCP_DOC.read_text()
    # appears in the ownership table with a read-only attribution
    assert FIELD in text
    assert "read-only" in text.lower() or "PULSE reads" in text
