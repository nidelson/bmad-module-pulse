#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml", "pytest"]
# ///
"""Unit tests for batch_plan.py — deterministic retroactive batch planner."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "batch_plan.py"


def run(*a: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *a],
                          capture_output=True, text=True)


def _story(p: Path, scored: bool):
    fm = 'story_id: "x"\ncategory: backend\nestimated_hours: 10\n'
    if scored:
        fm += "bcp:\n  schema_version: '1.0'\n  total: 5\n"
    p.write_text(f"---\n{fm}---\n# body\n")


def test_classifies_and_estimates(tmp_path: Path):
    d = tmp_path / "docs" / "stories"
    d.mkdir(parents=True)
    _story(d / "1.md", False)
    _story(d / "2.md", False)
    _story(d / "3.md", True)
    r = run("--project-root", str(tmp_path), "--glob", "docs/stories/*.md")
    assert r.returncode == 0, r.stdout + r.stderr
    o = json.loads(r.stdout)
    assert o["matched"] == 3
    assert o["selected"] == 2
    assert o["skipped_already_scored"] == 1
    assert o["scored_by"] == "retroactive"
    assert o["cost_estimate"]["est_total_tokens"] > 0
    paths = {s["path"]: s for s in o["stories"]}
    assert paths["docs/stories/3.md"]["status"] == "already_scored"
    assert paths["docs/stories/3.md"]["selected"] is False


def test_rescore_includes_already_scored(tmp_path: Path):
    d = tmp_path / "docs" / "stories"
    d.mkdir(parents=True)
    _story(d / "1.md", True)
    r = run("--project-root", str(tmp_path), "--glob", "docs/stories/*.md",
            "--rescore")
    o = json.loads(r.stdout)
    assert o["selected"] == 1
    assert o["stories"][0]["selected"] is True


def test_no_match_is_error(tmp_path: Path):
    r = run("--project-root", str(tmp_path), "--glob", "nope/*.md")
    assert r.returncode == 1
    assert "no files matched" in json.loads(r.stdout)["error"]


def test_recursive_glob(tmp_path: Path):
    a = tmp_path / "docs" / "stories" / "epic1"
    a.mkdir(parents=True)
    _story(a / "5.7.md", False)
    r = run("--project-root", str(tmp_path), "--glob", "docs/**/*.md")
    o = json.loads(r.stdout)
    assert o["matched"] == 1 and o["selected"] == 1


if __name__ == "__main__":
    sys.exit(subprocess.call(
        ["uv", "run", "--with", "pytest", "--with", "pyyaml",
         "pytest", "-q", str(Path(__file__).parent)]))
