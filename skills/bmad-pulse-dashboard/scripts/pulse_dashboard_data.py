#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml>=6.0"]
# ///
"""One deterministic pass over `sprint-status.yaml` → every dashboard number.

Final slice of #111. This is the entry point the skill calls instead of doing
arithmetic in prose:

    python3 scripts/pulse_dashboard_data.py --sprint-status <path> [--json]

The division of labour this establishes:

    script  computes every number                (deterministic, testable)
    agent   writes prose, insights, framing      (what an LLM is actually good at)

An LLM computing a median is non-deterministic — same input, two possible
answers — and it fails silently, because a plausible median is indistinguishable
from a correct one. Everything above this line is now reproducible; everything
below it stays with the agent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:  # same contract as the other scripts in this repo
    print("Error: pyyaml is required (PEP 723 dependency)", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pulse_aggregations import (  # noqa: E402
    avg_leverage_vs_reference,
    h_per_bcp_by_category,
    load_stories,
    predictability,
    reference_regime_breaks,
    segment_split,
)
from pulse_forecast import capacity_forecast, drift_watchlist  # noqa: E402
from pulse_process import process_health_summary  # noqa: E402

__all__ = ["parse_sprint_status", "build_dashboard_data", "render_summary", "main"]


def parse_sprint_status(text: str) -> dict:
    """Parse the sprint-status file. Returns {} for empty input."""
    return yaml.safe_load(text) or {}


def build_dashboard_data(sprint_status: dict,
                         remaining_bcp_by_category: Optional[dict] = None) -> dict:
    """Every number the dashboard renders, in one deterministic pass.

    Read-only over consumer data: nothing here writes a story file, the BCP
    baseline, or any estimate.
    """
    stories = load_stories((sprint_status or {}).get("pulse_metrics") or {})
    return {
        "stories_measured": len(stories),
        "predictability": predictability(stories),
        "h_per_bcp": h_per_bcp_by_category(stories),
        "leverage_vs_reference": avg_leverage_vs_reference(stories),
        "segment_split": segment_split(stories),
        "reference_regime": reference_regime_breaks(stories),
        "process_health": process_health_summary(stories),
        "drift_watchlist": drift_watchlist(stories),
        "forecast": capacity_forecast(stories, remaining_bcp_by_category or {}),
    }


def _fmt(value, suffix="", nd=1):
    """Missing renders as an em dash, never as 0 — absent is not a measurement."""
    return "—" if value is None else f"{value:.{nd}f}{suffix}"


def render_summary(data: dict) -> str:
    """Human-readable figures — the numbers only.

    Narrative, insights and anti-Goodhart framing stay with the agent; this
    exists so a human can eyeball the values without reading JSON.
    """
    out = [f"Stories medidas: {data['stories_measured']}"]

    p = data["predictability"]
    out.append(
        f"Previsibilidade: {_fmt(p['score'], '%')} "
        f"(margem de erro {_fmt(p['median_error_pct'], '%')}, n={p['n']}, {p['trend']})"
    )

    lv = data["leverage_vs_reference"]
    if lv["mean"] is not None:
        out.append(
            f"Alavancagem vs referência: {_fmt(lv['mean'], 'x')} "
            f"(geométrica {_fmt(lv['geo_mean'], 'x')}, n={lv['n']})"
        )

    fp = data["process_health"]["first_pass"]
    if fp["rate"] is not None:
        out.append(f"First-pass: {_fmt(fp['rate'], '%')} ({fp['passed']}/{fp['total']})")

    h = data["h_per_bcp"]
    if h["by_category"]:
        out.append(f"h/BCP (split micro/story = {_fmt(h['segment_split'], '', 0)}):")
        for cat, e in h["by_category"].items():
            band = e["pooled"]["band"]
            faixa = f" [{band[0]:.3f}–{band[1]:.3f}]" if band else ""
            out.append(
                f"  {cat}: {_fmt(e['pooled']['geo_mean'], '', 3)}{faixa} "
                f"(n={e['pooled']['n']})"
            )

    wl = data["drift_watchlist"]
    out.append(
        "Drift: nenhuma coorte acima do limiar"
        if not wl
        else f"Drift ({len(wl)} coortes): "
        + ", ".join(f"{e['label']} {e['median_abs_drift_pct']:.0f}%" for e in wl)
    )

    rr = data["reference_regime"]
    if not rr["single_regime"]:
        out.append(f"⚠ Regime de referência múltiplo: {list(rr['rates'])}")

    f = data["forecast"]
    if f["status"] == "ok":
        # Band first, point second — the point alone is false precision.
        out.append(
            f"Previsão: [{f['low_90']:.0f}–{f['high_90']:.0f}]h "
            f"(ponto ~{f['point']:.0f}h, precisão {f['precision']})"
        )
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Compute every dashboard number deterministically (issue #111)."
    )
    ap.add_argument("--sprint-status", required=True, type=Path)
    ap.add_argument(
        "--remaining-bcp",
        type=str,
        default=None,
        help='JSON map of remaining BCP per category, e.g. \'{"backend": 120}\'',
    )
    ap.add_argument("--json", action="store_true", help="emit the full data structure")
    args = ap.parse_args(argv)

    if not args.sprint_status.exists():
        print(f"error: {args.sprint_status} not found", file=sys.stderr)
        return 1

    try:
        remaining = json.loads(args.remaining_bcp) if args.remaining_bcp else {}
    except json.JSONDecodeError as exc:
        print(f"error: --remaining-bcp is not valid JSON: {exc}", file=sys.stderr)
        return 1

    data = build_dashboard_data(
        parse_sprint_status(args.sprint_status.read_text(encoding="utf-8")), remaining
    )
    print(
        json.dumps(data, indent=2, ensure_ascii=False, default=str)
        if args.json
        else render_summary(data)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
