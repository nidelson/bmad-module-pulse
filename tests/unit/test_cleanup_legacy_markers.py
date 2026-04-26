"""Tests for the --remove-pulse-markers mode of cleanup-legacy.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "skills/pulse-setup/scripts/cleanup-legacy.py"


def run(consumer: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--remove-pulse-markers",
            "--project-root",
            str(consumer),
        ],
        capture_output=True,
        text=True,
    )


def test_removes_marker_blocks_and_preserves_rest(bmad_63_consumer: Path):
    workflow = bmad_63_consumer / ".claude/skills/bmad-dev-story/workflow.md"
    before = workflow.read_text()
    assert "<!-- PULSE:auto-inject:start -->" in before

    result = run(bmad_63_consumer)
    assert result.returncode == 0, result.stderr

    after = workflow.read_text()
    assert "<!-- PULSE:auto-inject:start -->" not in after
    assert "<!-- PULSE:auto-inject:end -->" not in after
    assert "/pulse-track-start" not in after
    assert "/pulse-track-done" not in after
    # Surrounding non-PULSE content must still be there.
    assert "Mark story in-progress" in after
    assert "Implement" in after
    assert 'goal="Find next ready story"' in after


def test_silent_skip_when_workflow_md_absent(bmad_64_consumer: Path):
    # bmad-6.4.0 fixture has customize.toml but NOT workflow.md
    result = run(bmad_64_consumer)
    assert result.returncode == 0, result.stderr
    assert "workflow.md not found" in result.stdout or '"removed": 0' in result.stdout


def test_idempotent_when_no_markers_present(bmad_63_consumer: Path):
    workflow = bmad_63_consumer / ".claude/skills/bmad-dev-story/workflow.md"
    run(bmad_63_consumer)  # first run cleans
    mtime_after_first = workflow.stat().st_mtime
    content_after_first = workflow.read_text()

    result = run(bmad_63_consumer)  # second run should be a no-op
    assert result.returncode == 0
    assert workflow.read_text() == content_after_first
    # Allow 1s slack for filesystems with low resolution.
    assert workflow.stat().st_mtime - mtime_after_first < 2


def test_preserves_separation_between_user_steps_around_block(tmp_path: Path):
    """Regression: I1 — adjacent user-edited steps must keep at least one
    line break of separation after a PULSE block is removed between them.
    Earlier versions of the regex consumed the trailing newline on both
    sides, which collapsed `</step>\\n<step>` into `</step><step>`.
    """
    workflow_dir = tmp_path / ".claude/skills/bmad-dev-story"
    workflow_dir.mkdir(parents=True)
    workflow = workflow_dir / "workflow.md"
    workflow.write_text(
        '<step n="4">user step before</step>\n'
        "<!-- PULSE:auto-inject:start -->\n"
        '<step n="4.5">PULSE</step>\n'
        "<!-- PULSE:auto-inject:end -->\n"
        '<step n="5">user step after</step>\n'
    )

    result = run(tmp_path)
    assert result.returncode == 0, result.stderr

    after = workflow.read_text()
    assert "PULSE:auto-inject" not in after
    assert '<step n="4">user step before</step>' in after
    assert '<step n="5">user step after</step>' in after
    assert "</step><step" not in after, (
        "adjacent user steps were collapsed without separator"
    )
