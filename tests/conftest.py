"""Shared pytest fixtures for the repo-level suite."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

FIXTURES_ROOT = Path(__file__).parent / "fixtures"

# ── BCP scoring paths ────────────────────────────────────────────────────────
#
# The repo-level suite reaches into the skills the way an installed consumer
# would — by path, running the scripts as subprocesses. The co-located unit
# tests under `skills/*/scripts/tests/` import them instead; both angles matter,
# and the golden set is deliberately the subprocess one, because that is the
# call the SKILL.md chain actually makes.

REPO_ROOT = Path(__file__).parents[1]
SKILLS = REPO_ROOT / "skills"
RULE_PATH = SKILLS / "bmad-bcp-rule-card/assets/bcp-rule.yaml"
SCHEMA_PATH = SKILLS / "bmad-bcp-score/assets/bcp-frontmatter.schema.yaml"
APPLY_SCORE = SKILLS / "bmad-bcp-score/scripts/apply_score.py"
SEED_BASELINE = SKILLS / "bmad-pulse-setup/scripts/seed_baseline.py"

# One source for the cold-start rate the fixtures and the golden arithmetic
# share. Tests that build a baseline inline must use this too: a test whose own
# baseline says one number while its assertion multiplies by another passes or
# fails for reasons unrelated to what it claims to check.
COLD_START_SEED = 5.0


def run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a module script the same way the SKILL.md chain would."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session")
def rule() -> dict:
    return yaml.safe_load(RULE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def schema() -> dict:
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def seeded_baseline(tmp_path: Path) -> Path:
    """A fresh cold-start baseline: every category still on the seed."""
    path = tmp_path / "bcp-baseline.yaml"
    proc = run_script(
        SEED_BASELINE,
        "--baseline-path", str(path),
        "--seed", str(COLD_START_SEED),
        "--min-samples", "5",
        "--rolling-window", "10",
    )
    assert proc.returncode == 0, proc.stderr
    return path


@pytest.fixture
def story_file(tmp_path: Path):
    """Factory: write a story with given frontmatter, return its path."""
    def _make(frontmatter: dict, body: str = "Story body.\n") -> Path:
        p = tmp_path / "story.md"
        fm = yaml.dump(frontmatter, default_flow_style=False,
                       allow_unicode=True, sort_keys=False)
        p.write_text(f"---\n{fm}---\n{body}", encoding="utf-8")
        return p
    return _make


@pytest.fixture
def breakdown_file(tmp_path: Path):
    """Factory: write a breakdown JSON payload, return its path."""
    def _make(breakdown: dict) -> Path:
        p = tmp_path / "breakdown.json"
        p.write_text(json.dumps({"breakdown": breakdown}), encoding="utf-8")
        return p
    return _make


@pytest.fixture
def tmp_consumer_project(tmp_path: Path) -> Path:
    """Empty tmp directory simulating a fresh consumer project root."""
    return tmp_path


@pytest.fixture
def bmad_64_consumer(tmp_path: Path) -> Path:
    """Consumer project with BMAD 6.4.0 layout (customize.toml present)."""
    src = FIXTURES_ROOT / "bmad-6.4.0"
    dst = tmp_path / "consumer"
    shutil.copytree(src, dst)
    return dst


@pytest.fixture
def bmad_build_consumer(tmp_path: Path) -> Path:
    """Consumer project on the unified `bmad-build` architecture.

    Deliberately keeps the deprecated `bmad-dev-story` shim alongside it: that
    is the real-world layout, and the reason the probe must check `bmad-build`
    first. Detecting the old tier here is not a harmless mislabel — it sends
    the setup's overrides to a skill the user no longer invokes.
    """
    src = FIXTURES_ROOT / "bmad-build"
    dst = tmp_path / "consumer"
    shutil.copytree(src, dst)
    return dst


@pytest.fixture
def bmad_63_consumer(tmp_path: Path) -> Path:
    """Consumer project with BMAD 6.3.x layout (workflow.md present, no customize.toml)."""
    src = FIXTURES_ROOT / "bmad-6.3.x"
    dst = tmp_path / "consumer"
    shutil.copytree(src, dst)
    return dst
