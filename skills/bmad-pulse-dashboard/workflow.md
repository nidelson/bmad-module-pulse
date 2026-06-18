---
name: bmad-pulse-dashboard
description: 'Generate cumulative PULSE efficiency dashboard'
standalone: true
main_config: '{project-root}/_bmad/config.yaml'
config_section: 'pulse'
---

# Workflow Dashboard

**Goal:** Generate a cumulative dashboard with all PULSE efficiency metrics, cross-sprint trends, and process insights.

**Your Role:** You are Levi, compiling the complete efficiency view of the project.

You will continue to operate with your given name, identity, and communication_style, merged with the details of this role description.

## Conventions

- Bare paths (e.g. `customize.toml`) resolve from the skill root.
- `{skill-root}` resolves to this skill's installed directory (where `customize.toml` lives).
- `{project-root}`-prefixed paths resolve from the project working directory.
- `{skill-name}` resolves to the skill directory's basename.

## On Activation

### Step 1: Resolve the Workflow Block

Run: `python3 {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`

**If the script fails**, resolve the `workflow` block yourself by reading these three files in base → team → user order and applying the same structural merge rules as the resolver:

1. `{skill-root}/customize.toml` — defaults
2. `{project-root}/_bmad/custom/{skill-name}.toml` — team overrides
3. `{project-root}/_bmad/custom/{skill-name}.user.toml` — personal overrides

Any missing file is skipped. Scalars override, tables deep-merge, arrays of tables keyed by `code` or `id` replace matching entries and append new entries, and all other arrays append.

### Step 2: Execute Prepend Steps

Execute each entry in `{workflow.activation_steps_prepend}` in order before proceeding.

### Step 3: Load Persistent Facts

Treat every entry in `{workflow.persistent_facts}` as foundational context you carry for the rest of the workflow run. Entries prefixed `file:` are paths or globs under `{project-root}` — load the referenced contents as facts. All other entries are facts verbatim.

### Step 4: Load Config and Execute Append Steps

Load the PULSE configuration as described in INITIALIZATION below, then execute each entry in `{workflow.activation_steps_append}` in order. Activation is complete; begin the workflow EXECUTION section.

---

## INITIALIZATION

### Configuration Loading

Load the `pulse` section from `{main_config}` and resolve all module variables:

- `project_name`, `communication_language`
- `pulse_data_folder`, `pulse_sprint_status_filename`
- `pulse_dashboard_folder`, `pulse_dashboard_format`
- `pulse_include_trend_chart`, `pulse_include_capacity_forecast`
- `pulse_dev_categories`, `pulse_levi_verbosity`
- `date` as current system-generated datetime

### Paths

- `sprint_status_file` = `{pulse_data_folder}/{pulse_sprint_status_filename}`
- `dashboard_file` = `{pulse_dashboard_folder}/dashboard.md`

---

## EXECUTION

### Step 1: Collect Data

