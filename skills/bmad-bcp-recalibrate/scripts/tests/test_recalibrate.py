#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml", "pytest"]
# ///
"""Unit tests for recalibrate.py — per-category baseline recalibration."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parent.parent / "recalibrate.py"


def run(*a: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *a],
                          capture_output=True, text=True)


def _baseline(tmp: Path, min_samples=5, window=10) -> Path:
    p = tmp / "bcp-baseline.yaml"
    p.write_text(yaml.dump({
        "schema_version": "1.0",
        "config_snapshot": {"seed": 4.13, "min_samples": min_samples,
                            "rolling_window": window},
        "categories": {},
    }))
    return p


def _samples(tmp: Path, items) -> Path:
    p = tmp / "s.json"
    p.write_text(json.dumps(items))
    return p


def _load(bp: Path) -> dict:
    return yaml.safe_load(bp.read_text())


def test_observed_hpb_and_mean(tmp_path: Path):
    bp = _baseline(tmp_path)
    s = _samples(tmp_path, [
        {"category": "backend", "bcp_total": 10, "actual_hours": 40, "id": "a", "at": "2026-01-01"},
        {"category": "backend", "bcp_total": 10, "actual_hours": 60, "id": "b", "at": "2026-01-02"},
    ])
    r = run("--baseline", str(bp), "--samples", str(s))
    assert r.returncode == 0, r.stdout + r.stderr
    cat = _load(bp)["categories"]["backend"]
    # observed: 4.0 and 6.0 -> mean 5.0
    assert cat["h_per_bcp"] == 5.0
    assert cat["n_samples"] == 2
    assert cat["is_seed"] is True            # < min_samples(5)


def test_leaves_seed_at_min_samples(tmp_path: Path):
    bp = _baseline(tmp_path, min_samples=3)
    items = [{"category": "web", "bcp_total": 5, "actual_hours": 25,
              "id": f"x{i}", "at": f"2026-01-0{i+1}"} for i in range(3)]
    run("--baseline", str(bp), "--samples", str(_samples(tmp_path, items)))
    cat = _load(bp)["categories"]["web"]
    assert cat["n_samples"] == 3
    assert cat["is_seed"] is False
    assert cat["h_per_bcp"] == 5.0           # 25/5 each
    assert len(cat["history"]) == 1


def test_fifo_window(tmp_path: Path):
    bp = _baseline(tmp_path, min_samples=1, window=2)
    items = [{"category": "be", "bcp_total": 1, "actual_hours": h,
              "id": f"i{n}", "at": f"2026-02-0{n+1}"}
             for n, h in enumerate([2, 4, 12])]
    run("--baseline", str(bp), "--samples", str(_samples(tmp_path, items)))
    cat = _load(bp)["categories"]["be"]
    assert len(cat["samples"]) == 2          # window trimmed
    assert cat["h_per_bcp"] == 8.0           # mean of last two: (4,12)
    assert cat["n_samples"] == 3             # cumulative count, not window


def test_dedup_by_id(tmp_path: Path):
    bp = _baseline(tmp_path, min_samples=1)
    s = _samples(tmp_path, [
        {"category": "be", "bcp_total": 2, "actual_hours": 8, "id": "dup", "at": "2026-03-01"},
    ])
    run("--baseline", str(bp), "--samples", str(s))
    r2 = run("--baseline", str(bp), "--samples", str(s))
    out = json.loads(r2.stdout)
    assert out["categories"]["be"]["skipped_dup"] == 1
    assert _load(bp)["categories"]["be"]["n_samples"] == 1


def test_chronological_order(tmp_path: Path):
    bp = _baseline(tmp_path, min_samples=1, window=1)
    # later 'at' must win the single-slot window regardless of input order
    s = _samples(tmp_path, [
        {"category": "be", "bcp_total": 1, "actual_hours": 99, "id": "late", "at": "2026-12-31"},
        {"category": "be", "bcp_total": 1, "actual_hours": 3, "id": "early", "at": "2026-01-01"},
    ])
    run("--baseline", str(bp), "--samples", str(s))
    assert _load(bp)["categories"]["be"]["h_per_bcp"] == 99.0


def test_story_manual_actual_hours(tmp_path: Path):
    bp = _baseline(tmp_path, min_samples=1)
    story = tmp_path / "5.7.md"
    story.write_text("---\n" + yaml.dump({
        "story_id": "5.7", "category": "backend",
        "bcp": {"total": 8, "scored_at": "2026-05-01T00:00:00Z"},
    }) + "---\n# s\n")
    r = run("--baseline", str(bp), "--story", str(story),
            "--actual-hours", "40")
    assert r.returncode == 0, r.stdout
    assert _load(bp)["categories"]["backend"]["h_per_bcp"] == 5.0


def test_story_reads_pulse_metrics_when_present(tmp_path: Path):
    bp = _baseline(tmp_path, min_samples=1)
    story = tmp_path / "s.md"
    story.write_text("---\n" + yaml.dump({
        "story_id": "1", "category": "web",
        "bcp": {"total": 4}, "pulse_metrics": {"actual_hours": 20},
    }) + "---\n# s\n")
    run("--baseline", str(bp), "--story", str(story))
    assert _load(bp)["categories"]["web"]["h_per_bcp"] == 5.0


def test_missing_actual_hours_errors_without_pulse(tmp_path: Path):
    bp = _baseline(tmp_path)
    story = tmp_path / "s.md"
    story.write_text("---\n" + yaml.dump({
        "category": "be", "bcp": {"total": 3}}) + "---\n# s\n")
    r = run("--baseline", str(bp), "--story", str(story))
    assert r.returncode == 1
    assert "actual_hours" in json.loads(r.stdout)["error"]


def test_dry_run_no_write(tmp_path: Path):
    bp = _baseline(tmp_path, min_samples=1)
    before = bp.read_text()
    s = _samples(tmp_path, [{"category": "be", "bcp_total": 2,
                             "actual_hours": 8, "id": "z", "at": "2026-01-01"}])
    r = run("--baseline", str(bp), "--samples", str(s), "--dry-run")
    assert json.loads(r.stdout)["dry_run"] is True
    assert bp.read_text() == before


def test_invalid_sample_rejected(tmp_path: Path):
    bp = _baseline(tmp_path)
    s = _samples(tmp_path, [{"category": "be", "bcp_total": 0,
                             "actual_hours": 8, "id": "q"}])
    r = run("--baseline", str(bp), "--samples", str(s))
    assert r.returncode == 1
    assert "bcp_total" in json.loads(r.stdout)["error"]


if __name__ == "__main__":
    sys.exit(subprocess.call(
        ["uv", "run", "--with", "pytest", "--with", "pyyaml",
         "pytest", "-q", str(Path(__file__).parent)]))
