"""Unit tests for skills/bmad-pulse-setup/scripts/detect_bmad_capability.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "skills/bmad-pulse-setup/scripts/detect_bmad_capability.py"


def run(consumer: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(consumer)],
        capture_output=True,
        text=True,
    )


def test_returns_zero_on_bmad_64(bmad_64_consumer: Path):
    result = run(bmad_64_consumer)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["capability"] == "bmad-6.4.0+"
    assert payload["customize_toml_path"].endswith(".claude/skills/bmad-dev-story/customize.toml")


def test_returns_one_on_bmad_63(bmad_63_consumer: Path):
    result = run(bmad_63_consumer)
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["capability"] == "bmad-6.3.x"
    assert payload["workflow_md_path"].endswith(".claude/skills/bmad-dev-story/workflow.md")


def test_returns_two_when_bmad_absent(tmp_consumer_project: Path):
    result = run(tmp_consumer_project)
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["capability"] == "bmad-not-installed"
