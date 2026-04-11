---
name: pulse-setup
description: Installs and configures the PULSE module in a BMAD project. Use when the user requests 'install PULSE', 'configure PULSE', or 'setup PULSE'.
---

# Module Setup

## Overview

Installs and configures a BMad module into a project. Module identity (name, code, version) comes from `./assets/module.yaml`. Collects user preferences and writes them to three files:

- **`{project-root}/_bmad/config.yaml`** — shared project config: core settings at root (e.g. `output_folder`, `document_output_language`) plus a section per module with metadata and module-specific values. User-only keys (`user_name`, `communication_language`) are **never** written here.
- **`{project-root}/_bmad/config.user.yaml`** — personal settings intended to be gitignored: `user_name`, `communication_language`, and any module variable marked `user_setting: true` in `./assets/module.yaml`. These values live exclusively here.
- **`{project-root}/_bmad/module-help.csv`** — registers module capabilities for the help system.

Both config scripts use an anti-zombie pattern — existing entries for this module are removed before writing fresh ones, so stale values never persist.

`{project-root}` is a **literal token** in config values — never substitute it with an actual path. It signals to the consuming LLM that the value is relative to the project root, not the skill root.

## On Activation

1. Read `./assets/module.yaml` for module metadata and variable definitions (the `code` field is the module identifier)
2. Check if `{project-root}/_bmad/config.yaml` exists — if a section matching the module's code is already present, inform the user this is an update
3. Check for per-module configuration at `{project-root}/_bmad/pulse/config.yaml` and `{project-root}/_bmad/core/config.yaml`. If either file exists:
   - If `{project-root}/_bmad/config.yaml` does **not** yet have a section for this module: this is a **fresh install**. Inform the user that installer config was detected and values will be consolidated into the new format.
   - If `{project-root}/_bmad/config.yaml` **already** has a section for this module: this is a **legacy migration**. Inform the user that legacy per-module config was found alongside existing config, and legacy values will be used as fallback defaults.
   - In both cases, per-module config files and directories will be cleaned up after setup.

If the user provides arguments (e.g. `accept all defaults`, `--headless`, or inline values like `user name is BMad, I speak Swahili`), map any provided values to config keys, use defaults for the rest, and skip interactive prompting. Still display the full confirmation summary at the end.

## Collect Configuration

Ask the user for values. Show defaults in brackets. Present all values together so the user can respond once with only the values they want to change (e.g. "change language to Swahili, rest are fine"). Never tell the user to "press enter" or "leave blank" — in a chat interface they must type something to respond.

**Default priority** (highest wins): existing new config values > legacy config values > `./assets/module.yaml` defaults. When legacy configs exist, read them and use matching values as defaults instead of `module.yaml` defaults. Only keys that match the current schema are carried forward — changed or removed keys are ignored.

**Core config** (only if no core keys exist yet): `user_name` (default: BMad), `communication_language` and `document_output_language` (default: English — ask as a single language question, both keys get the same answer), `output_folder` (default: `{project-root}/_bmad-output`). Of these, `user_name` and `communication_language` are written exclusively to `config.user.yaml`. The rest go to `config.yaml` at root and are shared across all modules.

**Module config**: Read each variable in `./assets/module.yaml` that has a `prompt` field. Ask using that prompt with its default value (or legacy value if available).

**Validation rules:**
- If `pulse_estimation_method` = `story_points` and `pulse_story_point_hours_factor` has not been set, warn before continuing
- If `pulse_dev_categories` = `custom`, request a comma-separated list

## Write Files

Write a temp JSON file with the collected answers structured as `{"core": {...}, "module": {...}}` (omit `core` if it already exists). Then run both scripts — they can run in parallel since they write to different files:

```bash
python3 ./scripts/merge-config.py --config-path "{project-root}/_bmad/config.yaml" --user-config-path "{project-root}/_bmad/config.user.yaml" --module-yaml ./assets/module.yaml --answers {temp-file} --legacy-dir "{project-root}/_bmad"
python3 ./scripts/merge-help-csv.py --target "{project-root}/_bmad/module-help.csv" --source ./assets/module-help.csv --legacy-dir "{project-root}/_bmad" --module-code pulse
```

Both scripts output JSON to stdout with results. If either exits non-zero, surface the error and stop. The scripts automatically read legacy config values as fallback defaults, then delete the legacy files after a successful merge. Check `legacy_configs_deleted` and `legacy_csvs_deleted` in the output to confirm cleanup.

Run `./scripts/merge-config.py --help` or `./scripts/merge-help-csv.py --help` for full usage.

## Register Agent in Manifest

After writing config and help CSV, register the Levi agent in the project's agent manifest so it appears in Party Mode and other agent-aware features.

Check if `{project-root}/_bmad/_config/agent-manifest.csv` exists:
- If **yes**: merge the PULSE agent entry using the same anti-zombie pattern (remove existing rows with `name="pulse"`, then append)
- If **no**: skip this step and inform the user that the agent manifest was not found — Levi will still work via direct skill invocation but won't appear in Party Mode

