#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Core dashboard aggregations, ported from `workflow.md` → Step 1 (issue #111).

Second slice. Builds on `pulse_stats.py` (slice 1) and covers the three
aggregations the dashboard reads first:

    predictability_score      the hero metric
    h_per_bcp_by_category     the typical-cost baseline
    avg_leverage_vs_reference the sellable multiplier

PORTING RULE: this is a translation, not a redesign. Where the prose specifies
a behaviour, the code reproduces it — including the choices this module's author
would have made differently. One such tension is flagged inline (see
`avg_leverage_vs_reference`) and raised for a human rather than silently
"fixed": changing a published metric's definition under the cover of a refactor
is how a dashboard starts lying about its own history.

The two guardrails are global and easy to get subtly wrong, so they live in one
place each and every caller goes through them:

- `EFFORT_FLOOR_HOURS` — stories under it are excluded from typical-cost and
  leverage aggregates (a 2-minute patch divides by almost zero and reads as
  500x), but stay in raw counts and are still rendered, marked.
- `MIN_N_FOR_SEGMENT` — a (category, segment) pair thinner than this is not
  reported on its own; its stories still count in the category's pooled figure.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Optional

from pulse_stats import (
    clamped_error_to_accuracy,
    confidence_band,
    geometric_mean,
    half_split_direction,
    median,
)

__all__ = [
    "EFFORT_FLOOR_HOURS",
    "MIN_N_FOR_SEGMENT",
    "Story",
    "load_stories",
    "predictability",
    "segment_split",
    "h_per_bcp_by_category",
    "avg_leverage_vs_reference",
    "reference_regime_breaks",
]

# ≈6 minutes. Below this, `reference / actual` is division by almost zero: a
# dependency bump reads as 500x leverage and drags a category baseline toward 0.
EFFORT_FLOOR_HOURS = 0.1
# A (category, segment) pair needs this many eligible stories to be reported on
# its own; below it, the stories fold into the category's pooled baseline.
MIN_N_FOR_SEGMENT = 3


class Story:
    """One `pulse_metrics` entry, with the field access rules applied once.

    The dashboard's prose repeats "read X, fall back to Y" for several fields;
    concentrating that here keeps every aggregation reading the same value.
    """

    __slots__ = ("key", "raw")

    def __init__(self, key: str, raw: dict):
        self.key = key
        self.raw = raw or {}

    def _num(self, *path) -> Optional[float]:
        node: Any = self.raw
        for p in path:
            if not isinstance(node, dict):
                return None
            node = node.get(p)
        if node is None or isinstance(node, bool):
            return None
        try:
            return float(node)
        except (TypeError, ValueError):
            return None

    @property
    def category(self) -> str:
        return str(self.raw.get("category") or "uncategorized")

    @property
    def actual_hours(self) -> Optional[float]:
        return self._num("actual_hours")

    @property
    def estimated_hours(self) -> Optional[float]:
        return self._num("estimated_hours")

    @property
    def leverage_vs_reference(self) -> Optional[float]:
        return self._num("leverage_vs_reference")

    @property
    def estimated_hours_reference(self) -> Optional[float]:
        return self._num("estimated_hours_reference")

    @property
    def h_per_bcp_actual(self) -> Optional[float]:
        return self._num("bcp_recorded", "h_per_bcp_actual")

    @property
    def bcp_total(self) -> Optional[float]:
        """Final BCP, never the start snapshot.

        `bcp_at_start` is only a fallback: when a story is rescored mid-flight
        the two differ, and the snapshot reports a rate that was never in force
        — which invents a governance breach that never happened.
        """
        recorded = self._num("bcp_recorded", "total")
        return recorded if recorded is not None else self._num("bcp_at_start", "total")

    @property
    def is_rescored(self) -> bool:
        """Start and final BCP disagree — the label the render layer must show."""
        a = self._num("bcp_recorded", "total")
        b = self._num("bcp_at_start", "total")
        return a is not None and b is not None and a != b

    @property
    def estimate_error_pct(self) -> Optional[float]:
        """Persisted value when present; recomputed for older entries.

        The two are identical by definition — track-done writes exactly this —
        so preferring the persisted one costs nothing and keeps the dashboard
        consistent with what the story file says about itself.
        """
        persisted = self._num("estimate_error_pct")
        if persisted is not None:
            return abs(persisted)
        actual, estimated = self.actual_hours, self.estimated_hours
        if actual is None or estimated is None:
            return None
        # Floor the denominator: a zero estimate would otherwise divide by zero.
        return abs(actual - estimated) / max(estimated, 0.01) * 100

    @property
    def above_effort_floor(self) -> bool:
        """False for near-zero-effort stories AND for stories with no hours.

        Unknown effort is not "passes the floor": admitting it would let an
        unmeasured story into a cost baseline as if it were free.
        """
        hours = self.actual_hours
        return hours is not None and hours >= EFFORT_FLOOR_HOURS


