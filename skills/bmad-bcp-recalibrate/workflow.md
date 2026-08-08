# BCP — Recalibrate

## Overview

Updates `bcp-baseline.yaml` per category from **real hours**: each sample `(category, bcp_total, actual_hours)` produces an observed `h_per_bcp` (`actual_hours / bcp_total`); the baseline keeps a FIFO window per category and `h_per_bcp` becomes the window's mean. `bmad-bcp-score` derives hours from that factor **from the first sample onward**; once `min_samples` accumulate, the category **leaves the seed** (`is_seed: false`) and the factor stops being marked provisional. The 5.0 seed applies only to a category with no samples at all.

This is what makes predictability mean something. A recalibrated factor is the squad's own delivery rate, so estimate error stops measuring whoever made the guess and starts measuring the delivery.

**Non-negotiable — works without PULSE:** the source of `actual_hours` is agnostic. It reads `pulse_metrics.actual_hours` from the story **if present** (a file convention, zero cross-awareness) **or** accepts a manual `--actual-hours`. The script never imports, requires or checks for PULSE — `actual_hours` is just a number.

The deterministic part lives in `scripts/recalibrate.py` (window mean, dedup by id, chronological order, `is_seed` flip, snapshot into `history`). Idempotent: a sample whose `id` was already applied is skipped.

## Conventions

- Bare paths resolve from the skill root (`scripts/`).
- `{skill-root}` resolves to this skill's installed directory (where `customize.toml` lives).
- `{project-root}`-prefixed paths resolve from the project root.

## On Activation

1. **Resolve workflow customization:** run `python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`. Keep `activation_steps_prepend`, `activation_steps_append`, `persistent_facts` and `on_complete` for the later steps. If the script fails, resolve the `workflow` block by reading `{skill-root}/customize.toml` plus the team/user overrides in `{project-root}/_bmad/custom/bmad-bcp-recalibrate.{toml,user.toml}` (scalars: override wins; arrays: append).
2. **Prepend steps:** execute each entry of `workflow.activation_steps_prepend` in order before continuing.
3. **Persistent facts:** treat each entry of `workflow.persistent_facts` as foundational context for the whole session. Entries prefixed with `file:` load the content of the path/glob under `{project-root}`; the rest are verbatim facts.
4. **Baseline:** `bcp.bcp_baseline_path` from config, or `{project-root}/_bmad-output/implementation-artifacts/bcp-baseline.yaml`. Absent → stop and direct the user to seed the baseline.
5. **Source of real hours** (in order of preference):
   - The user passed `--actual-hours N` plus a story → a single manual sample.
   - The story has `pulse_metrics.actual_hours` → read by convention.
   - Batch: assemble a JSON of samples `[{category, bcp_total, actual_hours, id?, at?}]` from several completed stories (each story needs `bcp.total`).
   - No source → ask the user for the real hours; **do not invent them**.
6. **Append steps:** execute each entry of `workflow.activation_steps_append` in order.

## Recalibrate

Prefer **preview** first:

```bash
python3 scripts/recalibrate.py --baseline "{baseline-path}" \
  --story "{story-abs-path}" [--actual-hours N] [--category X] --dry-run
```

or in batch:

```bash
python3 scripts/recalibrate.py --baseline "{baseline-path}" \
  --samples {tmp-samples.json} --dry-run
```

Present per category in `{communication_language}`: `h_per_bcp` old → new, `n_samples`, the `is_seed` flip (blind → calibrated), and samples skipped by dedup. In chronological order (the `at` field; defaults to `bcp.scored_at`).

After confirmation (or directly if the user asked for non-interactive), run **without** `--dry-run` to persist. Non-zero exit: show the error verbatim and stop.

## Confirm

Summarize: affected categories with `h_per_bcp` old→new, which ones left the seed (`is_seed: true→false`), and the total of samples applied vs skipped. Remind the user that `recalibrate` does **not** change `bcp.total` on already-scored stories — only the factor; re-deriving hours for old stories requires `bmad-bcp-rescore`.

## On Completion

After Confirm (and once `bcp-baseline.yaml` has been persisted by the run without `--dry-run`), follow the `workflow.on_complete` resolved at activation:

- **Empty** value (default) → finish with no further action.
- **Non-empty** value → follow the string verbatim as a terminal instruction — it is the last step before exiting.

**Invariants (always true — any override must respect them):**

- The hook runs **after** persistence — `bcp-baseline.yaml` already reflects the new state.
- The hook **MUST NOT mutate** `bcp-baseline.yaml` (single-writer principle — only `recalibrate.py` writes the baseline).
- An error in the hook is a **warning**, not a rollback — recalibrate already wrote; a downstream failure is guidance, not a regression.
- On a `--dry-run` run (no persistence) the hook is **skipped** — it only fires when the baseline actually changed.

To customize (team-level, committed): edit `{project-root}/_bmad/custom/bmad-bcp-recalibrate.toml`. User-level (gitignored): `bmad-bcp-recalibrate.user.toml`.

## Design Notes

- **Not coupled to tracking:** `actual_hours` is read as a frontmatter key by convention; its absence is expected and handled (falls back to `--actual-hours`). Scoring never writes `pulse_metrics`.
- **Cold start protected:** while `n_samples < min_samples` the category stays `is_seed: true`. `bmad-bcp-score` **uses** that `h_per_bcp` anyway, marking the source as `baseline:<cat>:provisional`. Only a category with **no samples at all** falls back to the seed. Until 2026-07-31 the provisional value was discarded — but the fallback is the seed, which is a **market** rate rather than a prediction of our own delivery: it traded a ~20% sampling error for a ~80× unit error. Withholding a measurement is only conservative when the fallback measures the same thing.
- **Idempotence:** dedup by `id` (story_id/scored_at) across `samples` and `history.last_id`. `bmad-bcp-backfill-baseline` chains `score-batch` plus this skill relying on exactly that.
- `history` per category keeps a snapshot per run (cap 50, FIFO) — the audit trail of how the factor evolved.
- FIFO window = `config_snapshot.rolling_window`; `min_samples` and `seed` come from the snapshot too.
- **Customization surface:** `customize.toml` follows the BMad pattern — three layers (skill defaults < team `<project>/_bmad/custom/*.toml` < user `*.user.toml`) resolved by `_bmad/scripts/resolve_customization.py`. `on_complete` is the extension point for chaining post-persistence actions without forking the skill.
