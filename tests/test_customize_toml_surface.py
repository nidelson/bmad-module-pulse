"""Structural tests for the customize.toml override surface shipped by
every PULSE skill.

These tests pin the contract introduced in v0.4.5 (#31): every skill ships
a customize.toml that mirrors the bmm namespace surface plus the
PULSE-specific extensions defined per skill. They catch the class of
regression where an override key is silently removed or renamed,
breaking customer workflows that depend on it.

We do NOT invoke BMAD core's resolve_customization.py here — that script
lives in the consumer project and validates its own merge semantics.
What we validate is that PULSE ships the right keys, with the right
shapes, in the right files.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import tomlkit

REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "skills"


# Skills that ship a customize.toml under the [workflow] namespace.
WORKFLOW_SKILLS = [
    "bmad-pulse-setup",
    "bmad-pulse-track-start",
    "bmad-pulse-track-done",
    "bmad-pulse-dashboard",
]

# Skills that ship a customize.toml under the [agent] namespace.
AGENT_SKILLS = [
    "bmad-agent-pulse",
]

# Required workflow keys per bmm parity. Setup is the minimal exception:
# it does not need on_complete because setup is a one-shot install.
WORKFLOW_REQUIRED_KEYS = {
    "activation_steps_prepend",
    "activation_steps_append",
    "persistent_facts",
}

# Required agent keys per bmm parity.
AGENT_REQUIRED_KEYS = {
    "name",
    "title",
    "icon",
    "activation_steps_prepend",
    "activation_steps_append",
    "persistent_facts",
    "role",
    "identity",
    "communication_style",
    "principles",
    "menu",
}


def _load(skill: str) -> dict:
    path = SKILLS_DIR / skill / "customize.toml"
    assert path.exists(), f"customize.toml missing for skill {skill!r} at {path}"
    return tomlkit.loads(path.read_text())


@pytest.mark.parametrize("skill", WORKFLOW_SKILLS + AGENT_SKILLS)
def test_every_pulse_skill_ships_customize_toml(skill: str):
    """Every PULSE skill must ship a customize.toml — closes the gap
    documented in #31 where PULSE diverged from bmm convention."""
    path = SKILLS_DIR / skill / "customize.toml"
    assert path.exists(), (
        f"Missing customize.toml for {skill!r}. Per #31, every PULSE skill "
        f"must ship the override surface for parity with bmm."
    )


@pytest.mark.parametrize("skill", WORKFLOW_SKILLS)
def test_workflow_customize_has_required_keys(skill: str):
    """Workflow skills must declare the bmm-parity [workflow] surface."""
    data = _load(skill)
    assert "workflow" in data, f"{skill}/customize.toml missing [workflow] section"
    workflow = data["workflow"]
    missing = WORKFLOW_REQUIRED_KEYS - workflow.keys()
    assert not missing, (
        f"{skill}/customize.toml [workflow] missing required keys: {missing}. "
        f"Required surface: {sorted(WORKFLOW_REQUIRED_KEYS)}"
    )


@pytest.mark.parametrize("skill", AGENT_SKILLS)
def test_agent_customize_has_required_keys(skill: str):
    """Agent skills must declare the bmm-parity [agent] surface."""
    data = _load(skill)
    assert "agent" in data, f"{skill}/customize.toml missing [agent] section"
    agent = data["agent"]
    missing = AGENT_REQUIRED_KEYS - agent.keys()
    assert not missing, (
        f"{skill}/customize.toml [agent] missing required keys: {missing}. "
        f"Required surface: {sorted(AGENT_REQUIRED_KEYS)}"
    )


@pytest.mark.parametrize(
    "skill,array_key",
    [
        ("bmad-pulse-setup", "activation_steps_prepend"),
        ("bmad-pulse-setup", "activation_steps_append"),
        ("bmad-pulse-setup", "persistent_facts"),
        ("bmad-pulse-track-start", "activation_steps_prepend"),
        ("bmad-pulse-track-start", "activation_steps_append"),
        ("bmad-pulse-track-start", "persistent_facts"),
        ("bmad-pulse-track-done", "activation_steps_prepend"),
        ("bmad-pulse-track-done", "activation_steps_append"),
        ("bmad-pulse-track-done", "persistent_facts"),
        ("bmad-pulse-dashboard", "activation_steps_prepend"),
        ("bmad-pulse-dashboard", "activation_steps_append"),
        ("bmad-pulse-dashboard", "persistent_facts"),
    ],
)
def test_workflow_arrays_are_arrays(skill: str, array_key: str):
    """bmm parity: every workflow array must be a TOML array, not a scalar,
    so the resolver can append overrides without type errors."""
    data = _load(skill)
    value = data["workflow"][array_key]
    assert isinstance(value, list), (
        f"{skill}/customize.toml [workflow].{array_key} must be a list, "
        f"got {type(value).__name__}"
    )


@pytest.mark.parametrize("skill", ["bmad-pulse-track-start", "bmad-pulse-track-done", "bmad-pulse-dashboard"])
def test_workflow_on_complete_is_scalar_string(skill: str):
    """on_complete is the terminal hook — must be a string scalar so
    override semantics (override wins) work. Setup is exempt: it is a
    one-shot install and intentionally omits on_complete."""
    data = _load(skill)
    on_complete = data["workflow"].get("on_complete")
    assert on_complete is not None, f"{skill}/customize.toml missing on_complete"
    assert isinstance(on_complete, str), (
        f"{skill}/customize.toml [workflow].on_complete must be a string, "
        f"got {type(on_complete).__name__}"
    )


