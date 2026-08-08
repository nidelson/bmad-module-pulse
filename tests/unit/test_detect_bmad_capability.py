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


def test_returns_zero_on_bmad_build(bmad_build_consumer: Path):
    result = run(bmad_build_consumer)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["capability"] == "bmad-build"
    assert payload["customize_toml_path"].endswith(".claude/skills/bmad-build/customize.toml")


def test_bmad_build_wins_over_deprecated_dev_story(bmad_build_consumer: Path):
    """The deprecated shim must not shadow the architecture in use.

    `bmad-dev-story/customize.toml` survives alongside `bmad-build`, so a probe
    that checks it first reports `bmad-6.4.0+` and the setup silently injects
    into a workflow the user never runs. Detection order is the whole fix.
    """
    assert (bmad_build_consumer / ".claude/skills/bmad-dev-story/customize.toml").exists()
    payload = json.loads(run(bmad_build_consumer).stdout)
    assert payload["capability"] == "bmad-build"


def test_bmad_build_targets_only_bmad_build(bmad_build_consumer: Path):
    """Review runs inside bmad-build via workflow.review_layers.

    So `bmad-code-review` is not a target here — injecting into both would fire
    track-done twice.
    """
    payload = json.loads(run(bmad_build_consumer).stdout)
    assert payload["inject_targets"] == ["bmad-build"]


def test_legacy_targets_both_skills(bmad_64_consumer: Path):
    payload = json.loads(run(bmad_64_consumer).stdout)
    assert payload["inject_targets"] == ["bmad-dev-story", "bmad-code-review"]


def test_no_inject_targets_when_unsupported(bmad_63_consumer: Path, tmp_consumer_project: Path):
    for consumer in (bmad_63_consumer, tmp_consumer_project):
        payload = json.loads(run(consumer).stdout)
        assert payload.get("inject_targets", []) == []


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
