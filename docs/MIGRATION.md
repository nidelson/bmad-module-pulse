# Migrating to PULSE v0.4.0

PULSE v0.4.0 drops support for BMAD <6.4.0 and migrates auto-tracking
integration from `workflow.md` markers to BMAD v6.4.0's `customize.toml`
framework. This is a one-time migration. After upgrading, PULSE
auto-tracking will survive future BMAD core upgrades transparently.

## TL;DR

```bash
# 1. Make sure BMAD core is on v6.4.0 or higher
npx bmad-method install

# 2. Upgrade PULSE
npx bmad-method install --custom-source https://github.com/nidelson/bmad-module-pulse

# 3. Re-run pulse-setup
/pulse-setup

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

## What `pulse-setup` does for you

1. **Capability check** — verifies BMAD ≥6.4.0 is installed; aborts with a
   clear message otherwise.
2. **Legacy cleanup** — removes any `<!-- PULSE:auto-inject -->` blocks from
   `workflow.md` if it still exists.
3. **Emits two override files** — `_bmad/custom/bmad-dev-story.toml` and
   `_bmad/custom/bmad-code-review.toml`.
4. **Prints `.gitignore` snippet** — read-only; you copy-paste it manually.

## Conflict policy

If `_bmad/custom/bmad-dev-story.toml` or `_bmad/custom/bmad-code-review.toml`
already exists in your project (e.g. you customized it), `pulse-setup`
**aborts** with a message naming the file. Choose one:

- **Keep your version** — do nothing, ignore the abort, your file is untouched.
- **Restore PULSE defaults** — re-run with `--force` (passed through to the
  inject script). This overwrites your customization.
- **Merge manually** — diff against the template at
  `node_modules/.../bmad-module-pulse/skills/pulse-setup/assets/customize-templates/<skill>.toml`,
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
- Output of `python3 .claude/skills/pulse-setup/scripts/detect_bmad_capability.py --project-root .`
- Contents of `_bmad/custom/` (if any)
