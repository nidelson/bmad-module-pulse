#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Process-health aggregations, ported from `workflow.md` (issue #111).

Third slice. Covers the quality-and-friction half of the dashboard:

    first_pass_rate     did the work pass review without rework?
    review_cycles       how much rework, when it did not
    halt_aggregations   where the wall-clock went that was not work

`halts` is the awkward one: the field has three valid shapes across the corpus,
and the spec is explicit that all three must be handled *without crashing*. The
shapes are not interchangeable — B carries durations, C does not — so the code
never guesses a missing duration. An unknown minute count stays unknown and is
reported as such, because a zero would silently understate approval friction.

Anti-Goodhart, ported verbatim from the invariant in `workflow.md`:

    leverage = estimated_hours / actual_hours

    When the estimation basis is calibrated, this ratio collapses to ~1.0x BY
    CONSTRUCTION. So a HIGH multiplier signals an inflated or uncalibrated
    basis, NOT speed — and a leverage TARGET would literally reward never
    calibrating. `vs_plano_leverage` is therefore computed (predictability math
    needs it) and deliberately NOT rendered as a metric.

`first_pass_rate` is a rate over a small denominator and the temptation is to
report it alone; `process_health_summary` keeps the raw counts next to it so a
reader can see 27/33 rather than a lone percentage.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable, Optional

from pulse_aggregations import Story

__all__ = [
    "HaltEntry",
    "normalize_halts",
    "first_pass_rate",
    "review_cycle_stats",
    "halt_aggregations",
    "vs_plano_leverage",
    "process_health_summary",
]

# Shape C prefixes → kind. Only `approval_wait` is inferable from legacy strings;
# anything else stays `unknown` rather than being forced into a bucket.
_LEGACY_PREFIXES = ("approval_wait",)


class HaltEntry:
    """One halt, normalized across the three shapes.

    `duration_min is None` means UNKNOWN, never zero. The distinction matters:
    zero would quietly pull the approval-wait average down and understate the
    friction the metric exists to expose.
    """

    __slots__ = ("kind", "context", "duration_min", "pre_approved_batch", "shape")

    def __init__(self, kind="unknown", context=None, duration_min=None,
                 pre_approved_batch: Any = False, shape="B"):
        self.kind = kind
        self.context = context
        self.duration_min = duration_min
        self.pre_approved_batch = bool(pre_approved_batch)
        self.shape = shape

    @property
    def is_approval_wait(self) -> bool:
        return self.kind == "approval_wait"

    @property
    def counts_toward_minutes(self) -> bool:
        """Pre-approved batches are excluded: waiting on a batch the human
        already authorised is not friction the process should be charged for.
        """
        return (
            self.is_approval_wait
            and self.duration_min is not None
            and not self.pre_approved_batch
        )


def normalize_halts(raw: Any) -> tuple[list[HaltEntry], int, int]:
    """Return (entries, opaque_count, legacy_string_count) for any shape.

    Shape A (int) is an OPAQUE COUNT: it contributes to `total_halts` but yields
    no entries, because inventing entries would fabricate kinds that were never
    recorded. It is returned separately rather than mixed into the entry list.
    """
    if raw is None:
        return [], 0, 0

    # Shape A — bool first: `True` is an int in Python and would count as 1 halt.
    if isinstance(raw, bool):
        return [], 0, 0
    if isinstance(raw, int):
        return [], max(raw, 0), 0

    if not isinstance(raw, list):
        return [], 0, 0  # unknown shape: degrade, never crash

    entries: list[HaltEntry] = []
    legacy = 0
    for item in raw:
        if isinstance(item, dict):  # Shape B
            entries.append(
                HaltEntry(
                    kind=str(item.get("kind") or "unknown"),
                    context=item.get("context"),
                    duration_min=_coerce_minutes(item.get("duration_min")),
                    pre_approved_batch=item.get("pre_approved_batch"),
                    shape="B",
                )
            )
        elif isinstance(item, str):  # Shape C — legacy, pre-0.5.0
            legacy += 1
            kind = "unknown"
            for prefix in _LEGACY_PREFIXES:
                if item.startswith(prefix):
                    kind = prefix
                    break
            # duration_min stays None: counted as a halt, excluded from minutes.
            entries.append(HaltEntry(kind=kind, context=item, shape="C"))
    return entries, 0, legacy


