"""Invariants for the opt-in auto-dashboard trigger (#51).

The contract: `bmad-pulse-track-done` ships a default `on_complete` hook
that reads `pulse_auto_dashboard` from the loaded pulse config and, when
`yes`, invokes `/bmad-pulse-dashboard` to regenerate the cumulative
dashboard after the Efficiency Pulse card is shown. When the flag is
`no`, missing, empty, or any other value, the hook is a silent no-op —
preserving the pre-flag behavior of v0.4.10 and earlier.

These tests pin:

1. The config flag `pulse_auto_dashboard` is declared in module.yaml
   with the documented default `no`, a yes/no single-select, and a
   prompt that flags the merge-conflict trade-off so the installer
   surfaces it before the user picks `yes`.
2. The default `on_complete` for `bmad-pulse-track-done` references
   the flag, invokes the dashboard skill, and documents the silent
   no-op semantics.
3. The pre-flag default (`on_complete = ""`) is replaced — the file
   no longer ships the empty scalar that would skip the auto-trigger
   entirely.

A future change that drops the flag or breaks the conditional
semantics — flipping the default to `yes`, hard-coding the dashboard
invocation regardless of config, or moving the trigger to a passive
field like `persistent_facts` (cf. the v0.4.10 fix in #47) — must
fail this file.
"""
from __future__ import annotations

from pathlib import Path

import tomlkit
import yaml

REPO_ROOT = Path(__file__).parent.parent
MODULE_YAML = REPO_ROOT / "skills/bmad-pulse-setup/assets/module.yaml"
TRACK_DONE_TOML = REPO_ROOT / "skills/bmad-pulse-track-done/customize.toml"
TRACK_DONE_WORKFLOW = REPO_ROOT / "skills/bmad-pulse-track-done/workflow.md"


def _load_module_yaml() -> dict:
    return yaml.safe_load(MODULE_YAML.read_text())


def _load_track_done_workflow_block() -> dict:
    return tomlkit.loads(TRACK_DONE_TOML.read_text())["workflow"]


# --- module.yaml flag declaration ---------------------------------------


def test_pulse_auto_dashboard_declared_in_module_yaml():
    """The flag must be a top-level key in module.yaml so the BMAD
    installer surfaces it during /bmad-pulse-setup."""
    cfg = _load_module_yaml()
    assert "pulse_auto_dashboard" in cfg, (
        "module.yaml must declare pulse_auto_dashboard so the installer "
        "prompts the user during setup. See README 'Auto-dashboard'."
    )


def test_pulse_auto_dashboard_default_is_no():
    """Default MUST be `no` for backward compatibility. Flipping the
    default to `yes` would silently re-introduce merge conflicts on
    upgrade for any team with parallel PRs."""
    cfg = _load_module_yaml()
    entry = cfg["pulse_auto_dashboard"]
    assert entry["default"] == "no", (
        f"pulse_auto_dashboard default must be 'no' (got {entry['default']!r}) — "
        f"opt-in is load-bearing because auto-regen guarantees merge conflicts "
        f"in parallel-PR workflows; see README 'Auto-dashboard'."
    )


def test_pulse_auto_dashboard_is_yes_no_single_select():
    """Exactly two options, `yes` and `no`. A free-form text input or
    a third value (e.g. `ci-only`) is out of scope for this flag — the
    semantics are binary and CI-driven workflows belong in mitigation
    strategy #2 in the README."""
    cfg = _load_module_yaml()
    entry = cfg["pulse_auto_dashboard"]
    assert "single-select" in entry, (
        "pulse_auto_dashboard must be a single-select so the installer "
        "surfaces the trade-off explicitly. Free-form input is rejected."
    )
    values = {opt["value"] for opt in entry["single-select"]}
    assert values == {"yes", "no"}, (
        f"pulse_auto_dashboard options must be exactly {{'yes','no'}} "
        f"(got {values}). Binary semantics — third-state behaviors belong "
        f"in CI strategies (README strategy #2), not in this flag."
    )


def test_pulse_auto_dashboard_prompt_surfaces_merge_conflict_warning():
    """The installer prompt MUST warn about merge conflicts before the
    user picks `yes`. The README documents three mitigations; the prompt
    is the early-warning surface that funnels the user there."""
    cfg = _load_module_yaml()
    prompt = cfg["pulse_auto_dashboard"]["prompt"].lower()
    assert "conflict" in prompt or "merge" in prompt, (
        "pulse_auto_dashboard prompt must mention merge conflicts so the "
        "user is warned at install time. README documents three "
        "mitigation strategies; the prompt is the funnel."
    )


# --- track-done on_complete default --------------------------------------


def test_track_done_on_complete_is_non_empty():
    """The shipped default must be a real instruction string, not the
    empty scalar. Empty would mean the auto-dashboard feature is
    unreachable without a user override — defeats opt-in semantics."""
    wf = _load_track_done_workflow_block()
    assert isinstance(wf.get("on_complete"), str), (
        "bmad-pulse-track-done customize.toml must declare on_complete as a string."
    )
    assert wf["on_complete"].strip(), (
        "bmad-pulse-track-done on_complete must ship a non-empty default. "
        "Empty default makes auto-dashboard unreachable without user override; "
        "see issue #51 for the opt-in semantics."
    )


def test_track_done_on_complete_references_flag():
    """The default must read `pulse_auto_dashboard` — that's how the
    conditional behavior is gated."""
    wf = _load_track_done_workflow_block()
    assert "pulse_auto_dashboard" in wf["on_complete"], (
        "bmad-pulse-track-done on_complete must reference pulse_auto_dashboard "
        "so the conditional semantics are wired to the config flag."
    )


def test_track_done_on_complete_invokes_dashboard_skill():
    """The default must call out the dashboard skill explicitly so the
    BMAD agent knows what to invoke when the flag is on."""
    wf = _load_track_done_workflow_block()
    assert "bmad-pulse-dashboard" in wf["on_complete"], (
        "bmad-pulse-track-done on_complete must invoke the bmad-pulse-dashboard "
        "skill when the flag is on."
    )


def test_track_done_on_complete_documents_silent_no_op():
    """When the flag is `no`, missing, or any other value, the default
    behavior must be a silent no-op. This is what guarantees backward
    compatibility — without this, a non-empty default would inevitably
    change behavior on upgrade for projects that never opt in."""
    wf = _load_track_done_workflow_block()
    body = wf["on_complete"].lower()
    assert "silent" in body or "no-op" in body or "do not" in body, (
        "bmad-pulse-track-done on_complete must document the silent no-op "
        "branch (when the flag is no/missing/other). Without this, the "
        "non-empty default risks behavior change on upgrade for projects "
        "that never opt in."
    )


# --- workflow.md documentation -------------------------------------------


def test_workflow_md_documents_auto_dashboard_default():
    """The workflow doc's 'On Completion' section must reference the
    new opt-in default so a reader of workflow.md understands what the
    shipped default actually does — not just the override mechanic."""
    body = TRACK_DONE_WORKFLOW.read_text()
    assert "pulse_auto_dashboard" in body, (
        "workflow.md must mention pulse_auto_dashboard in the On Completion "
        "section so the reader knows what the shipped default does."
    )
