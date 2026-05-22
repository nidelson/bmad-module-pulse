"""Regression tests for issue #47: PULSE auto-tracking trigger wiring.

`track-start` failed to fire automatically because its trigger lived in the
`persistent_facts` array of the `bmad-dev-story` override — passive context
the BMAD agent merely carries, not an executed step. `track-done`, wired in
`on_complete` (an active hook), worked fine.

These tests pin the asymmetry fix: the track-start trigger must live in an
*executed* customize array (`activation_steps_*`), never only in
`persistent_facts`; track-done must stay on the active `on_complete` hook.
"""
from __future__ import annotations

from pathlib import Path

import tomlkit

REPO_ROOT = Path(__file__).parents[1]
TEMPLATES = REPO_ROOT / "skills/bmad-pulse-setup/assets/customize-templates"
DEV_STORY_TMPL = TEMPLATES / "bmad-dev-story.toml"
CODE_REVIEW_TMPL = TEMPLATES / "bmad-code-review.toml"
TRACK_START_WF = REPO_ROOT / "skills/bmad-pulse-track-start/workflow.md"


def _workflow(path: Path) -> dict:
    return tomlkit.loads(path.read_text())["workflow"]


def test_track_start_trigger_is_an_executed_activation_step():
    """The track-start trigger must live in activation_steps_append /
    _prepend — arrays the BMAD agent EXECUTES — so it fires deterministically."""
    wf = _workflow(DEV_STORY_TMPL)
    steps = list(wf.get("activation_steps_append", [])) + list(
        wf.get("activation_steps_prepend", [])
    )
    assert any("bmad-pulse-track-start" in s for s in steps), (
        "bmad-dev-story.toml must invoke bmad-pulse-track-start from an "
        "activation_steps_* array (executed), not from passive context."
    )


def test_track_start_trigger_not_in_passive_persistent_facts():
    """Passive `persistent_facts` is the bug from #47 — the track-start
    trigger must not regress back into it."""
    wf = _workflow(DEV_STORY_TMPL)
    facts = wf.get("persistent_facts", [])
    assert not any("bmad-pulse-track-start" in str(f) for f in facts), (
        "bmad-dev-story.toml persistent_facts must NOT carry the track-start "
        "trigger — persistent_facts is passive context, it does not execute "
        "(issue #47)."
    )


def test_track_start_trigger_decoupled_from_in_progress_status():
    """The trigger must resolve the story from the story file/path, not from
    the sprint-status `in-progress` field (the story may still be ready-for-dev)."""
    wf = _workflow(DEV_STORY_TMPL)
    steps = " ".join(wf.get("activation_steps_append", []))
    assert "in-progress" in steps and "NOT" in steps, (
        "the track-start trigger must explicitly state it does NOT depend on "
        "the sprint-status in-progress field"
    )


def test_track_done_stays_on_active_on_complete_hook():
    """track-done was never broken — pin that it stays on the active
    on_complete hook so a future edit cannot make it passive too."""
    wf = _workflow(CODE_REVIEW_TMPL)
    on_complete = wf.get("on_complete", "")
    assert "bmad-pulse-track-done" in on_complete, (
        "bmad-code-review.toml must invoke bmad-pulse-track-done from on_complete"
    )


def test_track_start_skill_does_not_hard_exit_without_in_progress_story():
    """track-start Step 1 must not silently exit when no story is in-progress —
    it should prefer an explicit story id and otherwise ask the user."""
    text = TRACK_START_WF.read_text()
    assert "inform and exit" not in text, (
        "track-start Step 1 must not silently 'inform and exit' on a missing "
        "in-progress story — that dead-ends the auto-tracking path (issue #47)."
    )
    assert "ready-for-dev" in text, (
        "track-start Step 1 should acknowledge a story may still be "
        "`ready-for-dev` when track-start fires."
    )
