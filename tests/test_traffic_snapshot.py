"""Tests for scripts/traffic-snapshot.py — the weekly metrics merge helper.

The script reads a JSON payload from stdin shaped like
`{"clones": [{"timestamp", "count", "uniques"}, ...], "views": [...]}`
and merges it into `_metrics/traffic.json` (relative to cwd), deduplicating
entries by timestamp.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts/traffic-snapshot.py"


def run(payload: dict, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def test_merge_fresh_into_empty_produces_sorted_output(tmp_path: Path):
    payload = {
        "clones": [
            {"timestamp": "2026-04-25T00:00:00Z", "count": 10, "uniques": 5},
            {"timestamp": "2026-04-23T00:00:00Z", "count": 3, "uniques": 2},
        ],
        "views": [
            {"timestamp": "2026-04-25T00:00:00Z", "count": 7, "uniques": 4},
        ],
    }
    result = run(payload, tmp_path)
    assert result.returncode == 0, result.stderr

    metrics = json.loads((tmp_path / "_metrics/traffic.json").read_text())
    assert [e["timestamp"] for e in metrics["clones"]] == [
        "2026-04-23T00:00:00Z",
        "2026-04-25T00:00:00Z",
    ], "clones must be sorted by timestamp ascending"
    assert metrics["views"][0]["count"] == 7


def test_rerun_with_same_payload_is_idempotent(tmp_path: Path):
    payload = {
        "clones": [{"timestamp": "2026-04-25T00:00:00Z", "count": 1, "uniques": 1}],
        "views": [{"timestamp": "2026-04-25T00:00:00Z", "count": 1, "uniques": 1}],
    }
    run(payload, tmp_path)
    first = (tmp_path / "_metrics/traffic.json").read_bytes()
    run(payload, tmp_path)
    second = (tmp_path / "_metrics/traffic.json").read_bytes()
    assert first == second, "running twice with same payload must be byte-identical"


def test_merge_preserves_history_and_dedups_by_timestamp(tmp_path: Path):
    metrics_dir = tmp_path / "_metrics"
    metrics_dir.mkdir()
    (metrics_dir / "traffic.json").write_text(
        json.dumps({
            "clones": [{"timestamp": "2026-04-20T00:00:00Z", "count": 5, "uniques": 3}],
            "views": [],
        })
    )
    fresh = {
        "clones": [
            {"timestamp": "2026-04-20T00:00:00Z", "count": 99, "uniques": 99},
            {"timestamp": "2026-04-25T00:00:00Z", "count": 8, "uniques": 4},
        ],
        "views": [
            {"timestamp": "2026-04-25T00:00:00Z", "count": 2, "uniques": 1},
        ],
    }
    result = run(fresh, tmp_path)
    assert result.returncode == 0, result.stderr

    merged = json.loads((metrics_dir / "traffic.json").read_text())
    timestamps = [e["timestamp"] for e in merged["clones"]]
    assert timestamps == ["2026-04-20T00:00:00Z", "2026-04-25T00:00:00Z"]

    apr_20 = next(e for e in merged["clones"] if e["timestamp"] == "2026-04-20T00:00:00Z")
    assert apr_20["count"] == 99, "fresh entry must overwrite existing entry with same timestamp"
