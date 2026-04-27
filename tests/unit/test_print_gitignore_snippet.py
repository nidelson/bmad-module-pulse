"""Tests for skills/bmad-pulse-setup/scripts/print_gitignore_snippet.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "skills/bmad-pulse-setup/scripts/print_gitignore_snippet.py"


def run(consumer: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(consumer)],
        capture_output=True,
        text=True,
    )


def test_prints_snippet_when_allowlist_absent(tmp_consumer_project: Path):
    # No .gitignore file present → should print snippet and a "create .gitignore" hint.
    result = run(tmp_consumer_project)
    assert result.returncode == 0
    assert "!_bmad/custom/" in result.stdout
    assert "_bmad/custom/" in result.stdout


def test_prints_snippet_when_gitignore_exists_without_allowlist(tmp_consumer_project: Path):
    (tmp_consumer_project / ".gitignore").write_text("node_modules/\n")
    result = run(tmp_consumer_project)
    assert result.returncode == 0
    assert "!_bmad/custom/" in result.stdout


def test_silent_when_allowlist_already_present(tmp_consumer_project: Path):
    (tmp_consumer_project / ".gitignore").write_text(
        "node_modules/\n_bmad/*\n!_bmad/custom/\n_bmad/custom/*\n!_bmad/custom/*.toml\n"
    )
    result = run(tmp_consumer_project)
    assert result.returncode == 0
    assert "!_bmad/custom/" not in result.stdout
    assert "already" in result.stdout.lower() or result.stdout.strip() == ""


def test_prints_snippet_when_allowlist_is_only_commented_out(tmp_consumer_project: Path):
    """Regression: I2 — a commented `# !_bmad/custom/` line must NOT count
    as an active allowlist. Otherwise a user who decided NOT to allowlist
    would be silently told nothing to do, and their .toml files would be
    git-ignored without warning.
    """
    (tmp_consumer_project / ".gitignore").write_text(
        "node_modules/\n_bmad/*\n# !_bmad/custom/\n# !_bmad/custom/*.toml\n"
    )
    result = run(tmp_consumer_project)
    assert result.returncode == 0
    assert "!_bmad/custom/" in result.stdout, (
        "commented-out allowlist must be ignored; snippet should be printed"
    )
