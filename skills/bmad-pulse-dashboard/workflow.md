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
