#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Forecast and drift detection, ported from `workflow.md` (issue #111).

Fourth slice. The two forward-looking aggregations:

    cohort_drift        estimation drift per (category, segment), shared with
                        `bmad-pulse-track-start` as an at-estimation-time alert
    capacity_forecast   hours to finish the remaining scored backlog

Forecasting is where a dashboard is most tempted to lie, so two rules from the
spec are enforced in the return shape rather than left to the renderer:

1. LEAD WITH THE BAND, NEVER THE POINT. `~412h` reads as precision the data
   does not have; the 90% interval can be many-x wide when baselines are thin.
   `point` is present but always accompanied by `low_90`/`high_90` and by a
   `precision` flag derived from how much of the backlog has no baseline of its
   own.

2. SILENCE BEATS A FALSE ALARM. A cohort with fewer than 3 samples returns
   `insufficient` and callers must stay quiet. Drift computed from 1-2 stories
   is owned by its outlier, and a spurious alert at estimation time trains the
   team to ignore the real ones.

The total band deliberately SUMS the per-category bounds instead of combining
them in quadrature. That assumes correlated errors, which is the conservative
choice: when one category's baseline is off, the others usually are too (same
team, same period, same estimation habits).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Optional

from pulse_stats import confidence_band, geometric_mean, half_split_direction, median
from pulse_aggregations import (
    EFFORT_FLOOR_HOURS,
    MIN_N_FOR_SEGMENT,
    Story,
    h_per_bcp_by_category,
    segment_split,
)

__all__ = [
    "COHORT_WINDOW",
    "DRIFT_ALERT_THRESHOLD_PCT",
    "cohort_key",
    "cohort_drift",
    "drift_watchlist",
    "capacity_forecast",
]

# Only the last K completed stories of a cohort count: a baseline that never
# forgets cannot detect that a team got better.
COHORT_WINDOW = 5
# Median absolute drift above this puts a cohort on the watchlist.
DRIFT_ALERT_THRESHOLD_PCT = 25.0


def cohort_key(story: Story, split: Optional[float]) -> tuple:
    """`(category, segment)` when the story is BCP-scored, else `(category,)`.

    The fallback is what keeps non-BCP projects working: they still cohort by
    category instead of collapsing into one meaningless global bucket.
    """
    total = story.bcp_total
    if total is None or split is None:
        return (story.category,)
    return (story.category, "micro" if total < split else "story")


def cohort_drift(stories: Iterable[Story], key: tuple,
                 split: Optional[float] = None) -> dict:
    """Median absolute estimate error over the last `COHORT_WINDOW` stories.

    Returns `status: insufficient` below `MIN_N_FOR_SEGMENT` samples — callers
    must stay silent rather than raise an alarm a single story could explain.
    """
    stories = list(stories)
    if split is None:
        split = segment_split(stories)

    matching = [s for s in stories if cohort_key(s, split) == key]
    recent = matching[-COHORT_WINDOW:]  # file order = chronological proxy
    errors = [e for e in (s.estimate_error_pct for s in recent) if e is not None]

    if len(errors) < MIN_N_FOR_SEGMENT:
        return {
            "status": "insufficient",
            "median_abs_drift_pct": None,
            "n": len(errors),
            "sample_story_ids": [s.key for s in recent],
        }
    return {
        "status": "ok",
        "median_abs_drift_pct": median(errors),
        "n": len(errors),
        "sample_story_ids": [s.key for s in recent],
    }


def drift_watchlist(stories: Iterable[Story]) -> list[dict]:
    """Cohorts drifting past the threshold, worst first.

    Healthy cohorts are omitted entirely — an empty list is the healthy default,
    not missing data. Listing everything would bury the signal it exists to
    surface.
    """
    stories = list(stories)
    split = segment_split(stories)
    keys = {cohort_key(s, split) for s in stories}

    out = []
    for key in keys:
        d = cohort_drift(stories, key, split)
        if d["status"] != "ok":
            continue
        value = d["median_abs_drift_pct"]
        if value is None or value <= DRIFT_ALERT_THRESHOLD_PCT:
            continue
        matching = [s for s in stories if cohort_key(s, split) == key]
        errors = [e for e in (s.estimate_error_pct for s in matching) if e is not None]
        out.append({
            "cohort": key,
            "label": " / ".join(key),
            "median_abs_drift_pct": value,
            "n": d["n"],
            "trend": half_split_direction(errors),
        })
    return sorted(out, key=lambda e: e["median_abs_drift_pct"], reverse=True)


