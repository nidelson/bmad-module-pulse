#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Collect recalibration samples from already-BCP-scored stories.

Bridges `bmad-bcp-score-batch` → `bmad-bcp-recalibrate`: scans a glob of
stories, and for each that has a `bcp.total` AND a real-hours figure,
emits a sample `{category, bcp_total, actual_hours, id, at}`. The emitted
JSON list is fed straight into `recalibrate.py --samples`.

Real hours source (PULSE-agnostic): `pulse_metrics.actual_hours` if
present, else an entry in an optional `--actual-hours-map` JSON keyed by
story_id. Stories missing either bcp.total or actual_hours are skipped
and reported (never invented).

Stable `id` (story_id, else filename stem) makes the downstream
recalibration idempotent — re-running backfill cannot double-count.

Exit codes: 0=success, 1=validation error, 2=runtime error
"""
from __future__ import annotations

import argparse
import glob as globlib
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: pyyaml is required (PEP 723 dependency)", file=sys.stderr)
    sys.exit(2)


def frontmatter(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None
    return fm if isinstance(fm, dict) else None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project-root", type=Path, required=True)
    p.add_argument("--glob", required=True)
    p.add_argument("--actual-hours-map",
                   help="JSON {story_id: hours} for PULSE-absent backfill")
    p.add_argument("--out", help="write samples JSON here (else stdout)")
    args = p.parse_args()

    hours_map = {}
    if args.actual_hours_map:
        try:
            hours_map = json.loads(
                Path(args.actual_hours_map).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(json.dumps({"status": "error",
                              "error": f"bad --actual-hours-map: {e}"}, indent=2))
            return 1

    root: Path = args.project_root
    matches = sorted(Path(m) for m in
                     globlib.glob(str(root / args.glob), recursive=True)
                     if Path(m).is_file())
    if not matches:
        print(json.dumps({"status": "error",
                          "error": f"no files matched {args.glob!r}"}, indent=2))
        return 1

    samples, skipped = [], []
    for m in matches:
        rel = str(m.relative_to(root)) if root in m.parents else str(m)
        fm = frontmatter(m)
        if not fm:
            skipped.append({"path": rel, "reason": "no frontmatter"})
            continue
        bcp = fm.get("bcp") or {}
        total = bcp.get("total")
        if not isinstance(total, (int, float)) or total <= 0:
            skipped.append({"path": rel, "reason": "no positive bcp.total"})
            continue
        sid = str(fm.get("story_id") or m.stem)
        actual = (fm.get("pulse_metrics") or {}).get("actual_hours")
        if actual is None:
            actual = hours_map.get(sid)
        if not isinstance(actual, (int, float)) or actual <= 0:
            skipped.append({"path": rel, "reason": "no actual_hours",
                            "story_id": sid})
            continue
        category = fm.get("category")
        if not category:
            skipped.append({"path": rel, "reason": "no category"})
            continue
        samples.append({
            "category": category, "bcp_total": total,
            "actual_hours": actual, "id": sid,
            "at": bcp.get("scored_at") or "",
        })

    payload = {
        "status": "success",
        "collected": len(samples),
        "skipped": len(skipped),
        "skipped_detail": skipped,
        "samples": samples,
    }
    if args.out:
        try:
            Path(args.out).write_text(
                json.dumps(samples, indent=2, ensure_ascii=False),
                encoding="utf-8")
        except OSError as e:
            print(json.dumps({"status": "error", "error": str(e)}, indent=2))
            return 2
        payload["out"] = args.out
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
