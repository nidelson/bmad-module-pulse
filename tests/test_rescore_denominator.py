"""A rescored story must not be measured against its start-time BCP total.

`bcp_at_start` is a snapshot: what the story was worth when work began. It is
worth keeping — it is the only in-band evidence that a rescore happened. But it
is the wrong DENOMINATOR for anything, because every numerator it gets paired
with comes from the story's *final* scoring:

  - `estimated_hours` is derived upstream by bmad-bcp-score from the final BCP,
    so `estimated_hours / bcp_at_start.total` mixes two scorings and describes
    no state the story was ever in.
  - `estimated_hours_reference` is likewise `final_bcp x reference_rate`, so
    dividing it by the start snapshot reports a reference rate that was never
    in force — a phantom regime break.

Observed in the wild (SIP, story 13-0-mcp-data): start 15 BCP, rescored to 13.
The frozen anchor was 65h. Dividing by the snapshot gives 65/15 = 4.33 h/BCP
next to the project's real 5.0, which reads as an ungoverned change to the
market-quote ruler — the one number the module tells teams to treat as
audit-grade. Nobody changed the ruler; the story was rescored.

The blast radius is not cosmetic: `h_per_bcp_actual` feeds the observed
per-category baseline and `drift_pct` feeds the convergence signal, so a stale
denominator biases the numbers a team calibrates its estimates against.

These are text invariants over the workflow markdown because the dashboard and
track-done math is agent instruction, not a Python compute layer (same approach
as test_reference_leverage.py).
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
TRACK_DONE = REPO_ROOT / "skills/bmad-pulse-track-done/workflow.md"
BACKFILL = REPO_ROOT / "skills/bmad-pulse-track-backfill/workflow.md"
DASHBOARD = REPO_ROOT / "skills/bmad-pulse-dashboard/workflow.md"


def _regime_paragraph() -> str:
    """The reference-regime-break rule, isolated from the rest of the file."""
    text = DASHBOARD.read_text()
    marker = "reference regime break"
    assert marker in text, "dashboard must still define the regime-break check"
    start = text.index(marker)
    return text[start : start + 1600]


# --- the anchor's denominator (dashboard regime break) ----------------------


def test_regime_break_divides_by_final_bcp_not_start_snapshot():
    para = _regime_paragraph()
    assert "estimated_hours_reference / bcp_recorded.total" in para, (
        "the implied reference rate must divide by the story's FINAL BCP; "
        "bcp_at_start yields a rate that was never in force"
    )
    assert "estimated_hours_reference / bcp_at_start.total" not in para


def test_regime_break_keeps_start_snapshot_as_fallback_only():
    """Absence of bcp_recorded is normal for older entries — degrade, do not
    crash, but be explicit that it is a fallback."""
    para = _regime_paragraph()
    low = para.lower()
    assert "fall back" in low and "bcp_at_start.total" in para


def test_rescore_is_labelled_rescore_not_regime_break():
    """The distinction is the whole point: a governance breach and a rescore
    look identical in the arithmetic and demand opposite responses."""
    para = _regime_paragraph()
    assert "rescored" in para.lower(), (
        "when the two totals disagree the story must be labelled as rescored, "
        "not reported as a changed ruler"
    )


# --- the productivity denominator (track-done h/BCP) ------------------------


def test_track_done_resolves_bcp_total_from_final_frontmatter():
    text = TRACK_DONE.read_text()
    idx = text.index("**BCP productivity")
    block = text[idx : idx + 1400]
    assert "frontmatter `bcp.total`" in block, (
        "h/BCP must divide by the final BCP — estimated_hours came from it"
    )
    # The start snapshot may appear only as the fallback, after the primary.
    primary = block.index("frontmatter `bcp.total`")
    fallback = block.index("bcp_at_start.total")
    assert primary < fallback, "final BCP must be resolved before the snapshot"


def test_track_done_explains_why_the_denominator_matters():
    """A bare rule invites a future edit to 'simplify' it back. Pin the reason
    to the downstream damage, not to style."""
    block = TRACK_DONE.read_text()
    idx = block.index("**BCP productivity")
    block = block[idx : idx + 1800]
    low = block.lower()
    assert "baseline" in low and "drift" in low, (
        "the rationale must name what a stale denominator corrupts"
    )


def test_backfill_already_uses_the_final_block():
    """Backfill reads the bcp.* block captured from the frontmatter, so it was
    never exposed to the snapshot bug. Locked so the two paths cannot drift."""
    text = BACKFILL.read_text()
    idx = text.index("**BCP productivity")
    block = text[idx : idx + 400]
    assert "`bcp.*` block" in block
    assert "bcp_at_start" not in block