1. Read `{sprint_status_file}` in full
2. Extract all entries from the `pulse_metrics:` section
3. Group by epic — infer epic_id from the numeric prefix of story_id (e.g. `15.3` → epic 15, `4.4.1` → epic 4)
4. Calculate aggregations:
   - Total stories measured
   - **`predictability_score`** — the v0.6 **hero metric**. The **median** of the per-story estimate error `|actual_hours - estimated_hours| / estimated_hours` across all stories with `pulse_metrics` (floor `estimated_hours` at 0.01 to avoid divide-by-zero). Report as a percentage; **lower is better** — it reads "estimates are X% off, median". Method-agnostic: for BCP stories it equals `|bcp_recorded.drift_pct|` (the BCP totals cancel), so it works whether or not the project uses BCP. Compute it global and per category. Median (not mean) for the same reason the v0.5 baseline is geometric — resist outliers. Pair it with a **trend arrow**: split the stories in story-order (chronological proxy) into first half vs second half and compare each half's median error → `↓ converging` / `→ stable` / `↑ diverging`. Needs `>= 4` stories for a trend; fewer → no arrow.
   - **`estimate_regime`** (v0.6 regime detection) — the basis each `estimated_hours` was derived from, read **read-only** from the story's `estimated_hours_basis` frontmatter field when present (`bcp` / `hours` / `story_points` / `tshirt`), falling back to `{pulse_estimation_method}` when the field is absent. PULSE **never writes** `estimated_hours_basis` and **never derives hours from it** — it only labels what each multiplier is measured *against* (so "5x" reads "vs PLAN (bcp)" not an unqualified number). Report the dominant regime across stories for the leverage context line; annotate a story in the breakdown when its regime differs from the project default. (`estimated_hours_pre_bcp` stays ignored.)
   - **`cohort_drift(category, segment)`** (v0.7 — the shared primitive for estimation-time drift alerts; also consumed by `bmad-pulse-track-start`). For a **cohort**, the **median** of the per-story estimate error `|actual_hours - estimated_hours| / estimated_hours * 100` over the **last `K = 5` completed stories** in that cohort (story-order = chronological proxy; floor `estimated_hours` at 0.01). For BCP stories this equals `|bcp_recorded.drift_pct|`. The **cohort key** is `(category, segment)` when the story carries BCP (segment = `micro`/`story` from the v0.5 median split), else `(category)` alone — fallback documented so non-BCP projects still cohort by category. Returns `(median_abs_drift_pct, n, sample_story_ids)` where `n` is the cohort size considered (≤ K). **Requires `n >= 3`** to be meaningful — fewer → `insufficient` (callers must stay silent, no false alarm). This is read-only over `pulse_metrics`; it never writes or alters any estimate.
   - **`drift_watchlist`** (v0.7) — the forward-looking companion to the track-start alert. For **every** cohort present in `pulse_metrics`, evaluate `cohort_drift`; keep only cohorts with `n >= 3` **and** `median_abs_drift_pct > T = 25%`, sorted by `median_abs_drift_pct` desc. Each entry carries `(cohort_label, median_abs_drift_pct, n, trend)` where `trend` reuses the v0.6 half-split direction (`↓`/`→`/`↑`). Healthy cohorts (≤ T) are omitted. Empty list is the healthy default.
   - Average, minimum, and maximum leverage
   - Total estimated hours vs total actual hours
   - First-pass rate
   - Leverage by category (use `{pulse_dev_categories}`)
   - **Halt aggregations** (read `process_health.halts` from each story; the field has three valid shapes — handle all without crashing):
     - **Shape A** (integer): treat as opaque count, skip duration math.
     - **Shape B** (list of objects): structured — read `kind`, `context`, `duration_min`, `pre_approved_batch`.
     - **Shape C** (list of plain strings, legacy pre-0.5.0): infer `kind` from prefix when possible (`approval_wait_*` → `approval_wait`); `duration_min` is unknown — count as halt but exclude from minute aggregations.
     - Aggregations:
       - `total_halts` — sum across all stories (integers + list lengths regardless of shape)
       - `total_approval_wait_count` — count of entries where `kind == approval_wait` (Shape B explicit, Shape C inferred via prefix)
       - `total_approval_wait_minutes` — sum of `duration_min` for Shape B entries with `kind == approval_wait` and `pre_approved_batch != true` (Shape C contributes 0 — duration unknown)
       - `total_pre_approved_batch_count` — count of `approval_wait` entries with `pre_approved_batch: true` (Shape B only)
       - `legacy_halt_string_count` — count of Shape C entries encountered (used to surface migration hint in insights)
       - `stories_with_approval_wait` — list of `(story_id, total_minutes)` pairs for the breakdown table (entries with unknown minutes show as `?min`)
   - **BCP aggregations** (read `bcp_recorded` and `bcp_at_start` / `estimation_basis` from each story; all optional — a story without them is normal and contributes nothing):
     - _Since v0.5.0, per-category h/BCP baselines use the **geometric** mean of the per-story ratios, not the arithmetic mean (pre-0.5.0). Baselines recomputed from the same data will shift; this is intentional — see the v0.5 honest-measurement-engine notes._
     - `bcp_stories` — list of stories that have a `bcp_recorded` block
     - `total_bcp` — sum of `bcp_recorded.total` across `bcp_stories`
     - `bcp_throughput` — `total_bcp` grouped by epic (proxy for BCP/sprint when sprint segmentation is unavailable)
     - `segment_split` — the **median** of `bcp_recorded.total` over **all** `bcp_stories` (one global value). Computed **only when `bcp_stories` is non-empty** — never evaluate `median([])`. A story is `micro` when `bcp_recorded.total < segment_split`, else `story`. This split is data-driven: PULSE assumes nothing about the BCP point scale and stays zero-coupled to BCP. (Since v0.5.0.)
     - `h_per_bcp_by_category` — for each `(category, segment)` with `segment ∈ {micro, story}`, the **geometric mean** of `bcp_recorded.h_per_bcp_actual` over the `bcp_stories` in that category and segment: `exp(mean(ln(h_per_bcp_actual)))`, equivalently `(∏ h_per_bcp_actual)^(1/n)`. h/BCP values are multiplicative ratios, so the geometric mean is the unbiased central tendency and resists outliers (a single 10x story does not drag the baseline the way an arithmetic mean would). Round to 2 decimals. Also compute a per-category **pooled** baseline (`all` segment — geometric mean over every `bcp_story` in the category, ignoring the split) for the continuity row. **Thin-segment fallback:** a `(category, segment)` pair with `n < 3` is not reported on its own; those stories still count in the category's pooled `all` baseline. `n == 0` → pair omitted.
     - `h_per_bcp_estimated_by_category` — same **geometric mean**, segmented the same way (per `(category, segment)` plus pooled `all`), over `bcp_recorded.h_per_bcp_estimated` (for the drift comparison).
     - `h_per_bcp_band` — for each baseline (every `(category, segment)` and each pooled `all`), a **confidence band** around the geometric mean of `bcp_recorded.h_per_bcp_actual`, so the baseline reads as a range, not false precision. Compute the **sample geometric standard deviation** `GSD = exp(sample_std(ln(h_per_bcp_actual)))`, where `sample_std` uses the `n-1` (sample, not population) denominator — we estimate, not enumerate. The band is `[geo_mean / GSD, geo_mean * GSD]` (multiplier `k = 1`, ≈ 68% of a log-normal sample — a **typical range**, not a 95% CI; with PULSE's small `n` a wider band would be unactionable). **Require `n >= 3` to emit a band**; for `n < 3` emit the point with an explicit `(n=2)` / `(n=1)` marker and no interval (a GSD from 2 samples has 1 degree of freedom — one outlier distorts it). Carry `n` alongside every baseline so thin samples are visible. (Since v0.5.0.)
     - `drift_trend` — ordered list of `(story_id, bcp_recorded.drift_pct)` for `bcp_stories` (story-order = chronological proxy)
     - `h_per_bcp_convergence` — the v0.6 **self-referential drift signal**: is the h/BCP baseline *stabilizing* over time? Split `drift_trend` in story-order into a first half and a second half and compare the **median `|drift_pct|`** of each: second-half median meaningfully **lower** → `converging` (estimates closing on reality); meaningfully **higher** → `diverging`; within a small tolerance → `stable`. The confidence band (`h_per_bcp_band`) narrowing across the same split is corroborating evidence (report it alongside). **Requires `>= 4` `bcp_stories`** for a reading — fewer → `insufficient data (thin sample)`, no label. This consumes the v0.5 drift/band data; it does not recompute raw ratios.
     - `top_bcp_stories` — `bcp_stories` sorted by `bcp_recorded.total` desc, top 5 (proxy for "elements driving BCP" — PULSE does not read `bcp.breakdown`, so it ranks by total points per story)

### Step 2: Generate Dashboard

Generate the dashboard in the format(s) defined in `pulse_dashboard_format` (`markdown`, `yaml`, or `both`).

For `markdown` format (default), write `{dashboard_file}` with the following structure:

```markdown
# ⚡ PULSE — Dashboard de Eficiência

> Process Utilization & Leverage Statistics Engine
> Gerado em: {date} | Projeto: {project_name}

---

## 🏆 Estatísticas Gerais

| Métrica                 | Valor                                |
| ----------------------- | ------------------------------------ |
| Stories medidas         | {total}                              |
| **Previsibilidade**     | **{predictability_score}% de erro (mediana) {trend_arrow}** |
| Horas estimadas (humano)| {total_estimated}h                   |
| Horas reais (IA)        | {total_actual}h                      |
| Horas economizadas      | {saved}h                             |
| Taxa de first-pass      | {rate}%                              |
| AI Leverage (vs PLANO, {dominant_regime}) | {avg}x — contexto, não meta |

> **Previsibilidade é o número-herói** (menor = estimativas mais perto da realidade; `↓` = convergindo). Leverage aparece só como contexto e lê-se "vs PLANO ({dominant_regime})", nunca "vs humano" — o regime é a base da estimativa (`estimated_hours_basis`, read-only), pra o multiplicador ser lido contra o plano certo. Um multiplicador alto sinaliza base de estimativa não-calibrada, não velocidade (veja o invariante anti-Goodhart abaixo).

> **Invariante anti-Goodhart — leverage não é meta.** `leverage = estimated_hours / actual_hours`. Quando a base de estimativa está calibrada (estimativas derivadas de um baseline que casa com a realidade), essa razão colapsa pra **~1.0x por construção** — então um multiplicador *alto* sinaliza base de estimativa inflada ou não-calibrada, **não** velocidade, e uma *meta de leverage* literalmente premiaria nunca calibrar. O sinal durável é a **previsibilidade**: o drift de h/BCP por categoria convergindo a zero (as estimativas casam com os resultados?). Leia todo multiplicador como "vs PLANO", nunca "vs humano". (v0.5 travou esse invariante; v0.6 agiu sobre ele — a previsibilidade agora lidera o dashboard e a celebração do track-done dispara por acurácia, não por magnitude de leverage.)

<!-- CONDITIONAL: include only if pulse_include_trend_chart == yes -->
## 📈 Tendência de Leverage por Epic

Sparkline: cada █ = 0.5x de leverage, máximo 20 caracteres.

{for each epic with data}
Epic {N}: {sparkline} {avg}x ({count} stories)
{end}

Exemplo: Epic 14: ████████░░ 3.5x (4 stories)
<!-- END CONDITIONAL trend_chart -->

## 📊 Leverage por Categoria

| Categoria | Leverage médio (vs PLANO) | Stories | Melhor |
| --------- | ------------------------- | ------- | ------ |
{for each category in pulse_dev_categories}
| {category} | {x}x | {n} | {best} |
{end}

<!-- CONDITIONAL: include only if pulse_include_capacity_forecast == yes -->
## 🔮 Previsão de Capacidade

Baseado no leverage médio de {avg}x:

- 10h estimadas → ~{10/avg}h reais
- 40h estimadas → ~{40/avg}h reais
- 80h estimadas → ~{80/avg}h reais
<!-- END CONDITIONAL capacity_forecast -->

<!-- CONDITIONAL: include only if total_approval_wait_count > 0 OR total_pre_approved_batch_count > 0 -->
## ⏸ Pausas de Aprovação (Approval-Wait)

| Métrica                                 | Valor                              |
| --------------------------------------- | ---------------------------------- |
| Pausas de aprovação (subtraídas)        | {total_approval_wait_count}        |
| Tempo total de aprovação subtraído      | {total_approval_wait_minutes}min   |
| Decisões de batch pré-aprovadas (puladas)| {total_pre_approved_batch_count}  |

{if stories_with_approval_wait}
**Por story:**

| Story | Minutos de aprovação |
| ----- | -------------------- |
{for each (story_id, minutes) in stories_with_approval_wait}
| {story_id} | {minutes}min |
{end}
{end}

> Pausas de aprovação medem latência de governança (decisões human-in-the-loop) e são subtraídas de `actual_hours` pra o leverage refletir trabalho real de dev, não tempo de espera. `pre_approved_batch` marca decisões duráveis que legitimamente removem latência em stories seguintes — essas são reportadas, mas não subtraídas.

{if legacy_halt_string_count > 0}
> ⚠ {legacy_halt_string_count} entradas de halt legadas (strings simples, formato pré-0.5.0) foram detectadas. As durações não são legíveis por máquina e foram excluídas dos totais de minutos. Migre essas entradas pro formato estruturado (com `kind`, `context`, `duration_min`) pra leverage acurado nas stories históricas.
{end}
<!-- END CONDITIONAL approval_wait -->

<!-- CONDITIONAL: include only if bcp_stories is non-empty (≥1 story has a bcp_recorded block) -->
## 📊 Produtividade BCP

> Telemetria de Business Complexity Points. As horas foram derivadas upstream pelo
> [`bmad-module-bcp`](https://github.com/nidelson/bmad-module-bcp); PULSE só
> reporta produtividade observada e nunca é dono do baseline BCP.

| Métrica               | Valor          |
| --------------------- | -------------- |
| Stories com BCP       | {len(bcp_stories)} |
| Total BCP pontuado    | {total_bcp}    |

**Throughput (BCP por epic):**

{for each epic in bcp_throughput}
Epic {N}: {bcp} BCP ({count} stories)
{end}

**h/BCP real por categoria e segmento de tamanho:**

> Stories divididas na mediana de BCP observada (`segment_split` = {segment_split} BCP): abaixo = `micro`, igual/acima = `story`. A linha `all` agrupa as duas, pra continuidade com dashboards pré-0.5. Um segmento com menos de 3 stories é dobrado em `all` em vez de mostrado sozinho (fino demais pra confiar).
>
> A célula `h/BCP real` mostra a média geométrica com sua **faixa típica** `[low–high]` (≈68%, GSD amostral, `k=1`). A faixa só aparece quando `n >= 3`; pra `n < 3` mostra o ponto puro (o `n` está na coluna `n` — amostras de menos pra uma faixa confiável).

| Categoria | Segmento | n | h/BCP real (faixa típica) | h/BCP est. | Drift |
| --------- | -------- | - | ------------------------- | ---------- | ----- |
{for each category with bcp_stories}
{for each segment in [micro, story] with n >= 3}
| {category} | {segment} | {n} | {h_per_bcp_by_category}h [{band.low}–{band.high}] | {h_per_bcp_estimated_by_category}h | {drift:+}% |
{end}
| {category} | all | {n_all} | {pooled h_per_bcp_by_category}h{if n_all >= 3} [{pooled band.low}–{pooled band.high}]{end} | {pooled h_per_bcp_estimated_by_category}h | {drift:+}% |
{end}

**Convergência do baseline (h/BCP está estabilizando?):**

> {if bcp_stories count >= 4}**{h_per_bcp_convergence}** — a mediana de |drift| foi de {first_half_median}% (1ª metade) pra {second_half_median}% (2ª metade); a faixa de confiança {band narrowed / widened / held} no mesmo split. Convergir é a direção saudável: estimativas se fechando na realidade.{else}_Dados insuficientes (amostra fina — precisa de ≥4 stories BCP pra uma leitura de convergência)._{end}

**Tendência de drift (h/BCP estimado vs real):**

{for each (story_id, drift_pct) in drift_trend}
{story_id}: {drift_pct:+}%
{end}

**Top stories por BCP:**

| Story | BCP | h/BCP real |
| ----- | --- | ---------- |
{for each story in top_bcp_stories}
| {story_id} | {bcp_recorded.total} | {bcp_recorded.h_per_bcp_actual}h |
{end}

> Nota: PULSE ranqueia pelo total de BCP por story. O detalhamento por elemento
> (`bcp.breakdown`) é do `bmad-module-bcp` e é intencionalmente não
> lido aqui — isso preserva o zero coupling.
<!-- END CONDITIONAL bcp -->

## 🚦 Monitor de drift de estimativa

> Companheiro prospectivo do alerta do track-start: quais coortes estão estimando mal *agora*, pra você reestimar antes de se comprometer. Uma coorte só é listada quando tem ≥3 stories concluídas e seu erro de estimativa mediano passa de 25% nas últimas 5. Coortes saudáveis são omitidas.

{if drift_watchlist non-empty}
| Coorte | Mediana \|drift\| | n | Tendência |
| ------ | --------------- | - | --------- |
{for each (cohort_label, median_abs_drift_pct, n, trend) in drift_watchlist}
| {cohort_label} | {median_abs_drift_pct}% | {n} | {trend} |
{end}
{else}
_Nenhuma coorte derivando — estimativas no rumo._
{end}

## 💡 Insights de Processo

{insights gerados a partir dos dados}

## 📋 Detalhamento por Story

| Story | Est. | Real | Leverage (vs PLANO) | Qualidade | Categoria |
| ----- | ---- | ---- | ------------------- | --------- | --------- |

{for each story with pulse_metrics data}
| {id} | {est}h | {actual}h | {lev}x | {quality} | {cat} |
{end}

---

_PULSE — Contra fatos, não há argumentos._
_Dashboard gerado automaticamente pelo módulo PULSE._
```

For `yaml` format, generate `{pulse_dashboard_folder}/dashboard.yaml` with the same data structured as YAML.

For `both` format, generate both files.

### Step 3: Display Summary

Display in the terminal the General Statistics block + (if `pulse_include_trend_chart == yes`) Trend + a Process Insight.
The detail level of the summary must respect `pulse_levi_verbosity`.

### Step 4: Report Location

```text
⚡ Levi: Dashboard salvo em {dashboard_file}
   {total} stories medidas | Leverage médio: {avg}x
```

---

## BEHAVIOR RESTRICTIONS

- If no data exists in the `pulse_metrics:` section, inform and suggest running track-start/track-done first
- Create the `{pulse_dashboard_folder}` directory if it does not exist
- Always overwrite dashboard.md (it is the most recent version)
- The rendered dashboard template above is **PT-BR by default** (section titles, table headers, labels, messages, notes). Keep all technical jargon in English (`h/BCP`, `BCP`, `leverage`, `drift`, `micro`/`story`, field names) and every `{placeholder}` verbatim. If `communication_language` is set to another language, localize the rendered labels/messages accordingly (jargon and placeholders still unchanged); the internal aggregation logic in Step 1 stays English regardless.
- Communicate in the language configured in `communication_language`
- Respect `pulse_levi_verbosity` for level of detail in responses
- The leverage trend section must only be included if `pulse_include_trend_chart == yes`
- The capacity forecast section must only be included if `pulse_include_capacity_forecast == yes`
- The categories table must use the categories defined in `pulse_dev_categories` (not hardcoded categories)
- The Approval-Wait Halts section must only be rendered when `total_approval_wait_count + total_pre_approved_batch_count > 0`
- The BCP Productivity section must only be rendered when at least one story has a `bcp_recorded` block; stories without BCP data render unchanged in all other sections
- Never read or write the BCP baseline file — BCP productivity is computed purely from `pulse_metrics` fields PULSE itself recorded
- When reading `process_health.halts`, accept both shapes (integer count and structured list) and degrade gracefully — never crash on legacy data

---

## Extra Sections

After the standard dashboard sections have been rendered and BEFORE writing the file to `dashboard_file`, append each entry in `{workflow.extra_sections}` to the end of the markdown buffer, in order. Each entry is either a literal markdown block or a `file:{project-root}/...` reference whose contents are inlined verbatim. Sections render in the listed order.

## On Completion

After `dashboard_file` has been written and the confirmation message displayed, execute the `{workflow.on_complete}` scalar if non-empty. Override wins; an empty value means no custom post-completion behavior.
