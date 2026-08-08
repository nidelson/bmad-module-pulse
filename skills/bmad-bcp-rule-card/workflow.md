# BCP — Rule Card

## Overview

Renders CI&T's canonical **Business Complexity Points (BCP)** ruler for quick reference during scoring: 10 complexity elements × 5 sizes (XS, S, M, L, XL) on the Fibonacci scale [1, 2, 3, 5, 8], with each element's definition and the verbatim descriptor of every cell.

The ruler lives in `assets/bcp-rule.yaml` — a **verbatim** transcription of the ruler published by CI&T, MIT-licensed since May 2026 (`flow-ciandt/bcp-agent`). This skill only **reads and displays**; it never modifies the rule.

Available when `pulse_estimation_method = "bcp"`. It is read-only and harmless under any other method, but the scores it explains are only produced when scoring is enabled.

## Conventions

- Bare paths resolve from the skill root (e.g. `assets/bcp-rule.yaml`).
- `{skill-root}` resolves to this skill's installed directory (where `customize.toml` lives).
- `{project-root}`-prefixed paths resolve from the project root.

## On Activation

1. **Resolve workflow customization:** run `python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`. Keep `activation_steps_prepend`, `activation_steps_append`, `persistent_facts` and `on_complete` for the later steps. If the script fails, resolve the `workflow` block by reading `{skill-root}/customize.toml` plus the team/user overrides in `{project-root}/_bmad/custom/bmad-bcp-rule-card.{toml,user.toml}` (scalars: override wins; arrays: append).
2. **Prepend steps:** execute each entry of `workflow.activation_steps_prepend` in order.
3. **Persistent facts:** treat each entry of `workflow.persistent_facts` as foundational context for the whole session. Entries prefixed with `file:` load the content of the path/glob under `{project-root}`; the rest are verbatim facts.
4. **Ruler:** read `assets/bcp-rule.yaml`. Treat `descriptors.<size>: null` as an **empty cell** in the canonical ruler. Do not invent text to fill it — the ruler is sparse on purpose, and a filled cell is a different ruler, which makes the score incomparable with every other installation.
5. **Optional filter:** accept a filter argument — an element name or slug (e.g. `business_rules`, `Boundaries`) → display only that element. No argument → display the full ruler.
6. **Append steps:** execute each entry of `workflow.activation_steps_append` in order.

## Render

Produce a readable card in `{communication_language}`:

1. **Header** — the title "Business Complexity Ruler" plus the size scale with points: `XS=1 · S=2 · M=3 · L=5 · XL=8` (from `sizes`).
2. **Table** — one row per element, columns: Element · Definition · XS · S · M · L · XL. Render `null` cells as an em dash `—`. Mark elements with `always_there: true` (e.g. an "always present" badge) — the ruler groups them under "ALWAYS THERE".
3. **Attribution footer (MANDATORY, never omit)** — display the `license.attribution` block verbatim plus the `license.url` link. MIT requires preserving the copyright notice and the licence text; emitting the card without the attribution breaches the licence.

If the terminal or context is narrow, prefer a per-element list layout over a wide table — but the three parts above are invariant.

## On Completion

Once the card has been rendered, follow the `workflow.on_complete` resolved at activation:

- **Empty** value (default) → finish with no further action.
- **Non-empty** value → follow the string verbatim as a terminal instruction — it is the last step before exiting.

**Specifics of this skill (read-only):**

- There is no persisted artifact — the hook runs **after display**, not after persistence. Use it to offer follow-up actions, suggest related skills, or log the lookup.
- The hook **MUST NOT modify** `assets/bcp-rule.yaml` (immutable by design decision — cross-team score comparability).
- An error in the hook is a **warning** — the card was already displayed.

To customize (team-level, committed): edit `{project-root}/_bmad/custom/bmad-bcp-rule-card.toml`. User-level (gitignored): `bmad-bcp-rule-card.user.toml`.

## Design Notes

- **Immutability is a design decision, not a legal constraint.** `assets/bcp-rule.yaml` is MIT — legally modifiable. Editing elements, definitions, descriptors or points is what breaks cross-team score comparability, which is the only property that makes a BCP score worth anything: 10 BCP from one squad must be 10 BCP from another. Diverging is allowed and requires bumping `rule_version`, accepting that the resulting scores no longer compare with other installations. `tests/test_bcp_rule_immutability.py` enforces the bump. Only editorial `hints` blocks (if present, authored here and not part of the CI&T framework) are mutable.
- No scripts: rendering YAML into a table is a native LLM capability; a script would add nothing (outcome-driven principle).
- The **New Domain Entities** definition in the canonical ruler talks about "interactions ... sources/destinations ... durability of the information exchanged", which reads like Boundaries semantics. It is the **published text, verbatim**. Do not correct it — the transcription's value is being identical to what every other team scores against, and a clearer wording here would be a silent divergence.
- **Customization surface:** `customize.toml` follows the BMad pattern — three layers (skill defaults < team `<project>/_bmad/custom/*.toml` < user `*.user.toml`) resolved by `_bmad/scripts/resolve_customization.py`. `on_complete` is the extension point for chaining post-display actions without forking the skill.
