# PULSE Migration Guide

Per-release upgrade notes. Newest first. Each section is self-contained;
skip to the version you are migrating from.

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