def test_setup_customize_does_not_ship_on_complete():
    """Setup is a one-shot install — on_complete has no meaningful semantics
    and is intentionally omitted to avoid implying a hook point exists."""
    data = _load("bmad-pulse-setup")
    assert "on_complete" not in data["workflow"], (
        "bmad-pulse-setup/customize.toml should NOT declare on_complete — "
        "setup is one-shot, see #31 spec."
    )


def test_agent_pulse_celebration_threshold_override_present():
    """PULSE-specific scalar on the Levi agent: celebration_threshold_override.
    Empty string is the default — non-empty overrides
    pulse_leverage_threshold_exceptional at runtime."""
    data = _load("bmad-agent-pulse")
    agent = data["agent"]
    assert "celebration_threshold_override" in agent, (
        "bmad-agent-pulse/customize.toml [agent] missing "
        "celebration_threshold_override scalar (PULSE-specific)."
    )
    assert isinstance(agent["celebration_threshold_override"], str), (
        "celebration_threshold_override must be a string scalar so override "
        "semantics work; got "
        f"{type(agent['celebration_threshold_override']).__name__}"
    )


def test_agent_pulse_menu_uses_array_of_tables():
    """Agent menu must be an array of tables so the resolver can merge by
    `code`. A flat array breaks the merge-by-code contract."""
    data = _load("bmad-agent-pulse")
    menu = data["agent"]["menu"]
    assert isinstance(menu, list), "menu must be a list"
    assert menu, "menu must ship at least one default capability"
    for item in menu:
        assert isinstance(item, dict), f"menu item {item!r} must be a table"
        assert "code" in item, f"menu item {item!r} missing required `code` key"


def test_agent_pulse_menu_codes_are_unique():
    """Duplicate codes would corrupt merge-by-code semantics."""
    data = _load("bmad-agent-pulse")
    codes = [item["code"] for item in data["agent"]["menu"]]
    assert len(codes) == len(set(codes)), (
        f"Duplicate codes in bmad-agent-pulse menu: {codes}"
    )


def test_agent_pulse_menu_skills_resolve():
    """Every `skill` entry in the menu must resolve to a real PULSE skill."""
    data = _load("bmad-agent-pulse")
    menu_skills = [item["skill"] for item in data["agent"]["menu"] if "skill" in item]
    real_skills = {p.name for p in SKILLS_DIR.glob("*") if (p / "SKILL.md").exists()}
    for skill_ref in menu_skills:
        assert skill_ref in real_skills, (
            f"bmad-agent-pulse menu references {skill_ref!r} but no such "
            f"skill folder exists. Available: {sorted(real_skills)}"
        )


def test_track_done_ships_halt_categories_extra():
    """PULSE-specific append array on track-done: halt_categories_extra
    must exist as an empty array by default."""
    data = _load("bmad-pulse-track-done")
    halts = data["workflow"].get("halt_categories_extra")
    assert halts is not None, (
        "bmad-pulse-track-done/customize.toml [workflow] missing "
        "halt_categories_extra (PULSE-specific append array)."
    )
    assert isinstance(halts, list), (
        f"halt_categories_extra must be a list, got {type(halts).__name__}"
    )


def test_track_done_ships_metric_post_hooks():
    """PULSE-specific append array on track-done: metric_post_hooks
    must exist as an empty array by default."""
    data = _load("bmad-pulse-track-done")
    hooks = data["workflow"].get("metric_post_hooks")
    assert hooks is not None, (
        "bmad-pulse-track-done/customize.toml [workflow] missing "
        "metric_post_hooks (PULSE-specific append array)."
    )
    assert isinstance(hooks, list), (
        f"metric_post_hooks must be a list, got {type(hooks).__name__}"
    )


def test_dashboard_ships_extra_sections():
    """PULSE-specific append array on dashboard: extra_sections
    must exist as an empty array by default."""
    data = _load("bmad-pulse-dashboard")
    sections = data["workflow"].get("extra_sections")
    assert sections is not None, (
        "bmad-pulse-dashboard/customize.toml [workflow] missing "
        "extra_sections (PULSE-specific append array)."
    )
    assert isinstance(sections, list), (
        f"extra_sections must be a list, got {type(sections).__name__}"
    )


@pytest.mark.parametrize("skill", WORKFLOW_SKILLS + AGENT_SKILLS)
def test_customize_starts_with_do_not_edit_header(skill: str):
    """Every customize.toml must start with the bmm canonical header so
    automated tooling can detect the file class and operators understand
    that overrides go in _bmad/custom/, not here."""
    path = SKILLS_DIR / skill / "customize.toml"
    first_line = path.read_text().splitlines()[0]
    assert "DO NOT EDIT" in first_line.upper(), (
        f"{skill}/customize.toml must start with the bmm canonical header "
        f"'# DO NOT EDIT -- overwritten on every update.', got: {first_line!r}"
    )
