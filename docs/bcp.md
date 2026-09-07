# BCP Estimation

`pulse_estimation_method=bcp` turns on complexity-based estimation: stories are
scored in **Business Complexity Points** (BCP, a CI&T framework —
<https://ciandt.com/us/en-us/complexitypoints>) and `estimated_hours` is derived
from the score instead of being guessed. Scoring ships **inside this module** as
the six `bmad-bcp-*` skills; nothing else has to be installed.

It is **opt-in and stays opt-in**. `hours` is the default, and a project that
never enables BCP renders a complete dashboard with no BCP sections and no
warning about their absence — that is the baseline product, not a degraded mode.

## Why it exists

Without BCP the estimate is a subjective guess, so what PULSE can honestly report
is **leverage** — the ratio between the guess and the actual. Recalibrating a
guess converges on nothing, because there is no comparable unit underneath it.

With BCP the estimate is derived from a canonical ruler — `10 BCP × 5h/BCP = 50h`
— which makes it comparable across teams and across time. Only then does
recalibration mean something, and what it measures is the squad's
**predictability**. Leverage does not disappear; it changes denominator (see
[Stable leverage](#stable-leverage-vs-the-frozen-reference) below).

## The skills

| Skill | What it does |
| ----- | ------------ |
| `bmad-bcp-rule-card` | Displays the canonical ruler (10 elements × 5 sizes) |
| `bmad-bcp-score` | Scores a story and derives `estimated_hours` |
| `bmad-bcp-score-batch` | Scores several existing stories retroactively |
| `bmad-bcp-rescore` | Re-scores a story after a scope change |
| `bmad-bcp-recalibrate` | Recalibrates the per-category baseline from real hours |
| `bmad-bcp-backfill-baseline` | Leaves the cold start using delivered history |

The skill names keep the `bmad-bcp-` prefix. It now names the **feature**, not a
separate module — renaming would break existing installs for no gain.

## The internal boundary

Absorbing scoring did not merge the two halves. The `bmad-bcp-*` skills own
scoring; the `bmad-pulse-*` skills own tracking and reporting, and stay
**passive** toward BCP data: they never convert BCP to hours, never read or write
the baseline, and never write story frontmatter.

That is a design rule, not a leftover from the split. Tracking → scoring coupling
stays **zero**: the tracking skills do not know how anything is scored, they read
named fields by file convention. It is what keeps the reported productivity an
*observation* of the scoring rather than a second, divergent implementation of
it. The port changed which side of a repository boundary each half sits on; it
did not license either half to reach into the other.

**Single writer:** `apply_score.py` (in `bmad-bcp-score`) is the only thing that
writes `bcp.*`, `estimated_hours`, and `estimated_hours_reference`.

| Field                       | Written by                                                   |
| --------------------------- | ------------------------------------------------------------ |
| `estimated_hours` (story)   | BMAD/Amelia originally; `bmad-bcp-score` overwrites it (scoring = consent) |
| `estimated_hours_pre_bcp`   | `bmad-bcp-score` (audit — the tracking skills ignore it)      |
| `estimated_hours_basis`     | `bmad-bcp-score` (audit); the dashboard **reads it read-only** to label the regime — never writes it, never derives hours from it |
| `estimated_hours_reference` | `bmad-bcp-score` (frozen leverage anchor); tracking **reads it read-only** to compute `leverage_vs_reference` |
| `bcp.*` (story frontmatter) | `bmad-bcp-score` exclusively — tracking reads, never writes   |
| `bcp-baseline.yaml`         | `bmad-bcp-recalibrate` / `bmad-bcp-backfill-baseline` exclusively — tracking never reads or writes it |
| `pulse_metrics.*`           | the `bmad-pulse-*` tracking skills exclusively                |
| `actual_hours`              | `bmad-pulse-track-done`                                       |

The one place the two halves meet is **ordering**, and it is enforced by a file
rather than negotiated: when scoring is enabled, setup writes an `on_complete`
sequence whose STEP 1 is `bmad-pulse-track-done` and whose STEP 2 is
`bmad-bcp-recalibrate`, reading the `actual_hours` STEP 1 just recorded. Nothing
recalibrates before the real hours exist.

## Frontmatter contract (read-only for tracking)

```yaml
---
story_id: "5.7"
estimated_hours: 86.7              # tracking reads this — writer-agnostic
estimated_hours_pre_bcp: 80        # scoring audit — tracking ignores
estimated_hours_basis: bcp         # scoring audit; read read-only for the regime label
estimated_hours_reference: 105.0   # frozen leverage anchor (#65); read read-only
category: backend

bcp:                               # written by bmad-bcp-score — tracking surfaces it
  schema_version: "1.0"
  rule_version: "1.0"
  total: 21
  scored_at: "<iso8601>"
  scored_by: bruno                 # frozen schema value for the agent-driven path
  breakdown: { ... }               # tracking does NOT interpret this
  history: []                      # tracking does NOT interpret this
---
```

> **`category` has no fixed enum — it is whatever `pulse_dev_categories` says.** The
> field is free text validated only against your project's configured list
> (`_bmad/custom/config.toml`, or the module's setup prompt). If your project ships
> harness/tooling work (dependency overrides, dev-loop scripts, process scaffolding)
> alongside product code, give it its own category (e.g. `harness`) instead of
> forcing it into `backend`/`security`/`fullstack`. Categories exist so `h_per_bcp`
> calibrates separately per kind of work — mixing harness samples into a product
> category pollutes that category's rate for everyone who scores product work
> against it, in both directions: harness samples drag a product rate toward
> harness's own economics, and vice versa.

The schema lives at `skills/bmad-bcp-score/assets/bcp-frontmatter.schema.yaml` and
is enforced by `jsonschema` in the test suite — it is a contract, not
documentation with a `.yaml` extension.

> **`scored_by: bruno`.** Bruno was the scoring agent's persona before v0.9. The
> persona is retired, but the token is a **schema enum value already written into
> delivered stories**; changing it would fail validation on every one of them.
> The name is frozen where it is data, and gone where it was a voice.

## Behavior rules

| Condition | Behavior |
| --------- | -------- |
| `bcp` block absent | Behave as without BCP (no change) |
| `bcp` present, `pulse_estimation_method=bcp` | Use `estimated_hours` as-is (already derived by scoring). Snapshot `bcp_at_start`. Surface the BCP section |
| `bcp` present, `pulse_estimation_method≠bcp` | Use `estimated_hours` as usual. Still record `bcp_at_start` as opt-in telemetry |
| `bcp.schema_version` unknown (≠ `"1.0"`) | Emit a one-line warning, ignore `bcp.*` for that story |

## Configuration

```toml
# _bmad/config.toml — [modules.pulse]
pulse_estimation_method = "bcp"     # 4th value, alongside hours / story_points / tshirt
bcp_reference_h_per_bcp = "5.0"     # frozen anchor rate — governance-only, never recalibrated
```

With `bcp`, `pulse_story_point_hours_factor` is **not** required — there is no
conversion factor to configure; hours come from the score times the category
baseline.

The `bcp_*` keys live under `[modules.pulse]`. They were previously written under
`[modules.bcp]` by the standalone module's manifest; that table is still read as a
fallback so an upgrading project does not silently revert to defaults, but
`[modules.pulse]` is the home.

## Track-start extension

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

## Track-done extension

When a BCP total is available (`bcp_at_start.total`, or story `bcp.total` as
fallback), `bmad-pulse-track-done` records:

```yaml
pulse_metrics:
  "5.7":
    # ... existing fields ...
    leverage_vs_reference: 6.9      # estimated_hours_reference / actual_hours (#65)
    bcp_recorded:
      total: 21
      h_per_bcp_actual: 5.0        # actual_hours / bcp.total
      h_per_bcp_estimated: 5.0     # estimated_hours / bcp.total
      drift_pct: 0.0
```

Track-done does **not** update the baseline. That is `bmad-bcp-recalibrate`,
running after it in the `on_complete` sequence.

## Stable leverage vs the frozen reference

Scoring writes a second hours figure, `estimated_hours_reference = bcp.total ×
reference_h_per_bcp`, where the **reference rate** is a frozen, governed
benchmark that never recalibrates. Tracking reads it read-only and divides:

```text
leverage_vs_reference = estimated_hours_reference / actual_hours
```

Two distinct, complementary numbers — one collapses (and that is the point), one
does not:

| Metric | Denominator | Behavior as the team calibrates | Audience / cadence |
| ------ | ----------- | ------------------------------- | ------------------ |
| Predictability (hero on the `bcp` path) | plan (recalibrated) | converges → vs-PLAN leverage collapses to ~1.0x | planning / per-story |
| `leverage_vs_reference` | reference (**frozen**) | **stable — does not collapse** | board / C-Level, ROI |

The frozen denominator is what makes the ROI multiplier honest and durable: it is
"vs a fixed external benchmark", **not** "vs human" and **not** a target —
predictability stays the hero (see the dashboard anti-Goodhart note). Tracking
never computes the reference, never reads the baseline, never converts BCP→hours,
and never writes story frontmatter.

**Graceful degradation:** no `estimated_hours_reference` (scoring off, or a story
scored before the anchor existed) → only the vs-PLAN leverage is reported. A
governed change of the reference rate (e.g. 5h→4h, forward-only) is surfaced on
the dashboard as a **labelled regime break** so pre/post stories are never
compared naively.

## Dashboard extension

A conditional **📊 Produtividade BCP** section appears only when ≥1 story has a
`bcp_recorded` block. It renders BCP throughput per epic, actual vs estimated
h/BCP per category, a drift trend, and top stories by BCP total.

> **Design note — "top elements driving BCP":** the original feature request
> mentioned per-element ranking. The dashboard intentionally ranks by
> *story-level* BCP total instead: `bcp.breakdown` belongs to `bmad-bcp-score`,
> and per-element analytics belong to the skill that produced them, not to the
> one that reports observed productivity.

## Backwards compatibility

Stories without a `bcp` block behave exactly as before. The BCP section is absent
unless BCP data exists. All four `pulse_estimation_method` values (`hours`,
`story_points`, `tshirt`, `bcp`) are supported.

Projects that used the standalone BCP module need **no data migration**:
`bcp-baseline.yaml` and the story frontmatter keep their schema. The port moved
where the code lives, not what it writes.

## History and attribution

Scoring, the ruler, and baseline calibration were originally developed as a
separate BMAD module and were absorbed into PULSE in v0.9
([#84](https://github.com/nidelson/bmad-module-pulse/issues/84)). That repository
is archived: its issues and PRs remain the record of how the ruler and the
baseline were calibrated, but nothing there needs to be installed, and its skills
were removed before archival so a stale install cannot shadow the ones here.

The BCP framework itself is © CI&T, MIT-licensed — see
[ATTRIBUTION.md](../ATTRIBUTION.md).

## Related

- BCP framework reference: <https://ciandt.com/us/en-us/complexitypoints>
- The canonical ruler: `skills/bmad-bcp-rule-card/assets/bcp-rule.yaml`
