---
name: bmad-pulse-track-backfill
description: 'Retroactively record HI/HF and PULSE metrics for an unmeasured story'
standalone: true
main_config: '{project-root}/_bmad/config.yaml'
config_section: 'pulse'
---

# Workflow Track Backfill

**Goal:** Reconstruct a complete `pulse_metrics:` entry — start, end, and the
same leverage/process math `track-done` produces — for a story whose
`track-start`/`track-done` were never invoked, marking it `retroactive: true`
for traceability.

**Your Role:** You are Maxine, recovering lost measurements with rigor and
honest provenance. You never disguise reconstructed data as real-time data.

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
- `pulse_estimation_method` — `hours` / `story_points` / `tshirt` / `bcp`
- `pulse_story_point_hours_factor` (story points → hours conversion factor)
- `pulse_field_estimated_hours`, `pulse_field_dev_count`, `pulse_field_category`
- `pulse_dev_categories` — list of valid configured categories
- `pulse_leverage_threshold_exceptional`, `pulse_leverage_threshold_solid`, `pulse_leverage_warning_threshold`
- `pulse_verbosity`, `pulse_coaching_mode`
- `date` as current system-generated datetime (ISO 8601)

> **Renamed in v0.9.** `pulse_verbosity` and `pulse_coaching_mode` were
> `pulse_levi_verbosity` and `pulse_levi_coaching_mode`. Read the new key
> first and **fall back to the legacy name** when it is absent: an upgrading
> project still has the old key in its config, and a rename without a
> fallback reverts it to the default silently — the setting is still in the
> file, just no longer read, so nothing looks broken.

