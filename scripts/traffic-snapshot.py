#!/usr/bin/env python3
"""Append the current rolling-14d traffic data to _metrics/traffic.json.

Reads `clones` and `views` payloads from stdin (passed by gh CLI in the
workflow), merges with the existing _metrics/traffic.json, deduplicates
by timestamp, and writes back. Designed to be idempotent: running twice
on the same day produces identical output.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

METRICS_FILE = Path("_metrics/traffic.json")


def merge(existing: dict, fresh: dict, key: str) -> list[dict]:
    by_ts = {entry["timestamp"]: entry for entry in existing.get(key, [])}
    for entry in fresh.get(key, []):
        by_ts[entry["timestamp"]] = entry
    return sorted(by_ts.values(), key=lambda e: e["timestamp"])


def main() -> int:
    fresh = json.load(sys.stdin)

    existing: dict = {"clones": [], "views": []}
    if METRICS_FILE.exists():
        existing = json.loads(METRICS_FILE.read_text())

    merged = {
        "clones": merge(existing, fresh, "clones"),
        "views": merge(existing, fresh, "views"),
    }

    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    METRICS_FILE.write_text(json.dumps(merged, indent=2) + "\n")
    print(f"wrote {METRICS_FILE}: {len(merged['clones'])} clone entries, "
          f"{len(merged['views'])} view entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
