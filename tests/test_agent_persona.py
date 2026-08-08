"""The agent persona is Maxine, and the retirement of Levi is bounded (#84).

Swapping the persona looks like a find-and-replace and is not one. The name
appears in four kinds of place, and only the first should change:

| where                                      | what it is           | rename? |
| ------------------------------------------ | -------------------- | ------- |
| customize.toml, SKILL.md, workflows, README | the live persona     | yes     |
| `pulse_levi_*` config keys                  | consumer-facing API  | yes, with fallback |
| `bmad-pulse-agent-levi/` in cleanup scripts | a legacy folder name | **no**  |
| docs/MIGRATION.md history, CHANGELOG        | the record           | **no**  |

The third row is the trap. Those strings are the *old directory* an upgrading
project still has on disk; rewriting them makes the cleanup silently stop
matching, and the project keeps two divergent entry points for one agent
forever. The tests below pin the boundary in both directions — gone from the
persona surfaces, still present in the migration surfaces.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
SKILLS = REPO_ROOT / "skills"

AGENT_DIR = SKILLS / "bmad-agent-pulse"
CUSTOMIZE = AGENT_DIR / "customize.toml"
AGENT_SKILL = AGENT_DIR / "SKILL.md"
FRAGMENT = SKILLS / "bmad-pulse-setup/assets/agent-manifest-fragment.csv"
MODULE_YAML = SKILLS / "bmad-pulse-setup/assets/module.yaml"

# Everything the user reads or hears the persona through.
PERSONA_SURFACES = [
    AGENT_SKILL,
    FRAGMENT,
    MODULE_YAML,
    SKILLS / "bmad-pulse-dashboard/workflow.md",
    SKILLS / "bmad-pulse-track-start/workflow.md",
    SKILLS / "bmad-pulse-track-done/workflow.md",
    SKILLS / "bmad-pulse-track-backfill/workflow.md",
]

# Where the old name is a fact about the past, not a live reference.
MIGRATION_SURFACES = [
    SKILLS / "bmad-pulse-setup/scripts/cleanup-legacy.py",
    SKILLS / "bmad-pulse-setup/scripts/reconcile-skills.py",
]

LEGACY_FOLDER = "bmad-pulse-agent-levi"

NAME = "Maxine"
TITLE = "Delivery Predictability Analyst"
ICON = "💓"


@pytest.fixture(scope="module")
def agent_block() -> dict:
    return tomllib.loads(CUSTOMIZE.read_text(encoding="utf-8"))["agent"]


# ── the persona is Maxine everywhere the user meets her ──────────────────────


def test_customize_declares_maxine(agent_block: dict):
    assert agent_block["name"] == NAME
    assert agent_block["title"] == TITLE
    assert agent_block["icon"] == ICON


def test_manifest_fragment_agrees_with_customize(agent_block: dict):
    """Party Mode reads the fragment; the skill reads customize.toml. They are
    two files describing one agent, so a swap that updates only one leaves the
    roster listing a name the agent never answers to."""
    row = FRAGMENT.read_text(encoding="utf-8").splitlines()[1]
    assert f'"{NAME}"' in row
    assert f'"{TITLE}"' in row
    assert f'"{ICON}"' in row


def test_no_persona_surface_still_speaks_as_levi():
    """Includes the `⚡ Levi:` output prefixes in the track workflows — the
    line the user actually sees, and the easiest one to miss because it is
    inside fenced example blocks rather than prose."""
    stale = [p.name for p in PERSONA_SURFACES if "Levi" in p.read_text(encoding="utf-8")]
    assert not stale, f"still speaking as Levi: {stale}"


def test_no_customize_value_names_levi(agent_block: dict):
    """customize.toml is checked by *value*, not by raw text: its header
    comment legitimately points at the swap, and that breadcrumb belongs where
    a reader opening the file will hit it. A comment is not speech — a value
    is, so the assertion walks the parsed block instead of grepping."""

    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                yield from walk(v)
        elif isinstance(node, list):
            for v in node:
                yield from walk(v)
        elif isinstance(node, str):
            yield node

    offenders = [v for v in walk(agent_block) if "Levi" in v]
    assert not offenders, f"live customize.toml values still name Levi: {offenders}"


def test_principles_carry_the_measure_the_system_rule(agent_block: dict):
    """The first principle is load-bearing, not decorative: a delivery metric
    is the artifact most easily turned into a stick, and a team measured to be
    punished learns to lie to the metric — which corrupts the data the rest of
    the module depends on."""
    joined = " ".join(agent_block["principles"]).lower()
    assert "measure the system, never the person" in joined
    assert "two denominators" in joined


# ── the retirement does not reach into the migration path ────────────────────


def test_legacy_folder_name_survives_in_the_cleanup_scripts():
    """The counterweight to the test above. `bmad-pulse-agent-levi` is a path
    that still exists on upgrading installs; the cleanup only finds it by
    literal name."""
    for path in MIGRATION_SURFACES:
        assert LEGACY_FOLDER in path.read_text(encoding="utf-8"), (
            f"{path.name} lost the legacy folder name — upgrading projects "
            f"would keep two entry points for one agent"
        )


def test_migration_doc_explains_the_swap():
    doc = (REPO_ROOT / "docs/MIGRATION.md").read_text(encoding="utf-8")
    assert "Maxine" in doc
    assert "pulse_levi_verbosity" in doc, (
        "the renamed config keys must be named in the migration doc — a "
        "consumer greps for the key they have, not the one they should have"
    )


# ── config keys stop carrying a persona name ─────────────────────────────────


def test_config_keys_are_persona_free():
    """`pulse_levi_verbosity` is why a cosmetic swap was a breaking change: a
    consumer-facing key named after the persona couples the two. The keys are
    renamed so the next persona costs nothing."""
    text = MODULE_YAML.read_text(encoding="utf-8")
    assert "pulse_verbosity:" in text
    assert "pulse_coaching_mode:" in text
    assert not re.search(r"^pulse_levi_\w+:", text, re.MULTILINE), (
        "module.yaml still declares a pulse_levi_* key"
    )


@pytest.mark.parametrize(
    "workflow",
    [
        "bmad-pulse-dashboard",
        "bmad-pulse-track-done",
        "bmad-pulse-track-backfill",
    ],
)
def test_workflows_fall_back_to_the_legacy_key(workflow: str):
    """Renaming without a fallback would silently revert every upgrading
    project to the default verbosity — the setting stays in their config file,
    unread, so nothing looks broken and the behaviour just changes."""
    text = (SKILLS / workflow / "workflow.md").read_text(encoding="utf-8")
    assert "pulse_verbosity" in text
    assert "pulse_levi_verbosity" in text, (
        f"{workflow} reads the new key but never falls back to the legacy one"
    )
