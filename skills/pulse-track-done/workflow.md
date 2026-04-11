---
name: pulse-track-done
description: 'Record story completion and calculate PULSE efficiency metrics'
standalone: true
main_config: '{project-root}/_bmad/config.yaml'
config_section: 'pulse'
---

# Workflow Track Done

**Goal:** Record the completion timestamp, calculate AI Leverage Ratio, and display the Efficiency Pulse for the story.

**Your Role:** You are Levi, closing the measurement cycle and celebrating (or diagnosing) the result.

---

## INITIALIZATION

### Configuration Loading

Load the config from the `pulse` section of `{main_config}` and resolve all module variables from that section:

- `output_folder`, `user_name`, `communication_language`
- `pulse_data_folder`, `pulse_dashboard_folder`
- `pulse_sprint_status_filename`
- `pulse_estimation_method` (story_points / hours / t-shirt)
- `pulse_story_point_hours_factor` (story points → hours conversion factor)
- `pulse_leverage_threshold_exceptional` (e.g. 4)
- `pulse_leverage_threshold_solid` (e.g. 2)
- `pulse_leverage_warning_threshold` (e.g. 1)
- `pulse_alert_on_halt` (yes / warn / no)
- `pulse_alert_unused_skills` (yes / no)
- `pulse_process_health_checks` (standard / strict / minimal)
- `pulse_levi_verbosity` (concise / standard / verbose)
- `pulse_levi_coaching_mode` (yes / metrics-only)
- `date` as current system-generated datetime (ISO 8601)

### Paths

- `sprint_status_file` = `{pulse_data_folder}/{pulse_sprint_status_filename}`
- `efficiency_artifacts` = `{pulse_dashboard_folder}`

---

## EXECUTION

### Step 1: Identify Story

1. If arguments were passed (e.g. `15.3`), use them as the story ID
2. If not, read `{sprint_status_file}` and identify stories in the `pulse_metrics:` section that have `start_ts` but NOT `end_ts`
3. If no eligible story found, inform and exit

### Step 2: Record Completion

1. Locate the story ID entry in the `pulse_metrics:` section of file `{sprint_status_file}`
2. Add the `end_ts` field with the current ISO 8601 timestamp
3. Ask the user: "How many review cycles were needed?" → `review_cycles`
4. Ask (optional): "Effective AI working time? (leave empty to use wall-clock)" → `effective_hours`

### Step 3: Calculate Metrics

**Estimate conversion by configured method:**

If `pulse_estimation_method` is `story_points`:
```text
estimated_hours = story_points * pulse_story_point_hours_factor
```

If `pulse_estimation_method` is `t-shirt`:
```text
Standard conversion table (t-shirt → hours):
  S  = 2h
  M  = 4h
  L  = 8h
  XL = 16h
estimated_hours = table value corresponding to the registered size
```

If `pulse_estimation_method` is `hours`:
```text
estimated_hours = value recorded directly in hours
```

**Leverage calculation:**
```text
elapsed_minutes = (end_ts - start_ts) in minutes
actual_hours = effective_hours ?? (elapsed_minutes / 60)
leverage_ratio = estimated_hours / actual_hours
first_pass = review_cycles == 1
```

1. Add the `review_cycles` field with the value provided by the user
2. Add the `actual_hours` field with the calculated value
3. Add the `leverage_ratio` field with the calculated value (1 decimal)
4. Add the `first_pass` field as a boolean

### Step 4: Generate Efficiency Pulse + Process Health

Display in the terminal:

```text
⚡ Levi: Story {story_id} — DONE!

   📊 Efficiency
   Human estimate: {estimated_hours}h ({dev_count} devs)
   Actual AI time: {actual_hours}h ({elapsed_minutes}min wall-clock)
   AI Leverage: {leverage_ratio}x
   Quality: {first_pass ? "✅ first-pass" : "🔄 " + review_cycles + " cycles"}
   Tasks: {task_count}
   Category: {category}
   {leverage_ratio >= pulse_leverage_threshold_exceptional ? "🔥 Exceptional!" : leverage_ratio >= pulse_leverage_threshold_solid ? "💪 Solid!" : leverage_ratio < pulse_leverage_warning_threshold ? "⚠ Below expectations — review estimates or process." : "📊 Data recorded."}

   📋 Process Health
   Flow: {flow_check}
   HALTs: {halt_count} | Underused skills: {unused_skills_list}

   💡 {process_insight}
```

