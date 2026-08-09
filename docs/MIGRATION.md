# PULSE Migration Guide

Per-release upgrade notes. Newest first. Each section is self-contained;
skip to the version you are migrating from.

---

## v0.9.1 — the track-done card celebrates something different on the `hours` path (issue #97)

**Who this affects:** every install **not** using `pulse_estimation_method = "bcp"`
— which is the default. No action required; nothing to configure. The data written
to `pulse_metrics` is unchanged, including `estimate_error_pct`. Only the closing
line of the terminal card changed.

**What changed:** the celebration used to trigger on estimate accuracy on every
path. It now does so only on `bcp`.

| Path | Before | After |
| --- | --- | --- |
| `bcp` | `🎯 On-plan (estimate within 15%)` / `⚠ Off-plan` | unchanged |
| `hours`, `story_points`, `tshirt` | same as `bcp` | `✅ Clean run — first-pass, no HALTs`, `✅ First-pass`, or `📊 Data recorded.` |

**Why.** Accuracy is a property of the *team* only when the estimate comes from a
comparable unit. Without a ruler, the estimator and the executor are the same
agent, and a trophy for being on-plan rewards padding the estimate — the mirror
image of the v0.6 problem, where a trophy for leverage magnitude rewarded
inflating it. Both incentives act on the same variable, in opposite directions,
so the honest move on that path is to celebrate what is *observed* instead:
first-pass review, and a clean HALT count.

The off-plan warning moved with it, for the same reason: "review the estimate
basis" is advice about a ruler. Where the basis is a person's judgement, it reads
as blame for a number nothing could have calibrated.

**Two details:**

- `bmad-pulse-track-backfill` branches identically, except its non-`bcp`
  celebration checks first-pass **only**. That skill does not reconstruct halts,
  so claiming "no HALTs" would assert data it deliberately refuses to invent.
