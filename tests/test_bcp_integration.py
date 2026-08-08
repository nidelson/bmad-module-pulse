"""Invariant tests for the BCP (Business Complexity Points) integration.

Issue #30: PULSE accepts `pulse_estimation_method=bcp` and surfaces BCP
telemetry while staying passive toward the scoring side. Since #84 that side is
the sibling `bmad-bcp-*` skills in this same module rather than a separate one —
the boundary is now internal, and these tests are what keep it a boundary.

These are meta/invariant tests in the same spirit as
``test_cross_file_invariants.py`` — they pin the loose-coupling contract in
the workflow markdown so a future edit cannot silently make PULSE compute
hours from BCP or write the BCP baseline.
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[1]
MODULE_YAML = REPO_ROOT / "skills/bmad-pulse-setup/assets/module.yaml"
TRACK_START = REPO_ROOT / "skills/bmad-pulse-track-start/workflow.md"
TRACK_DONE = REPO_ROOT / "skills/bmad-pulse-track-done/workflow.md"
DASHBOARD = REPO_ROOT / "skills/bmad-pulse-dashboard/workflow.md"
SETUP_SKILL = REPO_ROOT / "skills/bmad-pulse-setup/SKILL.md"
BCP_DOC = REPO_ROOT / "docs/bcp.md"

EXPECTED_METHODS = {"hours", "story_points", "tshirt", "bcp"}


def test_module_yaml_offers_exactly_four_estimation_methods():
    """module.yaml pins the supported estimation methods. `bcp` is the 4th;
    the set must stay exactly these four so docs/tests/workflows agree."""
    data = yaml.safe_load(MODULE_YAML.read_text())
    entry = data["pulse_estimation_method"]
    values = {opt["value"] for opt in entry["single-select"]}
    assert values == EXPECTED_METHODS, (
        f"pulse_estimation_method values {sorted(values)} != "
        f"expected {sorted(EXPECTED_METHODS)}"
    )
    assert entry["default"] == "hours", "bcp must be opt-in, not the default"


def test_bcp_label_says_where_the_hours_come_from():
    """The bcp option label must say what produces `estimated_hours`.

    It used to assert the label named `bmad-module-bcp`, because the hours were
    computed by a separate module PULSE had to be told about. Issue #84 moved
    the scoring skills into this module, so naming an external one is now a
    wrong install instruction — a user reading it would go looking for something
    they do not need. The label must still explain the derivation; what changed
    is who does it.
    """
    data = yaml.safe_load(MODULE_YAML.read_text())
    label = next(
        opt["label"]
        for opt in data["pulse_estimation_method"]["single-select"]
        if opt["value"] == "bcp"
    )
    assert "estimated_hours" in label
    assert "bmad-bcp-" in label, "label must point at the skills that do the scoring"
    assert "bmad-module-bcp" not in label, (
        "the standalone module is deprecated; the label must not send users to install it"
    )


def test_track_done_config_doc_lists_bcp():
    """The track-done config-loading line enumerates the methods; bcp must be
    listed so the workflow's own documentation matches module.yaml."""
    text = TRACK_DONE.read_text()
    assert "story_points / hours / t-shirt / bcp" in text, (
        "track-done config line must enumerate bcp alongside the other methods"
    )


def test_track_done_consumes_estimated_hours_as_is_for_bcp():
    """PULSE must NOT convert BCP points to hours — the bcp branch reads
    estimated_hours directly, identical to the hours branch."""
    text = TRACK_DONE.read_text()
    assert "If `pulse_estimation_method` is `bcp`:" in text
    # The bcp branch must explicitly disclaim hour computation.
    assert "does NOT" in text and "compute hours from BCP" in text


def test_track_start_snapshots_bcp_at_start():
    text = TRACK_START.read_text()
    assert "bcp_at_start" in text
    assert "estimation_basis: bcp" in text
    # Unknown schema_version must be tolerated, not crash.
    assert "schema_version" in text


def test_track_done_records_bcp_recorded():
    text = TRACK_DONE.read_text()
    assert "bcp_recorded" in text
    for field in ("h_per_bcp_actual", "h_per_bcp_estimated", "drift_pct"):
        assert field in text, f"track-done must record {field}"


def test_dashboard_bcp_section_is_conditional():
    """The BCP Productivity section must be gated on bcp_recorded existing —
    stories without BCP must not trigger it."""
    text = DASHBOARD.read_text()
    assert "📊 Produtividade BCP" in text
    assert "CONDITIONAL" in text and "bcp_recorded" in text


def test_pulse_never_writes_story_frontmatter_or_baseline():
    """Loose-coupling contract: every workflow that touches bcp.* must state
    it is read-only and never writes the BCP baseline."""
    for wf in (TRACK_START, TRACK_DONE):
        text = wf.read_text()
        assert "baseline" in text.lower(), f"{wf.name} must mention baseline boundary"
        assert "read-only" in text.lower() or "DO NOT write" in text, (
            f"{wf.name} must assert read-only handling of bcp.*"
        )


def test_setup_skill_waives_factor_for_bcp():
    """bcp must not require pulse_story_point_hours_factor."""
    text = SETUP_SKILL.read_text()
    assert "pulse_estimation_method` = `bcp`" in text
    assert "not** require `pulse_story_point_hours_factor`" in text


def test_bcp_doc_exists_and_states_the_internal_boundary():
    """The boundary survived the port; only its two sides changed name. It is
    now between sibling skills in one module, so the doc must still spell out
    what tracking may not do — and must no longer send the reader to a module."""
    assert BCP_DOC.exists(), "docs/bcp.md must exist"
    text = " ".join(BCP_DOC.read_text().split())  # prose wraps; assert on content
    assert "never convert BCP to hours" in text or "never converts BCP→hours" in text
    assert "never read or write the baseline" in text
    assert "apply_score.py" in text, "the single-writer rule must name its writer"
    assert "companion module" not in text, (
        "the companion-module framing is dead — scoring ships in this module"
    )


# --- Opt-in lock -----------------------------------------------------------
# BCP is opt-in permanently: `hours` is the default and turning BCP on is always
# an explicit user action, never a consequence of install, upgrade, or a prompt
# whose comfortable answer is "yes". Without BCP, PULSE is the baseline product
# rather than a degraded mode. These tests keep that a guarantee instead of a
# convention — the port is exactly where it would be broken by accident.


def test_default_estimation_method_is_hours():
    data = yaml.safe_load(MODULE_YAML.read_text())
    assert data["pulse_estimation_method"]["default"] == "hours", (
        "BCP must never become the default — turning it on is the user's call"
    )


def test_bcp_is_offered_as_a_choice_never_preselected():
    """Discoverability is allowed; pressure is not.

    `bcp` must be present in the option list (a user cannot choose what they
    cannot see) yet never be the value a user gets by pressing enter.
    """
    data = yaml.safe_load(MODULE_YAML.read_text())
    field = data["pulse_estimation_method"]
    values = [opt["value"] for opt in field["single-select"]]
    assert "bcp" in values
    assert field["default"] != "bcp"


def test_dashboard_treats_missing_bcp_as_normal_not_as_a_warning():
    """A project with no BCP data must render a complete dashboard.

    No BCP section, and no notice about its absence — nothing should imply the
    project is incorrectly configured.
    """
    text = DASHBOARD.read_text()
    assert "all optional — a story without them is normal" in text, (
        "dashboard must state that absent BCP telemetry is the normal case"
    )
    assert "contributes nothing" in text
