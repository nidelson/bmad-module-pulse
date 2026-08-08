#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Recalibrate the per-category BCP baseline from real hours.

Each sample is (category, bcp_total, actual_hours). The observed
hours-per-BCP is actual_hours / bcp_total. Samples are applied in
chronological order into a per-category FIFO window
(`config_snapshot.rolling_window`); `h_per_bcp` becomes the window mean.
A category leaves the seed (`is_seed: false`) once it has accumulated
`config_snapshot.min_samples` samples.

Source-agnostic: callers pass samples from `pulse_metrics.actual_hours`
OR a manual `--actual-hours` value. This script never imports, requires,
or checks for PULSE — `actual_hours` is just a number.

Idempotent: samples carry an `id`; re-applying a known id is skipped
(unless --allow-dup). `n_samples` counts accepted (deduped) samples.

Exit codes: 0=success, 1=validation error, 2=runtime error
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: pyyaml is required (PEP 723 dependency)", file=sys.stderr)
    sys.exit(2)

HISTORY_CAP = 50


def load_samples(args) -> list[dict]:
    if args.samples:
        data = json.loads(Path(args.samples).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("--samples must be a JSON list")
        return data
    if not args.story:
        raise ValueError("provide --samples or --story")
    text = Path(args.story).read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("story has no frontmatter")
    fm = yaml.safe_load(text.split("---", 2)[1]) or {}
    bcp = fm.get("bcp") or {}
    bcp_total = bcp.get("total")
    if not isinstance(bcp_total, (int, float)) or bcp_total <= 0:
        raise ValueError("story has no positive bcp.total (score it first)")
    if args.actual_hours is not None:
        actual = args.actual_hours
    else:
        # File-convention read; absent without PULSE is expected.
        pm = fm.get("pulse_metrics") or {}
        actual = pm.get("actual_hours")
        if actual is None:
            raise ValueError(
                "no actual_hours: pass --actual-hours (PULSE absent or "
                "pulse_metrics.actual_hours not set)")
    category = args.category or fm.get("category")
    if not category:
        raise ValueError("no category (story frontmatter or --category)")
    sid = args.id or f"{fm.get('story_id', Path(args.story).stem)}"
    at = bcp.get("scored_at") or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    return [{"category": category, "bcp_total": bcp_total,
             "actual_hours": actual, "id": sid, "at": at}]


def recalibrate(baseline: dict, samples: list[dict], allow_dup: bool,
                 now: str) -> dict:
    snap = baseline.setdefault("config_snapshot", {})
    seed = float(snap.get("seed", 4.13))
    min_samples = int(snap.get("min_samples", 5))
    window = int(snap.get("rolling_window", 10))
    cats = baseline.setdefault("categories", {})

    # Chronological order; stable for samples without 'at'.
    ordered = sorted(enumerate(samples),
                     key=lambda t: (str(t[1].get("at") or ""), t[0]))

    summary = {}
    for _, s in ordered:
        cat = s.get("category")
        bt = s.get("bcp_total")
        ah = s.get("actual_hours")
        sid = s.get("id")
        at = s.get("at") or now
        if not cat:
            raise ValueError(f"sample missing category: {s}")
        if not isinstance(bt, (int, float)) or bt <= 0:
            raise ValueError(f"sample bcp_total must be > 0: {s}")
        if not isinstance(ah, (int, float)) or ah <= 0:
            raise ValueError(f"sample actual_hours must be > 0: {s}")

        c = cats.setdefault(cat, {
            "h_per_bcp": seed, "n_samples": 0, "is_seed": True,
            "samples": [], "history": [],
        })
        seen_ids = {x.get("id") for x in c["samples"]} | \
                   {h.get("last_id") for h in c["history"]}
        if sid in seen_ids and not allow_dup:
            summary.setdefault(cat, {"applied": 0, "skipped_dup": 0,
                                     "old_h": c["h_per_bcp"]})
            summary[cat]["skipped_dup"] += 1
            continue

        obs = ah / bt
        c["samples"].append({"id": sid, "bcp_total": bt,
                             "actual_hours": ah, "h": round(obs, 4),
                             "at": at})
        if len(c["samples"]) > window:
            c["samples"] = c["samples"][-window:]
        c["n_samples"] = int(c.get("n_samples", 0)) + 1
        mean_h = sum(x["h"] for x in c["samples"]) / len(c["samples"])
        st = summary.setdefault(cat, {"applied": 0, "skipped_dup": 0,
                                      "old_h": c["h_per_bcp"]})
        c["h_per_bcp"] = round(mean_h, 4)
        c["is_seed"] = c["n_samples"] < min_samples
        st["applied"] += 1
        st["new_h"] = c["h_per_bcp"]
        st["n_samples"] = c["n_samples"]
        st["is_seed"] = c["is_seed"]

    # Per-category history snapshot for this run (audit trail).
    for cat, st in summary.items():
        if st.get("applied"):
            c = cats[cat]
            c["history"].append({
                "at": now, "h_per_bcp": c["h_per_bcp"],
                "n_samples": c["n_samples"], "is_seed": c["is_seed"],
                "applied": st["applied"], "last_id": c["samples"][-1]["id"],
            })
            if len(c["history"]) > HISTORY_CAP:
                c["history"] = c["history"][-HISTORY_CAP:]
    return summary


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--samples", help="JSON list of {category,bcp_total,actual_hours,id?,at?}")
    p.add_argument("--story", type=Path)
    p.add_argument("--actual-hours", type=float, default=None)
    p.add_argument("--category", default=None)
    p.add_argument("--id", default=None)
    p.add_argument("--allow-dup", action="store_true")
    p.add_argument("--now", default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    now = args.now or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    try:
        baseline = yaml.safe_load(
            args.baseline.read_text(encoding="utf-8")) or {}
        samples = load_samples(args)
        summary = recalibrate(baseline, samples, args.allow_dup, now)
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as e:
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        return 1

    result = {"status": "success", "dry_run": bool(args.dry_run),
              "categories": summary}
    if not args.dry_run:
        try:
            args.baseline.write_text(
                yaml.dump(baseline, default_flow_style=False,
                          allow_unicode=True, sort_keys=False),
                encoding="utf-8")
        except OSError as e:
            print(json.dumps({"status": "error", "error": str(e)}, indent=2))
            return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
