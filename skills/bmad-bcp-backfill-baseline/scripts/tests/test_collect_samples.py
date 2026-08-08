#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml", "pytest"]
# ///
"""Unit tests for collect_samples.py — score-batch → recalibrate bridge."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parent.parent / "collect_samples.py"


def run(*a: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *a],
                          capture_output=True, text=True)


def _story(p: Path, fm: dict):
    p.write_text("---\n" + yaml.dump(fm, sort_keys=False) + "---\n# s\n")


def test_collects_with_pulse_metrics(tmp_path: Path):
    d = tmp_path / "docs" / "stories"
    d.mkdir(parents=True)
    _story(d / "1.md", {"story_id": "1", "category": "backend",
                        "bcp": {"total": 8, "scored_at": "2026-01-01T00:00:00Z"},
                        "pulse_metrics": {"actual_hours": 40}})
    r = run("--project-root", str(tmp_path), "--glob", "docs/stories/*.md")
    assert r.returncode == 0, r.stdout + r.stderr
    o = json.loads(r.stdout)
    assert o["collected"] == 1 and o["skipped"] == 0
    s = o["samples"][0]
    assert s == {"category": "backend", "bcp_total": 8, "actual_hours": 40,
                 "id": "1", "at": "2026-01-01T00:00:00Z"}


def test_actual_hours_map_without_pulse(tmp_path: Path):
    d = tmp_path / "docs"
    d.mkdir()
    _story(d / "5.7.md", {"story_id": "5.7", "category": "web",
                          "bcp": {"total": 5}})
    hm = tmp_path / "hm.json"
    hm.write_text(json.dumps({"5.7": 30}))
    o = json.loads(run("--project-root", str(tmp_path), "--glob",
                        "docs/*.md", "--actual-hours-map", str(hm)).stdout)
    assert o["collected"] == 1
    assert o["samples"][0]["actual_hours"] == 30
    assert o["samples"][0]["id"] == "5.7"


def test_skips_missing_pieces(tmp_path: Path):
    d = tmp_path / "s"
    d.mkdir()
    _story(d / "no_bcp.md", {"story_id": "a", "category": "be"})
    _story(d / "no_hours.md", {"story_id": "b", "category": "be",
                               "bcp": {"total": 3}})
    _story(d / "no_cat.md", {"story_id": "c", "bcp": {"total": 3},
                             "pulse_metrics": {"actual_hours": 9}})
    o = json.loads(run("--project-root", str(tmp_path),
                       "--glob", "s/*.md").stdout)
    assert o["collected"] == 0 and o["skipped"] == 3
    reasons = {x["reason"] for x in o["skipped_detail"]}
    assert reasons == {"no positive bcp.total", "no actual_hours",
                       "no category"}


def test_out_file_written(tmp_path: Path):
    d = tmp_path / "s"
    d.mkdir()
    _story(d / "1.md", {"story_id": "1", "category": "be",
                        "bcp": {"total": 2},
                        "pulse_metrics": {"actual_hours": 8}})
    out = tmp_path / "samples.json"
    run("--project-root", str(tmp_path), "--glob", "s/*.md",
        "--out", str(out))
    data = json.loads(out.read_text())
    assert data == [{"category": "be", "bcp_total": 2, "actual_hours": 8,
                     "id": "1", "at": ""}]


def test_no_match_error(tmp_path: Path):
    r = run("--project-root", str(tmp_path), "--glob", "nope/*.md")
    assert r.returncode == 1
    assert "no files matched" in json.loads(r.stdout)["error"]


def test_recursive_glob_and_stem_id(tmp_path: Path):
    d = tmp_path / "docs" / "stories" / "epic2"
    d.mkdir(parents=True)
    # no story_id -> id falls back to filename stem
    _story(d / "9.3.md", {"category": "mobile", "bcp": {"total": 4},
                          "pulse_metrics": {"actual_hours": 16}})
    o = json.loads(run("--project-root", str(tmp_path),
                       "--glob", "docs/**/*.md").stdout)
    assert o["collected"] == 1
    assert o["samples"][0]["id"] == "9.3"


if __name__ == "__main__":
    sys.exit(subprocess.call(
        ["uv", "run", "--with", "pytest", "--with", "pyyaml",
         "pytest", "-q", str(Path(__file__).parent)]))
