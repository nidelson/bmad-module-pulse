#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Seed the BCP per-category baseline file for cold start.

Creates `bcp-baseline.yaml` with a config snapshot (seed h/BCP,
min_samples, rolling_window) and an empty `categories` map. Categories
are populated later by `bmad-bcp-recalibrate` from real actual_hours.

Every scoring run reads this file; `apply_score.py` fails outright when it is
absent. That makes this setup-time script part of the runtime contract rather
than install scaffolding, which is why it lives here rather than staying behind
with the standalone module's installer (issue #84).

Idempotent: if the baseline already exists it is left untouched and the
script reports `action: skipped_exists`. Pass --force to overwrite.

Exit codes: 0=success (created or skipped), 2=runtime error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: pyyaml is required (PEP 723 dependency)", file=sys.stderr)
    sys.exit(2)

SCHEMA_VERSION = "1.0"


def build_baseline(seed: float, min_samples: int, rolling_window: int) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "config_snapshot": {
            "seed": seed,
            "min_samples": min_samples,
            "rolling_window": rolling_window,
        },
        "categories": {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-path", type=Path, required=True)
    parser.add_argument("--seed", type=float, default=5.0,
                        help="Seed hours-per-BCP for cold start")
    parser.add_argument("--min-samples", type=int, default=5,
                        help="Minimum samples before a category leaves the seed")
    parser.add_argument("--rolling-window", type=int, default=10,
                        help="FIFO recalibration window size")
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing baseline")
    args = parser.parse_args()

    dest: Path = args.baseline_path
    # Captured before the write: the reported action asked `dest.exists()`
    # afterwards, when it is always true, so `--force` on a fresh path reported
    # "overwritten" for a file it had just created.
    existed = dest.exists()

    if existed and not args.force:
        print(json.dumps({
            "status": "success",
            "action": "skipped_exists",
            "baseline_path": str(dest.resolve()),
        }, indent=2))
        return 0

    baseline = build_baseline(args.seed, args.min_samples, args.rolling_window)
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            yaml.dump(baseline, f, default_flow_style=False,
                      allow_unicode=True, sort_keys=False)
    except OSError as e:
        print(json.dumps({
            "status": "error",
            "error": f"Failed to write {dest}: {e}",
        }, indent=2))
        return 2

    print(json.dumps({
        "status": "success",
        "action": "overwritten" if existed else "created",
        "baseline_path": str(dest.resolve()),
        "config_snapshot": baseline["config_snapshot"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
