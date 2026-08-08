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

Resolve the PULSE configuration **toml-first** (issue #73):

1. Run `python3 {project-root}/_bmad/scripts/resolve_config.py --project-root {project-root} --key modules.pulse --key core` and read `pulse_*` from the `modules.pulse` table and core keys (`output_folder`, `user_name`, `communication_language`) from `core`.
2. **Per-key fallback** — for any key absent from the resolved toml, read it from the legacy `pulse:` section (module keys) or root (core keys) of `{main_config}`; the yaml is the lowest-priority layer, never authoritative over the toml.
3. **Default last** — if neither has the key, use the `module.yaml` default.

If `resolve_config.py` is unavailable (pre-#2285 install), read `{main_config}` directly as before.

The keys this workflow uses:

- `output_folder`, `user_name`, `communication_language`
- `pulse_data_folder`, `pulse_dashboard_folder`
- `pulse_sprint_status_filename`
- `pulse_estimation_method` (story_points / hours / t-shirt / bcp)
- `pulse_story_point_hours_factor` (story points → hours conversion factor)
- `pulse_leverage_threshold_exceptional` (e.g. 4) — _legacy since v0.6: no longer drives celebration (kept for back-compat)_
- `pulse_leverage_threshold_solid` (e.g. 2) — _legacy since v0.6: no longer drives celebration_
- `pulse_leverage_warning_threshold` (e.g. 1) — _legacy since v0.6: no longer drives celebration_
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

   Every entry from `{workflow.halt_categories_extra}` is also a valid `kind` value. Surface these extra categories in the prompt alongside the built-ins so the user can pick them directly (e.g. `security_review_wait`, `ux_review_wait`).

   For each halt, capture:
   - `kind` (built-in enum above OR any entry from `{workflow.halt_categories_extra}`)
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

If `pulse_estimation_method` is `bcp`:

```text
estimated_hours = value recorded directly in hours
                  (already derived upstream by bmad-module-bcp — PULSE does NOT
                   compute hours from BCP points; it consumes the field as-is,
                   identical to the `hours` branch)
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
estimate_error_pct = round(abs(actual_hours - estimated_hours) / max(0.01, estimated_hours) * 100, 1)  # how far the estimate was from reality; equals |drift_pct| for BCP stories
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
5. Add the `estimate_error_pct` field with the calculated value — the per-story **predictability** signal (accuracy of plan vs reality, **lower is better**; `0%` = perfectly on-plan). Persist it next to `leverage_ratio`: the leverage ratio is a 1.0-centered multiplier that *mis-signals* predictability (a calibrated `0.9` reads like "weak leverage" when it is in fact good predictability), so the explicit accuracy field is the one that reads as previsibilidade per-story. The dashboard's `predictability_score` is the median of this across stories.

**Stable leverage vs frozen reference (issue #65 — only when available):**

Resolve `estimated_hours_reference` as `pulse_metrics[story].estimated_hours_reference`
(snapshotted by track-start). If that snapshot is absent, re-read the story frontmatter
`estimated_hours_reference` (read-only) as a fallback. If neither yields a positive
number, **omit** this block entirely — behave exactly as today (vs-PLAN leverage only).

When a positive `estimated_hours_reference` is available, add a `leverage_vs_reference`
field to the story entry in `pulse_metrics`:

```text
leverage_vs_reference = round(estimated_hours_reference / actual_hours, 1)
```

This is the **stable ROI** number: its denominator is **frozen** (the reference rate is
governed upstream by `bmad-module-bcp`, never recalibrated), so unlike `leverage_ratio`
(vs PLAN, which collapses to ~1.0x by construction as the estimate basis calibrates) it
**does not collapse**. It is an honest multiplier **vs a fixed external benchmark**, not
"vs human" and not a target — predictability stays the hero metric. PULSE only **reads**
the field (file convention) and divides; it never computes the reference, never reads the
BCP baseline, and never writes the story frontmatter (read-only input owned by
`bmad-module-bcp`).

**BCP productivity (only when a BCP total is available for this story):**

Resolve `bcp_total` from the story frontmatter `bcp.total` (read-only) — the
story's **final** BCP. If the frontmatter yields no total, fall back to
`pulse_metrics[story].bcp_at_start.total` (snapshotted by track-start). If neither
yields a number, skip this block entirely — behave exactly as today.

**Why the final total, not the start snapshot.** `estimated_hours` is derived
upstream from the final BCP, so `h_per_bcp_estimated = estimated_hours / bcp_total`
only holds when the same total sits on both sides. A story rescored mid-flight
(start 15, final 13) measured against the snapshot pairs a numerator from one
scoring with a denominator from another, describing no state the story was ever
in. The error does not stay local: `h_per_bcp_actual` feeds the observed
per-category baseline and `drift_pct` feeds the convergence signal, so a stale
denominator biases the very numbers the team calibrates estimates against.

When the two totals differ, keep `bcp_at_start.total` as evidence of the rescore
(the dashboard labels such a story **rescored**) — the divergence is worth
recording, it just must not be the denominator.

When `bcp_total` is a positive number, add a `bcp_recorded` field to the story
entry in `pulse_metrics`:

```text
h_per_bcp_actual    = round(actual_hours    / bcp_total, 2)
h_per_bcp_estimated = round(estimated_hours / bcp_total, 2)
drift_pct           = round((h_per_bcp_actual - h_per_bcp_estimated)
                            / h_per_bcp_estimated * 100, 1)   # 0.0 if estimated == 0
```

```yaml
pulse_metrics:
  "5.7":
    # ... existing fields ...
    bcp_recorded:
      total: 21
      h_per_bcp_actual: 5.0
      h_per_bcp_estimated: 5.0
      drift_pct: 0.0
```

PULSE does **not** update any BCP baseline. Baseline maturation is the
`bmad-module-bcp` module's responsibility (via `/bmad-bcp-recalibrate`). This step
only records read-derived telemetry inside the `pulse_metrics:` section.

### Step 4: Generate Efficiency Pulse + Process Health

Display in the terminal:

```text
⚡ Levi: Story {story_id} — DONE!

   📊 Efficiency
   Human estimate: {estimated_hours}h ({dev_count} devs)
   Actual AI time: {actual_hours}h ({elapsed_minutes}min wall-clock)
   AI Leverage: {leverage_ratio}x (vs PLAN, not vs human)
   {if leverage_vs_reference}AI Leverage: {leverage_vs_reference}x (vs REFERENCE, frozen — stable ROI, does not collapse){end}
   Estimate accuracy: {estimate_error_pct}% off plan
   {if bcp_recorded}BCP: {bcp_recorded.total} pts | {bcp_recorded.h_per_bcp_actual}h/BCP actual vs {bcp_recorded.h_per_bcp_estimated}h/BCP est ({bcp_recorded.drift_pct:+}% drift){end}
   Quality: {first_pass ? "✅ first-pass" : "🔄 " + review_cycles + " cycles"}
   Tasks: {task_count}
   Category: {category}
   {estimate_error_pct <= 15 ? (first_pass ? "🎯 On-plan! (estimate within 15%, first-pass)" : "🎯 On-plan (estimate within 15%)") : estimate_error_pct >= 50 ? "⚠ Off-plan — review the estimate basis, not the speed." : "📊 Data recorded."}
   <!-- v0.6: celebration triggers on estimate ACCURACY (on-plan), not on leverage magnitude. A high multiplier is an uncalibrated estimate, not a win (anti-Goodhart). pulse_leverage_threshold_exceptional/solid are retired as celebration triggers — leverage is reported "vs PLAN" as context only. -->

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
- DO NOT write to the story frontmatter or to any BCP baseline file (`bcp-baseline.yaml`) — `bcp.*` is read-only input owned by `bmad-module-bcp`; baseline recalibration lives in that module
- Data is isolated in the `pulse_metrics:` section — zero risk of conflict
- Communicate in the language configured in `communication_language`
- Respect `pulse_levi_verbosity` for level of detail (concise / standard / verbose)
- Respect `pulse_levi_coaching_mode` (yes = suggest improvements, metrics-only = data only)
- If no entry exists for the story ID in `pulse_metrics:`, warn and suggest running track-start first

---

## Post-Metric Hooks

After Step 6 has produced the final metrics card but BEFORE displaying it to the user, execute each entry in `{workflow.metric_post_hooks}` in order. Each entry is a shell command or skill invocation string — treat it as a hook that may publish the metrics to an external destination (Grafana, Slack, a webhook, a downstream pipeline). Surface any non-zero exit codes as a one-line warning appended to the card; do not fail the workflow on hook errors.

## On Completion

After the Efficiency Pulse has been displayed AND all `{workflow.metric_post_hooks}` have run, execute the `{workflow.on_complete}` scalar if non-empty. Override wins; an empty value means no custom post-completion behavior.

The shipped default for `on_complete` is an opt-in auto-dashboard trigger gated by `pulse_auto_dashboard` in the `pulse` config section. When that flag is `yes`, the default invokes `/bmad-pulse-dashboard` to regenerate the cumulative dashboard right after the Efficiency Pulse card is shown. When the flag is `no`, missing, or any other value, the default behaves as a silent no-op — preserving the pre-flag behavior. To disable the auto-dashboard while keeping the flag enabled (or to swap in a different post-completion hook), override `on_complete` in `_bmad/custom/bmad-pulse-track-done.toml`.

In parallel-PR workflows, auto-regenerating `dashboard.md` on every track-done **will produce merge conflicts** — the file is rewritten in full each run. See the README "Auto-dashboard" section for the three documented mitigation strategies before enabling.
