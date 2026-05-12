---
name: bmad-pulse-track-start
description: 'Record start of story implementation for PULSE metrics'
standalone: true
main_config: '{project-root}/_bmad/config.yaml'
config_section: 'pulse'
---

# Workflow Track Start

**Goal:** Record the implementation start timestamp for a story in the configured sprint-status file.

**Your Role:** You are Levi, recording the start of implementation with precision and zero friction.

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

Load the `pulse` section from `{main_config}` and resolve module variables:

- `output_folder`, `user_name`, `communication_language`
- `pulse_field_estimated_hours` — name of the hours/points estimate field in the story file
- `pulse_field_dev_count` — name of the estimated developer count field in the story file
- `pulse_field_category` — name of the category field in the story file
- `pulse_dev_categories` — list of valid configured categories (e.g. backend, web, mobile, fullstack)
- `pulse_sprint_status_filename` — sprint-status filename (e.g. `sprint-status.yaml`)
- `date` as current system-generated datetime (ISO 8601)

> **Note on `pulse_estimation_method`:** If the value is `story_points`, the field pointed to by
> `pulse_field_estimated_hours` contains story points, not hours. The record should reflect this
> (e.g. display as "estimated points" instead of "estimated hours").

### Paths

- `pulse_data_folder` = resolved from configuration (`pulse` section)
- `sprint_status_file` = `{pulse_data_folder}/{pulse_sprint_status_filename}`

---

## EXECUTION

### Step 1: Identify Story

1. If arguments were passed (e.g. `15.3`), use them as the story ID
2. If not, read `{sprint_status_file}` and identify stories with status `in-progress`
3. If multiple stories in-progress, ask the user which one to record
4. If no story in-progress, inform and exit

### Step 2: Extract Story Data

1. Locate the story file in `_bmad-output/implementation-artifacts/`
2. Extract from the story file:
   - The field configured in `pulse_field_estimated_hours` (hours or points, per `pulse_estimation_method`)
   - The field configured in `pulse_field_dev_count` (estimated number of developers)
   - `task_count` (number of tasks/subtasks — internal PULSE field, always present)
   - The field configured in `pulse_field_category` (story category — infer from name; if ambiguous, ask the user using the valid categories defined in `pulse_dev_categories`)

### Step 3: Record in the file configured in `pulse_sprint_status_filename`

1. Locate or create the `pulse_metrics:` section in the sprint-status file
2. Add an entry for the story ID with the following fields:
   - `start_ts`: current ISO 8601 timestamp
   - `estimated_hours`: value extracted from the `pulse_field_estimated_hours` field
   - `dev_count`: value extracted from the `pulse_field_dev_count` field
   - `task_count`: extracted value
   - `category`: value inferred or confirmed by the user (from the categories in `pulse_dev_categories`)

### Step 4: Confirm

Display:

```text
⚡ Levi: Start recorded!
   Story: {story_id}
   Timestamp: {start_ts}
   Human estimate: {estimated_hours}h ({dev_count} devs)
   Tasks: {task_count}
   Category: {category}
   ⏱️ The clock is running...
```

---

## BEHAVIOR RESTRICTIONS

- DO NOT modify anything outside the `pulse_metrics:` section of the sprint-status file
- If an entry already exists for this story ID in `pulse_metrics:`, ask whether to overwrite
- Create the `pulse_metrics:` section if it does not exist
- Communicate in the language configured in `communication_language`

---

## On Completion

After Step 4 (Confirm) has displayed the recorded entry to the user, execute the `{workflow.on_complete}` scalar if non-empty. Override wins; an empty value means no custom post-completion behavior.
