"""Invariant tests for the bmad-pulse-track-backfill skill.

Issue #41: PULSE can retroactively reconstruct a `pulse_metrics:` entry for a
story whose track-start/track-done were never invoked (early-adoption stories,
workflow interruptions), marking it `retroactive: true` for traceability.

These are meta/invariant tests in the same spirit as
``test_bcp_integration.py`` — they pin the provenance and loose-coupling
contract in the workflow markdown so a future edit cannot silently let
backfill masquerade reconstructed data as real-time data, or start writing
the story frontmatter / BCP baseline.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import tomlkit
import yaml

REPO_ROOT = Path(__file__).parents[1]
SKILL_DIR = REPO_ROOT / "skills/bmad-pulse-track-backfill"
SKILL_MD = SKILL_DIR / "SKILL.md"
WORKFLOW = SKILL_DIR / "workflow.md"
CUSTOMIZE = SKILL_DIR / "customize.toml"
MARKETPLACE = REPO_ROOT / ".claude-plugin/marketplace.json"
MODULE_HELP = REPO_ROOT / "skills/bmad-pulse-setup/assets/module-help.csv"
AGENT_CUSTOMIZE = REPO_ROOT / "skills/bmad-agent-pulse/customize.toml"
AGENT_SKILL = REPO_ROOT / "skills/bmad-agent-pulse/SKILL.md"
DOCS_INDEX = REPO_ROOT / "docs/index.md"


def _frontmatter(path: Path) -> dict:
    parts = path.read_text().split("---", 2)
    return yaml.safe_load(parts[1]) if len(parts) >= 3 else {}


def test_skill_folder_and_frontmatter_name():
    assert SKILL_MD.exists(), "skills/bmad-pulse-track-backfill/SKILL.md must exist"
    assert WORKFLOW.exists(), "workflow.md must exist"
    for path in (SKILL_MD, WORKFLOW):
        assert _frontmatter(path)["name"] == "bmad-pulse-track-backfill"


def test_workflow_accepts_hi_hf_arguments():
    """The skill's whole purpose: take --hi / --hf and a story id."""
    text = WORKFLOW.read_text()
    assert "--hi" in text and "--hf" in text
    assert "story_id" in text


def test_actual_hours_derived_from_hi_hf():
    """actual_hours must be reconstructed from the HI/HF span, not invented."""
    text = WORKFLOW.read_text()
    assert "elapsed_minutes = (HF - HI)" in text
    assert "actual_hours" in text and "leverage_ratio  = estimated_hours / actual_hours" in text


def test_retroactive_flag_is_mandatory():
    """retroactive: true is the provenance marker — it must be asserted as
    mandatory and non-negotiable, so reconstructed data is never disguised
    as real-time measurement."""
    text = WORKFLOW.read_text()
    assert "retroactive: true" in text
    assert "retroactive_note" in text
    assert "mandatory and non-negotiable" in text
    # Must NOT fabricate process_health (halts/flow are live-only signal).
    assert "Never reconstruct `process_health`" in text


def test_pulse_never_writes_story_frontmatter_or_baseline():
    """Loose-coupling contract identical to track-start/track-done: read-only
    on story frontmatter, never the BCP baseline."""
    text = WORKFLOW.read_text()
    assert "baseline" in text.lower()
    assert "read-only" in text.lower() or "DO NOT write" in text
    assert "DO NOT modify anything outside the `pulse_metrics:` section" in text


def test_workflow_documents_canonical_mapping_shape():
    """Issue #41 illustrated a list shape; PULSE canonically stores
    pulse_metrics as a mapping keyed by story id. The deviation must be
    documented so the entry stays readable by every other PULSE skill."""
    text = WORKFLOW.read_text()
    assert "mapping keyed by story id" in text


def test_customize_toml_surface():
    data = tomlkit.loads(CUSTOMIZE.read_text())
    assert "DO NOT EDIT" in CUSTOMIZE.read_text().splitlines()[0].upper()
    wf = data["workflow"]
    for key in ("activation_steps_prepend", "activation_steps_append", "persistent_facts"):
        assert isinstance(wf[key], list), f"{key} must be a list"
    assert isinstance(wf["on_complete"], str)


def test_marketplace_lists_backfill_skill():
    data = json.loads(MARKETPLACE.read_text())
    skills = data["plugins"][0]["skills"]
    assert "./skills/bmad-pulse-track-backfill" in skills
    assert SKILL_DIR.is_dir()


def test_module_help_registers_backfill():
    rows = list(csv.DictReader(MODULE_HELP.read_text().splitlines()))
    backfill = [r for r in rows if r["skill"] == "bmad-pulse-track-backfill"]
    assert len(backfill) == 1, "module-help.csv must register bmad-pulse-track-backfill exactly once"
    assert backfill[0]["menu-code"] == "TB"


def test_agent_menu_exposes_backfill():
    data = tomlkit.loads(AGENT_CUSTOMIZE.read_text())
    skills = [m.get("skill") for m in data["agent"]["menu"]]
    assert "bmad-pulse-track-backfill" in skills
    assert "bmad-pulse-track-backfill" in AGENT_SKILL.read_text()


def test_docs_index_documents_backfill():
    text = DOCS_INDEX.read_text()
    assert "bmad-pulse-track-backfill" in text
    assert "retroactive" in text