def _coerce_minutes(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        minutes = float(value)
    except (TypeError, ValueError):
        return None
    return minutes if minutes >= 0 else None


def first_pass_rate(stories: Iterable[Story]) -> dict:
    """Share of stories approved without rework.

    Only stories that actually carry `first_pass` count. A missing field is NOT
    a failure — treating absence as `False` would invent rework that never
    happened and make older entries look worse than they were.
    """
    flags = [
        s.raw.get("first_pass") for s in stories if isinstance(s.raw.get("first_pass"), bool)
    ]
    if not flags:
        return {"rate": None, "passed": 0, "total": 0, "not_first_pass": []}
    passed = sum(1 for f in flags if f)
    not_first = [
        s.key for s in stories if s.raw.get("first_pass") is False
    ]
    return {
        "rate": passed / len(flags) * 100,
        "passed": passed,
        "total": len(flags),
        "not_first_pass": not_first,
    }


def review_cycle_stats(stories: Iterable[Story]) -> dict:
    """Rework volume: review cycles and dev attempts.

    Reported as a distribution, not just a mean: `{1: 27, 2: 4, 3: 2}` says
    something a mean of 1.3 hides — that most stories pass in one cycle and a
    few needed three.
    """
    cycles = [s.raw.get("review_cycles") for s in stories]
    cycles = [int(c) for c in cycles if isinstance(c, int) and not isinstance(c, bool)]
    devs = [s.raw.get("dev_count") for s in stories]
    devs = [int(d) for d in devs if isinstance(d, int) and not isinstance(d, bool)]
    return {
        "review_cycles": {
            "mean": (sum(cycles) / len(cycles)) if cycles else None,
            "max": max(cycles) if cycles else None,
            "distribution": dict(sorted(Counter(cycles).items())),
            "n": len(cycles),
        },
        "dev_attempts": {
            "mean": (sum(devs) / len(devs)) if devs else None,
            "max": max(devs) if devs else None,
            "distribution": dict(sorted(Counter(devs).items())),
            "n": len(devs),
        },
    }


def halt_aggregations(stories: Iterable[Story]) -> dict:
    """Where the wall-clock went that was not work.

    `total_halts` counts every shape (Shape A integers plus list lengths), while
    minute totals draw only on Shape B — the only shape that records duration.
    `approval_wait_unknown_minutes` makes that gap explicit instead of letting a
    reader mistake a partial sum for the whole.
    """
    total_halts = 0
    legacy_strings = 0
    approval_count = 0
    approval_minutes = 0.0
    unknown_minutes = 0
    pre_approved = 0
    by_kind: Counter = Counter()
    per_story: list[tuple[str, Optional[float]]] = []

    for s in stories:
        ph = s.raw.get("process_health") or {}
        entries, opaque, legacy = normalize_halts(ph.get("halts") if isinstance(ph, dict) else None)
        total_halts += opaque + len(entries)
        legacy_strings += legacy

        story_minutes: Optional[float] = None
        has_approval = False
        for e in entries:
            by_kind[e.kind] += 1
            if not e.is_approval_wait:
                continue
            has_approval = True
            approval_count += 1
            if e.pre_approved_batch:
                pre_approved += 1
            elif e.duration_min is None:
                unknown_minutes += 1
            else:
                approval_minutes += e.duration_min
                story_minutes = (story_minutes or 0.0) + e.duration_min
        if has_approval:
            per_story.append((s.key, story_minutes))

    return {
        "total_halts": total_halts,
        "by_kind": dict(by_kind.most_common()),
        "approval_wait_count": approval_count,
        "approval_wait_minutes": approval_minutes,
        "approval_wait_unknown_minutes": unknown_minutes,
        "pre_approved_batch_count": pre_approved,
        "legacy_halt_string_count": legacy_strings,
        "stories_with_approval_wait": per_story,
    }


def vs_plano_leverage(stories: Iterable[Story]) -> dict:
    """`estimated_hours / actual_hours` — COMPUTED, NEVER RENDERED AS A METRIC.

    ⚠️ ANTI-GOODHART INVARIANT (ported verbatim from `workflow.md`).
    A calibrated estimation basis drives this ratio to ~1.0x by construction, so
    a high value means the basis was inflated, not that the team was fast. A
    leverage target here would reward never calibrating.

    The return carries `render: False` and `collapses_to` so a caller that tries
    to render it has to override an explicit flag rather than trip over silence.
    """
    ratios = []
    for s in stories:
        est, act = s.estimated_hours, s.actual_hours
        if est is None or act is None or act < 0.1 or est <= 0:
            continue
        ratios.append(est / act)
    if not ratios:
        return {"mean": None, "min": None, "max": None, "n": 0, "render": False}
    return {
        "mean": sum(ratios) / len(ratios),
        "min": min(ratios),
        "max": max(ratios),
        "n": len(ratios),
        "render": False,
        "collapses_to": 1.0,
        "why_not_rendered": (
            "A calibrated basis drives this to ~1.0x by construction; a high "
            "value signals an inflated basis, not speed. It IS the "
            "predictability signal — see the hero metric."
        ),
    }


def process_health_summary(stories: Iterable[Story]) -> dict:
    """Everything the process-health section needs, in one pass."""
    stories = list(stories)
    fp = first_pass_rate(stories)
    unused: Counter = Counter()
    flow_complete = 0
    flow_known = 0
    for s in stories:
        ph = s.raw.get("process_health")
        if not isinstance(ph, dict):
            continue
        for skill in ph.get("unused_skills") or []:
            unused[str(skill)] += 1
        if isinstance(ph.get("flow_complete"), bool):
            flow_known += 1
            flow_complete += 1 if ph["flow_complete"] else 0
    return {
        "first_pass": fp,
        "cycles": review_cycle_stats(stories),
        "halts": halt_aggregations(stories),
        "vs_plano": vs_plano_leverage(stories),
        "flow_complete": {"complete": flow_complete, "known": flow_known},
        "most_unused_skills": dict(unused.most_common(5)),
    }
