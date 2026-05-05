---
name: bmad-pulse-track-done
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
5. Ask about halts >2min (skip if `effective_hours` was provided — wall-clock is being overridden):

   **Prompt:** "Were there any halts >2min during execution?" — examples:
   - `approval_wait` — paused waiting for explicit user approval (admin merge, scope expansion, irreversible action)
   - `incident` — external infra outage, GitHub down, dependency unavailable
   - `external_pause` — user-initiated break that should not count as dev work
   - `other` — anything else (document with note)

   For each halt, capture:
   - `kind` (enum above)
   - `context` (short identifier, e.g., `admin_merge_decision`, `github_outage`)
   - `duration_min` (integer minutes, must be >2)
   - `pre_approved_batch` (boolean, default false — set `true` if a prior story granted durable approval covering this case, e.g., "admin merge pre-approved across the entire epic-setup batch")
   - `note` (optional human context)

   **Threshold rule:** only document halts with `duration_min > 2`. Below that is conversational latency, not a halt.

   **Pre-approved batch rule:** if a prior story in the same batch already captured the approval decision and the user confirmed it applies durably (e.g., "Admin merge for entire epic-setup batch"), set `pre_approved_batch: true` on subsequent halt entries OR omit the halt entirely with a comment explaining the durable decision. This rewards batch-decision behavior, which is operationally correct for human-in-the-loop AI workflows.

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

# Halt subtraction (only when halts is a structured list, not a legacy integer):
halt_minutes = sum(
  h.duration_min for h in halts
  if isinstance(halts, list)
  and h.duration_min
  and not h.pre_approved_batch
)

actual_hours = effective_hours ?? max(0.01, (elapsed_minutes - halt_minutes) / 60)
leverage_ratio = estimated_hours / actual_hours
first_pass = review_cycles == 1
```

**Halt subtraction rules:**

- If `effective_hours` is provided, `halt_minutes` is ignored (user already supplied the corrected value).
- If `halts` is a legacy integer (e.g., `halts: 0`), no subtraction — the field carries no duration data.
- If `halts` is a structured list, each entry with `duration_min` and `pre_approved_batch != true` contributes to `halt_minutes`.
- If `halts` is a list of plain strings (legacy free-form shape, see Shape C below), no subtraction — duration data lives only in YAML comments and is not machine-readable. Emit a warning suggesting migration to Shape B.
- Floor `actual_hours` at 0.01h to avoid divide-by-zero in `leverage_ratio`.
- Document the subtraction inline with a YAML comment on `actual_hours` so the math is traceable, e.g.:
  ```yaml
  actual_hours: 0.65  # 46min wall-clock - 7min approval_wait_admin_merge_decision
  ```

1. Add the `review_cycles` field with the value provided by the user
2. Add the `actual_hours` field with the calculated value (with traceability comment when halts were subtracted)
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
   {if any halt.kind == approval_wait}Approval-wait: {n} halt(s), {total_min}min total ({pre_approved_count} pre-approved batch){end}

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
   - Combine two sources:
     - **Story-file HALTs:** locate the story file in the configured implementation artifacts folder, read the "Dev Agent Record" section, count occurrences of the word "HALT".
     - **Captured halts:** the structured list collected in Step 2 (if `halts` is a list, count its length; if it is a legacy integer, use that integer directly).
   - `halt_count = max(story_file_halts, captured_halts_count)` — captured halts dominate when they exist (they carry duration), but a story-file-only HALT still surfaces in the count.
   - If `pulse_alert_on_halt` is `yes`: display an alert if `halt_count > 0`
   - If `pulse_alert_on_halt` is `warn`: display as an informational warning
   - If `pulse_alert_on_halt` is `no`: record internally but do not display
   - If 0: display "0"
   - When the captured list contains any `kind: approval_wait` entries, surface them separately in the card:
     `Approval-wait: {N} halt(s), {total_min}min total ({pre_approved_count} pre-approved batch)`

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
   - Add the `process_health` field to the story entry in `pulse_metrics`.
   - `halts` accepts two shapes (writers should prefer the structured list whenever halts were observed; the integer form remains valid for "no halts captured"):

   **Shape A — no halts captured (legacy / shorthand):**

   ```yaml
   process_health:
     flow_complete: true
     halts: 0
     unused_skills: ['tea:automate']
     insight: 'Consider tea:automate for fullstack stories'
   ```

   **Shape B — structured list (required when halts >2min were captured):**

   ```yaml
   process_health:
     flow_complete: true
     halts:
       - kind: approval_wait               # approval_wait | incident | external_pause | other
         context: admin_merge_decision     # short identifier
         duration_min: 7                   # integer minutes (>2)
         pre_approved_batch: false         # true skips actual_hours subtraction
         note: 'CI blocked by GH incident, waited for user merge override decision'  # optional
       - kind: incident
         context: github_outage
         duration_min: 360
     unused_skills: []
     insight: 'Approval-wait dominated this story — consider batching the next governance call.'
   ```

   **Shape C — legacy free-form strings (read-only fallback for pre-0.5.0 data):**

   ```yaml
   process_health:
     halts:
       - approval_wait_admin_merge_decision  # ~7min — duration in comment, not machine-readable
   ```

   - Readers MUST handle all three shapes. Treat `halts: 0` as "empty list" semantically. Treat `halts: <int N>` as "N opaque halts, no duration data." Treat a string entry as "1 opaque halt, kind/context inferred from string prefix when possible (e.g., `approval_wait_*` → `kind: approval_wait`), `duration_min` unknown — do NOT subtract from `actual_hours`."
   - Writers MUST NOT emit Shape C. Always write Shape A (no halts) or Shape B (structured). Shape C exists only to keep dashboards from breaking on historical data written before v0.5.0.
   - When Shape C is detected, surface a one-line warning in the track-done card: `⚠ Legacy halt format detected — consider migrating to structured shape for accurate leverage.`

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
