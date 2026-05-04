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

### Step 2: Generate Dashboard

Generate the dashboard in the format(s) defined in `pulse_dashboard_format` (`markdown`, `yaml`, or `both`).

For `markdown` format (default), write `{dashboard_file}` with the following structure:

```markdown
# ⚡ PULSE — Efficiency Dashboard

> Process Utilization & Leverage Statistics Engine
> Generated at: {date} | Project: {project_name}

---

## 🏆 General Statistics

| Metric                  | Value              |
| ----------------------- | ------------------ |
| Stories measured        | {total}            |
| Avg AI Leverage         | {avg}x             |
| Human estimated hours   | {total_estimated}h |
| Actual AI hours         | {total_actual}h    |
| Hours saved             | {saved}h           |
| First-pass rate         | {rate}%            |

<!-- CONDITIONAL: include only if pulse_include_trend_chart == yes -->
## 📈 Leverage Trend by Epic

Sparkline: each █ = 0.5x leverage, maximum 20 characters.

{for each epic with data}
Epic {N}: {sparkline} {avg}x ({count} stories)
{end}

Example: Epic 14: ████████░░ 3.5x (4 stories)
<!-- END CONDITIONAL trend_chart -->

## 📊 Leverage by Category

| Category | Avg Leverage | Stories | Best |
| -------- | ------------ | ------- | ---- |
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

## 💡 Process Insights

{insights generated based on the data}

## 📋 Story Breakdown

| Story | Est. | Actual | Leverage | Quality | Category |
| ----- | ---- | ------ | -------- | ------- | -------- |

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
- When reading `process_health.halts`, accept both shapes (integer count and structured list) and degrade gracefully — never crash on legacy data
