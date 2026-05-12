"""Tests for the --remove-legacy-agent mode of cleanup-legacy.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "skills/bmad-pulse-setup/scripts/cleanup-legacy.py"

LEGACY = ".claude/skills/bmad-pulse-agent-levi"
CANONICAL = ".claude/skills/bmad-agent-pulse"


def run(consumer: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--remove-legacy-agent",
            "--project-root",
            str(consumer),
            *extra,
        ],
        capture_output=True,
        text=True,
    )


def _seed_skill(project: Path, relpath: str, with_file: str = "SKILL.md") -> Path:
    skill = project / relpath
    skill.mkdir(parents=True)
    (skill / with_file).write_text("---\nname: stub\n---\nstub\n")
    return skill


def test_removes_legacy_when_canonical_exists(tmp_path: Path):
    legacy = _seed_skill(tmp_path, LEGACY)
    canonical = _seed_skill(tmp_path, CANONICAL)

    result = run(tmp_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert payload["action"] == "removed"
    assert payload["files_removed"] == 1
    assert "bmad-pulse-agent-levi" in payload["notice"]
    assert not legacy.exists()
    assert canonical.exists(), "canonical must never be touched"


def test_idempotent_when_already_removed(tmp_path: Path):
    _seed_skill(tmp_path, CANONICAL)
    # No legacy folder seeded.

    result = run(tmp_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["action"] == "skipped_already_absent"
    assert payload["files_removed"] == 0


def test_skips_when_only_legacy_exists(tmp_path: Path):
    """Safety: do not delete the legacy folder if the canonical replacement
    is missing — otherwise the project is stranded without a Levi agent."""
    legacy = _seed_skill(tmp_path, LEGACY)

    result = run(tmp_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["action"] == "skipped_no_canonical"
    assert payload["files_removed"] == 0
    assert legacy.exists(), "legacy must NOT be removed without canonical present"
    assert "Refusing to remove" in payload["notice"]


def test_handles_clean_project_with_neither_folder(tmp_path: Path):
    result = run(tmp_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["action"] == "skipped_already_absent"


def test_repeat_invocations_are_safe(tmp_path: Path):
    _seed_skill(tmp_path, LEGACY)
    _seed_skill(tmp_path, CANONICAL)

    first = run(tmp_path)
    second = run(tmp_path)

    assert first.returncode == 0
    assert second.returncode == 0
    first_payload = json.loads(first.stdout)
    second_payload = json.loads(second.stdout)
    assert first_payload["action"] == "removed"
    assert second_payload["action"] == "skipped_already_absent"


def test_errors_when_project_root_missing():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--remove-legacy-agent"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert "--project-root" in payload["error"]


def test_mutually_exclusive_with_remove_pulse_markers(tmp_path: Path):
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--remove-legacy-agent",
            "--remove-pulse-markers",
            "--project-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert "mutually exclusive" in payload["error"]


def test_canonical_must_be_a_directory(tmp_path: Path):
    """Defensive: a stray file named bmad-agent-pulse must not be treated
    as a valid canonical replacement."""
    _seed_skill(tmp_path, LEGACY)
    skills_dir = tmp_path / ".claude/skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    (skills_dir / "bmad-agent-pulse").write_text("not a folder")

    result = run(tmp_path)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["action"] == "skipped_no_canonical"
    assert (tmp_path / LEGACY).exists()
