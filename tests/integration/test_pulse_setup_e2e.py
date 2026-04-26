"""End-to-end orchestration tests: simulate the SKILL.md script chain.

These tests don't run the LLM — they run the same script sequence the LLM
would, and assert filesystem deltas. This catches regressions in the
script contract (exit codes, paths, JSON outputs).
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[2] / "skills/pulse-setup/scripts"
GOLDEN = Path(__file__).parents[1] / "fixtures/golden"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        text=True,
    )


@pytest.mark.integration
def test_e2e_fresh_install_on_bmad_64(bmad_64_consumer: Path):
    """Test full pulse-setup script chain on BMAD 6.4.0 consumer."""
    # 1. Capability gate
    detect = run(str(SCRIPTS / "detect_bmad_capability.py"),
                 "--project-root", str(bmad_64_consumer))
    assert detect.returncode == 0

    # 2. Cleanup legacy (no-op on 6.4)
    cleanup = run(str(SCRIPTS / "cleanup-legacy.py"),
                  "--remove-pulse-markers",
                  "--project-root", str(bmad_64_consumer))
    assert cleanup.returncode == 0

    # 3. Emit overrides
    for skill in ("bmad-dev-story", "bmad-code-review"):
        emit = run(str(SCRIPTS / "inject_customize.py"),
                   "--project-root", str(bmad_64_consumer),
                   "--skill", skill)
        assert emit.returncode == 0, emit.stderr

    # 4. Assert golden snapshot match
    for skill, golden in (
        ("bmad-dev-story", "customize-bmad-dev-story.toml"),
        ("bmad-code-review", "customize-bmad-code-review.toml"),
    ):
        out = bmad_64_consumer / f"_bmad/custom/{skill}.toml"
        assert sha256(out) == sha256(GOLDEN / golden)

    # 5. Gitignore advice script
    advice = run(str(SCRIPTS / "print_gitignore_snippet.py"),
                 "--project-root", str(bmad_64_consumer))
    assert advice.returncode == 0
    assert "!_bmad/custom/" in advice.stdout


@pytest.mark.integration
def test_e2e_rerun_without_force_aborts_byte_stable(bmad_64_consumer: Path):
    """Test re-run without --force aborts cleanly with byte-stable output."""
    # First install
    for skill in ("bmad-dev-story", "bmad-code-review"):
        run(str(SCRIPTS / "inject_customize.py"),
            "--project-root", str(bmad_64_consumer),
            "--skill", skill)
    out = bmad_64_consumer / "_bmad/custom/bmad-dev-story.toml"
    first_hash = sha256(out)

    # Second run without --force
    rerun = run(str(SCRIPTS / "inject_customize.py"),
                "--project-root", str(bmad_64_consumer),
                "--skill", "bmad-dev-story")
    assert rerun.returncode == 3
    assert sha256(out) == first_hash, "byte-stable invariant violated"


@pytest.mark.integration
def test_e2e_capability_gate_aborts_on_bmad_63(bmad_63_consumer: Path):
    """Test capability gate aborts on BMAD 6.3.x, but cleanup still works."""
    detect = run(str(SCRIPTS / "detect_bmad_capability.py"),
                 "--project-root", str(bmad_63_consumer))
    assert detect.returncode == 1
    # Even though detection failed, cleanup-legacy should still work to remove markers
    cleanup = run(str(SCRIPTS / "cleanup-legacy.py"),
                  "--remove-pulse-markers",
                  "--project-root", str(bmad_63_consumer))
    assert cleanup.returncode == 0
    workflow = bmad_63_consumer / ".claude/skills/bmad-dev-story/workflow.md"
    assert "<!-- PULSE:auto-inject:start -->" not in workflow.read_text()
