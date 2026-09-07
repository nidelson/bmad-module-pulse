# BCP — Backfill Baseline

## Overview

Chains **`score-batch` → sample collection → `recalibrate`** to kill the cold start: a squad adopting BCP with stories already delivered leaves the seed (5.0) on day one, with a per-category `h_per_bcp` faithful to its real history.

An **orchestration** skill. It duplicates no logic: retroactive scoring is delegated to the installed `bmad-bcp-score-batch` and recalibration to the installed `bmad-bcp-recalibrate`; the only deterministic piece of its own is `scripts/collect_samples.py` (the bridge: scored stories → samples JSON, with a stable `id` that guarantees idempotence).

## Conventions

- Bare paths resolve from the skill root (`scripts/`).
- `{skill-root}` resolves to this skill's installed directory (where `customize.toml` lives).
- `{project-root}`-prefixed paths resolve from the project root.

## On Activation

1. **Resolve workflow customization:** run `python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`. Keep `activation_steps_prepend`, `activation_steps_append`, `persistent_facts` and `on_complete` for the later steps. If the script fails, resolve the `workflow` block by reading `{skill-root}/customize.toml` plus the team/user overrides in `{project-root}/_bmad/custom/bmad-bcp-backfill-baseline.{toml,user.toml}` (scalars: override wins; arrays: append).
2. **Prepend steps:** execute each entry of `workflow.activation_steps_prepend` in order.
3. **Persistent facts:** treat each entry of `workflow.persistent_facts` as foundational context for the whole session. Entries prefixed with `file:` load the content of the path/glob under `{project-root}`; the rest are verbatim facts.
4. **History glob:** stories already delivered (e.g. `docs/stories/**/*.md`). No argument → ask.
5. **Dependencies (the scoring skills installed):**
   - `{project-root}/.claude/skills/bmad-bcp-score-batch/scripts/batch_plan.py`
   - `{project-root}/.claude/skills/bmad-bcp-score/scripts/apply_score.py` + `references/auto-score.md`
   - `{project-root}/.claude/skills/bmad-bcp-rule-card/assets/bcp-rule.yaml`
   - `{project-root}/.claude/skills/bmad-bcp-recalibrate/scripts/recalibrate.py`
   - Baseline: `bcp.bcp_baseline_path` or `{project-root}/_bmad-output/implementation-artifacts/bcp-baseline.yaml`
   - Missing → stop and direct the user to seed the baseline and install the scoring skills.
6. **Source of real hours:** `pulse_metrics.actual_hours` on the stories **or** a JSON `{story_id: hours}` supplied by the user (`--actual-hours-map`) — backfill works **without any tracking data**. Neither available → ask the user; do not invent hours.
7. **Append steps:** execute each entry of `workflow.activation_steps_append` in order.

## Step 1 — Score Batch (retroactive)

Follow the `bmad-bcp-score-batch` flow over the glob (`retroactive` scoring). Idempotent: stories that already carry `bcp.*` are skipped. At the end, the historical stories have `bcp.total`.

## Step 2 — Collect Samples

```bash
python3 scripts/collect_samples.py --project-root "{project-root}" \
  --glob "{glob}" [--actual-hours-map {tmp-hours.json}] \
  --out {tmp-samples.json}
```

Report `collected` vs `skipped` (with reasons: no `bcp.total`, no `actual_hours`, no `category`). Skipped stories do not enter the baseline — tell the user which ones and why, so they can complete the hours map and re-run.

## Step 3 — Recalibrate

Preview first:

```bash
python3 "{project-root}/.claude/skills/bmad-bcp-recalibrate/scripts/recalibrate.py" \
  --baseline "{baseline-path}" --samples {tmp-samples.json} --dry-run
```

Present per category: `h_per_bcp` old → new, `n_samples`, the `is_seed` flip (blind → calibrated). After confirmation (or directly if non-interactive), repeat **without** `--dry-run`.

## Idempotence

Re-running the backfill **does not corrupt** the baseline:

- `score-batch` skips already-scored stories (without `--rescore`).
- `collect_samples.py` emits a stable `id` (`story_id`/stem).
- `recalibrate.py` dedups by `id` (in `samples` and `history.last_id`) → already-applied samples are skipped.

So a backfill is safe to re-run partially (e.g. filling in missing hours and running again processes only the delta).

## Confirm

Summarize: stories scored in the batch, samples collected vs skipped (with reasons), categories that left the seed (`is_seed: true→false`) and the resulting `h_per_bcp`. Remind the user that stories scored in the batch got an `estimated_hours` derived from the **seed** (blind at scoring time); to re-derive with the newly calibrated factor, run `bmad-bcp-rescore` on the ones that matter.

## On Completion

After Confirm (and once `bcp-baseline.yaml` has been persisted by the Step 3 run without `--dry-run`), follow the `workflow.on_complete` resolved at activation:

- **Empty** value (default) → finish with no further action.
- **Non-empty** value → follow the string verbatim as a terminal instruction — it is the last step before exiting.

**Invariants (always true — any override must respect them):**

- The hook runs **after** persistence — scored stories are on disk AND `bcp-baseline.yaml` reflects the calibration.
- The hook **MUST NOT mutate** story frontmatter or `bcp-baseline.yaml` (single-writer principle).
- An error in the hook is a **warning**, not a rollback — the backfill already wrote.
- On `--dry-run` (no baseline persistence) the hook is **skipped**.

To customize (team-level, committed): edit `{project-root}/_bmad/custom/bmad-bcp-backfill-baseline.toml`. User-level (gitignored): `bmad-bcp-backfill-baseline.user.toml`.

## Design Notes

- **Zero duplication:** orchestrates installed skills (`score-batch`, `recalibrate`), and the ruler lives only in `rule-card` — a second copy could diverge, and diverging rulers destroy cross-team comparability. The only thing owned here is the `collect_samples.py` bridge.
- **No tracking required:** `--actual-hours-map` covers the case where no tracking data exists; `pulse_metrics.actual_hours` is read by convention when present.
- **Resilient and partial:** stories without hours are skipped and reported rather than blocking the rest; completing them and re-running processes only the delta (idempotence).
- Chronological order of recalibration is guaranteed by `recalibrate.py` (the `at` field = `bcp.scored_at`).
- **Customization surface:** `customize.toml` follows the BMad pattern — three layers (skill defaults < team `<project>/_bmad/custom/*.toml` < user `*.user.toml`) resolved by `_bmad/scripts/resolve_customization.py`. `on_complete` is the extension point for chaining post-backfill actions without forking the skill.
