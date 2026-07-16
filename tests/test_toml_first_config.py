"""Issue #73: every PULSE config consumer must resolve toml-first.

The consumers are markdown workflows/agents (the LLM reads config), so these
are structural assertions over their prose: each must invoke the BMAD core
``resolve_config.py`` for ``modules.pulse``, and document the per-key yaml
fallback and the default-last precedence.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]

CONSUMERS = [
    "skills/bmad-pulse-track-start/workflow.md",
    "skills/bmad-pulse-track-done/workflow.md",
    "skills/bmad-pulse-track-backfill/workflow.md",
    "skills/bmad-pulse-dashboard/workflow.md",
    "skills/bmad-agent-pulse/SKILL.md",
]


@pytest.mark.parametrize("rel", CONSUMERS)
def test_consumer_invokes_resolve_config_for_modules_pulse(rel: str):
    text = (REPO / rel).read_text(encoding="utf-8")
    assert "resolve_config.py" in text, f"{rel} must resolve config toml-first"
    assert "--key modules.pulse" in text, f"{rel} must read the modules.pulse table"


@pytest.mark.parametrize("rel", CONSUMERS)
def test_consumer_documents_yaml_fallback_and_default_last(rel: str):
    text = (REPO / rel).read_text(encoding="utf-8").lower()
    assert "fallback" in text, f"{rel} must document the per-key yaml fallback"
    assert "config.yaml" in text, f"{rel} must name config.yaml as the fallback layer"
    assert "default" in text, f"{rel} must document the module.yaml default as last resort"


@pytest.mark.parametrize("rel", CONSUMERS)
def test_consumer_yaml_is_not_authoritative(rel: str):
    """The old prose loaded the pulse section from config.yaml as the source of
    truth. That phrasing must be gone — toml is authoritative now."""
    text = (REPO / rel).read_text(encoding="utf-8")
    assert "Load the `pulse` section from `{main_config}`" not in text
    assert "Load config from `{project-root}/_bmad/config.yaml`, section `pulse`" not in text


def test_merge_config_writes_custom_toml_not_yaml_module_section():
    """The setup write-path must target custom/config.toml for the module
    section and must not re-introduce a config.yaml module write."""
    script = (REPO / "skills/bmad-pulse-setup/scripts/merge-config.py").read_text(
        encoding="utf-8"
    )
    assert "custom" in script and "config.toml" in script
    assert "write_module_toml" in script
    # anti-zombie strip of the legacy yaml module section
    assert "del config[module_code]" in script
