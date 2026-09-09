#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Deterministic statistical primitives for the PULSE dashboard.

Every aggregation in `workflow.md` → Step 1 is built from the handful of
functions below. They live in code rather than in prose because an LLM asked to
compute `exp(mean(ln(x)))` over 34 stories carries silent variance: the same
input can yield two different numbers on two runs, and a plausible geometric
mean is indistinguishable from a correct one by eye.

Scope note (issue #111): this module is the arithmetic floor only. Reading
`sprint-status.yaml`, grouping by category, applying the effort guardrails and
rendering markdown stay where they are for now — they are the next slices.

DESIGN RULES, each one load-bearing:

1. **Ratios use the geometric mean, never the arithmetic one.** `h_per_bcp` and
   the leverage family are multiplicative: a story at 2x and one at 0.5x should
   average to 1x, which is what the geometric mean gives and the arithmetic one
   (1.25x) does not.

2. **Sample statistics, not population.** The GSD uses the `n-1` denominator.
   PULSE estimates a process from a handful of stories; it never enumerates a
   closed population.

3. **Thin samples return `None`, never a number.** A GSD from two points has one
   degree of freedom — one outlier owns it. Callers must render "n=2, no band"
   instead of a false interval. `None` is a value the render layer can see;
   a plausible-looking number is not.

4. **Non-positive values are rejected, not silently dropped.** `ln(0)` is
   undefined and a negative ratio is a data defect upstream. Failing loudly here
   is how that defect gets found; skipping the entry would bias the baseline
   downward and hide it forever.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence

__all__ = [
    "geometric_mean",
    "geometric_sd",
    "confidence_band",
    "median",
    "clamped_error_to_accuracy",
    "half_split_direction",
]

# Multiplier for the ~68% band (one geometric SD). The dashboard's typical-cost
# view uses this; the 90% forecast interval uses K_90 below.
K_TYPICAL = 1.0
# 1.645 is the standard normal quantile for 90% two-sided coverage; applied in
# log space it gives the 90% interval of a log-normal.
K_90 = 1.645
# Below this many samples a dispersion estimate is not reported. Three is the
# smallest n with more than one degree of freedom.
MIN_N_FOR_DISPERSION = 3
# A trend needs enough points that a half-split means something.
MIN_N_FOR_TREND = 4


def _validate_positive(values: Sequence[float], where: str) -> list[float]:
    """Reject non-positive input instead of dropping it.

    A zero or negative ratio reaching this module means something upstream wrote
    a bad measurement. Silently skipping it produces a baseline that looks fine
    and is wrong; raising sends the reader to the real defect.
    """
    out = []
    for v in values:
        f = float(v)
        if f <= 0 or math.isnan(f) or math.isinf(f):
            raise ValueError(
                f"{where}: expected a positive finite ratio, got {v!r}. "
                "Zero, negative or non-finite means a defect upstream — fix the "
                "recorded metric rather than filtering it here."
            )
        out.append(f)
    return out


def geometric_mean(values: Sequence[float]) -> Optional[float]:
    """`exp(mean(ln(x)))` — the unbiased centre for multiplicative ratios.

    Computed in log space rather than as `(prod)^(1/n)`: the direct product
    overflows or loses precision well before n gets interesting.

    Empty input returns `None` (there is no centre of nothing) — never 0.0,
    which would read as a real measurement downstream.
    """
    if not values:
        return None
    xs = _validate_positive(values, "geometric_mean")
    return math.exp(sum(math.log(x) for x in xs) / len(xs))


def geometric_sd(values: Sequence[float]) -> Optional[float]:
    """Sample geometric standard deviation: `exp(sample_std(ln(x)))`.

    Returns `None` below `MIN_N_FOR_DISPERSION` — see design rule 3. The caller
    is expected to render the point estimate with an explicit `(n=2)` marker
    rather than inventing an interval.
    """
    if len(values) < MIN_N_FOR_DISPERSION:
        return None
    xs = _validate_positive(values, "geometric_sd")
    logs = [math.log(x) for x in xs]
    mean_log = sum(logs) / len(logs)
    # n-1: sample, not population (design rule 2).
    variance = sum((l - mean_log) ** 2 for l in logs) / (len(logs) - 1)
    return math.exp(math.sqrt(variance))


def confidence_band(
    values: Sequence[float], k: float = K_TYPICAL
) -> Optional[tuple[float, float, float, int]]:
    """`(low, centre, high, n)` around the geometric mean, or `None`.

    The band is multiplicative — `[gm / GSD**k, gm * GSD**k]` — because the
    underlying quantity is a ratio. An additive band around a geometric mean
    would put the lower bound below zero for dispersed samples.

    `k=1.0` is the ~68% typical range; `k=1.645` the ~90% interval. Returns
    `None` when dispersion cannot be estimated, so a thin sample can never be
    rendered as a confident range.
    """
    gm = geometric_mean(values)
    gsd = geometric_sd(values)
    if gm is None or gsd is None:
        return None
    spread = gsd**k
    return (gm / spread, gm, gm * spread, len(values))


def median(values: Sequence[float]) -> Optional[float]:
    """Median, with the even case averaging the two middle values.

    Written out rather than delegated to `statistics.median` so the tie rule is
    visible at the call site: several dashboard aggregations split a cohort on
    this value, and "which side does the middle story fall on" changes the
    segmentation.
    """
    if not values:
        return None
    xs = sorted(float(v) for v in values)
    mid = len(xs) // 2
    if len(xs) % 2:
        return xs[mid]
    return (xs[mid - 1] + xs[mid]) / 2


def clamped_error_to_accuracy(error_pct: float) -> float:
    """`max(0, 100 - E)` — the predictability score.

    The clamp is not cosmetic: an estimate off by 150% would otherwise render as
    -50% predictable, which invites the reading "worse than useless" when the
    honest statement is "we cannot predict this at all". Zero is the floor of the
    scale, not a value to go below.
    """
    return max(0.0, 100.0 - abs(float(error_pct)))


def half_split_direction(
    ordered_errors: Sequence[float], tolerance_pct: float = 5.0
) -> str:
    """Compare the median error of the first half against the second.

    Returns `converging` (error falling — estimates closing on reality),
    `diverging`, `stable`, or `insufficient` below `MIN_N_FOR_TREND`.

    The tolerance exists so that noise does not read as a trend: with PULSE's
    sample sizes a two-point median shift is well within what one story can move,
    and an arrow that flips every run teaches the reader to ignore it.

    Note the direction convention: the input is *error*, so falling error is the
    good outcome. Callers that render an accuracy arrow must not invert this
    twice.
    """
    n = len(ordered_errors)
    if n < MIN_N_FOR_TREND:
        return "insufficient"
    half = n // 2
    first = median([abs(float(e)) for e in ordered_errors[:half]])
    second = median([abs(float(e)) for e in ordered_errors[n - half :]])
    if first is None or second is None:
        return "insufficient"
    delta = second - first
    if abs(delta) <= tolerance_pct:
        return "stable"
    return "diverging" if delta > 0 else "converging"
