"""Tests for reconcile-skills.py — idempotent self-heal of deployed skills.

Covers the bug from issue #36: BMAD's additive deploy leaves pre-existing
files stale and renamed folders orphaned when updating over an existing
install. Reconcile must converge the deployed tree to the source version
and be a no-op when already in sync.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).parents[2]
    / "skills/bmad-pulse-setup/scripts/reconcile-skills.py"
)

PULSE_SKILLS = [
    "bmad-pulse-setup",
    "bmad-agent-pulse",
    "bmad-pulse-dashboard",
    "bmad-pulse-track-start",
    "bmad-pulse-track-done",
]


def run(project: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--project-root",
            str(project),
            *extra,
        ],
        capture_output=True,
        text=True,
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def make_source(root: Path, version: str) -> Path:
    """A fresh PULSE source tree at the given module_version."""
    source = root / "source"
    for skill in PULSE_SKILLS:
        _write(source / "skills" / skill / "SKILL.md", f"---\nname: {skill}\n---\n")
    _write(
        source / "skills/bmad-pulse-setup/assets/module.yaml",
        f"name: PULSE\ncode: pulse\nmodule_version: {version}\n",
    )
    return source


def deploy_stale(project: Path, version: str) -> None:
    """Simulate an additive BMAD deploy stuck at an older version:
    pre-existing files frozen, plus an orphan renamed folder."""
    skills = project / ".claude/skills"
    for skill in PULSE_SKILLS:
        _write(skills / skill / "SKILL.md", f"---\nname: {skill}\nSTALE\n---\n")
    _write(
        skills / "bmad-pulse-setup/assets/module.yaml",
        f"name: PULSE\ncode: pulse\nmodule_version: {version}\n",
    )
    # Orphan folder from a pre-rename version (bmad-pulse-agent-levi ->
    # bmad-agent-pulse in 0.4.5).
    _write(skills / "bmad-pulse-agent-levi/SKILL.md", "---\nname: levi\n---\n")


def test_reconciles_stale_install_to_source_version(tmp_path: Path):
    source = make_source(tmp_path, "0.4.5")
    project = tmp_path / "proj"
    deploy_stale(project, "0.4.4")

    result = run(project, "--source", str(source))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["action"] == "reconciled"
    assert payload["from_version"] == "0.4.4"
    assert payload["to_version"] == "0.4.5"

    deployed = (
        project
        / ".claude/skills/bmad-pulse-setup/assets/module.yaml"
    ).read_text()
    assert "module_version: 0.4.5" in deployed
    assert "STALE" not in (
        project / ".claude/skills/bmad-pulse-setup/SKILL.md"
    ).read_text()


def test_prunes_orphaned_renamed_folder(tmp_path: Path):
    source = make_source(tmp_path, "0.4.5")
    project = tmp_path / "proj"
    deploy_stale(project, "0.4.4")

    result = run(project, "--source", str(source))

    payload = json.loads(result.stdout)
    assert "bmad-pulse-agent-levi" in payload["legacy_folders_removed"]
    assert not (project / ".claude/skills/bmad-pulse-agent-levi").exists()
    assert (project / ".claude/skills/bmad-agent-pulse").is_dir()


def test_idempotent_second_run_is_noop(tmp_path: Path):
    source = make_source(tmp_path, "0.4.5")
    project = tmp_path / "proj"
    deploy_stale(project, "0.4.4")

    first = run(project, "--source", str(source))
    second = run(project, "--source", str(source))

    assert json.loads(first.stdout)["action"] == "reconciled"
    second_payload = json.loads(second.stdout)
    assert second_payload["action"] == "up_to_date"
    assert second_payload["files_written"] == 0
    assert second_payload["files_deleted"] == 0
    assert second_payload["legacy_folders_removed"] == []


def test_dry_run_makes_no_writes(tmp_path: Path):
    source = make_source(tmp_path, "0.4.5")
    project = tmp_path / "proj"
    deploy_stale(project, "0.4.4")

    result = run(project, "--source", str(source), "--dry-run")

    payload = json.loads(result.stdout)
    assert payload["dry_run"] is True
    assert payload["action"] == "reconciled"
    # Nothing actually changed on disk.
    assert "STALE" in (
        project / ".claude/skills/bmad-pulse-setup/SKILL.md"
    ).read_text()
    assert (project / ".claude/skills/bmad-pulse-agent-levi").exists()


def test_skips_when_no_source_or_cache(tmp_path: Path):
    """Fresh install path: no manifest, no cache — non-fatal skip so
    bmad-pulse-setup can continue."""
    project = tmp_path / "proj"
    (project / ".claude/skills").mkdir(parents=True)

    result = run(project, "--cache-root", str(tmp_path / "empty-cache"))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["action"] == "skipped_no_source"


def test_discovers_cache_from_manifest(tmp_path: Path):
    project = tmp_path / "proj"
    (project / ".claude/skills").mkdir(parents=True)
    _write(
        project / "_bmad/_config/manifest.yaml",
        "modules:\n"
        "  - name: core\n    version: 6.6.0\n"
        "  - name: pulse\n"
        "    version: main\n"
        "    repoUrl: https://github.com/nidelson/bmad-module-pulse\n",
    )
    cache_root = tmp_path / "cache"
    cache_dir = cache_root / "github.com/nidelson/bmad-module-pulse"
    make_source(cache_dir.parent, "0.4.5")
    # make_source writes to <parent>/source; relocate to the exact cache path
    (cache_dir.parent / "source").rename(cache_dir)

    result = run(project, "--cache-root", str(cache_root))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["action"] == "reconciled"
    assert payload["to_version"] == "0.4.5"


def test_keeps_legacy_when_canonical_absent_from_source(tmp_path: Path):
    """Safety: if the source set has no canonical replacement, the rename
    did not happen in this version — do not prune the legacy folder."""
    source = tmp_path / "source"
    # Source WITHOUT bmad-agent-pulse.
    _write(source / "skills/bmad-pulse-setup/SKILL.md", "---\nname: s\n---\n")
    _write(
        source / "skills/bmad-pulse-setup/assets/module.yaml",
        "module_version: 0.4.5\n",
    )
    project = tmp_path / "proj"
    _write(
        project / ".claude/skills/bmad-pulse-agent-levi/SKILL.md",
        "---\nname: levi\n---\n",
    )

    result = run(project, "--source", str(source))

    payload = json.loads(result.stdout)
    assert payload["legacy_folders_removed"] == []
    assert (project / ".claude/skills/bmad-pulse-agent-levi").exists()


def test_errors_on_missing_project_root(tmp_path: Path):
    result = run(tmp_path / "does-not-exist", "--source", str(tmp_path))
    assert result.returncode == 1
    assert json.loads(result.stdout)["status"] == "error"
