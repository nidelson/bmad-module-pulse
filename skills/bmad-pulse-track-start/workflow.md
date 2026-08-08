---
name: bmad-pulse-track-start
description: 'Record start of story implementation for PULSE metrics'
standalone: true
main_config: '{project-root}/_bmad/config.yaml'
config_section: 'pulse'
---

# Workflow Track Start

**Goal:** Record the implementation start timestamp for a story in the configured sprint-status file.

**Your Role:** You are Maxine, recording the start of implementation with precision and zero friction.

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
- `pulse_estimation_method` — `hours` / `story_points` / `tshirt` / `bcp`
- `pulse_field_estimated_hours` — name of the hours/points estimate field in the story file
- `pulse_field_dev_count` — name of the estimated developer count field in the story file
- `pulse_field_category` — name of the category field in the story file
- `pulse_dev_categories` — list of valid configured categories (e.g. backend, web, mobile, fullstack)
- `pulse_sprint_status_filename` — sprint-status filename (e.g. `sprint-status.yaml`)
- `date` as current system-generated datetime (ISO 8601)

> **Note on `pulse_estimation_method`:** If the value is `story_points`, the field pointed to by
> `pulse_field_estimated_hours` contains story points, not hours. The record should reflect this
> (e.g. display as "estimated points" instead of "estimated hours").
>
> **Note on `bcp` (Business Complexity Points):** PULSE stays **passive and zero-coupled** —
> it does NOT compute hours from BCP. The `bcp` value only signals that the upstream
> `estimated_hours` was already derived by the [`bmad-module-bcp`](https://github.com/nidelson/bmad-module-bcp)
> module (install = consent to overwrite). PULSE reads `estimated_hours` exactly as for
> `hours`, and additionally snapshots the `bcp.*` block for audit (see Step 2/3). PULSE
> never writes to the story frontmatter and never touches the BCP baseline file.

### Paths

- `pulse_data_folder` = resolved from configuration (`pulse` section)
- `sprint_status_file` = `{pulse_data_folder}/{pulse_sprint_status_filename}`

---

## EXECUTION

### Step 1: Identify Story

1. **Explicit story id — preferred path (this is how auto-tracking invokes the skill).**
   If an argument was passed (e.g. `15.3`), or a story id / story file path is
   available from the invoking context, use it as the story ID directly. Do
   **not** require the story to be marked `in-progress` in sprint-status —
   track-start fires at implementation start, when the story may still be
   `ready-for-dev`. The sprint-status status field is not a precondition.
2. **Fallback — no story id available (manual no-argument invocation).** Read
   `{sprint_status_file}` and identify stories with status `in-progress`.
3. If exactly one story is `in-progress`, use it.
4. If multiple stories are `in-progress`, ask the user which one to record.
5. If no story is `in-progress`, do **not** silently exit — ask the user for the
   story id (the story may simply not have been transitioned to `in-progress` yet).

### Step 2: Extract Story Data

1. Locate the story file in `_bmad-output/implementation-artifacts/`
2. Extract from the story file:
   - The field configured in `pulse_field_estimated_hours` (hours or points, per `pulse_estimation_method`)
   - The field configured in `pulse_field_dev_count` (estimated number of developers)
   - `task_count` (number of tasks/subtasks — internal PULSE field, always present)
   - The field configured in `pulse_field_category` (story category — infer from name; if ambiguous, ask the user using the valid categories defined in `pulse_dev_categories`)
   - The `bcp:` frontmatter block, **only if present** (written exclusively by `bmad-module-bcp`):
     - Read `bcp.schema_version`. If it is a value this skill does not recognize (anything other than `"1.0"`), emit a one-line warning (`⚠ Unknown bcp.schema_version <v> — ignoring bcp.* for this story`) and treat the block as absent for the rest of the workflow.
     - Otherwise capture `bcp.total`, `bcp.rule_version`, and `bcp.scored_by` for the snapshot in Step 3. PULSE does not interpret `bcp.breakdown` or `bcp.history`.
     - This extraction is **read-only** — PULSE never writes back to the story frontmatter.
   - The `estimated_hours_reference` field, **only if present** (frozen leverage anchor written by `bmad-module-bcp`, issue #65). It is `bcp.total × reference_h_per_bcp` — a **frozen** denominator for stable leverage that does not collapse as the team calibrates. Capture it read-only for the snapshot in Step 3. PULSE never computes it, never reads the BCP baseline, and never writes it back to the story frontmatter. When absent (BCP not installed, or older BCP), omit it — behave exactly as today.

### Step 3: Record in the file configured in `pulse_sprint_status_filename`

1. Locate or create the `pulse_metrics:` section in the sprint-status file
2. Add an entry for the story ID with the following fields:
   - `start_ts`: current ISO 8601 timestamp
   - `estimated_hours`: value extracted from the `pulse_field_estimated_hours` field
   - `dev_count`: value extracted from the `pulse_field_dev_count` field
   - `task_count`: extracted value
   - `category`: value inferred or confirmed by the user (from the categories in `pulse_dev_categories`)
3. **BCP snapshot (only when a valid `bcp:` block was captured in Step 2):** add to the same story entry:
   - `estimation_basis: bcp`
   - `bcp_at_start:` with `total`, `rule_version`, `scored_by` taken from the `bcp.*` block

   ```yaml
   pulse_metrics:
     "5.7":
       start_ts: "..."
       estimated_hours: 86.7
       estimation_basis: bcp
       estimated_hours_reference: 105.0   # frozen leverage anchor (issue #65) — only when present
       bcp_at_start:
         total: 21
         rule_version: "1.0"
         scored_by: bruno
   ```

   When `pulse_estimation_method` is not `bcp` but a valid `bcp:` block is present, the
   snapshot is still recorded as opt-in telemetry (`estimation_basis` reflects the
   configured method, `bcp_at_start` is added alongside). When no valid `bcp:` block is
   present, omit both fields entirely — behave exactly as today.
4. **Frozen reference snapshot (only when `estimated_hours_reference` was captured in Step 2):** add `estimated_hours_reference` to the same story entry, copied verbatim from the story frontmatter. This is the frozen denominator track-done uses for the stable `leverage_vs_reference` (issue #65). Omit the field entirely when it is absent — it is opt-in telemetry, never fabricated.

### Step 4: Estimation drift check (advisory — non-blocking)

This is the v0.7 "action that matters": surface drift at the commitment gate so a
bad estimate can be caught *before* it becomes a promise. Compute
`cohort_drift(category, segment)` from the existing `pulse_metrics:` history (see
the `bmad-pulse-dashboard` aggregation for the canonical definition):

- **Segment** (only when a `bcp.total` was captured this run): `micro` if
  `bcp.total < median(bcp.total over recorded stories)`, else `story`. Without
  BCP, the cohort is `category` alone (documented fallback).
- **Cohort drift**: the **median `|estimate error|%`** over the **last `K = 5`**
  completed stories in the cohort (a completed story has both `estimated_hours`
  and a recorded `actual_hours`/drift). For BCP stories this equals
  `|bcp_recorded.drift_pct|`.
- **Emit the advisory only when `n >= 3` and the median exceeds `T = 25%`.**
  Otherwise stay **silent** — no false alarm on a healthy or thin cohort.

The advisory is **non-blocking**: a one-line heads-up in the Confirm card. The
start is recorded regardless and PULSE **never changes `estimated_hours`** — the
re-estimate decision is the human's/agent's. Defaults `K=5` / `T=25%` are inline
(may become config later).

> **Advisory invariant (do not regress).** Estimation is owned **upstream** (BMAD/Amelia, or BCP/Bruno) — PULSE stays passive. This alert **informs, it never drives**: it reads `pulse_metrics` history, it never writes the story frontmatter, never writes or adjusts `estimated_hours`, never halts the start, and never re-scores anything. If a future edit makes it mutate an estimate or block the flow, that breaks the contract (locked by `tests/test_action_alert.py`).

### Step 5: Confirm

Display:

```text
💓 Maxine: Start recorded!
   Story: {story_id}
   Timestamp: {start_ts}
   Human estimate: {estimated_hours}h ({dev_count} devs)
   {if bcp_at_start}BCP: {bcp_at_start.total} pts (rule {bcp_at_start.rule_version}, scored by {bcp_at_start.scored_by}){end}
   Tasks: {task_count}
   Category: {category}
   {if cohort_drift alert (n >= 3 and median > 25%)}⚠ Heads up: stories like {category}{if segment}/{segment}{end} were off +{median_abs_drift}% (median) over the last {K} — re-estimate before committing? (advisory; PULSE will not change your estimate){end}
   ⏱️ The clock is running...
```

---

## BEHAVIOR RESTRICTIONS

- DO NOT modify anything outside the `pulse_metrics:` section of the sprint-status file
- DO NOT write to the story file frontmatter or to any BCP baseline file — `bcp.*` is read-only input owned by `bmad-module-bcp`
- The v0.7 drift advisory (Step 4) is **advisory-only and non-blocking**: it NEVER writes or changes `estimated_hours`, never auto-adjusts the estimate, and never halts the start. It only surfaces a heads-up; the re-estimate decision belongs to the human/agent.
- If an entry already exists for this story ID in `pulse_metrics:`, ask whether to overwrite
- Create the `pulse_metrics:` section if it does not exist
- Communicate in the language configured in `communication_language`

---

## On Completion

After Step 4 (Confirm) has displayed the recorded entry to the user, execute the `{workflow.on_complete}` scalar if non-empty. Override wins; an empty value means no custom post-completion behavior.