def load_stories(pulse_metrics: dict) -> list[Story]:
    """Wrap raw entries, preserving file order (the chronological proxy).

    Story order is what every trend in this module splits on. Sorting here — by
    key, by date, by anything — would silently change the trend arrows.
    """
    return [Story(k, v) for k, v in (pulse_metrics or {}).items() if isinstance(v, dict)]


def predictability(stories: Iterable[Story]) -> dict:
    """The hero metric: accuracy, higher is better, target 100%.

    Deliberately computed over ALL stories with an error — the effort floor does
    not apply here. A two-minute story that took two minutes was predicted
    correctly; excluding it would discard a real signal. The floor exists for
    ratios with `actual_hours` in the denominator, which this is not.
    """
    errors = [e for e in (s.estimate_error_pct for s in stories) if e is not None]
    med = median(errors) if errors else None
    if med is None:
        return {"score": None, "median_error_pct": None, "trend": "insufficient", "n": 0}
    return {
        "score": clamped_error_to_accuracy(med),
        "median_error_pct": med,
        # Input is error, so `converging` means error falling = accuracy rising.
        "trend": half_split_direction(errors),
        "n": len(errors),
    }


def segment_split(stories: Iterable[Story]) -> Optional[float]:
    """Median BCP total over ALL scored stories — the micro/story boundary.

    Data-driven on purpose: the dashboard assumes nothing about the BCP point
    scale and never reads the BCP baseline to find out.

    Computed over every scored story, including near-zero-effort ones. "Raw
    counts stay raw": the split is a property of story SIZE, and effort is a
    different axis — filtering here would move the boundary for everyone.
    """
    totals = [s.bcp_total for s in stories]
    totals = [t for t in totals if t is not None and t > 0]
    return median(totals) if totals else None


def _segment_of(story: Story, split: Optional[float]) -> str:
    total = story.bcp_total
    if split is None or total is None:
        return "all"
    return "micro" if total < split else "story"


def h_per_bcp_by_category(stories: Iterable[Story]) -> dict:
    """Typical cost per BCP point, per (category, segment), plus pooled `all`.

    Geometric mean, because h/BCP is a multiplicative ratio: one 10x story must
    not drag the baseline the way an arithmetic mean would.

    Thin-segment fallback: a pair below `MIN_N_FOR_SEGMENT` is not reported on
    its own, but its stories still count in the category's pooled `all` figure —
    they are not discarded, only not shown as a segment of their own.
    """
    stories = list(stories)
    split = segment_split(stories)

    eligible = [
        s for s in stories if s.above_effort_floor and s.h_per_bcp_actual is not None
    ]
    excluded = sum(
        1
        for s in stories
        if s.h_per_bcp_actual is not None and not s.above_effort_floor
    )

    by_pair: dict[tuple[str, str], list[float]] = defaultdict(list)
    by_cat: dict[str, list[float]] = defaultdict(list)
    for s in eligible:
        h = s.h_per_bcp_actual
        if h is None:  # already filtered above; keeps the type narrow
            continue
        by_pair[(s.category, _segment_of(s, split))].append(h)
        by_cat[s.category].append(h)

    out: dict[str, dict] = {}
    for cat, values in sorted(by_cat.items()):
        band = confidence_band(values)
        entry = {
            "pooled": {
                "geo_mean": geometric_mean(values),
                "n": len(values),
                # None below 3 samples: a band from 1 degree of freedom is owned
                # by its outlier, and rendering it would be false precision.
                "band": (band[0], band[2]) if band else None,
            },
            "segments": {},
        }
        for seg in ("micro", "story"):
            vals = by_pair.get((cat, seg), [])
            if len(vals) < MIN_N_FOR_SEGMENT:
                continue  # folded into pooled above, not lost
            b = confidence_band(vals)
            entry["segments"][seg] = {
                "geo_mean": geometric_mean(vals),
                "n": len(vals),
                "band": (b[0], b[2]) if b else None,
            }
        out[cat] = entry

    return {
        "by_category": out,
        "segment_split": split,
        "excluded_below_effort_floor": excluded,
    }