**How to evaluate Process Health:**

The verification level is determined by `pulse_process_health_checks`:

- **minimal**: checks HALTs only (if `pulse_alert_on_halt != no`)
- **standard**: checks BMAD flow + HALTs + underused skills (default)
- **strict**: all standard checks + additional pattern analysis

1. **Complete BMAD flow** (standard/strict):
   - Read `{sprint_status_file}` and verify the story's status transitions
   - Expected flow: backlog/ready-for-dev → in-progress → review → done
   - If all transitions occurred: "create-story → dev-story → code-review → done ✅"
   - If any step was skipped (e.g. directly from backlog to done): "⚠ Steps skipped"

2. **HALTs** (respect `pulse_alert_on_halt`):
   - Locate the story file in the configured implementation artifacts folder
   - Read the "Dev Agent Record" section of the story file
   - Count occurrences of the word "HALT"
   - If `pulse_alert_on_halt` is `yes`: display an alert if halt_count > 0
   - If `pulse_alert_on_halt` is `warn`: display as an informational warning
   - If `pulse_alert_on_halt` is `no`: record internally but do not display
   - If 0: display "0"

3. **Underused skills** (only if `pulse_alert_unused_skills` is `yes`):
   - If `category` is "fullstack" or "backend":
     - Check whether the TEA module is installed in the BMAD modules folder
     - Check whether the story's Change Log mentions "tea", "test architect", or "automate"
     - If TEA is installed but not mentioned: add "tea:automate" to the list
   - If no underused skills: display "none"
   - If `pulse_alert_unused_skills` is `no`: omit this check

4. **Insight** (respect `pulse_levi_coaching_mode`):
   - If `pulse_levi_coaching_mode` is `yes`: generate 1 actionable suggestion based on findings
     - Examples: "Consider tea:automate for fullstack stories"
     - If everything is OK: "Process executed with excellence — no action needed"
   - If `pulse_levi_coaching_mode` is `metrics-only`: display data only, no suggestions

5. **Persistence:**
   - Add the `process_health` field to the story entry in `pulse_metrics`:

```yaml
process_health:
  flow_complete: true
  halts: 0
  unused_skills: ['tea:automate']
  insight: 'Consider tea:automate for fullstack stories'
```

### Step 5: Compare with History

1. Read all `leverage_ratio` fields in the `pulse_metrics:` section of file `{sprint_status_file}`
2. Calculate the historical average
3. If this story is above the average: "↑ Above average ({avg}x)"
4. If this story is the new record: "🏆 New record!"

### Step 6: Trend Analysis (if sufficient data is available)

If 5+ stories with complete PULSE data exist, generate analysis:

- Compare leverage by `category` (backend vs web vs mobile vs fullstack)
- Check whether large stories (>5 tasks) have lower leverage
- Check correlation between `first_pass` and `leverage_ratio`
- Analyze the trend of `process_health.flow_complete` — if <80% complete, raise an alert
- Check whether `process_health.unused_skills` repeats patterns (same skill appears 3+ times)

Display as an additional section in the card (respecting `pulse_levi_verbosity`):

- **concise**: average and first-pass rate only
- **standard**: full display as below
- **verbose**: full display + breakdown by category and correlations

```text
   📈 Trends (N stories)
   Avg leverage: {avg}x | Best: {best_story} ({best}x)
   First-pass rate: {fp_rate}%
   Complete process: {flow_rate}%
   {trend_insight}
```

---

## BEHAVIOR RESTRICTIONS

- DO NOT modify anything outside the `pulse_metrics:` section of file `{sprint_status_file}`
- Data is isolated in the `pulse_metrics:` section — zero risk of conflict
- Communicate in the language configured in `communication_language`
- Respect `pulse_levi_verbosity` for level of detail (concise / standard / verbose)
- Respect `pulse_levi_coaching_mode` (yes = suggest improvements, metrics-only = data only)
- If no entry exists for the story ID in `pulse_metrics:`, warn and suggest running track-start first
