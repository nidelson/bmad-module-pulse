# BCP — Score Batch (retroactive)

## Overview

Scores **multiple** existing stories with the BCP framework, tagged `bcp.scored_by: retroactive`. It is the basis of first-class retroactive scoring: a squad with history adopts BCP and leaves the cold start on day one (it feeds `backfill-baseline`).

Orchestration: the **LLM judges each story** (auto-score, the same template as `bmad-bcp-score`); the **scripts do the deterministic part** — `scripts/batch_plan.py` resolves, classifies and estimates cost, and `apply_score.py` from the installed `bmad-bcp-score` applies each score (not duplicated — single source).

## Conventions

- Bare paths resolve from the skill root (`scripts/`).
- `{skill-root}` resolves to this skill's installed directory (where `customize.toml` lives).
- `{project-root}`-prefixed paths resolve from the project root.

## On Activation

1. **Resolve workflow customization:** run `python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`. Keep `activation_steps_prepend`, `activation_steps_append`, `persistent_facts` and `on_complete` for the later steps. If the script fails, resolve the `workflow` block by reading `{skill-root}/customize.toml` plus the team/user overrides in `{project-root}/_bmad/custom/bmad-bcp-score-batch.{toml,user.toml}` (scalars: override wins; arrays: append).
2. **Prepend steps:** execute each entry of `workflow.activation_steps_prepend` in order.
3. **Persistent facts:** treat each entry of `workflow.persistent_facts` as foundational context for the whole session. Entries prefixed with `file:` load the content of the path/glob under `{project-root}`; the rest are verbatim facts.
4. **Target glob:** the user's argument (e.g. `docs/stories/*.md`). No argument → ask.
5. **Dependencies (the scoring skills installed):**
   - Ruler: `{project-root}/.claude/skills/bmad-bcp-rule-card/assets/bcp-rule.yaml`
   - Engine: `{project-root}/.claude/skills/bmad-bcp-score/scripts/apply_score.py`
   - Template: `{project-root}/.claude/skills/bmad-bcp-score/references/auto-score.md`
   - Baseline: `{project-root}/_bmad-output/implementation-artifacts/bcp-baseline.yaml`
   - Any missing → stop and direct the user to run setup with the scoring skills installed.
6. **Append steps:** execute each entry of `workflow.activation_steps_append` in order.

## Plan

```bash
python3 scripts/batch_plan.py --project-root "{project-root}" --glob "{glob}" [--rescore]
```

Without `--rescore`, stories that already carry a `bcp.*` block are classified `already_scored` and do **not** enter the batch (idempotence — re-running does not re-score). The output lists `stories[]` plus `cost_estimate`.

## Dry-Run Cost

If the user asked for `--dry-run-cost` (or the batch is large): present `cost_estimate` in `{communication_language}`, making clear it is an **order-of-magnitude estimate**, not real billing. Ask for confirmation before running the batch. Without `--dry-run-cost` and with a small batch, proceed directly.

## Execute Batch

For each story with `selected: true` in the plan:

1. **Auto-score** — follow the `references/auto-score.md` template from the installed `bmad-bcp-score`: read the story plus the resolved ruler, produce the strict JSON (`breakdown`, `confidence`, …). Write it to a temporary file.
2. **Apply (deterministic):** resolve the story's absolute path by joining `{project-root}` with the plan's `path` field (already relative to the root). Then call:

   ```bash
   python3 "{project-root}/.claude/skills/bmad-bcp-score/scripts/apply_score.py" \
     --story "{story-abs-path}" --breakdown {tmp-breakdown.json} \
     --baseline "{baseline-path}" --rule "{rule-path}" --scored-by retroactive \
     [--reference-h-per-bcp {bcp_reference_h_per_bcp}]
   ```

   `scored_by` is **always `retroactive`** in this flow (distinguishing it from `manual`/`bruno`/`rescore`). Do not use `--rescore` here unless the user explicitly asked to re-score (then pass `--rescore` and plan with `--rescore` too). Include `--reference-h-per-bcp` **only** when `bcp_reference_h_per_bcp` is in the `bcp` config; the same value across the whole batch keeps the `estimated_hours_reference` anchor comparable between stories.
3. Non-zero exit on one story: record the failure and **do not abort the batch** — continue with the rest and report at the end.

On a large batch, process incrementally and report progress (N/total) so the run survives context compaction.

## Aggregate Report

At the end, summarize in `{communication_language}`: total stories in the batch, successfully scored, skipped (`already_scored`), failures (with reasons), the sum of `bcp.total`, and a note that the baseline has not moved yet — `recalibrate` and `backfill-baseline` are what adjust `h_per_bcp` with real hours.

## On Completion

After the Aggregate Report (and once the batch has finished — successes persisted, failures reported), follow the `workflow.on_complete` resolved at activation:

- **Empty** value (default) → finish with no further action.
- **Non-empty** value → follow the string verbatim as a terminal instruction — it is the last step before exiting.

**Invariants (always true — any override must respect them):**

- The hook runs **after** the batch finishes — every successful story is already persisted.
- The hook **MUST NOT mutate** story frontmatter (single-writer principle — only `apply_score.py` writes `bcp.*`).
- The hook **MUST NOT mutate** `bcp-baseline.yaml` (the batch never touches the baseline; `recalibrate`/`backfill-baseline` do).
- An error in the hook is a **warning**, not a rollback — the scores are already written.
- On a `--dry-run-cost` run (no batch persistence) the hook is **skipped**.

To customize (team-level, committed): edit `{project-root}/_bmad/custom/bmad-bcp-score-batch.toml`. User-level (gitignored): `bmad-bcp-score-batch.user.toml`.

## Design Notes

- **Single source:** reuses `apply_score.py` and the template from the installed `bmad-bcp-score` — zero duplication. The ruler lives only in `bmad-bcp-rule-card` for the same reason: a second copy could diverge, and diverging rulers destroy cross-team comparability.
- **Idempotent by default:** without `--rescore`, already-scored stories are skipped; re-running the batch is safe.
- **Non-blocking:** a failure on one story does not bring down the batch — retroactive scoring over a large history has to be resilient.
- The cost estimate is a declared heuristic, not real telemetry — an order of magnitude to decide whether to proceed, nothing more.
- **Customization surface:** `customize.toml` follows the BMad pattern — three layers (skill defaults < team `<project>/_bmad/custom/*.toml` < user `*.user.toml`) resolved by `_bmad/scripts/resolve_customization.py`. `on_complete` is the extension point for chaining post-batch actions without forking the skill.
