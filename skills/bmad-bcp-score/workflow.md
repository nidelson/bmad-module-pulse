# BCP — Score

## Overview

Scores **one** story with the Business Complexity Points framework and derives `estimated_hours` from score × per-category baseline, writing an auditable `bcp.*` block into the frontmatter. This is the heart of the BCP loop.

Available when `pulse_estimation_method = "bcp"`. Under any other method PULSE derives `estimated_hours` from the team's own estimate and this skill is never invoked.

Division of responsibility: the **LLM makes the judgement** (picking a size per element against the ruler); the **`scripts/apply_score.py` script does the deterministic part** (total, hours derivation, audit preservation, history, delta advisories, invariant validation, idempotent writes).

**Non-negotiables:**

- **Non-interactive by default** above the confidence threshold. Dry-run review **only** on: material divergence from the dev agent's estimate, low confidence, or a rescore.
- **Never** writes `pulse_metrics` (PULSE owns it). Every non-BCP frontmatter key is preserved verbatim.
- Audit: `estimated_hours_pre_bcp` is written **exactly once** (the dev agent's original); `estimated_hours_basis: bcp`; `hours_per_bcp` plus `hours_per_bcp_source` record the applied factor and its provenance, so that `estimated_hours = bcp.total × hours_per_bcp` is checkable without consulting the baseline (which is mutable).

## Conventions

- Bare paths resolve from the skill root (`references/`, `scripts/`, `assets/`).
- `{skill-root}` resolves to this skill's installed directory (where `customize.toml` lives).
- `{project-root}`-prefixed paths resolve from the project root.

## On Activation

1. **Resolve workflow customization:** run `python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`. Keep `activation_steps_prepend`, `activation_steps_append`, `persistent_facts` and `on_complete` for the later steps. If the script fails, resolve the `workflow` block by reading `{skill-root}/customize.toml` plus the team/user overrides in `{project-root}/_bmad/custom/bmad-bcp-score.{toml,user.toml}` (scalars: override wins; arrays: append).
2. **Prepend steps:** execute each entry of `workflow.activation_steps_prepend` in order.
3. **Persistent facts:** treat each entry of `workflow.persistent_facts` as foundational context for the whole session. Entries prefixed with `file:` load the content of the path/glob under `{project-root}`; the rest are verbatim facts.
4. **Target story:** the path passed as an argument, or the in-progress story from context.
5. **Ruler:** `{project-root}/.claude/skills/bmad-bcp-rule-card/assets/bcp-rule.yaml` — the single immutable source. Do not duplicate it: a second copy is a second ruler, and scores from two rulers do not compare. If absent, stop and report that BCP scoring is not installed.
6. **Baseline:** `{project-root}/_bmad-output/implementation-artifacts/bcp-baseline.yaml` (or `bcp.bcp_baseline_path` from config). If absent, stop and direct the user to seed the baseline.
7. **Config (toml-first):** run `python3 {project-root}/.claude/skills/bmad-bcp-score/scripts/bcp_config.py --project-root {project-root}` and read the `bcp` object from the JSON. The helper resolves **toml-first**: `[modules.bcp]` from `config.toml` (via the core's `resolve_config.py` — honouring `custom/config.toml` overrides), with a per-key **fallback** to the legacy `bcp` section of `config.yaml`, and the `module.yaml` **default** as a last resort. Keys that matter here: `bcp_confidence_threshold` (default 0.75), `bcp_non_interactive_default` (default yes), `bcp_overwrite_estimated_hours` (consent — when `no`, do not overwrite `estimated_hours`: append the `bcp.*` block and say so), `bcp_reference_h_per_bcp` (the frozen reference rate for the leverage anchor — when absent the script uses the seed; **never** the recalibrated factor). With no config the helper already returns defaults; carry on.
8. **Append steps:** execute each entry of `workflow.activation_steps_append` in order.

## Auto-Score

Load `references/auto-score.md` and follow the template: read the story plus the resolved ruler, decide presence and size per element, and produce the strict JSON (`breakdown`, `confidence`, `divergence_with_agent_estimate`, `rationale_summary`). Write that JSON to a temporary file.

`scored_by`: `retroactive` when the story is already delivered or historical; `rescore` when a `bcp.*` block exists and the user asks to score again; `bruno` when invoked through the module's agent; otherwise `manual`. The `bruno` token is a **frozen schema value**, not a persona — it names the agent-driven path in stories scored since v0.1 and stays spelled that way so already-scored frontmatter keeps validating.

> `bruno` is kept as a recorded value because stories already carry it. It names how a score was produced, not who is on the roster today.

## Decide Review Mode

**Dry-run review** (interactive) if **any** of: `confidence` < `bcp_confidence_threshold`; `divergence_with_agent_estimate` is true; it is a rescore (a `bcp.*` block already exists); or `bcp_non_interactive_default` = `no`.

Otherwise: **non-interactive** — apply directly.

## Apply

Always run in preview mode first to validate the invariants:

```bash
python3 scripts/apply_score.py --story "{story-path}" --breakdown {tmp-breakdown.json} --baseline "{baseline-path}" --rule "{rule-path}" --scored-by {scored_by} [--reference-h-per-bcp {bcp_reference_h_per_bcp}] [--rescore] --dry-run
```

Pass `--reference-h-per-bcp` **only** when `bcp_reference_h_per_bcp` is configured (step 7); omit it when absent and the script falls back to the seed automatically. Never derive that value from the recalibrated baseline — the anchor is frozen precisely so leverage against it does not collapse.

- **Non-interactive:** if the dry run exits 0, run it again **without** `--dry-run` to persist.
- **Dry-run review:** show the user the preview (total, `estimated_hours`, source of `h_per_bcp`, `estimated_hours_pre_bcp`, breakdown, advisories). Persist (rerun without `--dry-run`) only after explicit confirmation. On a rescore, pass `--rescore` (archives the previous block into `bcp.history`, FIFO cap 50).

Non-zero exit: show the error verbatim and stop (1 = validation, 2 = runtime, 3 = conflict).

## Surface Advisories

If `result.advisories` is non-empty (delta >50% on a rescore, cumulative drift >2×, or history truncation), relay them to the user in `{communication_language}` — they include the "consider splitting into sub-stories" suggestion. An advisory **does not block**; it is guidance.

## Confirm

Summarize: BCP total, derived `estimated_hours` (and the preserved `estimated_hours_pre_bcp`), source of `h_per_bcp` (`seed` vs `baseline:<category>`), derived `estimated_hours_reference` plus `reference_source` (`seed` vs `config`), `scored_by`, and the size of `bcp.history`. Confirm that `pulse_metrics` and every other key are untouched.

## On Completion

After Confirm (and once the `bcp.*` block has been persisted by the run without `--dry-run`), follow the `workflow.on_complete` resolved at activation:

- **Empty** value (default) → finish with no further action.
- **Non-empty** value → follow the string verbatim as a terminal instruction — it is the last step before exiting.

**Invariants (always true — any override must respect them):**

- The hook runs **after** persistence — the story frontmatter already reflects the new `bcp.*` block.
- The hook **MUST NOT mutate** the story frontmatter (single-writer principle — only `apply_score.py` writes `bcp.*`).
- An error in the hook is a **warning**, not a rollback — the score is already written.
- On a `--dry-run` run (no persistence) the hook is **skipped**.

To customize (team-level, committed): edit `{project-root}/_bmad/custom/bmad-bcp-score.toml`. User-level (gitignored): `bmad-bcp-score.user.toml`.

## Design Notes

- The ruler is read from the installed `bmad-bcp-rule-card` skill — single source, no copy. This avoids drift for the reason that matters after the MIT relicence: a duplicated ruler can diverge silently, and diverging rulers destroy cross-team score comparability. `tests/test_bcp_rule_immutability.py` guards the original.
- The script preserves the story body verbatim; it only re-serializes the frontmatter map (non-BCP keys kept, order preserved).
- Idempotence: re-running the same breakdown without `--rescore` neither overwrites `estimated_hours_pre_bcp` again nor pollutes `history`.
- `assets/bcp-frontmatter.schema.yaml` documents the contract; the script validates the invariants in code (no extra jsonschema dependency).
- **Three h/BCP numbers:** the _seed_ (cold start) and the _recalibrated_ factor (live, per category) derive the **plan** (`estimated_hours`) → predictability. The frozen _reference rate_ (`bcp_reference_h_per_bcp`) derives the **anchor** (`estimated_hours_reference`) → stable leverage that does not collapse. The script owns every BCP→hours conversion (single writer); PULSE only **reads** the fields. The reference rate changes only through **governance** (durable config plus a ledger, forward-only) — `recalibrate` never touches it.
- **Customization surface:** `customize.toml` follows the BMad pattern — three layers (skill defaults < team `<project>/_bmad/custom/*.toml` < user `*.user.toml`) resolved by `_bmad/scripts/resolve_customization.py`. `on_complete` is the extension point for chaining post-persistence actions without forking the skill.