def capacity_forecast(stories: Iterable[Story],
                      remaining_bcp_by_category: dict) -> dict:
    """Hours to finish the remaining scored backlog, as a BAND.

    `remaining_bcp_by_category` is read-only input from the caller (scored
    stories with no `pulse_metrics` entry yet). PULSE never writes story files,
    the BCP baseline, or any estimate.

    A category with no baseline of its own (n < 3) falls back to the pooled
    factor across all categories and is marked low-confidence. `precision`
    summarises that exposure so the band is never read as more solid than it is:

        pooled_pct > 50  -> baixa
        pooled_pct > 20  -> média
        else             -> alta
    """
    stories = list(stories)
    remaining = {
        k: float(v)
        for k, v in (remaining_bcp_by_category or {}).items()
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0
    }
    if not remaining:
        return {"status": "no_backlog", "point": None, "low_90": None,
                "high_90": None, "by_category": {}, "precision": None,
                "remaining_bcp_total": 0.0}

    agg = h_per_bcp_by_category(stories)["by_category"]

    # Pooled fallback: every eligible h/BCP ratio, regardless of category.
    all_ratios = [
        s.h_per_bcp_actual
        for s in stories
        if s.above_effort_floor and s.h_per_bcp_actual is not None
    ]
    all_ratios = [r for r in all_ratios if r is not None]
    pooled_factor = geometric_mean(all_ratios) if all_ratios else None
    pooled_band = confidence_band(all_ratios) if all_ratios else None

    if pooled_factor is None:
        return {"status": "no_baseline", "point": None, "low_90": None,
                "high_90": None, "by_category": {}, "precision": None,
                "remaining_bcp_total": sum(remaining.values())}

    per_cat: dict[str, dict] = {}
    total_point = total_low = total_high = 0.0
    pooled_bcp = 0.0

    for cat, bcp in sorted(remaining.items()):
        entry = agg.get(cat, {}).get("pooled") if cat in agg else None
        own = bool(entry and entry["n"] >= MIN_N_FOR_SEGMENT and entry["geo_mean"])
        if own and entry is not None:
            factor = entry["geo_mean"]
            band = entry["band"]
        else:
            factor = pooled_factor
            band = (pooled_band[0], pooled_band[2]) if pooled_band else None
            pooled_bcp += bcp

        low_f, high_f = band if band else (factor, factor)
        point_h, low_h, high_h = bcp * factor, bcp * low_f, bcp * high_f
        per_cat[cat] = {
            "remaining_bcp": bcp,
            "hours": point_h,
            "low_90": low_h,
            "high_90": high_h,
            "confidence": "ok" if own else "baixa (pooled)",
            "n": (entry["n"] if entry else 0),
        }
        total_point += point_h
        # Conservative on purpose: summing bounds assumes correlated errors.
        total_low += low_h
        total_high += high_h

    remaining_total = sum(remaining.values())
    pooled_pct = pooled_bcp / remaining_total * 100 if remaining_total else 0.0
    precision = "baixa" if pooled_pct > 50 else ("média" if pooled_pct > 20 else "alta")

    return {
        "status": "ok",
        "point": total_point,
        "low_90": total_low,
        "high_90": total_high,
        "by_category": per_cat,
        "remaining_bcp_total": remaining_total,
        "pooled_bcp": pooled_bcp,
        "pooled_pct": pooled_pct,
        "precision": precision,
        # Enforced in the return shape: a renderer must not headline `point`.
        "lead_with": "band",
        "effort_floor_hours": EFFORT_FLOOR_HOURS,
    }
