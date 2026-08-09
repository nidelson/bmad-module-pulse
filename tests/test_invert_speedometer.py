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
BCP_DOC = REPO_ROOT / "docs/bcp.md"


def test_predictability_score_is_defined_as_hero():
    """The aggregation must define predictability_score and call it the hero."""
    text = DASHBOARD.read_text()
    assert "predictability_score" in text
    assert "hero metric" in text.lower()


def test_predictability_is_median_estimate_error():
    """Hero is computed from the median per-story |actual - estimated| / estimated
    error; median (not mean) to resist outliers, consistent with the v0.5
    geometric choice. It is RENDERED as accuracy (100 - error), not raw error."""
    text = DASHBOARD.read_text()
    assert "|actual_hours - estimated_hours| / estimated_hours" in text
    assert "median" in text.lower()


def test_predictability_rendered_as_accuracy_not_raw_error():
    """The reframe: the hero reads as **accuracy** (higher is better, target
    100%) = max(0, 100 - error), NOT as a raw error % (which mis-signalled — an
    8.5% error reads as 91.5% predictable). The raw margin of error stays
    surfaced for transparency; the persisted data field is still estimate_error_pct."""
    text = DASHBOARD.read_text()
    assert "100 - E" in text or "100 − E" in text, "must define the accuracy transform"
    assert "higher is better" in text.lower()
    assert "target 100%" in text.lower()
    assert "max(0, 100 - estimate_error_pct)" in text, (
        "the per-story detail column must render accuracy, not raw error"
    )
    # the raw error name is preserved as the persisted data field
    assert "estimate_error_pct" in text
    # the headline row must NOT read "% de erro" any more (that was the bug)
    assert "{predictability_score}% de erro" not in text


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
    appear BEFORE the Alavancagem row — leverage is no longer the headline."""
    text = DASHBOARD.read_text()
    pred_idx = text.find("| **Previsibilidade**")
    lev_idx = text.find("| **Alavancagem (vs REFERÊNCIA)**")
    assert pred_idx != -1 and lev_idx != -1, "both rows must be present"
    assert pred_idx < lev_idx, "Predictability must lead; Alavancagem comes after"


def test_leverage_vs_plan_is_not_a_displayed_metric():
    """Concept lock: the vs-PLANO ratio (estimated_hours / actual_hours) collapses
    to ~1.0x = it IS predictability, so it is NOT rendered as a metric row/column.
    'Alavancagem' on the dashboard means the sellable vs-REFERÊNCIA multiplier. The
    vs-PLANO ratio survives only as the anti-Goodhart explanation, never as a number
    the board reads as 'leverage'."""
    text = DASHBOARD.read_text()
    # the Alavancagem metric is the frozen-reference multiplier
    assert "| **Alavancagem (vs REFERÊNCIA)**" in text
    # the old pre-v0.6 headline row must be gone
    assert "| Avg AI Leverage         | {avg}x             |" not in text
    # the vs-PLANO ratio must NOT be a rendered metric row/column
    assert "AI Leverage (vs PLANO," not in text, "vs-PLANO must not be a metric row"
    assert "Leverage (vs PLANO) | Qualidade" not in text, "story column must be Alavancagem"
    # but it MUST remain in the anti-Goodhart note as the explanation
    assert "vs PLANO" in text and "~1.0x por construção" in text


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


def test_bcp_doc_flips_basis_to_read_only():
    """docs/bcp.md must reflect the reversal: estimated_hours_basis is now read
    read-only (not 'ignores'), while estimated_hours_pre_bcp stays ignored and
    the zero-coupling language remains.

    The row wording changed with the port (the owner is a sibling skill, not a
    module), so these assert the two halves separately rather than pinning a
    table row verbatim: the fields must appear, and only `_pre_bcp` may be
    described as ignored.
    """
    text = BCP_DOC.read_text()
    assert "reads it read-only" in text
    basis_row = next(
        line for line in text.splitlines() if line.startswith("| `estimated_hours_basis`")
    )
    assert "ignore" not in basis_row.lower(), (
        f"estimated_hours_basis is read read-only, not ignored: {basis_row}"
    )
    pre_bcp_row = next(
        line for line in text.splitlines() if line.startswith("| `estimated_hours_pre_bcp`")
    )
    assert "ignore" in pre_bcp_row.lower(), (
        f"estimated_hours_pre_bcp must remain ignored: {pre_bcp_row}"
    )
    collapsed = " ".join(text.split())
    assert "coupling stays **zero**" in collapsed or "zero-coupled" in collapsed, (
        "the doc must still state the coupling invariant, whatever its two sides are called"
    )


# --- Phase 4: vs-PLAN labels + inverted celebration -------------------------


def test_estimate_error_pct_computed_in_both_recorders():
    """track-done and track-backfill must compute the per-story estimate error
    (|actual - estimated| / estimated) that drives the inverted celebration."""
    for wf in (TRACK_DONE, TRACK_BACKFILL):
        text = wf.read_text()
        assert "estimate_error_pct = round(abs(actual_hours - estimated_hours)" in text


def test_estimate_error_pct_persisted_in_both_recorders():
    """The per-story predictability signal must be PERSISTED to pulse_metrics,
    not only shown in the card — so previsibilidade is visible per-story (next
    to leverage_ratio, which mis-signals it), not only as the dashboard median.
    leverage_ratio (vs PLAN) is a 1.0-centered ratio; estimate_error_pct is the
    0-centered accuracy (lower is better) that actually reads as predictability."""
    done = TRACK_DONE.read_text()
    backfill = TRACK_BACKFILL.read_text()
    assert "Add the `estimate_error_pct` field" in done, (
        "track-done must persist estimate_error_pct in its pulse_metrics write list"
    )
    assert "estimate_error_pct:" in backfill, (
        "track-backfill's written entry must include estimate_error_pct"
    )


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


# --- #97: the celebration branches on estimation_method ---------------------
# Accuracy only earns a trophy where a canonical ruler makes the estimate
# comparable. On every other path the estimator and the executor are the same
# agent, so celebrating accuracy rewards padding and celebrating leverage
# magnitude rewards inflating — opposite incentives on the same variable. Those
# paths celebrate what is observed instead: first-pass, and a clean HALT count.
#
# These assert the STRUCTURE rather than substrings. Every string checked here
# was already present before the branch existed, so a substring test passes
# whether or not the branch is correct — the shape is the only thing that
# distinguishes the two worlds.


def _celebration_line(path) -> str:
    """The card's celebration line — the one that starts by picking a method."""
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith('{pulse_estimation_method == "bcp" ?')
    ]
    assert len(lines) == 1, (
        f"{path.parent.name}: expected exactly one method-branched celebration, "
        f"found {len(lines)}"
    )
    return lines[0]