- The legacy `pulse_leverage_threshold_*` keys stay retired as celebration
  triggers. The dashboard does band the hours-path leverage with them (#66), but
  that is reporting, not a per-story trophy.

---

## v0.9 — the agent is Maxine, and two config keys lost the old name (issue #84)

**Who this affects:** every install. The change is cosmetic at the surface and
has exactly two mechanical edges — a config key rename and a roster entry.

**What changed:**

- **Levi is retired; Maxine is the agent.** Name, title, icon (`⚡` → `💓`),
  role, identity and principles are new. The name came from _leverage_, which
  the module stopped headlining unconditionally in #66 — an agent named after a
  metric that is now one of two, chosen by configuration, was the wrong front
  door.
- **`pulse_levi_verbosity` → `pulse_verbosity`** and **`pulse_levi_coaching_mode`
  → `pulse_coaching_mode`.** A consumer-facing key naming the persona is what
  made a cosmetic swap into a breaking change; the keys are now persona-free so
  the next one costs nothing.
- **The party-mode roster entry is corrected in place.** `register-party-agent.py`
  normally preserves editorial fields (`name`/`title`/`icon`/`description`)
  because the team edits them by hand. It now makes one exception: a value that
  still matches _exactly_ what an older release of the script wrote is not a
  team edit, so it is refreshed. A name you chose yourself is still preserved.

**What you have to do: nothing.**

- **The keys keep working.** Every workflow reads the new name first and falls
  back to the legacy one. Your existing `pulse_levi_verbosity` is still
  honoured — rename it at your leisure. Without that fallback the setting would
  stay in your config file, unread, and silently revert to the default: nothing
  would look broken, the behaviour would just change.
- **Nothing moves on disk.** The skill folder is still
  `.claude/skills/bmad-agent-pulse/` and the party-mode key is still
  `[agents.bmad-agent-pulse]` — a rename in v0.4.5 already decoupled the path
  from the persona, so this swap does not touch either.
- **`/bmad-party-mode` will list Maxine** after the next setup run. If it still
  says Levi, the entry in `_bmad/custom/config.toml` was hand-edited at some
  point and is being preserved on purpose; re-run setup with `--force` to
  overwrite it.

**⚠ One case to watch: re-running setup.** The fallback covers the upgrade
path, where you update the module and change nothing else. If you *also* re-run
`bmad-pulse-setup`, it prompts for `pulse_verbosity` as a new key and writes
whatever you answer — including the default, if you accept it — and the new key
then wins over your old `pulse_levi_verbosity`. The old key is never deleted
(the writer upserts), so nothing is lost, but the effective value is the one you
just answered. If you had it on `verbose`, say so at the prompt, or copy the
value across afterwards.

**One thing that deliberately did not change.** `canonicalId` in the agent
manifest fragment stays `bmad-pulse-efficiency-analyst`. It is an identifier,
not a label — churning it on a persona swap is how stable references break.

---

## toml-first config — `config.toml` with per-key `config.yaml` fallback (issue #73)

**Who this affects:** installs on post-#2285 BMAD, where the canonical config is
`_bmad/config.toml` (resolved by `_bmad/scripts/resolve_config.py` across four
layers) and `_bmad/config.yaml` is legacy. Before this change PULSE read/wrote
**only** the yaml, so it never saw `config.toml` nor the `custom/config.toml`
overrides — a split-brain where the values diverged and PULSE stayed on the
legacy file.

**What changed:**

- **Consumers resolve toml-first.** Every workflow/agent now runs
  `resolve_config.py --key modules.pulse`, reads `pulse_*` from the resolved
  toml, **falls back per key** to the legacy `pulse:` section of `config.yaml`,
  and uses the `module.yaml` default only when neither has the key.
- **Setup writes toml.** `merge-config.py` writes the module section to
  `_bmad/custom/config.toml` under `[modules.pulse]` (the layer that wins over
  installer defaults), preserving that file's comments and other sections. It
  no longer writes the `pulse:` section into `config.yaml` and **strips** a
  stale one on run.

**⚠ Caveat crítico (pareamento obrigatório).** The `[modules.pulse]` in
`config.toml` on a post-#2285 install carries the *install defaults*
(`pulse_dev_categories = "standard_4"`, `pulse_estimation_method = "hours"`),
which do **not** match a team using a custom taxonomy (e.g.
`frontend, backend, fullstack, mobile, security`) or `bcp`. If PULSE goes
toml-first **without** the team's real values pinned in `custom/config.toml`,
it silently regresses to the install defaults and loses the custom taxonomy.

**How to migrate (re-run setup):** re-running `bmad-pulse-setup` is the
migration. It reads the current effective values (resolved toml, then the legacy
`pulse:` in `config.yaml`) and offers them as the prompt defaults; accepting the
defaults pins the team's answers into `custom/config.toml [modules.pulse]` and
strips the legacy yaml section. Verify `pulse_dev_categories` and
`pulse_estimation_method` in `custom/config.toml` after migrating.

---

## Upgrading over an existing install — automatic self-heal

This applies to **every** PULSE upgrade, not a specific version.

The upstream BMAD installer performs an *additive* deploy when PULSE is
already installed in a project: brand-new files are copied, but
pre-existing files (`module.yaml`, `SKILL.md`, …) are **not** overwritten
and renamed/removed skills are **not** pruned. Re-running
`npx bmad-method install` over an existing install therefore leaves a
mixed state frozen at the old version — new files present, old files
stale, orphan folders lingering (issue #36).

`bmad-pulse-setup` now self-heals this. Its first step,
`reconcile-skills.py`, force-syncs every PULSE skill directory from the
authoritative source (the freshly-fetched BMAD custom-module cache) and
prunes orphaned renamed folders. It is idempotent (no-op when already in
sync) and non-fatal on fresh installs.

```bash
# 1. Fetch the new PULSE version (refreshes the BMAD custom-module cache)
npx bmad-method install --custom-source https://github.com/nidelson/bmad-module-pulse

# 2. Re-run setup — reconcile converges the deployed tree automatically
/bmad-pulse-setup
```

If the deployed `bmad-pulse-setup` skill itself was stale, the first run
reconciles it in place; the JSON `notice` will ask you to run
`/bmad-pulse-setup` once more so the current version executes. Re-run it
once and you are converged.

**Production tip — pin a released tag.** Installing with the bare
`--custom-source` tracks `main` (`version: main` in the manifest), so
every re-run pulls whatever has since landed there. For deterministic,
team-reproducible installs, pin an explicit tag and bump it deliberately:

```bash
npx bmad-method install \
  --custom-source https://github.com/nidelson/bmad-module-pulse \
  --version v0.4.5
```

Reconcile still runs on every `/bmad-pulse-setup` and converges the
deployed tree to whatever the cache holds — pinning just makes *what the
cache holds* deterministic.

Manual reconcile (e.g. for a bug report) — `--dry-run` previews without
writing:

```bash
python3 .claude/skills/bmad-pulse-setup/scripts/reconcile-skills.py \
    --project-root . --dry-run
```

---

## Unified BMAD architecture — auto-tracking moves to `bmad-build` (issue #83)

**Symptom:** setup reported success, but no story ever gets `pulse_metrics`.
Nothing errors — the dashboard is simply empty, and the gap is usually noticed
weeks later.

**Cause.** Recent BMAD merges story creation, implementation and review into a
single `bmad-build` workflow, and keeps `bmad-dev-story` on disk as a
deprecated shim. PULSE's capability probe checked that shim first, reported the
old architecture, and the setup wrote its hooks into `_bmad/custom/bmad-dev-story.toml`
and `_bmad/custom/bmad-code-review.toml` — workflows you no longer invoke. The
gate passed, the summary claimed success, and auto-tracking never fired.

**What changes.** The probe now checks `bmad-build/customize.toml` **first** and
reports which skills to target in its payload:

```bash
python3 .claude/skills/bmad-pulse-setup/scripts/detect_bmad_capability.py --project-root .
# {"capability": "bmad-build", "inject_targets": ["bmad-build"], ...}
```

| Architecture | `capability` | Override file(s) |
|---|---|---|
| Unified (`bmad-build` present) | `bmad-build` | `_bmad/custom/bmad-build.toml` — both hooks in one file |
| Split (`bmad-dev-story` only) | `bmad-6.4.0+` | `_bmad/custom/bmad-dev-story.toml` + `_bmad/custom/bmad-code-review.toml` |

One file suffices on the unified architecture because review runs in-process
through `workflow.review_layers`, so `on_complete` is a genuine completion
point rather than a premature one.

### How to migrate

Only needed if you are on the unified architecture and PULSE was set up before
this fix. Check with the probe command above — if it prints `"bmad-build"` and
`_bmad/custom/bmad-build.toml` does not exist, you were affected.

```bash
# 1. Pull the new PULSE version
npx bmad-method install --custom-source https://github.com/nidelson/bmad-module-pulse

# 2. Remove the inert overrides (back them up first if you customized the text)
rm _bmad/custom/bmad-dev-story.toml _bmad/custom/bmad-code-review.toml

# 3. Re-run setup — it now emits bmad-build.toml
/bmad-pulse-setup
```

Stories completed while the hooks were inert have no `start_ts`. Recover them
with `/bmad-pulse-track-backfill`; there is nothing to repair in the sprint
status itself.

> Keep `_bmad/custom/bmad-code-review.toml` **only** if you deliberately run
> `/bmad-code-review` as a separate step. Having it alongside `bmad-build.toml`
> records track-done twice for the same story.

## v0.7.x → v0.8.0 — Previsibilidade para precificar (forecast de projeto)

**Quem isto afeta:** quem usa a seção de previsão do dashboard com BCP. **Breaking** numa seção: a antiga `Previsão de Capacidade` (extrapolação por leverage) foi **substituída** por `Previsão de Projeto` (`BCP × h/BCP ± IC 90%`).

A v0.8 vira a engine honesta pra **frente**: dado o backlog pontuado restante, prevê quantas horas falta — com intervalo de confiança de 90% — pra times que faturam por hora.

### O que muda

- **Previsão de Projeto** (substitui Previsão de Capacidade). PULSE enumera (read-only) as stories pontuadas **não-iniciadas** (com `bcp.total`, sem entrada em `pulse_metrics`) → BCP restante por categoria, e prevê `horas = BCP × h/BCP` (geométrico, calibrado da v0.5) com **IC de 90%** (escala a banda de confiança de k=1 ~68% pra k=1.645 ~90%). O total soma os limites por categoria (faixa **conservadora**, declarada). Categorias finas (n<3) usam baseline pooled e marcam **baixa confiança**. Backlog vazio → sem seção.
- **Digest** (`digest.md`). Um resumo conciso (previsibilidade + forecast + coortes em risco) é gerado junto do dashboard. **Entrega thin:** PULSE **não** chama Slack/Linear direto — você aponta `on_complete` pra um comando que posta o `digest.md` (ex.: webhook Slack via `curl`). Credenciais ficam no seu ambiente.
- **Quebra por desenvolvedor/agente:** **adiada** — PULSE não captura identidade hoje (só `dev_count`); fica pra um marco futuro com decisão de privacidade à parte. A v0.8 quebra por **categoria** (que já existe).

### O que você precisa fazer

**Nada no disco** além do upgrade normal. O forecast usa dados que PULSE já lê + os story files pontuados (read-only). Se o backlog não for enumerável, informe um total manual em `pulse_forecast_remaining_bcp`. Pra digests, configure `on_complete`.

> ⚠ **Breaking:** a seção `🔮 Previsão de Capacidade` deixou de existir; quem parseava ela (ou dependia da extrapolação por leverage) deve migrar pra `🔮 Previsão de Projeto`. As demais seções não mudaram de formato.

---

## v0.6.0 → v0.7.0 — A ação que importa (alerta de drift na estimativa)

**Quem isto afeta:** quem usa `/bmad-pulse-track-start` e o dashboard. **Aditivo** — nada existente muda de formato; a v0.7 só **acrescenta** um aviso e uma seção.

A v0.5/v0.6 são retrospectivas (você vê o drift depois que a story fechou). A v0.7 leva o sinal pro **momento do compromisso**: ao iniciar uma story, PULSE avisa se a coorte dela vem errando a estimativa — _antes_ de virar promessa. PULSE segue passivo: o alerta **informa, nunca dirige**.

### O que muda (tudo aditivo)

- **Alerta no track-start.** Ao registrar o start, PULSE computa o drift recente da coorte da story (`category` + segmento de tamanho quando há BCP) e, se as últimas 5 erraram > 25% na mediana (mínimo 3 stories), mostra uma linha **não-bloqueante**: `⚠ Heads up: stories like backend/story were off +N% (median) over the last 5 — re-estimate before committing?`. O start é registrado normalmente; **PULSE nunca altera `estimated_hours`** — reestimar é decisão sua.
- **Watch-list no dashboard.** Nova seção `🚦 Estimation drift watch` lista as coortes que estão estimando mal agora (mediana > 25%, ≥3 stories), ordenadas por drift, com tendência. Coortes saudáveis são omitidas; tudo saudável → "No cohorts drifting — estimates are tracking".

### O que você precisa fazer

**Nada.** Aditivo, sem migração de dados. Próximo `/bmad-pulse-track-start` e `/bmad-pulse-dashboard` já trazem o aviso e a seção. Os thresholds (`K=5`, `T=25%`) são inline nesta versão.

> ℹ️ **Não-breaking.** Nenhum formato existente foi reordenado ou removido; só houve acréscimos. O alerta é advisory e nunca toca a sua estimativa.

---

## v0.5.0 → v0.6.0 — Inverter o velocímetro (previsibilidade como herói)

**Quem isto afeta:** todos os usuários do dashboard e do track-done; mais profundamente quem usa `pulse_estimation_method=bcp`. Nada na coleta de dados muda — a virada é em como os números são **enquadrados**.

A v0.6 age sobre a engine honesta da v0.5: troca a métrica-herói de **alavancagem** → **previsibilidade/acurácia**. Um `~1.0x` estável é saudável; um multiplicador alto sinaliza estimativa inflada, não velocidade. PULSE segue passivo e zero-**write**-coupled ao `bmad-module-bcp`.

### O que muda

- **Métrica-herói invertida.** O `General Statistics` do dashboard agora **lidera** com `Predictability` (mediana do erro de estimativa por story `|actual−estimated|/estimated`, menor = melhor, com seta de tendência) e demove `Avg AI Leverage` pra uma linha de contexto `AI Leverage (vs PLAN) — context, not a target`.
- **Sinal de convergência.** Nova seção "Baseline convergence" mostra se o `h/BCP` está estabilizando (mediana de `|drift|` da 1ª vs 2ª metade + banda estreitando). Precisa de ≥4 stories BCP.
- **Detecção de regime.** PULSE passa a **ler** `estimated_hours_basis` (read-only) pra rotular cada multiplicador pela base (`vs PLAN (bcp)`, `vs PLAN (hours)`, …), com fallback pro `pulse_estimation_method`. Nunca escreve o campo, nunca deriva horas dele.
- **Celebração invertida.** O `track-done` (e `track-backfill`) param de premiar leverage alto (`🔥 Exceptional!` aposentado). O gatilho agora é **acurácia**: `🎯 On-plan` quando a estimativa erra ≤15%; `⚠ Off-plan — review the estimate basis` quando erra ≥50%. Os `pulse_leverage_threshold_*` ficam no `module.yaml` por back-compat, mas não disparam mais celebração.

### O que você precisa fazer

**Nada no disco** além do upgrade normal (`/bmad-pulse-setup`). A mudança é nos workflows; o próximo `/bmad-pulse-dashboard` e `/bmad-pulse-track-done` já renderizam o novo enquadramento. Sem migração de dados.

> ⚠ **Breaking para parsers e para quem dependia do troféu de leverage.** O `General Statistics` foi reordenado, colunas de leverage ganharam "(vs PLAN)" e a celebração do track-done mudou de gatilho. Se você scrapeia o dashboard ou automatiza em cima do "🔥 Exceptional", atualize. O número de leverage continua visível, só sem troféu.

---

## v0.4.x → v0.5.0 — Honest measurement engine (BCP dashboard)

**Who this affects:** only projects using `pulse_estimation_method=bcp`. If you
do not use BCP, the dashboard is unchanged — skip this section.

v0.5.0 reworks how the dashboard summarizes per-category **h/BCP** so the number
is honest rather than flattering. Nothing about tracking, frontmatter, or the
BCP module boundary changes — PULSE stays passive and zero-coupled to
`bmad-module-bcp` (it still only *reads* `bcp.*`, never writes a baseline). The
shift is entirely in how the **BCP Productivity** section is computed and
rendered.

### What changes

- **Geometric mean, not arithmetic.** Per-category h/BCP baselines are now the
  *geometric* mean of the per-story ratios (`exp(mean(ln(ratio)))`). h/BCP is a
  multiplicative ratio, so the arithmetic mean was biased high and fragile to a
  single outlier. **Baselines recomputed from the same data will shift** — this
  is the intended correction, not a regression.
- **Micro vs story-size segmentation.** Stories are split at the *observed
  median* BCP total (`micro` below, `story` at/above) and each segment gets its
  own baseline, so a 1-point fix no longer pollutes a 40-point story's number. A
  pooled `all` row remains for continuity. The split is data-driven — PULSE
  makes no assumption about your BCP point scale and there is **no new config
  key**.
- **Confidence band, not a point.** Each baseline now shows a *typical range*
  `[low–high]` (geometric standard deviation, ~68%) plus the sample size `n`.
  Ranges appear only at `n >= 3`; thinner samples show the bare point.
- **Leverage reframed (anti-Goodhart).** A new dashboard note states that
  leverage (`estimated_hours / actual_hours`) collapses to ~1.0x once the
  estimate basis is calibrated — so a *high* multiplier signals an uncalibrated
  estimate, not velocity, and the durable signal is **predictability** (h/BCP
  drift converging on zero). The hero-metric inversion itself lands in v0.6;
  v0.5 only locks the invariant.

### What you must do

**Nothing on disk** beyond a normal upgrade (`/bmad-pulse-setup`). The change is
in the dashboard workflow; the next `/bmad-pulse-dashboard` run renders the new
shape. There is no data migration — historical `pulse_metrics` are re-read and
re-summarized in place.

> ⚠ **Breaking only for tooling that parses the dashboard markdown.** The
> **BCP Productivity** table gained `Segment` and `n` columns and the h/BCP cell
> now carries a `[low–high]` range. If you scrape the dashboard, update your
> parser. The human-readable dashboard and all non-BCP sections are unaffected.

---

## Auto-tracking fix — regenerate the `bmad-dev-story` override (post-v0.4.9)

If `bmad-pulse-track-start` was **not firing automatically** at the start of
your stories (issue #47), the cause was the auto-tracking trigger living in
the `persistent_facts` array of `_bmad/custom/bmad-dev-story.toml`.
`persistent_facts` is passive context the agent merely carries — it did not
deterministically execute. The fix moves the trigger to
`activation_steps_append` (an executed activation step) and decouples it from
the sprint-status `in-progress` field.

The fix ships in the PULSE source, but **existing installs keep the old
override file**: `bmad-pulse-setup` aborts rather than overwrite a file you
may have customized. To pick up the fix, regenerate it:

```bash
# 1. Pull the new PULSE version
npx bmad-method install --custom-source https://github.com/nidelson/bmad-module-pulse

# 2. Remove the stale override (or back it up if you customized it)
rm _bmad/custom/bmad-dev-story.toml

# 3. Re-run setup — it re-emits the override with the activation-step trigger
/bmad-pulse-setup
```

Alternatively, re-run setup and let it overwrite via `--force` (passed through
to `inject_customize.py`). `bmad-code-review.toml` (track-done) is unchanged —
only the `bmad-dev-story` override needs regeneration.

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
| `<!-- PULSE:auto-inject -->` markers in `.claude/skills/bmad-dev-story/workflow.md` | `_bmad/custom/bmad-dev-story.toml` (track-start auto-trigger) |
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
