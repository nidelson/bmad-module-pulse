# PULSE ↔ BCP Integration

`pulse_estimation_method=bcp` lets PULSE report productivity for teams that
estimate in **Business Complexity Points** (BCP, a CI&T-shaped methodology —
<https://ciandt.com/us/en-us/complexitypoints>) instead of raw hours.

> **Port in progress ([#84](https://github.com/nidelson/bmad-module-pulse/issues/84)).** BCP is being absorbed into PULSE as an optional feature. The ruler
> (`bmad-bcp-rule-card`) and scoring (`bmad-bcp-score`) now ship here; calibration
> (`recalibrate`, `backfill-baseline`, `rescore`, `score-batch`) is still in the
> companion module until Phase 3. This page describes the boundary as it stands
> today — a boundary that is half internal, so read "companion module" below as
> "the part that has not moved yet".
>
> What does **not** change with the port: `bcp` stays opt-in with `hours` as the
> default, the frontmatter contract keeps its schema, and PULSE still never
> writes `bcp.*` itself.

PULSE stays **passive** toward BCP data: it never computes hours from BCP, never
owns the BCP baseline, and never writes to story frontmatter. The single-writer
principle survives the port unchanged — `apply_score.py` is the only thing that
writes `bcp.*`, and PULSE only reads those fields.

The scoring side — the scoring agent, scoring rules, baseline calibration, and
the `estimated_hours` derivation — originated in the companion module
[`bmad-module-bcp`](https://github.com/nidelson/bmad-module-bcp), which is being
deprecated in favour of this one.

## Ownership Boundary

PULSE → BCP coupling: **zero**. PULSE does not know how BCP scores anything.
BCP → PULSE coupling: **zero**. BCP optionally reads `pulse_metrics` in its own
`recalibrate` skill, by file convention only.

| Field                       | Owner                                                        |
| --------------------------- | ------------------------------------------------------------ |
| `estimated_hours` (story)   | BMAD/Amelia originally; BCP overwrites if installed (install = consent) |
| `estimated_hours_pre_bcp`   | BCP (audit — PULSE ignores)                                   |
| `estimated_hours_basis`     | BCP writes it (audit); since v0.6 PULSE **reads it read-only** to label the dashboard regime — never writes it, never derives hours from it |
| `estimated_hours_reference` | BCP writes it (frozen leverage anchor); since #65 PULSE **reads it read-only** to compute stable `leverage_vs_reference` — never writes it, never computes it |
| `bcp.*` (story frontmatter) | BCP exclusively — PULSE reads, never writes                   |
| `bcp-baseline.yaml`         | BCP exclusively — PULSE never reads or writes                 |
| `pulse_metrics.*`           | PULSE exclusively                                             |
| `actual_hours`              | PULSE                                                         |

PULSE's only behavioral change is **semantic**: `bcp` tells PULSE the upstream
`estimated_hours` was BCP-derived, so the dashboard surfaces a BCP section. It
does *not* mean PULSE converts BCP points to hours.

## Frontmatter PULSE Reads (story file, read-only)

```yaml
---
story_id: "5.7"
estimated_hours: 86.7              # PULSE reads this — writer-agnostic
estimated_hours_pre_bcp: 80        # BCP audit — PULSE ignores
estimated_hours_basis: bcp         # BCP audit; PULSE reads read-only for the regime label (never writes/derives)
estimated_hours_reference: 105.0   # frozen leverage anchor (#65); PULSE reads read-only for stable leverage_vs_reference
category: backend

bcp:                               # written by BCP — PULSE surfaces it
  schema_version: "1.0"
  rule_version: "1.0"
  total: 21
  scored_at: "<iso8601>"
  scored_by: bruno
  breakdown: { ... }               # PULSE does NOT interpret this
  history: []                      # PULSE does NOT interpret this
---
```

## Behavior Rules

| Condition                                              | PULSE behavior                                                                                          |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| `bcp` block absent                                     | Behave as today (no change).                                                                            |
| `bcp` present, `pulse_estimation_method=bcp`           | Use `estimated_hours` as-is (already overwritten by BCP). Snapshot `bcp_at_start`. Surface BCP section.  |
| `bcp` present, `pulse_estimation_method≠bcp`           | Use `estimated_hours` as today. Still record `bcp_at_start` as opt-in telemetry.                          |
| `bcp.schema_version` unknown (≠ `"1.0"`)               | Emit a one-line warning, ignore `bcp.*` for that story.                                                  |

## Configuration

```yaml
# _bmad/config.yaml — pulse section
pulse_estimation_method: bcp        # 4th value, alongside hours / story_points / tshirt
```

No baseline-related keys live in PULSE. With `bcp`, `pulse_story_point_hours_factor`
is **not** required — there is no conversion factor; hours are derived upstream.

## Track-Start Extension

When a valid `bcp:` block is present, `bmad-pulse-track-start` snapshots it:

```yaml
pulse_metrics:
  "5.7":
    start_ts: "..."
    estimated_hours: 86.7
    estimation_basis: bcp
    estimated_hours_reference: 105.0   # frozen leverage anchor (#65) — only when present
    bcp_at_start:
      total: 21
      rule_version: "1.0"
      scored_by: bruno
```

## Track-Done Extension

When a BCP total is available (`bcp_at_start.total`, or story `bcp.total` as
fallback), `bmad-pulse-track-done` records:

```yaml
pulse_metrics:
  "5.7":
    # ... existing fields ...
    leverage_vs_reference: 6.9      # estimated_hours_reference / actual_hours (#65) — only when reference present
    bcp_recorded:
      total: 21
      h_per_bcp_actual: 5.0        # actual_hours / bcp.total
      h_per_bcp_estimated: 5.0     # estimated_hours / bcp.total
      drift_pct: 0.0
```

PULSE does **not** update any baseline. Baseline maturation is the BCP module's
responsibility (via `/bmad-bcp-recalibrate`).

## Stable leverage vs frozen reference (issue #65)

BCP can write a second hours figure, `estimated_hours_reference = bcp.total ×
reference_h_per_bcp`, where the **reference rate** is a frozen, governed
benchmark (it never recalibrates). PULSE reads it **read-only** and divides:

```text
leverage_vs_reference = estimated_hours_reference / actual_hours
```

Two distinct, complementary numbers — one collapses (and that is the point),
one does not:

| Metric                  | Denominator            | Behavior as the team calibrates | Audience / cadence  |
| ----------------------- | ---------------------- | ------------------------------- | ------------------- |
| Predictability (hero)   | plan (recalibrated)    | converges → vs-PLAN leverage collapses to ~1.0x | planning / per-story |
| `leverage_vs_reference` | reference (**frozen**) | **stable — does not collapse**  | board / C-Level, ROI |

The frozen denominator is what makes the ROI multiplier honest and durable: it
is "vs a fixed external benchmark", **not** "vs human" and **not** a target —
predictability stays the hero (see the dashboard anti-Goodhart note). PULSE
stays zero-coupled: it never computes the reference, never reads the BCP
baseline, never converts BCP→hours, and never writes the story frontmatter.
**Graceful degradation:** no `estimated_hours_reference` (BCP absent or older) →
PULSE reports only the vs-PLAN leverage, exactly as before. A governed change of
the reference rate (e.g. 5h→4h, forward-only) is surfaced on the dashboard as a
**labelled regime break** so pre/post stories are never compared naively.

## Dashboard Extension

A conditional **📊 BCP Productivity** section appears only when ≥1 story has a
`bcp_recorded` block. It renders BCP throughput per epic, actual vs estimated
h/BCP per category, a drift trend, and top stories by BCP total.

> **Design note — "top elements driving BCP":** the original feature request
> mentioned per-element ranking. PULSE intentionally ranks by *story-level* BCP
> total instead, because `bcp.breakdown` (the per-element data) is owned by
> `bmad-module-bcp`. Reading it here would break zero coupling. Per-element
> analytics belong in the BCP module's own reporting.

## Backwards Compatibility

Stories without a `bcp` block behave exactly as before. The BCP section is
absent unless BCP data exists. All four `pulse_estimation_method` values
(`hours`, `story_points`, `tshirt`, `bcp`) are supported.

## Related

- Companion module (scoring side): <https://github.com/nidelson/bmad-module-bcp>
- Companion issue: <https://github.com/nidelson/bmad-module-bcp/issues/1>
- BCP framework reference: <https://ciandt.com/us/en-us/complexitypoints>
