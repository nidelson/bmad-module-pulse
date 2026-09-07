# BCP — Rescore

## Overview

Re-scores **one** story that already carries a `bcp.*` block: recomputes the total, archives the previous score into `bcp.history` (FIFO, cap 50) and re-derives `estimated_hours`, always preserving the audit trail. Used after a story's scope changes, or when the ruler or the team's understanding evolves.

A **thin, script-free** skill: the deterministic work (archiving history, cap 50 plus warning, advisories for >50% delta and >2× cumulative drift, hours re-derivation, audit preservation, idempotent writes) already lives in `apply_score.py` from the installed `bmad-bcp-score`, invoked with `--rescore`. This skill formalizes the re-scoring flow with **mandatory review** — a rescore is never silent.

## Conventions

- Bare paths resolve from the skill root.
- `{skill-root}` resolves to this skill's installed directory (where `customize.toml` lives).
- `{project-root}`-prefixed paths resolve from the project root.

## On Activation

1. **Resolve workflow customization:** run `python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`. Keep `activation_steps_prepend`, `activation_steps_append`, `persistent_facts` and `on_complete` for the later steps. If the script fails, resolve the `workflow` block by reading `{skill-root}/customize.toml` plus the team/user overrides in `{project-root}/_bmad/custom/bmad-bcp-rescore.{toml,user.toml}` (scalars: override wins; arrays: append).
2. **Prepend steps:** execute each entry of `workflow.activation_steps_prepend` in order.
3. **Persistent facts:** treat each entry of `workflow.persistent_facts` as foundational context for the whole session. Entries prefixed with `file:` load the content of the path/glob under `{project-root}`; the rest are verbatim facts.
4. **Target story:** the path passed as an argument, or the story from context.
5. **Precondition:** the story **must** have a `bcp.*` block. If it does not, this is not a rescore — direct the user to `/bmad-bcp-score` (first score).
6. **Dependencies (the scoring skills installed):**
   - Ruler: `{project-root}/.claude/skills/bmad-bcp-rule-card/assets/bcp-rule.yaml`
   - Engine: `{project-root}/.claude/skills/bmad-bcp-score/scripts/apply_score.py`
   - Template: `{project-root}/.claude/skills/bmad-bcp-score/references/auto-score.md`
   - Baseline: `{project-root}/_bmad-output/implementation-artifacts/bcp-baseline.yaml`
   - Any missing → stop and direct the user to run setup.
7. **Append steps:** execute each entry of `workflow.activation_steps_append` in order.

## Re-Score

1. Show the user the current score (`bcp.total`, breakdown, `estimated_hours`) and the reason for the rescore (ask if not supplied — it becomes the note's context).
2. **Auto-score** — follow the `references/auto-score.md` template from the installed `bmad-bcp-score`, reading the current story plus the ruler plus the previous `bcp.*` block as context. Produce the strict JSON. Write it to a temporary file.
3. **Mandatory preview** (a rescore is always review-mandatory — a non-negotiable inherited from `bmad-bcp-score`):

   ```bash
   python3 "{project-root}/.claude/skills/bmad-bcp-score/scripts/apply_score.py" \
     --story "{story-abs-path}" --breakdown {tmp-breakdown.json} \
     --baseline "{baseline-path}" --rule "{rule-path}" \
     --scored-by rescore --rescore [--reference-h-per-bcp {bcp_reference_h_per_bcp}] --dry-run
   ```

   Include `--reference-h-per-bcp` **only** when `bcp_reference_h_per_bcp` is in the resolved config. Resolve it **toml-first** by running `python3 {project-root}/.claude/skills/bmad-bcp-score/scripts/bcp_config.py --project-root {project-root}` and reading `bcp.bcp_reference_h_per_bcp` from the JSON: the helper reads `[modules.bcp]` from `config.toml`, with a per-key **fallback** to the `bcp` section of `config.yaml`, and the `module.yaml` **default** last. Omit the flag when the value is the seed default or absent (it falls back to the seed). Passing the same value on a rescore keeps the `estimated_hours_reference` anchor consistent — **never** derive it from the recalibrated baseline.

4. Present the preview in `{communication_language}`: total old → new, `estimated_hours` old → new, source of `h_per_bcp`, `estimated_hours_reference` old → new (the frozen anchor), the size of `bcp.history` after archiving, and **every advisory** (>50% delta, >2× cumulative drift, history truncation → "consider splitting into sub-stories").
5. Only after **explicit confirmation**, repeat **without** `--dry-run` to persist.
6. Non-zero exit: show the error verbatim and stop.

## Surface Advisories

An advisory **does not block** — it is guidance. If the delta suggests a split, make clear the user may accept it anyway; the decision is theirs. `bcp.history` keeps the trail either way.

## Confirm

Summarize: total old → new, `estimated_hours` old → new (and `estimated_hours_pre_bcp` **unchanged** — the original estimate's audit is immutable after the first score), `scored_by: rescore`, the new `history_len`, and the advisories. Confirm that `pulse_metrics` and every non-BCP key are untouched.

## On Completion

After Confirm (and once the new `bcp.*` block has been persisted and the previous one archived into `bcp.history` by the run without `--dry-run`), follow the `workflow.on_complete` resolved at activation:

- **Empty** value (default) → finish with no further action.
- **Non-empty** value → follow the string verbatim as a terminal instruction — it is the last step before exiting.

**Invariants (always true — any override must respect them):**

- The hook runs **after** persistence — the story frontmatter already reflects the new `bcp.*`, and the previous one is in `bcp.history`.
- The hook **MUST NOT mutate** the story frontmatter (single-writer principle — only `apply_score.py --rescore` writes `bcp.*` and rotates `history`).
- An error in the hook is a **warning**, not a rollback — the rescore is already written.
- On a `--dry-run` run (no persistence) the hook is **skipped**.

To customize (team-level, committed): edit `{project-root}/_bmad/custom/bmad-bcp-rescore.toml`. User-level (gitignored): `bmad-bcp-rescore.user.toml`.

## Design Notes

- **No duplication:** reuses `apply_score.py --rescore` and the template from the installed `bmad-bcp-score`; the ruler lives only in `bmad-bcp-rule-card`, because a second copy could diverge and diverging rulers destroy cross-team comparability.
- `estimated_hours_pre_bcp` does **not** change on a rescore — it captures only the dev agent's original, written exactly once at the first score. A rescore touches `estimated_hours`, `bcp.total` and `bcp.history`.
- Idempotence: the engine archives the previous snapshot into `history` on every `--rescore`; re-running with the same breakdown still archives, because that is rescore semantics — each invocation is an audit event. Which is exactly why the review is mandatory: it prevents accidental rescores.
- **Customization surface:** `customize.toml` follows the BMad pattern — three layers (skill defaults < team `<project>/_bmad/custom/*.toml` < user `*.user.toml`) resolved by `_bmad/scripts/resolve_customization.py`. `on_complete` is the extension point for chaining post-rescore actions without forking the skill.