> **Note on `pulse_estimation_method`:** estimate conversion is identical to
> `track-done` (see Step 4). For `story_points` the estimate field holds
> points; for `bcp` PULSE stays **passive and zero-coupled** — it does NOT
> compute hours from BCP. `bcp` only signals the upstream `estimated_hours`
> was already derived by [`bmad-module-bcp`](https://github.com/nidelson/bmad-module-bcp);
> PULSE reads `estimated_hours` exactly as for `hours` and additionally
> snapshots the read-only `bcp.*` block for audit. PULSE never writes the
> story frontmatter and never touches the BCP baseline file.

### Paths

- `sprint_status_file` = `{pulse_data_folder}/{pulse_sprint_status_filename}`

---

## EXECUTION

### Step 1: Parse Arguments

Expected invocation:

```text
/bmad-pulse-track-backfill [story_id] --hi "2026-05-18 14:00" --hf "2026-05-18 15:00"
```

1. `story_id` — first positional argument (e.g. `1.2`).
2. `--hi` (HI, hora início) — implementation start, parsed as a local datetime.
3. `--hf` (HF, hora fim) — implementation end.
4. Optional `--review-cycles N` — defaults to `1` (first-pass) if omitted; prompt only if not supplied and `pulse_verbosity` is not `concise`.
5. Optional `--effective-hours H` — overrides the wall-clock derivation when the user already knows the effective AI working time (mirrors `track-done`'s `effective_hours`).
6. Optional `--note "..."` — free text appended to `retroactive_note`.

Any of `story_id`, `--hi`, `--hf` missing → prompt the user for the missing value(s). Do not invent timestamps.

### Step 2: Validate Inputs

1. Parse `--hi` and `--hf` to ISO 8601 (`YYYY-MM-DDTHH:MM:SS`). Accept `YYYY-MM-DD HH:MM` and ISO forms; reject anything unparseable with a one-line error and exit.
2. Require `HF > HI`. If `HF <= HI`, error (`⚠ HF must be after HI`) and exit — never write a non-positive duration.
3. Read `{sprint_status_file}`. If a `pulse_metrics:` entry already exists for `story_id`:
   - If it has both `start_ts` and `end_ts` and **no** `retroactive: true`, warn: this looks like real-time tracked data — backfilling would overwrite genuine measurements. Ask for explicit confirmation before proceeding.
   - Otherwise ask whether to overwrite the existing (likely earlier backfill) entry.

### Step 3: Extract Story Data (read-only)

1. Locate the story file in the configured implementation-artifacts folder.
2. Extract, identically to `track-start`:
   - the field configured in `pulse_field_estimated_hours` (hours or points per `pulse_estimation_method`)
   - the field configured in `pulse_field_dev_count`
   - `task_count` (number of tasks/subtasks)
   - the field configured in `pulse_field_category` (infer from name; if ambiguous, ask using `pulse_dev_categories`)
   - the `bcp:` frontmatter block **only if present** (written exclusively by `bmad-module-bcp`):
     - Read `bcp.schema_version`. If it is anything other than `"1.0"`, emit `⚠ Unknown bcp.schema_version <v> — ignoring bcp.* for this story` and treat the block as absent.
     - Otherwise capture `bcp.total`, `bcp.rule_version`, `bcp.scored_by`. PULSE does not interpret `bcp.breakdown` or `bcp.history`.
   - This extraction is **read-only** — PULSE never writes back to the story frontmatter.
3. If the story file or the estimate field cannot be found, ask the user to supply `estimated_hours` (and `category`) directly rather than aborting — the backfill's purpose is to recover otherwise-lost data.

### Step 4: Calculate Metrics

Estimate conversion is identical to `track-done`:

- `story_points` → `estimated_hours = points * pulse_story_point_hours_factor`
- `tshirt` → S=2h, M=4h, L=8h, XL=16h
- `hours` → value used directly
- `bcp` → value used directly (already derived upstream by `bmad-module-bcp`; PULSE does NOT compute hours from BCP — it consumes the field as-is, identical to the `hours` branch)

Leverage:

```text
elapsed_minutes = (HF - HI) in minutes
actual_hours    = effective_hours ?? max(0.01, elapsed_minutes / 60)
leverage_ratio  = estimated_hours / actual_hours
estimate_error_pct = round(abs(actual_hours - estimated_hours) / max(0.01, estimated_hours) * 100, 1)  # |drift_pct| for BCP stories
first_pass      = review_cycles == 1
```

There is no halt subtraction in backfill — halts are real-time-only signal that
cannot be reconstructed honestly after the fact. If the user supplied
`--effective-hours`, it wins (they already corrected for non-dev time);
otherwise `actual_hours` is the raw `HF − HI` wall-clock, floored at 0.01h to
avoid divide-by-zero.

**BCP productivity (only when a BCP total is available):** resolve `bcp_total`
from the `bcp.*` block captured in Step 3. If absent, skip this block entirely.
When `bcp_total` is a positive number:

```text
h_per_bcp_actual    = round(actual_hours    / bcp_total, 2)
h_per_bcp_estimated = round(estimated_hours / bcp_total, 2)
drift_pct           = round((h_per_bcp_actual - h_per_bcp_estimated)
                            / h_per_bcp_estimated * 100, 1)   # 0.0 if estimated == 0
```

PULSE does **not** update any BCP baseline — baseline maturation is the
`bmad-module-bcp` module's responsibility (via `/bmad-bcp-recalibrate`).

**Stable leverage vs frozen reference (issue #65 — only when available):**
read `estimated_hours_reference` from the story frontmatter (read-only — the
frozen leverage anchor written by `bmad-module-bcp`). When it is a positive
number, record `leverage_vs_reference = round(estimated_hours_reference /
actual_hours, 1)`. This denominator is **frozen** (governed upstream, never
recalibrated), so unlike `leverage_ratio` (vs PLAN, which collapses to ~1.0x as
the basis calibrates) it **does not collapse** — an honest ROI multiplier vs a
fixed external benchmark, not vs human and not a target. Absent → omit the
field, behave exactly as today. PULSE only reads and divides; it never computes
the reference, reads the baseline, or writes the story frontmatter.

### Step 5: Write the Retroactive Entry

In the `pulse_metrics:` section of `{sprint_status_file}`, create or overwrite
the entry for `story_id`. **Shape note:** PULSE stores `pulse_metrics` as a
**mapping keyed by story id** (same shape `track-start`/`track-done` write and
the dashboard reads), not a list. Use that canonical shape so the entry is
readable by every other PULSE skill:

```yaml
pulse_metrics:
  "1.2":
    start_ts: "2026-05-18T14:00:00"
    end_ts: "2026-05-18T15:00:00"
    estimated_hours: 103
    dev_count: 1
    task_count: 4
    category: backend
    actual_hours: 1.0          # retroactive backfill: HF 15:00 - HI 14:00
    review_cycles: 1
    leverage_ratio: 103.0
    estimate_error_pct: 99.0   # predictability: |actual - estimated| / estimated (lower is better)
    first_pass: true
    retroactive: true
    retroactive_note: "Data inserted manually via track-backfill — TS/TD not invoked in the original cycle"
```

Rules:

1. `retroactive: true` is **mandatory and non-negotiable** on every entry this
   skill writes. Never omit it, never set it to `false`. It is the provenance
   marker that lets the dashboard and any consumer distinguish reconstructed
   data from real-time measurement.
2. `retroactive_note` always records that TS/TD were not invoked in the
   original cycle. Append the user's `--note` text when provided.
3. Annotate `actual_hours` with a YAML comment showing the HI/HF derivation
   (or `effective_hours override` when `--effective-hours` was supplied) so the
   math stays traceable.
4. Always write `estimate_error_pct` (the per-story **predictability** signal —
   accuracy of plan vs reality, **lower is better**). It is the field that reads
   as previsibilidade per-story; `leverage_ratio` is a 1.0-centered ratio that
   mis-signals it. The dashboard medians this across stories.
5. **BCP snapshot (only when a valid `bcp:` block was captured):** add
   `estimation_basis: <method>`, `bcp_at_start:` (`total`, `rule_version`,
   `scored_by`), and `bcp_recorded:` (`total`, `h_per_bcp_actual`,
   `h_per_bcp_estimated`, `drift_pct`). When no valid `bcp:` block is present,
   omit all BCP fields entirely.
6. **Frozen-reference leverage (only when `estimated_hours_reference` is present
   in the story frontmatter):** add `leverage_vs_reference` (issue #65). Omit it
   entirely when the field is absent — never fabricate it.
7. Do not write `process_health` — flow/halt/skill checks require real-time
   observation `track-done` performs live. Backfill deliberately leaves
   `process_health` absent; readers already treat it as optional.

### Step 6: Confirm

Display (respect `pulse_verbosity`):

```text
💓 Maxine: Backfill recorded — RETROACTIVE entry for story {story_id}
   ⚠ Reconstructed data — TS/TD were not run in the original cycle.

   HI: {start_ts}  →  HF: {end_ts}
   Human estimate: {estimated_hours}h ({dev_count} devs)
   Actual AI time: {actual_hours}h ({elapsed_minutes}min wall-clock)
   AI Leverage: {leverage_ratio}x (vs PLAN, not vs human)
   {if leverage_vs_reference}AI Leverage: {leverage_vs_reference}x (vs REFERENCE, frozen — stable ROI, does not collapse){end}
   Estimate accuracy: {estimate_error_pct}% off plan
   {if bcp_recorded}BCP: {bcp_recorded.total} pts | {bcp_recorded.h_per_bcp_actual}h/BCP actual vs {bcp_recorded.h_per_bcp_estimated}h/BCP est ({bcp_recorded.drift_pct:+}% drift){end}
   Quality: {first_pass ? "✅ first-pass" : "🔄 " + review_cycles + " cycles"}
   Category: {category}
   {estimate_error_pct <= 15 ? (first_pass ? "🎯 On-plan! (estimate within 15%, first-pass)" : "🎯 On-plan (estimate within 15%)") : estimate_error_pct >= 50 ? "⚠ Off-plan — review the estimate basis, not the speed." : "📊 Data recorded."}

   💡 {if pulse_coaching_mode == yes}Run /bmad-pulse-track-start and /bmad-pulse-track-done on future stories to capture process health and halts, which backfill cannot reconstruct.{end}
```

### Step 7: Offer Dashboard Refresh

Ask the user (default yes unless `pulse_verbosity` is `concise`, in which
case proceed without prompting): "Regenerate the PULSE dashboard now to include
this story?" If yes, invoke the `bmad-pulse-dashboard` skill. Consumers who
want this unconditional can set it in `{workflow.on_complete}` instead.

---

## BEHAVIOR RESTRICTIONS

- DO NOT modify anything outside the `pulse_metrics:` section of `{sprint_status_file}`
- DO NOT write to the story file frontmatter or to any BCP baseline file (`bcp-baseline.yaml`) — `bcp.*` is read-only input owned by `bmad-module-bcp`; baseline recalibration lives in that module
- Every entry this skill writes MUST carry `retroactive: true` — backfilled data is never presented as real-time data
- Never reconstruct `process_health` or halts — those require live observation; leave them absent
- If a real-time-tracked entry (has `start_ts`+`end_ts`, no `retroactive` flag) already exists for the story, require explicit confirmation before overwriting
- Create the `pulse_metrics:` section if it does not exist
- Communicate in the language configured in `communication_language`

---

## On Completion

After Step 6 (Confirm) has displayed the recorded entry and the optional
dashboard refresh in Step 7 has run, execute the `{workflow.on_complete}`
scalar if non-empty. Override wins; an empty value means no custom
post-completion behavior.
