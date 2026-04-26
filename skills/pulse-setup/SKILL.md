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

## Generate Customize Overrides (Auto-Tracking)

After cleanup, configure auto-tracking by emitting two `customize.toml`
overrides in the consumer project. Auto-tracking now uses BMAD v6.4.0's
TOML-based customization framework instead of injecting steps into
`workflow.md`. This survives BMAD core upgrades because the override files
live in `_bmad/custom/`, which BMAD never overwrites.

### Capability Gate

Run the capability detector first:

```bash
python3 ./scripts/detect_bmad_capability.py --project-root "{project-root}"
```

The script exits 0 (BMAD ≥6.4.0), 1 (BMAD ≤6.3.x), or 2 (BMAD not installed)
and prints a JSON payload to stdout describing the detection.

- **Exit 0** — proceed with override emission below.
- **Exit 1** — abort with this message: "PULSE v0.4.0 requires BMAD ≥6.4.0.
  Detected BMAD ≤6.3.x. Either upgrade BMAD (`npx bmad-method install`) or
  pin to PULSE v0.3.x via `--version`."
- **Exit 2** — abort: "BMAD is not installed in this project root. Run
  `npx bmad-method install` first, then re-run `/pulse-setup`."

### Cleanup Legacy Markers

Even on a fresh BMAD ≥6.4.0 install, scan for stale `<!-- PULSE:auto-inject -->`
blocks in `workflow.md` left over from previous PULSE versions. The script
silently skips when `workflow.md` is absent (BMAD 6.4.0 removed it from
`bmad-dev-story`).

```bash
python3 ./scripts/cleanup-legacy.py \
    --remove-pulse-markers \
    --project-root "{project-root}"
```

### Emit Override Files

Emit the two override files. The conflict policy is **abort + `--force`**:
if either destination already exists, the script exits 3 and the file is
left untouched (sha256-stable). The user can re-run with `--force` after
inspecting the conflict.

```bash
python3 ./scripts/inject_customize.py \
    --project-root "{project-root}" \
    --skill bmad-dev-story
python3 ./scripts/inject_customize.py \
    --project-root "{project-root}" \
    --skill bmad-code-review
```

If either invocation exits 3, surface the message to the user verbatim
(it includes the destination path and instructs how to re-run with
`--force`). Do NOT auto-retry with `--force` — the choice is the user's.

### .gitignore Allowlist Snippet

Print a copy-paste-ready snippet for the consumer's `.gitignore` so that
`_bmad/custom/*.toml` is committed (team overrides) while `*.user.toml`
stays private. The script is read-only — never modifies the file.

```bash
python3 ./scripts/print_gitignore_snippet.py --project-root "{project-root}"
```

Surface the script's stdout to the user.

### Post-Injection

Inform the user:

- "PULSE auto-tracking integrated via `_bmad/custom/bmad-dev-story.toml` and
  `_bmad/custom/bmad-code-review.toml`. Every story will now automatically
  track start (during `/bmad-dev-story`) and completion (after
  `/bmad-code-review`)."
- "To disable: delete the two `.toml` files from `_bmad/custom/`."
- "To customize: edit the files manually. Re-running `/pulse-setup` will
  abort if you changed them — pass `--force` only if you want PULSE's
  defaults restored."

If any step above failed, do NOT block the rest of the setup. Report the
failure clearly and continue — the user can rerun the failing piece later.

## Confirm

Use the script JSON output to display what was written — config values set (written to `config.yaml` at root for core, module section for module values), user settings written to `config.user.yaml` (`user_keys` in result), help entries added, fresh install vs update. If legacy files were deleted, mention the migration. If legacy directories were removed, report the count and list (e.g. "Cleaned up 106 installer package files from pulse/, core/ — skills are installed at .claude/skills/"). Then display the `module_greeting` from `./assets/module.yaml` to the user.

## Outcome

Once the user's `user_name` and `communication_language` are known (from collected input, arguments, or existing config), use them consistently for the remainder of the session: address the user by their configured name and communicate in their configured `communication_language`.