To merge, reuse the `merge-help-csv.py` script since it handles generic CSV merge with anti-zombie:

```bash
python3 ./scripts/merge-help-csv.py --target "{project-root}/_bmad/_config/agent-manifest.csv" --source ./assets/agent-manifest-fragment.csv --module-code pulse
```

Note: the `--module-code` flag scopes the anti-zombie removal to rows where the first column matches "pulse", which corresponds to the `name` column in agent-manifest.csv.

If successful, inform the user: "Agent Levi registered in agent-manifest.csv — available in Party Mode and agent-aware features."

## Create Output Directories

After writing config, create any output directories that were configured. For filesystem operations only (such as creating directories), resolve the `{project-root}` token to the actual project root and create each path-type value from `config.yaml` that does not yet exist — this includes `output_folder` and any module variable whose value starts with `{project-root}/`. The paths stored in the config files must continue to use the literal `{project-root}` token; only the directories on disk should use the resolved paths. Use `mkdir -p` or equivalent to create the full path.

## Cleanup Legacy Directories

After both merge scripts complete successfully, remove the installer's package directories. Skills and agents in these directories are already installed at `.claude/skills/` — the `_bmad/` directory should only contain config files.

```bash
python3 ./scripts/cleanup-legacy.py --bmad-dir "{project-root}/_bmad" --module-code pulse --skills-dir "{project-root}/.claude/skills"
```

The script verifies that every skill in the legacy directories exists at `.claude/skills/` before removing anything. Directories without skills (like `_config/`) are removed directly. If the script exits non-zero, surface the error and stop. Missing directories (already cleaned by a prior run) are not errors — the script is idempotent.

Check `directories_removed` and `files_removed_count` in the JSON output for the confirmation step. Run `./scripts/cleanup-legacy.py --help` for full usage.

## Integrate with Dev Story (Auto-Tracking)

After cleanup, check if `{project-root}/.claude/skills/bmad-dev-story/workflow.md` exists. If it does, inject PULSE tracking steps automatically so that every story execution tracks metrics without manual intervention.

### Detection

1. Check if `{project-root}/.claude/skills/bmad-dev-story/workflow.md` exists
2. If **not found**: skip this section and inform the user that automatic tracking is not available — they can use `/pulse-track-start` and `/pulse-track-done` manually
3. If **found**: check if PULSE markers already exist in the file (search for `<!-- PULSE:auto-inject:start -->`)
   - If markers exist: this is an **update** — remove content between markers before re-injecting
   - If no markers: this is a **fresh injection**

### Injection

Insert the following block **at the very beginning** of the workflow execution steps (after the initialization/setup section, before the first implementation step):

```markdown
<!-- PULSE:auto-inject:start -->
### PULSE — Track Start

Before starting implementation, register this story for efficiency tracking:

1. Run `/pulse-track-start {story_id}` where `{story_id}` is the current story identifier
2. This records the start timestamp and extracts estimation data from the story file
3. If track-start has already been registered for this story, skip this step

> This step was automatically added by PULSE setup. Remove the markers to disable.
<!-- PULSE:auto-inject:end -->
```

Insert the following block **at the very end** of the workflow (after code review / final steps, before any cleanup or exit):

```markdown
<!-- PULSE:auto-inject:start -->
### PULSE — Track Done

After the story is complete and reviewed, register completion and calculate metrics:

1. Run `/pulse-track-done {story_id}` where `{story_id}` is the current story identifier
2. This calculates AI Leverage Ratio, Process Health, and displays the Efficiency Pulse
3. Answer Levi's questions about review cycles and effective time

> This step was automatically added by PULSE setup. Remove the markers to disable.
<!-- PULSE:auto-inject:end -->
```

### Post-Injection

Inform the user:
- "PULSE auto-tracking integrated with `/bmad-dev-story`. Every story will now automatically track start and completion metrics."
- "To disable: remove the `<!-- PULSE:auto-inject -->` blocks from the dev-story workflow."

If the injection fails for any reason (file permissions, unexpected format), do NOT block the setup — inform the user and suggest manual integration.

## Confirm

Use the script JSON output to display what was written — config values set (written to `config.yaml` at root for core, module section for module values), user settings written to `config.user.yaml` (`user_keys` in result), help entries added, fresh install vs update. If legacy files were deleted, mention the migration. If legacy directories were removed, report the count and list (e.g. "Cleaned up 106 installer package files from pulse/, core/ — skills are installed at .claude/skills/"). Then display the `module_greeting` from `./assets/module.yaml` to the user.

## Outcome

Once the user's `user_name` and `communication_language` are known (from collected input, arguments, or existing config), use them consistently for the remainder of the session: address the user by their configured name and communicate in their configured `communication_language`.