def avg_leverage_vs_reference(stories: Iterable[Story]) -> dict:
    """The sellable multiplier, vs the frozen market-quote reference.

    Computed only over stories that carry `leverage_vs_reference`; stories
    without a frozen reference contribute nothing, and the metric is simply
    absent when none has one (graceful degradation, not a zero).

    ⚠️ PORTED AS SPECIFIED, AND THE AUTHOR DISAGREES — raised, not changed.
    The spec says "the mean", so this is the arithmetic mean. But leverage is a
    RATIO, and slice 1 exists precisely because the arithmetic mean is the wrong
    centre for ratios: it is pulled upward by high outliers, which on a metric
    labelled "the number that sells" biases in the flattering direction. The
    geometric mean is reported alongside as `geo_mean` so the difference is
    visible without changing what the dashboard has always published. Deciding
    which becomes the headline is a product call about a public metric, not a
    refactor — see the PR discussion.
    """
    eligible = [
        s
        for s in stories
        if s.leverage_vs_reference is not None and s.above_effort_floor
    ]
    excluded = sum(
        1
        for s in stories
        if s.leverage_vs_reference is not None and not s.above_effort_floor
    )
    if not eligible:
        return {
            "mean": None,
            "geo_mean": None,
            "n": 0,
            "by_category": {},
            "excluded_below_effort_floor": excluded,
        }

    values = [
        v for v in (s.leverage_vs_reference for s in eligible) if v is not None
    ]
    by_cat: dict[str, list[Story]] = defaultdict(list)
    for s in eligible:
        by_cat[s.category].append(s)

    per_cat = {}
    for cat, items in sorted(by_cat.items()):
        vals = [v for v in (s.leverage_vs_reference for s in items) if v is not None]
        if not vals:
            continue
        best = max(items, key=lambda s: s.leverage_vs_reference or 0.0)
        per_cat[cat] = {
            "mean": sum(vals) / len(vals),
            "geo_mean": geometric_mean(vals),
            "n": len(vals),
            "best": (best.key, best.leverage_vs_reference),
        }

    return {
        "mean": sum(values) / len(values),
        "geo_mean": geometric_mean(values),
        "n": len(values),
        "by_category": per_cat,
        "excluded_below_effort_floor": excluded,
    }


def reference_regime_breaks(stories: Iterable[Story]) -> dict:
    """Detect a changed governed reference rate across stories.

    The implied rate is `estimated_hours_reference / bcp_total` — a read-only
    division of two recorded telemetry fields, never a BCP→hours conversion and
    never a baseline read.

    Rescored stories are labelled rather than silently compared: when start and
    final BCP disagree, a reader auditing the rate needs to know which number
    produced it.
    """
    rates: dict[float, list[str]] = defaultdict(list)
    rescored: list[str] = []
    for s in stories:
        ref, total = s.estimated_hours_reference, s.bcp_total
        if ref is None or not total:
            continue
        rates[round(ref / total, 4)].append(s.key)
        if s.is_rescored:
            rescored.append(s.key)
    return {
        "rates": dict(sorted(rates.items())),
        "single_regime": len(rates) <= 1,
        "rescored_stories": rescored,
    }
