---
name: bmad-pulse-dashboard
description: 'Generate cumulative PULSE efficiency dashboard'
standalone: true
main_config: '{project-root}/_bmad/config.yaml'
config_section: 'pulse'
---

# Workflow Dashboard

**Goal:** Generate a cumulative dashboard with all PULSE efficiency metrics, cross-sprint trends, and process insights.

**Your Role:** You are Levi, compiling the complete efficiency view of the project.

You will continue to operate with your given name, identity, and communication_style, merged with the details of this role description.

## Conventions

- Bare paths (e.g. `customize.toml`) resolve from the skill root.
- `{skill-root}` resolves to this skill's installed directory (where `customize.toml` lives).
- `{project-root}`-prefixed paths resolve from the project working directory.
- `{skill-name}` resolves to the skill directory's basename.

## On Activation

### Step 1: Resolve the Workflow Block

Run: `python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`

**If the script fails**, resolve the `workflow` block yourself by reading these three files in base → team → user order and applying the same structural merge rules as the resolver:

1. `{skill-root}/customize.toml` — defaults
2. `{project-root}/_bmad/custom/{skill-name}.toml` — team overrides
3. `{project-root}/_bmad/custom/{skill-name}.user.toml` — personal overrides

Any missing file is skipped. Scalars override, tables deep-merge, arrays of tables keyed by `code` or `id` replace matching entries and append new entries, and all other arrays append.

### Step 2: Execute Prepend Steps

Execute each entry in `{workflow.activation_steps_prepend}` in order before proceeding.

### Step 3: Load Persistent Facts

Treat every entry in `{workflow.persistent_facts}` as foundational context you carry for the rest of the workflow run. Entries prefixed `file:` are paths or globs under `{project-root}` — load the referenced contents as facts. All other entries are facts verbatim.

### Step 4: Load Config and Execute Append Steps

Load the PULSE configuration as described in INITIALIZATION below, then execute each entry in `{workflow.activation_steps_append}` in order. Activation is complete; begin the workflow EXECUTION section.

---

## INITIALIZATION

### Configuration Loading

Load the `pulse` section from `{main_config}` and resolve all module variables:

- `project_name`, `communication_language`
- `pulse_data_folder`, `pulse_sprint_status_filename`
- `pulse_dashboard_folder`, `pulse_dashboard_format`
- `pulse_include_trend_chart`, `pulse_include_capacity_forecast`
- `pulse_dev_categories`, `pulse_levi_verbosity`
- `date` as current system-generated datetime

### Paths

- `sprint_status_file` = `{pulse_data_folder}/{pulse_sprint_status_filename}`
- `dashboard_file` = `{pulse_dashboard_folder}/dashboard.md`

---

## EXECUTION

### Step 1: Collect Data