def _split_branches(line: str) -> tuple[str, str]:
    """Return (bcp_branch, other_branch) by walking balanced parentheses."""
    body = line[line.index("?") + 1 :].rstrip("}").strip()
    assert body.startswith("("), f"expected a parenthesised bcp branch, got: {body[:40]}"
    depth = 0
    for index, char in enumerate(body):
        depth += (char == "(") - (char == ")")
        if depth == 0:
            bcp = body[1:index]
            rest = body[index + 1 :].lstrip()
            assert rest.startswith(":"), f"expected ':' after the bcp branch, got: {rest[:40]}"
            return bcp, rest[1:].strip().strip("()")
    raise AssertionError(f"unbalanced parentheses in celebration line: {line}")


def test_accuracy_trophy_is_confined_to_the_bcp_path():
    """🎯 On-plan may only appear where a ruler makes on-plan mean something."""
    for card in (TRACK_DONE, TRACK_BACKFILL):
        bcp, other = _split_branches(_celebration_line(card))
        assert "🎯 On-plan" in bcp, f"{card.parent.name}: bcp path lost its accuracy trophy"
        assert "🎯 On-plan" not in other, (
            f"{card.parent.name}: the non-bcp path celebrates estimate accuracy, which "
            f"rewards padding the estimate — the bug #97 exists to fix"
        )


def test_non_bcp_path_never_reads_the_estimate():
    """The whole point: no estimate-derived value may drive that path's outcome."""
    for card in (TRACK_DONE, TRACK_BACKFILL):
        _, other = _split_branches(_celebration_line(card))
        for forbidden in ("estimate_error_pct", "leverage_ratio", "leverage_vs_reference"):
            assert forbidden not in other, (
                f"{card.parent.name}: non-bcp celebration reads {forbidden}; it must "
                f"celebrate observed quality, not anything derived from the estimate"
            )
        assert "first_pass" in other, (
            f"{card.parent.name}: non-bcp celebration must reward the observed signal"
        )


def test_off_plan_warning_is_scoped_to_the_bcp_path():
    """"Review the estimate basis" is advice about a ruler.

    On the hours path the basis is a person's judgement, so the line reads as
    blame for a number nothing could have calibrated.
    """
    for card in (TRACK_DONE, TRACK_BACKFILL):
        bcp, other = _split_branches(_celebration_line(card))
        assert "Off-plan" in bcp, f"{card.parent.name}: bcp path lost the off-plan warning"
        assert "Off-plan" not in other, (
            f"{card.parent.name}: the non-bcp path still warns about the estimate basis"
        )


def test_only_track_done_celebrates_a_clean_halt_count():
    """track-backfill refuses to reconstruct halts, so it cannot claim there were none.

    Celebrating "no HALTs" on a retroactive entry would be a claim about data the
    skill deliberately does not have.
    """
    _, done_other = _split_branches(_celebration_line(TRACK_DONE))
    assert "halt_count == 0" in done_other, (
        "track-done observes halts live and should reward a clean run"
    )
    _, backfill_other = _split_branches(_celebration_line(TRACK_BACKFILL))
    assert "halt_count" not in backfill_other, (
        "track-backfill does not reconstruct halts — it must not celebrate their absence"
    )


def test_leverage_thresholds_marked_legacy():
    """The leverage thresholds stay for back-compat but are flagged legacy —
    they no longer drive any celebration."""
    text = TRACK_DONE.read_text()
    assert "legacy since v0.6" in text


def test_leverage_labeled_vs_plan_in_cards_and_tables():
    """The track-done card still reports both framings per-story (vs PLAN context +
    vs REFERENCE ROI). On the dashboard, the full "(vs REFERÊNCIA)" qualifier is
    DEFINED ONCE in General Statistics; the board-facing tables use the short
    "Alavancagem" label (the reader already saw the definition). The vs-PLANO ratio
    is not a column."""
    done = TRACK_DONE.read_text()
    assert "AI Leverage: {leverage_ratio}x (vs PLAN" in done  # track-done card stays EN
    dash = DASHBOARD.read_text()
    # full qualifier defined once, in General Statistics
    assert "**Alavancagem (vs REFERÊNCIA)**" in dash
    # tables use the short label
    assert "| Alavancagem média | Stories |" in dash  # category table
    assert "| Alavancagem | Qualidade |" in dash       # story detail column
    # the long qualifier must NOT be repeated on the tables
    assert "Alavancagem média (vs REFERÊNCIA)" not in dash
    assert "Alavancagem (vs REFERÊNCIA) | Qualidade" not in dash
