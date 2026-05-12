# PULSE Migration Guide

Per-release upgrade notes. Newest first. Each section is self-contained;
skip to the version you are migrating from.

---

## v0.4.4 → v0.4.5 — Levi agent consolidation

v0.4.5 consolidates the Levi agent into a single canonical skill folder
and aligns it with the bmad ecosystem convention (`bmad-agent-{module-code}`).
This closes a duplication that emerged on BMAD v6.6.0 installs, where the
core installer auto-provisioned `bmad-agent-pulse/` alongside the legacy
`bmad-pulse-agent-levi/` shipped by previous PULSE versions, producing two
divergent entry points for the same agent.

### What changes on disk

| Before (v0.4.4) | After (v0.4.5) |
|---|---|
| `skills/bmad-pulse-agent-levi/` in PULSE source | `skills/bmad-agent-pulse/` in PULSE source |
| `levi.agent.yaml` + `bmad-skill-manifest.yaml` sidecars | Persona inlined in `SKILL.md`, sidecars dropped |
| `.claude/skills/bmad-pulse-agent-levi/` AND `.claude/skills/bmad-agent-pulse/` after install (duplicate) | `.claude/skills/bmad-agent-pulse/` only (single canonical) |
| Persona text in PT-BR (in some installs) | Persona text in EN at source; runtime language follows `communication_language` in `_bmad/config.yaml` |

The slash command for talking to Levi remains the same:

```
/bmad-agent-pulse
```

If you previously typed `/bmad-pulse-agent-levi`, that command no longer
exists after the upgrade. Switch to `/bmad-agent-pulse`.

### How to upgrade

```bash
# 1. Pull the new PULSE version
npx bmad-method install --custom-source https://github.com/nidelson/bmad-module-pulse

# 2. Re-run setup — the cleanup step removes the legacy folder automatically
/bmad-pulse-setup
```

`bmad-pulse-setup` now invokes a new cleanup step that removes
`.claude/skills/bmad-pulse-agent-levi/` when the canonical
`.claude/skills/bmad-agent-pulse/` is present. The step is idempotent and
safety-checked: it refuses to delete the legacy folder if the canonical
replacement is missing, so a partial install can never strand you
without a Levi agent.

If you prefer to clean up manually:

```bash
# Verify the canonical folder exists first
ls .claude/skills/bmad-agent-pulse/SKILL.md

# Then remove the legacy folder
rm -rf .claude/skills/bmad-pulse-agent-levi/
```

### Persona language

The shipped persona text is now EN to match the public distribution.
Runtime language continues to flow from `communication_language` in
`_bmad/config.yaml` — set it to `Português do Brasil` (or any other
language) and Levi will greet you and reason in that language.

If your project previously contained hand-edited PT-BR text inside
`.claude/skills/bmad-agent-pulse/SKILL.md`, the upgrade will overwrite
it with the new EN source. Move any customizations into
`_bmad/custom/bmad-agent-pulse.toml` (forthcoming in #31) so they
survive future PULSE upgrades.

### Reporting issues

If `/bmad-pulse-setup` fails to clean up the legacy folder, run the
cleanup mode standalone and attach the JSON output to a bug report:

```bash
python3 .claude/skills/bmad-pulse-setup/scripts/cleanup-legacy.py \
    --remove-legacy-agent \
    --project-root .
```

---

# Migrating to PULSE v0.4.0

PULSE v0.4.0 ships **two breaking changes** in a single release:

1. **Drops support for BMAD <6.4.0** — auto-tracking is now wired through
   BMAD v6.4.0's `customize.toml` framework instead of `workflow.md` markers.
   After upgrading, PULSE auto-tracking will survive future BMAD core
   upgrades transparently.
2. **Skill folders and slash commands renamed** from `pulse-*` to
   `bmad-pulse-*` to align with the most recent BMAD ecosystem reference
   pattern. Re-running `/bmad-pulse-setup` is sufficient — old `pulse-*`
   folders can be deleted manually after the upgrade.

This is a one-time migration.

## Slash command rename

| Before (v0.3.x) | After (v0.4.0) |
|---|---|
| `/pulse-setup` | `/bmad-pulse-setup` |
| `/pulse-track-start` | `/bmad-pulse-track-start` |
| `/pulse-track-done` | `/bmad-pulse-track-done` |
| `/pulse-dashboard` | `/bmad-pulse-dashboard` |

## TL;DR

```bash
# 1. Make sure BMAD core is on v6.4.0 or higher
npx bmad-method install

# 2. Upgrade PULSE
npx bmad-method install --custom-source https://github.com/nidelson/bmad-module-pulse

# 3. Re-run bmad-pulse-setup
/bmad-pulse-setup

# 4. Append the printed snippet to your .gitignore (manual)

# 5. Commit the new files
git add _bmad/custom/bmad-dev-story.toml _bmad/custom/bmad-code-review.toml .gitignore
git commit -m "chore(pulse): migrate to v0.4.0 customize.toml integration"
```

## What changes

| Before (v0.3.x) | After (v0.4.0) |
|---|---|
| `<!-- PULSE:auto-inject -->` markers in `.claude/skills/bmad-dev-story/workflow.md` | `_bmad/custom/bmad-dev-story.toml` (track-start in `persistent_facts`) |
| Track-done injected at end of `bmad-dev-story` workflow | `_bmad/custom/bmad-code-review.toml` (track-done in `on_complete`) |
| Auto-tracking broken silently on every BMAD ≥6.4.0 install | Auto-tracking survives BMAD core upgrades |

## What `bmad-pulse-setup` does for you

1. **Capability check** — verifies BMAD ≥6.4.0 is installed; aborts with a
   clear message otherwise.
2. **Legacy cleanup** — removes any `<!-- PULSE:auto-inject -->` blocks from
   `workflow.md` if it still exists.
3. **Emits two override files** — `_bmad/custom/bmad-dev-story.toml` and
   `_bmad/custom/bmad-code-review.toml`.
4. **Prints `.gitignore` snippet** — read-only; you copy-paste it manually.

## Conflict policy

If `_bmad/custom/bmad-dev-story.toml` or `_bmad/custom/bmad-code-review.toml`
already exists in your project (e.g. you customized it), `bmad-pulse-setup`
**aborts** with a message naming the file. Choose one:

- **Keep your version** — do nothing, ignore the abort, your file is untouched.
- **Restore PULSE defaults** — re-run with `--force` (passed through to the
  inject script). This overwrites your customization.
- **Merge manually** — diff against the template at
  `node_modules/.../bmad-module-pulse/skills/bmad-pulse-setup/assets/customize-templates/<skill>.toml`,
  apply the PULSE bits to your file, then move on.

The conflict policy guarantees byte-stability: without `--force`, the file
on disk has identical sha256 before and after the failed run.

## Why track-done moved to `bmad-code-review`

In v0.3.x, track-done was injected at the end of `bmad-dev-story`. But
`bmad-dev-story` ends with story status `review`, not `done`. Recording
completion at that point produced premature metrics (review cycles not
yet measured). v0.4.0 places track-done on `bmad-code-review.on_complete`,
which fires after the review is approved and sprint status is synced —
the correct moment.

## Reporting issues

Open an issue at https://github.com/nidelson/bmad-module-pulse/issues with:
- BMAD version (`cat _bmad/_config/files-manifest.csv | head -1`)
- Output of `python3 .claude/skills/bmad-pulse-setup/scripts/detect_bmad_capability.py --project-root .`
- Contents of `_bmad/custom/` (if any)