1. Read `{sprint_status_file}` in full
2. Extract all entries from the `pulse_metrics:` section
3. Group by epic — infer epic_id from the numeric prefix of story_id (e.g. `15.3` → epic 15, `4.4.1` → epic 4)
4. Calculate aggregations:
   - Total stories measured
   - **`predictability_score`** — the v0.6 **hero metric**. The **median** of the per-story estimate error `|actual_hours - estimated_hours| / estimated_hours` across all stories with `pulse_metrics` (floor `estimated_hours` at 0.01 to avoid divide-by-zero). Report as a percentage; **lower is better** — it reads "estimates are X% off, median". Method-agnostic: for BCP stories it equals `|bcp_recorded.drift_pct|` (the BCP totals cancel), so it works whether or not the project uses BCP. Compute it global and per category. Median (not mean) for the same reason the v0.5 baseline is geometric — resist outliers. Pair it with a **trend arrow**: split the stories in story-order (chronological proxy) into first half vs second half and compare each half's median error → `↓ converging` / `→ stable` / `↑ diverging`. Needs `>= 4` stories for a trend; fewer → no arrow.
   - **`estimate_regime`** (v0.6 regime detection) — the basis each `estimated_hours` was derived from, read **read-only** from the story's `estimated_hours_basis` frontmatter field when present (`bcp` / `hours` / `story_points` / `tshirt`), falling back to `{pulse_estimation_method}` when the field is absent. PULSE **never writes** `estimated_hours_basis` and **never derives hours from it** — it only labels what each multiplier is measured *against* (so "5x" reads "vs PLAN (bcp)" not an unqualified number). Report the dominant regime across stories for the leverage context line; annotate a story in the breakdown when its regime differs from the project default. (`estimated_hours_pre_bcp` stays ignored.)
   - **`cohort_drift(category, segment)`** (v0.7 — the shared primitive for estimation-time drift alerts; also consumed by `bmad-pulse-track-start`). For a **cohort**, the **median** of the per-story estimate error `|actual_hours - estimated_hours| / estimated_hours * 100` over the **last `K = 5` completed stories** in that cohort (story-order = chronological proxy; floor `estimated_hours` at 0.01). For BCP stories this equals `|bcp_recorded.drift_pct|`. The **cohort key** is `(category, segment)` when the story carries BCP (segment = `micro`/`story` from the v0.5 median split), else `(category)` alone — fallback documented so non-BCP projects still cohort by category. Returns `(median_abs_drift_pct, n, sample_story_ids)` where `n` is the cohort size considered (≤ K). **Requires `n >= 3`** to be meaningful — fewer → `insufficient` (callers must stay silent, no false alarm). This is read-only over `pulse_metrics`; it never writes or alters any estimate.
   - **`drift_watchlist`** (v0.7) — the forward-looking companion to the track-start alert. For **every** cohort present in `pulse_metrics`, evaluate `cohort_drift`; keep only cohorts with `n >= 3` **and** `median_abs_drift_pct > T = 25%`, sorted by `median_abs_drift_pct` desc. Each entry carries `(cohort_label, median_abs_drift_pct, n, trend)` where `trend` reuses the v0.6 half-split direction (`↓`/`→`/`↑`). Healthy cohorts (≤ T) are omitted. Empty list is the healthy default.
   - Average, minimum, and maximum leverage
   - Total estimated hours vs total actual hours
   - First-pass rate
   - Leverage by category (use `{pulse_dev_categories}`)
   - **Halt aggregations** (read `process_health.halts` from each story; the field has three valid shapes — handle all without crashing):
     - **Shape A** (integer): treat as opaque count, skip duration math.
     - **Shape B** (list of objects): structured — read `kind`, `context`, `duration_min`, `pre_approved_batch`.
     - **Shape C** (list of plain strings, legacy pre-0.5.0): infer `kind` from prefix when possible (`approval_wait_*` → `approval_wait`); `duration_min` is unknown — count as halt but exclude from minute aggregations.
     - Aggregations:
       - `total_halts` — sum across all stories (integers + list lengths regardless of shape)
       - `total_approval_wait_count` — count of entries where `kind == approval_wait` (Shape B explicit, Shape C inferred via prefix)
       - `total_approval_wait_minutes` — sum of `duration_min` for Shape B entries with `kind == approval_wait` and `pre_approved_batch != true` (Shape C contributes 0 — duration unknown)
       - `total_pre_approved_batch_count` — count of `approval_wait` entries with `pre_approved_batch: true` (Shape B only)
       - `legacy_halt_string_count` — count of Shape C entries encountered (used to surface migration hint in insights)
       - `stories_with_approval_wait` — list of `(story_id, total_minutes)` pairs for the breakdown table (entries with unknown minutes show as `?min`)
   - **BCP aggregations** (read `bcp_recorded` and `bcp_at_start` / `estimation_basis` from each story; all optional — a story without them is normal and contributes nothing):
     - _Since v0.5.0, per-category h/BCP baselines use the **geometric** mean of the per-story ratios, not the arithmetic mean (pre-0.5.0). Baselines recomputed from the same data will shift; this is intentional — see the v0.5 honest-measurement-engine notes._
     - `bcp_stories` — list of stories that have a `bcp_recorded` block
     - `total_bcp` — sum of `bcp_recorded.total` across `bcp_stories`
     - `bcp_throughput` — `total_bcp` grouped by epic (proxy for BCP/sprint when sprint segmentation is unavailable)
     - `segment_split` — the **median** of `bcp_recorded.total` over **all** `bcp_stories` (one global value). Computed **only when `bcp_stories` is non-empty** — never evaluate `median([])`. A story is `micro` when `bcp_recorded.total < segment_split`, else `story`. This split is data-driven: PULSE assumes nothing about the BCP point scale and stays zero-coupled to BCP. (Since v0.5.0.)
     - `h_per_bcp_by_category` — for each `(category, segment)` with `segment ∈ {micro, story}`, the **geometric mean** of `bcp_recorded.h_per_bcp_actual` over the `bcp_stories` in that category and segment: `exp(mean(ln(h_per_bcp_actual)))`, equivalently `(∏ h_per_bcp_actual)^(1/n)`. h/BCP values are multiplicative ratios, so the geometric mean is the unbiased central tendency and resists outliers (a single 10x story does not drag the baseline the way an arithmetic mean would). Round to 2 decimals. Also compute a per-category **pooled** baseline (`all` segment — geometric mean over every `bcp_story` in the category, ignoring the split) for the continuity row. **Thin-segment fallback:** a `(category, segment)` pair with `n < 3` is not reported on its own; those stories still count in the category's pooled `all` baseline. `n == 0` → pair omitted.
     - `h_per_bcp_estimated_by_category` — same **geometric mean**, segmented the same way (per `(category, segment)` plus pooled `all`), over `bcp_recorded.h_per_bcp_estimated` (for the drift comparison).
     - `h_per_bcp_band` — for each baseline (every `(category, segment)` and each pooled `all`), a **confidence band** around the geometric mean of `bcp_recorded.h_per_bcp_actual`, so the baseline reads as a range, not false precision. Compute the **sample geometric standard deviation** `GSD = exp(sample_std(ln(h_per_bcp_actual)))`, where `sample_std` uses the `n-1` (sample, not population) denominator — we estimate, not enumerate. The band is `[geo_mean / GSD, geo_mean * GSD]` (multiplier `k = 1`, ≈ 68% of a log-normal sample — a **typical range**, not a 95% CI; with PULSE's small `n` a wider band would be unactionable). **Require `n >= 3` to emit a band**; for `n < 3` emit the point with an explicit `(n=2)` / `(n=1)` marker and no interval (a GSD from 2 samples has 1 degree of freedom — one outlier distorts it). Carry `n` alongside every baseline so thin samples are visible. (Since v0.5.0.)
     - `drift_trend` — ordered list of `(story_id, bcp_recorded.drift_pct)` for `bcp_stories` (story-order = chronological proxy)
     - `h_per_bcp_convergence` — the v0.6 **self-referential drift signal**: is the h/BCP baseline *stabilizing* over time? Split `drift_trend` in story-order into a first half and a second half and compare the **median `|drift_pct|`** of each: second-half median meaningfully **lower** → `converging` (estimates closing on reality); meaningfully **higher** → `diverging`; within a small tolerance → `stable`. The confidence band (`h_per_bcp_band`) narrowing across the same split is corroborating evidence (report it alongside). **Requires `>= 4` `bcp_stories`** for a reading — fewer → `insufficient data (thin sample)`, no label. This consumes the v0.5 drift/band data; it does not recompute raw ratios.
     - `top_bcp_stories` — `bcp_stories` sorted by `bcp_recorded.total` desc, top 5 (proxy for "elements driving BCP" — PULSE does not read `bcp.breakdown`, so it ranks by total points per story)

### Step 2: Generate Dashboard

Generate the dashboard in the format(s) defined in `pulse_dashboard_format` (`markdown`, `yaml`, or `both`).

For `markdown` format (default), write `{dashboard_file}` with the following structure:

```markdown
# ⚡ PULSE — Efficiency Dashboard

> Process Utilization & Leverage Statistics Engine
> Generated at: {date} | Project: {project_name}

---

## 🏆 General Statistics

| Metric                  | Value                                |
| ----------------------- | ------------------------------------ |
| Stories measured        | {total}                              |
| **Predictability**      | **{predictability_score}% off (median) {trend_arrow}** |
| Human estimated hours   | {total_estimated}h                   |
| Actual AI hours         | {total_actual}h                      |
| Hours saved             | {saved}h                             |
| First-pass rate         | {rate}%                              |
| AI Leverage (vs PLAN, {dominant_regime}) | {avg}x — context, not a target |

> **Predictability is the hero number** (lower = estimates closer to reality; `↓` = converging). Leverage is shown as context only and read "vs PLAN ({dominant_regime})", never "vs human" — the regime is the estimate basis (`estimated_hours_basis`, read-only) so the multiplier is read against the right plan. A high multiplier signals an uncalibrated estimate basis, not speed (see the anti-Goodhart invariant below).

> **Anti-Goodhart invariant — leverage is not a target.** `leverage = estimated_hours / actual_hours`. Once the estimate basis is calibrated (estimates derived from a baseline that matches reality), this ratio collapses to **~1.0x by construction** — so a *high* multiplier signals an inflated or uncalibrated estimate basis, **not** velocity, and a *leverage goal* would literally reward never calibrating. The durable signal is **predictability**: the per-category h/BCP drift converging on zero (do estimates match outcomes?). Read every multiplier as "vs PLAN", never "vs human". (v0.5 locked this invariant; v0.6 acted on it — predictability now leads the dashboard and the track-done celebration triggers on accuracy, not leverage magnitude.)

<!-- CONDITIONAL: include only if pulse_include_trend_chart == yes -->
## 📈 Leverage Trend by Epic

Sparkline: each █ = 0.5x leverage, maximum 20 characters.

{for each epic with data}
Epic {N}: {sparkline} {avg}x ({count} stories)
{end}

Example: Epic 14: ████████░░ 3.5x (4 stories)
<!-- END CONDITIONAL trend_chart -->

## 📊 Leverage by Category

| Category | Avg Leverage (vs PLAN) | Stories | Best |
| -------- | ---------------------- | ------- | ---- |
{for each category in pulse_dev_categories}
| {category} | {x}x | {n} | {best} |
{end}

<!-- CONDITIONAL: include only if pulse_include_capacity_forecast == yes -->
## 🔮 Capacity Forecast

Based on avg leverage of {avg}x:

- 10h estimated → ~{10/avg}h actual
- 40h estimated → ~{40/avg}h actual
- 80h estimated → ~{80/avg}h actual
<!-- END CONDITIONAL capacity_forecast -->

<!-- CONDITIONAL: include only if total_approval_wait_count > 0 OR total_pre_approved_batch_count > 0 -->
## ⏸ Approval-Wait Halts

| Metric                                  | Value                              |
| --------------------------------------- | ---------------------------------- |
| Approval-wait halts (subtracted)        | {total_approval_wait_count}        |
| Total approval-wait time subtracted     | {total_approval_wait_minutes}min   |
| Pre-approved batch decisions (skipped)  | {total_pre_approved_batch_count}   |

{if stories_with_approval_wait}
**By story:**

| Story | Approval-wait minutes |
| ----- | --------------------- |
{for each (story_id, minutes) in stories_with_approval_wait}
| {story_id} | {minutes}min |
{end}
{end}

> Approval-wait halts measure governance latency (human-in-the-loop decisions) and are subtracted from `actual_hours` so leverage reflects real dev work, not wait time. `pre_approved_batch` flags durable decisions that legitimately remove latency on subsequent stories — these are reported but not subtracted.

{if legacy_halt_string_count > 0}
> ⚠ {legacy_halt_string_count} legacy halt entries (plain strings, pre-0.5.0 format) were detected. Their durations are not machine-readable and were excluded from minute totals. Migrate these entries to the structured shape (with `kind`, `context`, `duration_min`) for accurate leverage on historical stories.
{end}
<!-- END CONDITIONAL approval_wait -->

<!-- CONDITIONAL: include only if bcp_stories is non-empty (≥1 story has a bcp_recorded block) -->
## 📊 BCP Productivity

> Business Complexity Points telemetry. Hours were derived upstream by
> [`bmad-module-bcp`](https://github.com/nidelson/bmad-module-bcp); PULSE only
> reports observed productivity and never owns the BCP baseline.

| Metric                | Value          |
| --------------------- | -------------- |
| Stories with BCP      | {len(bcp_stories)} |
| Total BCP scored      | {total_bcp}    |

**Throughput (BCP per epic):**

{for each epic in bcp_throughput}
Epic {N}: {bcp} BCP ({count} stories)
{end}

**Actual h/BCP by category and size segment:**

> Stories split at the observed median BCP (`segment_split` = {segment_split} BCP): below it = `micro`, at/above = `story`. The `all` row pools both, for continuity with pre-0.5 dashboards. A segment with fewer than 3 stories is folded into `all` rather than shown on its own (too thin to trust).
>
> The `Actual h/BCP` cell shows the geometric mean with its **typical range** `[low–high]` (≈68%, sample GSD, `k=1`). The range is shown only when `n >= 3`; for `n < 3` the bare point is shown (its `n` is in the `n` column — too few samples for a trustworthy range).

| Category | Segment | n | Actual h/BCP (typical range) | Est. h/BCP | Drift |
| -------- | ------- | - | ---------------------------- | ---------- | ----- |
{for each category with bcp_stories}
{for each segment in [micro, story] with n >= 3}
| {category} | {segment} | {n} | {h_per_bcp_by_category}h [{band.low}–{band.high}] | {h_per_bcp_estimated_by_category}h | {drift:+}% |
{end}
| {category} | all | {n_all} | {pooled h_per_bcp_by_category}h{if n_all >= 3} [{pooled band.low}–{pooled band.high}]{end} | {pooled h_per_bcp_estimated_by_category}h | {drift:+}% |
{end}

**Baseline convergence (is h/BCP stabilizing?):**

> {if bcp_stories count >= 4}**{h_per_bcp_convergence}** — median |drift| moved from {first_half_median}% (first half) to {second_half_median}% (second half); the confidence band {band narrowed / widened / held} over the same split. Converging is the healthy direction: estimates closing on reality.{else}_Insufficient data (thin sample — need ≥4 BCP stories for a convergence reading)._{end}

**Drift trend (estimated vs actual h/BCP):**

{for each (story_id, drift_pct) in drift_trend}
{story_id}: {drift_pct:+}%
{end}

**Top stories by BCP:**

| Story | BCP | Actual h/BCP |
| ----- | --- | ------------ |
{for each story in top_bcp_stories}
| {story_id} | {bcp_recorded.total} | {bcp_recorded.h_per_bcp_actual}h |
{end}

> Note: PULSE ranks by story-level BCP total. Per-element breakdown
> (`bcp.breakdown`) is owned by `bmad-module-bcp` and is intentionally not
> read here — this preserves zero coupling.
<!-- END CONDITIONAL bcp -->

## 🚦 Estimation drift watch

> Forward-looking companion to the track-start alert: which cohorts are estimating badly *right now*, so you can re-estimate before committing. A cohort is listed only when it has ≥3 completed stories and its median estimate error exceeds 25% over the last 5. Healthy cohorts are omitted.

{if drift_watchlist non-empty}
| Cohort | Median \|drift\| | n | Trend |
| ------ | -------------- | - | ----- |
{for each (cohort_label, median_abs_drift_pct, n, trend) in drift_watchlist}
| {cohort_label} | {median_abs_drift_pct}% | {n} | {trend} |
{end}
{else}
_No cohorts drifting — estimates are tracking._
{end}

## 💡 Process Insights

{insights generated based on the data}

## 📋 Story Breakdown

| Story | Est. | Actual | Leverage (vs PLAN) | Quality | Category |
| ----- | ---- | ------ | ------------------ | ------- | -------- |

{for each story with pulse_metrics data}
| {id} | {est}h | {actual}h | {lev}x | {quality} | {cat} |
{end}

---

_PULSE — Against facts, there are no arguments._
_Dashboard generated automatically by the PULSE module._
```

For `yaml` format, generate `{pulse_dashboard_folder}/dashboard.yaml` with the same data structured as YAML.

For `both` format, generate both files.

### Step 3: Display Summary

Display in the terminal the General Statistics block + (if `pulse_include_trend_chart == yes`) Trend + a Process Insight.
The detail level of the summary must respect `pulse_levi_verbosity`.

### Step 4: Report Location

```text
⚡ Levi: Dashboard saved at {dashboard_file}
   {total} stories measured | Avg leverage: {avg}x
```

---

## BEHAVIOR RESTRICTIONS

- If no data exists in the `pulse_metrics:` section, inform and suggest running track-start/track-done first
- Create the `{pulse_dashboard_folder}` directory if it does not exist
- Always overwrite dashboard.md (it is the most recent version)
- Communicate in the language configured in `communication_language`
- Respect `pulse_levi_verbosity` for level of detail in responses
- The leverage trend section must only be included if `pulse_include_trend_chart == yes`
- The capacity forecast section must only be included if `pulse_include_capacity_forecast == yes`
- The categories table must use the categories defined in `pulse_dev_categories` (not hardcoded categories)
- The Approval-Wait Halts section must only be rendered when `total_approval_wait_count + total_pre_approved_batch_count > 0`
- The BCP Productivity section must only be rendered when at least one story has a `bcp_recorded` block; stories without BCP data render unchanged in all other sections
- Never read or write the BCP baseline file — BCP productivity is computed purely from `pulse_metrics` fields PULSE itself recorded
- When reading `process_health.halts`, accept both shapes (integer count and structured list) and degrade gracefully — never crash on legacy data

---

## Extra Sections

After the standard dashboard sections have been rendered and BEFORE writing the file to `dashboard_file`, append each entry in `{workflow.extra_sections}` to the end of the markdown buffer, in order. Each entry is either a literal markdown block or a `file:{project-root}/...` reference whose contents are inlined verbatim. Sections render in the listed order.

## On Completion

After `dashboard_file` has been written and the confirmation message displayed, execute the `{workflow.on_complete}` scalar if non-empty. Override wins; an empty value means no custom post-completion behavior.
