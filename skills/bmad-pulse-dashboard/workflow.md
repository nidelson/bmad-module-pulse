---
name: bmad-pulse-dashboard
description: 'Generate cumulative PULSE efficiency dashboard'
standalone: true
main_config: '{project-root}/_bmad/config.yaml'
config_section: 'pulse'
---

# Workflow Dashboard

**Goal:** Generate a cumulative dashboard with all PULSE efficiency metrics, cross-sprint trends, and process insights.

**Your Role:** You are Maxine, compiling the complete delivery view of the project.

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

Resolve the PULSE configuration **toml-first** (issue #73):

1. Run `python3 {project-root}/_bmad/scripts/resolve_config.py --project-root {project-root} --key modules.pulse --key core` and read `pulse_*` from the `modules.pulse` table and core keys (`project_name`/`output_folder`, `communication_language`) from `core`.
2. **Per-key fallback** — for any key absent from the resolved toml, read it from the legacy `pulse:` section (module keys) or root (core keys) of `{main_config}`; the yaml is the lowest-priority layer, never authoritative over the toml.
3. **Default last** — if neither has the key, use the `module.yaml` default.

If `resolve_config.py` is unavailable (pre-#2285 install), read `{main_config}` directly as before.

The keys this workflow uses:

- `project_name`, `communication_language`
- `pulse_data_folder`, `pulse_sprint_status_filename`
- `pulse_dashboard_folder`, `pulse_dashboard_format`
- `pulse_include_trend_chart`, `pulse_include_capacity_forecast`
- `pulse_dev_categories`, `pulse_verbosity`
- `pulse_estimation_method` — **which leverage metric leads** (see below)
- `pulse_leverage_threshold_exceptional`, `pulse_leverage_threshold_solid` — bands for the **hours path only**
- `date` as current system-generated datetime

> **Renamed in v0.9.** `pulse_verbosity` and `pulse_coaching_mode` were
> `pulse_levi_verbosity` and `pulse_levi_coaching_mode`. Read the new key
> first and **fall back to the legacy name** when it is absent: an upgrading
> project still has the old key in its config, and a rename without a
> fallback reverts it to the default silently — the setting is still in the
> file, just no longer read, so nothing looks broken.

### The two paths (issue #66)

`pulse_estimation_method` selects which of two leverage metrics is the headline.
Branch on the **configured method**, never on whether a field happens to be
present: field presence answers "did this story record it", not "what does this
project measure", and a project can have a handful of stories carrying a field
it does not use.

| Path                        | Headline leverage                              | Denominator                                    | Under calibration  |
| --------------------------- | ---------------------------------------------- | ---------------------------------------------- | ------------------ |
| `hours` (default), `story_points`, `tshirt` | `leverage_ratio` — **vs PLAN** | `estimated_hours`                              | collapses to ~1.0x |
| `bcp`                       | `leverage_vs_reference` — **vs REFERENCE**     | `bcp_recorded.total × reference rate` (frozen) | stays stable       |

Both paths render a complete dashboard. **Neither warns about what the other
has** — a project on the hours path is not missing anything, and must not be
told it is.

Why the split is not cosmetic: `leverage_ratio` collapses toward 1.0x as the
estimate converges on reality, so on a calibrated basis a `0.9` reads as weak
leverage when it actually means the plan matched. That is why the BCP path
demotes it. But convergence is not free — it is what a canonical ruler buys. On
the hours path nothing recalibrates the estimate, so the ratio does not collapse
and it is the honest headline: the metric PULSE was born with (10h planned, 1h
actual, 10x).

The mirror image applies to predictability. On the BCP path it leads, because a
unit comparable across teams is what makes `estimate_error_pct` a property of
the delivery. On the hours path it may be shown as context but **must not be
presented as a property of the team** — without a comparable unit, estimate
error measures the estimator.

### Paths

- `sprint_status_file` = `{pulse_data_folder}/{pulse_sprint_status_filename}`
- `dashboard_file` = `{pulse_dashboard_folder}/dashboard.md`

---

## EXECUTION

### Step 1: Collect Data

1. Read `{sprint_status_file}` in full
2. Extract all entries from the `pulse_metrics:` section
3. Group by epic — infer epic_id from the numeric prefix of story_id (e.g. `15.3` → epic 15, `4.4.1` → epic 4)
4. **Enumerate the scored backlog** (v0.8 forecast input — read-only): scan the story files in the implementation-artifacts folder for stories that carry a `bcp:` block (with `bcp.total`) but have **no entry** in `pulse_metrics:` (i.e. scored but not yet started). These are the remaining work. Sum `bcp.total` by `category` → `remaining_bcp_by_category` (and `remaining_bcp_total`). If the story files cannot be enumerated, fall back to an optional manual total `pulse_forecast_remaining_bcp` (category-less). PULSE reads story files **read-only** — it never writes them, the BCP baseline, or any estimate. An empty backlog → no forecast.
5. Calculate aggregations:
   - Total stories measured
   - **`predictability_score`** — the v0.6 **hero metric**, rendered as **accuracy** (higher is better; **target 100%**). First compute the median per-story estimate **error** `E` across all stories with `pulse_metrics`: prefer each story's **persisted `estimate_error_pct`** (written by track-done/backfill) when present; for older entries without it, recompute `|actual_hours - estimated_hours| / estimated_hours` (floor `estimated_hours` at 0.01 to avoid divide-by-zero) — the two are identical by definition. Then `predictability_score = max(0, 100 - E)` (clamp at 0 — an estimate off by ≥100% reads as 0% predictable). Always surface the margin of error `E` alongside in parentheses so the raw signal stays visible ("X% (margem de erro Y%)"). Method-agnostic: for BCP stories `E` equals `|bcp_recorded.drift_pct|` (the BCP totals cancel), so it works whether or not the project uses BCP. Compute global and per category. Median (not mean) for the same reason the v0.5 baseline is geometric — resist outliers. Pair it with a **trend arrow** from the first-half vs second-half median error (story-order, chronological proxy): error **falling** → accuracy rising → `↑ converging`; error **rising** → accuracy falling → `↓ diverging`; within tolerance → `→ stable`. (The glyph tracks the accuracy direction — up is good — while the word tracks whether estimates are converging on reality.) Needs `>= 4` stories for a trend; fewer → no arrow.
   - **`estimate_regime`** (v0.6 regime detection) — the basis each `estimated_hours` was derived from, read **read-only** from the story's `estimated_hours_basis` frontmatter field when present (`bcp` / `hours` / `story_points` / `tshirt`), falling back to `{pulse_estimation_method}` when the field is absent. PULSE **never writes** `estimated_hours_basis` and **never derives hours from it** — it only labels what each multiplier is measured *against* (so "5x" reads "vs PLAN (bcp)" not an unqualified number). Report the dominant regime across stories for the leverage context line; annotate a story in the breakdown when its regime differs from the project default. (`estimated_hours_pre_bcp` stays ignored.)
   - **`cohort_drift(category, segment)`** (v0.7 — the shared primitive for estimation-time drift alerts; also consumed by `bmad-pulse-track-start`). For a **cohort**, the **median** of the per-story estimate error `|actual_hours - estimated_hours| / estimated_hours * 100` over the **last `K = 5` completed stories** in that cohort (story-order = chronological proxy; floor `estimated_hours` at 0.01). For BCP stories this equals `|bcp_recorded.drift_pct|`. The **cohort key** is `(category, segment)` when the story carries BCP (segment = `micro`/`story` from the v0.5 median split), else `(category)` alone — fallback documented so non-BCP projects still cohort by category. Returns `(median_abs_drift_pct, n, sample_story_ids)` where `n` is the cohort size considered (≤ K). **Requires `n >= 3`** to be meaningful — fewer → `insufficient` (callers must stay silent, no false alarm). This is read-only over `pulse_metrics`; it never writes or alters any estimate.
   - **`drift_watchlist`** (v0.7) — the forward-looking companion to the track-start alert. For **every** cohort present in `pulse_metrics`, evaluate `cohort_drift`; keep only cohorts with `n >= 3` **and** `median_abs_drift_pct > T = 25%`, sorted by `median_abs_drift_pct` desc. Each entry carries `(cohort_label, median_abs_drift_pct, n, trend)` where `trend` reuses the v0.6 half-split direction (`↓`/`→`/`↑`). Healthy cohorts (≤ T) are omitted. Empty list is the healthy default.
   - **`forecast`** (v0.8 — project hours to price the remaining work; requires BCP baselines). For each category in `remaining_bcp_by_category`, the point forecast is `hours_cat = remaining_bcp_cat × geo_mean(h_per_bcp_actual_cat)` (reusing the v0.5 geometric `h_per_bcp_by_category`). The **90% interval** scales the v0.5 confidence band from `k=1` (~68%) to **`k=1.645`** (~90% of a log-normal): `[hours_cat / GSD_cat^1.645, hours_cat × GSD_cat^1.645]`, where `GSD_cat` is the v0.5 sample geometric SD. Compose the **total** conservatively: `forecast_total = Σ hours_cat`, `forecast_low_90 = Σ low_cat`, `forecast_high_90 = Σ high_cat` — summing the bounds assumes the per-category errors are correlated (widest honest interval; **state this assumption** in the rendered note). A category with `n < 3` (no own baseline) uses the **pooled** `all` baseline and flags the forecast **low-confidence**. Manual-total fallback (`pulse_forecast_remaining_bcp`, no categories) uses the **global** geometric baseline + pooled GSD. Empty backlog → `forecast` is empty (no section). This is read-only: it never writes the backlog, the baseline, or any estimate. **Precision flag:** `pooled_bcp` = Σ remaining BCP across categories that fall back to the pooled baseline (n<3); `pooled_pct = round(pooled_bcp / remaining_bcp_total × 100)`; `forecast_precision` = `baixa` when `pooled_pct > 50`, `média` when `> 20`, else `alta`. The render **leads with the band** and the precision flag, not the point estimate — a thin-baseline forecast has a many-x interval, and headlining the point alone is false precision.
   - Average, minimum, and maximum vs-PLANO leverage (`estimated_hours / actual_hours`) — computed for the predictability math and the anti-Goodhart note, but **no longer rendered as a metric** (it collapses to ~1.0x = it IS the predictability; showing it as "leverage" required a legend).
   - **`avg_leverage_vs_reference`** (issue #65 — **the Alavancagem**, the sellable multiplier) — the mean of `leverage_vs_reference` over the stories that carry it (the field track-done records as `estimated_hours_reference / actual_hours`). Also compute **`avg_leverage_vs_reference_by_category`** (mean per `{pulse_dev_categories}`, plus the per-category best) for the "Alavancagem por Categoria" table; a category with no story carrying `leverage_vs_reference` renders `—`. Compute it **only over stories that have `leverage_vs_reference`**; stories without it (no frozen reference recorded) contribute nothing and the metric is simply absent when no story has one (graceful degradation → fall back to the vs-PLAN context line only). Unlike the vs-PLAN average, this denominator is **frozen** (governed configuration written by `bmad-bcp-score`, never recalibrated) so it **does not collapse** to ~1.0x as the estimate basis calibrates — it is the honest ROI multiplier vs a fixed external benchmark (board/C-Level cadence), **not vs human and not a target**. Also detect a **reference regime break**: the implied reference rate per story is `estimated_hours_reference / bcp_recorded.total` (a read-only division of two recorded telemetry fields — never a BCP→hours conversion, never a baseline read); when it differs across stories (the governed rate changed, e.g. 5h→4h forward-only), label the affected stories so no one compares pre/post naively. **Divide by `bcp_recorded.total`, NOT `bcp_at_start.total`** — the anchor is derived upstream from the story's **final** BCP, so the start snapshot reports a rate that was never in force. When a story is rescored mid-flight the two differ (e.g. start 15, final 13) and the snapshot invents a phantom regime (`65/15 = 4.33` where the real rate is `65/13 = 5.0`), sending readers to audit a governance breach that never happened. Fall back to `bcp_at_start.total` only when `bcp_recorded` is absent; when the two disagree, label the story **rescored** rather than reporting a changed ruler — the divergence is evidence of a rescore, whose trail lives in the story's own `bcp.history` block, not of a new market quote.
   - **`avg_leverage_ratio`** (issue #66 — **the Alavancagem on the hours path**) — the mean of `leverage_ratio` (`estimated_hours / actual_hours`, recorded by track-done) over all stories with `pulse_metrics`. Also compute **`avg_leverage_ratio_by_category`** (mean per `{pulse_dev_categories}`, plus the per-category best), the same shape as its vs-REFERENCE sibling so the rendering code path is one. Compute it on **every** path — it is persisted on both and stays available in the detail view — but render it as the headline only when `pulse_estimation_method` is not `bcp`. Subject to the same degenerate-effort guardrail below: the denominator is `actual_hours` here too, so a two-minute patch produces the same division-by-almost-zero artifact. Band it with `pulse_leverage_threshold_exceptional` / `pulse_leverage_threshold_solid`, which apply **only here** — a band calibrated for a human-judgement denominator is meaningless against a frozen reference rate, and applying it on the BCP path is how a converged `0.9` gets labelled "weak".
   - **GLOBAL degenerate-effort guardrail (applies to EVERY Alavancagem-family aggregate — `avg_leverage_ratio` and its per-category means/best, `avg_leverage_vs_reference`, the per-category means/best, `total_reference`/`actual_with_reference`/`savings_vs_reference`):** exclude any story with `actual_hours < 0.1h` (≈6 min — near-zero mechanical work, e.g. a dependency bump). Alavancagem is `reference / actual`; a near-zero denominator makes a trivial 2-minute patch read as 500x–625x, which would inflate the average and produce a fake "best" that is just division-by-almost-zero, not delivery leverage. Excluded stories are **still shown** in the per-story detail with a `⚠` marker (transparent, not deleted) and **still counted** everywhere else (first-pass, BCP productivity, predictability). Report how many were excluded (`{n_degen} esforço-zero excluídas`). This floor is the same denominator-hygiene the v0.5 engine applies elsewhere; it is NOT cherry-picking — it removes a known measurement artifact, consistently, and says so.
   - **Hours block** — `total_estimated` = Σ `estimated_hours` (the **BCP plan**, NOT the human estimate — never label it "humano"; the human gut lives in `estimated_hours_pre_bcp`, which the dashboard does not sum); `total_actual` = Σ `actual_hours`. Do **not** show `total_estimated − total_actual` as "savings": that is the predictability gap (it shrinks to ~0 as the team calibrates), not money saved. The honest savings is **vs the market quote**: `total_reference` = Σ `estimated_hours_reference` over the `n_with_reference` stories that carry it, `actual_with_reference` = Σ `actual_hours` over **those same** `n_with_reference` stories (apples-to-apples — NOT `total_actual`, which spans all stories), and `savings_vs_reference` = `total_reference − actual_with_reference`. Both reference-based figures are **partial** (only `n_with_reference` of `total` stories have a frozen reference) — always render the explicit `({n_with_reference}/{total} stories)` caveat, and render the savings as the **traceable subtraction** `{savings} = {total_reference} − {actual_with_reference}` so no reader subtracts the all-stories `total_actual` from the partial `total_reference` and gets a wrong figure.
   - First-pass rate
   - Alavancagem by category (use `{pulse_dev_categories}`) — vs REFERÊNCIA on the `bcp` path, vs PLANO on the others (#66)
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
     - `segment_split` — the **median** of `bcp_recorded.total` over **all** `bcp_stories` (one global value). Computed **only when `bcp_stories` is non-empty** — never evaluate `median([])`. A story is `micro` when `bcp_recorded.total < segment_split`, else `story`. This split is data-driven: the dashboard assumes nothing about the BCP point scale and never reads the BCP baseline to find out. (Since v0.5.0.)
     - **GLOBAL effort-floor guardrail (h/BCP family):** the typical-cost aggregations below — `h_per_bcp_by_category`, `h_per_bcp_estimated_by_category`, `h_per_bcp_band`, `drift_trend`, and `h_per_bcp_convergence` — are computed over `bcp_stories` **excluding** any story with `actual_hours < 0.1h` (the same near-zero-effort floor as the Alavancagem guardrail). A 2-minute dependency bump has a real-but-unrepresentative `h_per_bcp_actual` (~0.01) that drags the category baseline down, widens the band, and (because such stories cluster late) fakes a `diverging` convergence reading. Excluding them makes the dashboard's observed h/BCP align with the calibrated baseline `bmad-bcp-recalibrate` maintains. **Raw counts stay raw:** `bcp_stories` count ("Stories com BCP"), `total_bcp`, `segment_split`, `bcp_throughput`, and `top_bcp_stories` include **all** BCP stories — PULSE só reporta. Surface how many were excluded from the typical-cost view (`{n_degen_bcp}`).
     - `h_per_bcp_by_category` — for each `(category, segment)` with `segment ∈ {micro, story}`, the **geometric mean** of `bcp_recorded.h_per_bcp_actual` over the eligible (non-degenerate) `bcp_stories` in that category and segment: `exp(mean(ln(h_per_bcp_actual)))`, equivalently `(∏ h_per_bcp_actual)^(1/n)`. h/BCP values are multiplicative ratios, so the geometric mean is the unbiased central tendency and resists outliers (a single 10x story does not drag the baseline the way an arithmetic mean would). Round to 2 decimals. Also compute a per-category **pooled** baseline (`all` segment — geometric mean over every `bcp_story` in the category, ignoring the split) for the continuity row. **Thin-segment fallback:** a `(category, segment)` pair with `n < 3` is not reported on its own; those stories still count in the category's pooled `all` baseline. `n == 0` → pair omitted.
     - `h_per_bcp_estimated_by_category` — same **geometric mean**, segmented the same way (per `(category, segment)` plus pooled `all`), over `bcp_recorded.h_per_bcp_estimated` (for the drift comparison).
     - `h_per_bcp_band` — for each baseline (every `(category, segment)` and each pooled `all`), a **confidence band** around the geometric mean of `bcp_recorded.h_per_bcp_actual`, so the baseline reads as a range, not false precision. Compute the **sample geometric standard deviation** `GSD = exp(sample_std(ln(h_per_bcp_actual)))`, where `sample_std` uses the `n-1` (sample, not population) denominator — we estimate, not enumerate. The band is `[geo_mean / GSD, geo_mean * GSD]` (multiplier `k = 1`, ≈ 68% of a log-normal sample — a **typical range**, not a 95% CI; with PULSE's small `n` a wider band would be unactionable). **Require `n >= 3` to emit a band**; for `n < 3` emit the point with an explicit `(n=2)` / `(n=1)` marker and no interval (a GSD from 2 samples has 1 degree of freedom — one outlier distorts it). Carry `n` alongside every baseline so thin samples are visible. (Since v0.5.0.)
     - `drift_trend` — ordered list of `(story_id, bcp_recorded.drift_pct)` for `bcp_stories` (story-order = chronological proxy)
     - `h_per_bcp_convergence` — the v0.6 **self-referential drift signal**: is the h/BCP baseline *stabilizing* over time? Split `drift_trend` in story-order into a first half and a second half and compare the **median `|drift_pct|`** of each: second-half median meaningfully **lower** → `converging` (estimates closing on reality); meaningfully **higher** → `diverging`; within a small tolerance → `stable`. The confidence band (`h_per_bcp_band`) narrowing across the same split is corroborating evidence (report it alongside). **Requires `>= 4` `bcp_stories`** for a reading — fewer → `insufficient data (thin sample)`, no label. This consumes the v0.5 drift/band data; it does not recompute raw ratios.
     - `top_bcp_stories` — `bcp_stories` sorted by `bcp_recorded.total` desc, top 5 (proxy for "elements driving BCP" — PULSE does not read `bcp.breakdown`, so it ranks by total points per story)

> **Forecast passive invariant (v0.8, do not regress).** The project forecast and the digest are **read-only and passive**. PULSE reads the scored backlog (story files) and `pulse_metrics` to compute `BCP × h/BCP ± CI(90%)`, but it **never writes** the story frontmatter, the BCP baseline, the backlog, or any estimate — pricing is informational, it does not drive estimation (owned by BMAD, or by `bmad-bcp-score` when scoring is enabled). The digest is **generated only**; this skill never calls Slack/Linear or any external API itself — delivery is the user's `on_complete`. If a future edit makes the forecast mutate an estimate/baseline or call an external API directly, that breaks the contract (locked by `tests/test_forecast.py`).

### Step 2: Generate Dashboard

Generate the dashboard in the format(s) defined in `pulse_dashboard_format` (`markdown`, `yaml`, or `both`).

For `markdown` format (default), write `{dashboard_file}` with the following structure:

```markdown
# ⚡ PULSE — O Pulso de Entrega do Time

> Sinais de previsibilidade e alavancagem de entrega para times BMAD<br>
> Gerado em: {date} | Projeto: {project_name}

---

## 🏆 Estatísticas Gerais

| Métrica                 | Valor                                |
| ----------------------- | ------------------------------------ |
| Stories medidas         | {total}                              |
| **Previsibilidade**     | **{predictability_score}% (mediana) {trend_arrow}** — margem de erro {predictability_error}% |
| Horas planejadas (BCP)  | {total_estimated}h                   |
| Horas reais (IA)        | {total_actual}h                      |
| Taxa de first-pass      | {rate}%                              |
<!-- BRANCH ON pulse_estimation_method (issue #66). Exactly ONE Alavancagem row renders; the two are alternatives, never both.
     - method != "bcp"  → the vs-PLANO row below. No Cotação/Economia rows (there is no frozen reference on this path) and NO warning about their absence — this path is complete, not degraded.
     - method == "bcp"  → the vs-REFERÊNCIA row plus Cotação + Economia, still gated on avg_leverage_vs_reference existing (a BCP project whose stories predate the anchor has nothing to report yet). Those hours rows carry an explicit ({n_with_reference}/{total} stories) caveat — never sum a partial-coverage figure without saying how partial. -->
| **Alavancagem (vs PLANO)** | {avg_leverage_ratio}x — entrega vs o que foi planejado{if avg_leverage_ratio >= pulse_leverage_threshold_exceptional → ` (excepcional)`}{else if avg_leverage_ratio >= pulse_leverage_threshold_solid → ` (sólida)`} (n={total}{if n_degen > 0 → `, {n_degen} esforço-zero excluídas`}) |
| **Alavancagem (vs REFERÊNCIA)** | {avg_leverage_vs_reference}x — o número que vende: entrega vs cotação de mercado (frozen, não colapsa; n={n_with_reference}{if n_degen > 0 → `, {n_degen} esforço-zero excluídas`}) |
| Cotação de mercado      | {total_reference}h ({n_with_reference}/{total} stories) — o que o mercado orçaria |
| **Economia vs cotação** | **{savings_vs_reference}h** = {total_reference}h − {actual_with_reference}h reais (das mesmas {n_with_reference} stories) |
<!-- END CONDITIONAL reference_leverage -->
<!-- The vs-PLANO ratio (estimated_hours / actual_hours) is NOT shown as a metric row: it collapses to ~1.0x as the basis calibrates, which IS the predictability signal (see the hero row and the anti-Goodhart note). Showing it as "leverage" needed a legend ("1.0 = good"); that is the smell this removal fixes. Alavancagem here means the durable, sellable multiplier vs a frozen market-quote benchmark. -->

> **Alavancagem = o número que vende (vs REFERÊNCIA frozen, issue #65).** `Alavancagem = estimated_hours_reference / actual_hours`, onde `estimated_hours_reference` é a âncora frozen escrita por `bmad-bcp-score` (`bcp.total × reference_h_per_bcp`, a **taxa de cotação de mercado**). É o `5x / 10x / 20x` que o C-Level apresenta: *"entregamos em 1h o que o mercado **orça** em 20h"*. O denominador é **congelado** (governado por configuração, nunca recalibrado), então **não colapsa** — ao contrário da razão `estimated_hours / actual_hours` (vs PLANO), que colapsa pra ~1.0x ao calibrar e por isso **não é mostrada como alavancagem** (é a previsibilidade em forma de razão). Honestidade: o multiplicador é **vs a taxa de cotação**, nunca "vs a velocidade real dos concorrentes" (isso não medimos) e nunca uma meta a perseguir. Sem `estimated_hours_reference` (BCP ausente/antigo), a story não entra na alavancagem. Mudança governada da reference rate (5h→4h, forward-only) é **rotulada como quebra de regime** — ninguém compara pré/pós ingenuamente. **Define-once:** o qualificador "(vs REFERÊNCIA)" aparece só aqui (na linha de Estatísticas Gerais + esta legenda); nas tabelas "Alavancagem por Categoria" e "Detalhamento por Story" o rótulo é só **"Alavancagem"** — encurta a repetição, e o leitor já viu a definição. Acrescente uma frase à legenda: "Nas tabelas, 'Alavancagem' = vs REFERÊNCIA."

> **Previsibilidade é o número-herói** — **acurácia das estimativas, maior = melhor, meta 100%** (`100 − margem de erro`, com piso em 0%). 100% = entregamos exatamente o que planejamos; `↑` = subindo (estimativas convergindo pra realidade). A margem de erro crua aparece entre parênteses pra transparência. **Os três conceitos fixos:** *Previsibilidade* (meta 100%) e *Margem de erro* (meta 0% quando o time AI calibra) são duas faces da mesma moeda — acurácia; *Alavancagem* (vs REFERÊNCIA) é o multiplicador ortogonal que vende. O regime da estimativa (`estimated_hours_basis`, read-only — `vs PLANO ({dominant_regime})`) rotula contra que base a previsibilidade é medida; uma base não-calibrada infla a alavancagem-vs-plano, por isso essa razão não vira métrica de exibição (veja o invariante anti-Goodhart abaixo).

> **Invariante anti-Goodhart — leverage não é meta.** `leverage = estimated_hours / actual_hours`. Quando a base de estimativa está calibrada (estimativas derivadas de um baseline que casa com a realidade), essa razão colapsa pra **~1.0x por construção** — então um multiplicador *alto* sinaliza base de estimativa inflada ou não-calibrada, **não** velocidade, e uma *meta de leverage* literalmente premiaria nunca calibrar. O sinal durável é a **previsibilidade**: o drift de h/BCP por categoria convergindo a zero (as estimativas casam com os resultados?). Por isso essa razão "vs PLANO" **não é mostrada como alavancagem** — ela é a previsibilidade. A **Alavancagem** exibida usa um denominador **frozen** (a cotação de mercado), que não colapsa; lê-se "vs cotação", nunca "vs humano" e nunca como meta. (v0.5 travou esse invariante; v0.6 agiu sobre ele — a previsibilidade lidera o dashboard, a celebração do track-done dispara por acurácia, e a coluna de alavancagem passou a ser vs REFERÊNCIA, não vs PLANO.)

<!-- CONDITIONAL: include only if pulse_include_trend_chart == yes -->
## 📈 Tendência de Previsibilidade por Epic

Sparkline: cada █ = 5% de previsibilidade, máximo 20 caracteres (100%).

{for each epic with data, numeric epics first then the X bucket}
Epic {N}: {sparkline} {previsibilidade}% ({count} stories{if N == X → ` transversais`}{if count < 3 → ` · amostra fina`})
{end}

Exemplo:
Epic 14: ██████████████░░░░░░ 72% (4 stories)
Epic  X: ███░░░░░░░░░░░░░░░░░ 16% (6 stories transversais)

> Previsibilidade por epic = `max(0, 100 − mediana(estimate_error_pct))` das stories do epic — **maior = melhor** (qual epic entrega previsível). Epics com `< 3` stories são marcados **amostra fina** (ponto solto, não tendência). Stories sem prefixo numérico de epic (security patches, setup, infra transversal) viram o bucket **`Epic X`** com `transversais` no contador — rótulo curto pra não quebrar o alinhamento do sparkline.
<!-- END CONDITIONAL trend_chart -->

## 📊 Alavancagem por Categoria

> Multiplicador por categoria, **após o guardrail de esforço-zero** — `leverage_vs_reference` (vs cotação de mercado, frozen) na trilha `bcp`, `leverage_ratio` (vs plano) nas demais (stories com `actual < 0.1h` fora da média e do "melhor"). Categorias sem nenhuma story elegível mostram `—`. Categorias com `< 3` stories elegíveis são marcadas **amostra fina** (ponto solto, não tendência).

| Categoria | Alavancagem média | Stories | Melhor |
| --------- | ----------------- | ------- | ------ |
{for each category in pulse_dev_categories}
| {category} | {alav_ref}x | {n}{if n < 3 → ` · amostra fina`} | {best_ref}x |
{end}

<!-- CONDITIONAL: include only if pulse_include_capacity_forecast == yes AND forecast is non-empty (the scored backlog has remaining BCP) -->
## 🔮 Previsão de Projeto

> Horas pra concluir o backlog pontuado restante ({remaining_bcp_total} BCP não-iniciado), por `BCP × h/BCP`, com IC de 90%. Pra times que faturam por hora.

**Faixa: [{forecast_low_90}–{forecast_high_90}]h** (IC 90%) · ponto ~{forecast_total}h · ⚠ **precisão {forecast_precision}** — {pooled_bcp}/{remaining_bcp_total} BCP ({pooled_pct}%) sem baseline próprio (pooled)

<!-- Lead with the BAND, not the point. The point (~{forecast_total}h) looks precise but the 90% interval can be many-x wide when baselines are thin. `forecast_precision` = `baixa` if `pooled_pct > 50`, `média` if `> 20`, else `alta`, where `pooled_pct` = share of remaining BCP whose category has no own baseline (n<3, using the pooled `all` factor). Never headline a single point estimate without the band + coverage flag — that is false precision the board would over-trust. -->

| Categoria | BCP restante | Previsão (IC 90%) | Confiança |
| --------- | ------------ | ----------------- | --------- |
{for each category in remaining_bcp_by_category}
| {category} | {remaining_bcp_cat} | {hours_cat}h [{low_cat}–{high_cat}]h | {if n_cat >= 3}ok{else}baixa (pooled){end} |
{end}

> Faixa **conservadora**: o IC do total soma os limites por categoria (assume erros correlacionados — a faixa mais larga e honesta). Categorias sem baseline próprio (n<3) usam o baseline pooled e entram como **baixa confiança**. O forecast é read-only — não muda estimativa nem baseline.
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

> Telemetria de Business Complexity Points. As horas foram derivadas pela skill
> `bmad-bcp-score`; este dashboard só reporta a produtividade observada e nunca
> é dono do baseline BCP.

| Métrica               | Valor          |
| --------------------- | -------------- |
| Stories com BCP       | {len(bcp_stories)} |
| Total BCP pontuado    | {total_bcp}    |

**Throughput (BCP por epic):**

{for each epic in bcp_throughput}
Epic {N}: {bcp} BCP ({count} stories)
{end}

**h/BCP real por categoria e segmento de tamanho:**

> **Guardrail de esforço-zero:** {n_degen_bcp} stories com `actual < 0.1h` ficam **fora do custo típico** (h/BCP, faixa, drift, convergência) — alinha com o baseline do BCP. As contagens cruas (Stories com BCP, Total BCP) incluem todas.
>
> Stories divididas na mediana de BCP observada (`segment_split` = {segment_split} BCP): abaixo = `micro`, igual/acima = `story`. A linha `all` agrupa as duas, pra continuidade com dashboards pré-0.5. Um segmento (ou a categoria) com menos de 3 stories é marcado **amostra fina** (fino demais pra confiar).
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

> Nota: o dashboard ranqueia pelo total de BCP por story. O detalhamento por
> elemento (`bcp.breakdown`) é de `bmad-bcp-score` e intencionalmente não é lido
> aqui — a análise por elemento é da skill que pontua, não da que reporta.
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

> **Data-triggered, não free-form.** Cada insight tem um **gatilho** (condição nos dados) e **cita o número** que o disparou. Não escreva opinião solta nem elogio sem dado. Emita só os que disparam; ordem: alertas (⚠) antes de positivos (✅) antes de informativos (ℹ️). Se nenhum disparar, escreva uma linha "✅ Sem alertas — processo saudável.".

| Gatilho | Insight |
| --- | --- |
| `predictability_score < 70` **ou** trend `piorando` | ⚠ **Previsibilidade {score}% ({trend})** — {N} stories atrasaram (real > plano): {lista das piores por erro}. Revisar a base de estimativa dessas. |
| `first_pass_rate == 100` | ✅ **First-pass 100% ({total}/{total})** — qualidade impecável, zero retrabalho. |
| `pooled_pct > 50` (forecast) | ⚠ **Forecast baixa precisão** — {pooled_pct}% do backlog sem baseline próprio ({categorias pooled}). Calibre samples antes de cotar cliente. |
| `n_degen > 0` | ℹ️ **{n_degen} stories de esforço-zero** (`< 0.1h`, patches mecânicos) fora das médias de alavancagem e h/BCP — considere uma trilha de medição separada. |
| `h_per_bcp_convergence == diverging` | ⚠ **Baseline h/BCP diverging** ({1ª}% → {2ª}%) — estimativas se afastando; calibrar mais samples por categoria. |
| story não-BCP com `estimated_hours` destoante (≫ mediana) | ℹ️ **{story} não-pontuada via BCP** (plano {X}h vs {real}h) — rescorar pra consistência. |

Cada linha acima é renderizada **apenas se o gatilho for verdade**, com os placeholders preenchidos pelos valores reais. Mantém a seção grounded e consistente entre execuções — o oposto de "o LLM inventa um parágrafo".

## 📋 Detalhamento por Story

| Story | Plano | Real | Previsibilidade | Alavancagem | Qualidade | Categoria |
| ----- | ----- | ---- | --------------- | ----------- | --------- | --------- |

{for each story sorted by previsibilidade DESCENDING (best first — a gradient: scan down to where it degrades. The action items are already named in the Insights section above, so the detail does NOT need to lead with the worst — it reads as a narrative top→bottom.)}
| {id} | {est}h | {actual}h | {max(0, 100 - estimate_error_pct)}%{if actual_hours > est → ` ↓`}{if actual_hours < est → ` ↑`} | {leverage_vs_reference}x{if actual_hours < 0.1 → ` ⚠`}{if no estimated_hours_reference → `—`} | {quality} | {cat} |
{end}

> Ordenado por **previsibilidade (melhor primeiro)** — desça até onde degrada; daí pra baixo precisa melhorar. Os action items já estão nos **Insights** acima, então a lista lê-se como gradiente, não precisa liderar com o pior. **`Plano`** = `estimated_hours` (o plano de registro: BCP-derivado, ou a estimativa da Amelia quando não há BCP), nunca um número humano cru rotulado errado. **↓** = atrasou (real > plano, **risco de prazo**) · **↑** = adiantou (real < plano, **folga**) — a previsibilidade sozinha esconde a direção; um `0% ↓` é perigo, um `12% ↑` é só super-estimativa. **⚠** na Alavancagem = story de esforço-zero (`actual < 0.1h`) — mostrada mas **fora das médias** (distorce por divisão por quase-zero). `—` = story sem `estimated_hours_reference`. ⏪ = track-start retroativo.

> **Previsibilidade** por story = `max(0, 100 − estimate_error_pct)` — acurácia da estimativa, **maior = melhor, meta 100%**. O campo persistido `estimate_error_pct` é a fonte.
>
> **Alavancagem** depende do `pulse_estimation_method` (#66) e é a mesma coluna nos dois casos:
>
> - **`bcp`** → `leverage_vs_reference` (entrega vs cotação de mercado, o número que vende); mostra `—` quando a story não tem `estimated_hours_reference`. A razão vs PLANO **não aparece aqui**: com base calibrada ela colapsa pra ~1.0x e é justamente a previsibilidade, não uma alavancagem — mostrá-la como "leverage" exigiria legenda, e esse é o cheiro que esta coluna corrige.
> - **demais métodos** → `leverage_ratio` (`estimated_hours / actual_hours`, entrega vs plano). Aqui ela **não** colapsa, porque nada recalibra o denominador — é a alavancagem original do PULSE e é honesta como manchete.
>
> Nesta trilha, previsibilidade é contexto, não atributo do time: sem unidade comparável entre times, erro de estimativa mede quem estimou.

---

_PULSE — Contra fatos, não há argumentos._
_Dashboard gerado automaticamente pelo módulo PULSE._
```

For `yaml` format, generate `{pulse_dashboard_folder}/dashboard.yaml` with the same data structured as YAML.

For `both` format, generate both files.

### Step 2b: Generate digest artifact (v0.8 — thin delivery)

Also write a concise digest to `{pulse_dashboard_folder}/digest.md` — a short, postable summary (PT-BR, jargon kept) a teammate can read at a glance or that `on_complete` can ship to Slack/Linear. PULSE only **generates** the artifact; it **never calls any external API itself** (see On Completion). Keep it to the essentials:

```markdown
⚡ PULSE digest — {project_name} — {date}
• Previsibilidade: {predictability_score}% (mediana) {trend_arrow} — margem de erro {predictability_error}%
• Previsão de Projeto: {forecast_total}h [{forecast_low_90}–{forecast_high_90}]h (IC 90%) pra {remaining_bcp_total} BCP restante
• Coortes em risco: {if drift_watchlist non-empty}{drift_watchlist count} (>{T}% drift){else}nenhuma — estimativas no rumo{end}
```

Omit the forecast line when the backlog is empty. The digest is opt-in companion data — it does not replace `dashboard.md`.

### Step 3: Display Summary

Display in the terminal the General Statistics block + (if `pulse_include_trend_chart == yes`) Trend + a Process Insight.
The detail level of the summary must respect `pulse_verbosity`.

### Step 4: Report Location

```text
💓 Maxine: Dashboard salvo em {dashboard_file}
   {total} stories medidas | Previsibilidade: {predictability_score}% | Alavancagem: {avg_leverage_vs_reference if method == "bcp" else avg_leverage_ratio}x (vs {"REFERÊNCIA" if method == "bcp" else "PLANO"})
```

---

## BEHAVIOR RESTRICTIONS

- If no data exists in the `pulse_metrics:` section, inform and suggest running track-start/track-done first
- Create the `{pulse_dashboard_folder}` directory if it does not exist
- Always overwrite dashboard.md (it is the most recent version)
- The rendered dashboard template above is **PT-BR by default** (section titles, table headers, labels, messages, notes). Keep all technical jargon in English (`h/BCP`, `BCP`, `leverage`, `drift`, `micro`/`story`, field names) and every `{placeholder}` verbatim. If `communication_language` is set to another language, localize the rendered labels/messages accordingly (jargon and placeholders still unchanged); the internal aggregation logic in Step 1 stays English regardless.
- Communicate in the language configured in `communication_language`
- Respect `pulse_verbosity` for level of detail in responses
- The "Tendência de Previsibilidade por Epic" trend section must only be included if `pulse_include_trend_chart == yes`
- The project forecast section (`🔮 Previsão de Projeto`) must only be included if `pulse_include_capacity_forecast == yes` AND the scored backlog has remaining BCP (an empty backlog → no section). Since v0.8 it forecasts `BCP × h/BCP ± CI(90%)`, replacing the pre-0.8 leverage-extrapolation capacity forecast.
- The categories table must use the categories defined in `pulse_dev_categories` (not hardcoded categories)
- The Approval-Wait Halts section must only be rendered when `total_approval_wait_count + total_pre_approved_batch_count > 0`
- **Exactly one Alavancagem row renders, selected by `pulse_estimation_method` (#66).** On `bcp`, the "**Alavancagem (vs REFERÊNCIA)**" row, and only when `avg_leverage_vs_reference` exists (≥1 story has `leverage_vs_reference`) — with no such story, omit it: there is no alavancagem to report yet. On every other method, the "**Alavancagem (vs PLANO)**" row. Never render both, and never render the vs-PLANO ratio as a headline on the `bcp` path: with a calibrated basis it *is* the predictability, and presenting it as leverage is the mislabel this branch exists to fix.
- **A path is never described as missing what the other has.** Do not render the Cotação/Economia rows, or a note about their absence, outside the `bcp` path. The hours path is the default and complete configuration, not a degraded one.
- `pulse_leverage_threshold_exceptional` / `pulse_leverage_threshold_solid` band the **vs-PLANO** row only. Against a frozen reference they mean nothing — applying them there is how a converged `0.9` gets labelled "weak leverage" when it means the plan matched reality.
- Never write `estimated_hours_reference` — it is read-only input, derived upstream by the BCP scoring skills.
- Alavancagem is **reported, never a target**. On the `bcp` path predictability stays the hero and Alavancagem must not be promoted above it. On the other paths predictability may appear as context but must **not** be framed as a property of the team.
- The BCP Productivity section must only be rendered when at least one story has a `bcp_recorded` block; stories without BCP data render unchanged in all other sections
- Never read or write the BCP baseline file — BCP productivity is computed purely from `pulse_metrics` fields PULSE itself recorded
- The v0.8 digest (`digest.md`) is **generated only** — PULSE never calls Slack/Linear or any external API directly; delivery is delegated to the user-configured `on_complete` command (thin, local-first)
- When reading `process_health.halts`, accept both shapes (integer count and structured list) and degrade gracefully — never crash on legacy data

---

## Extra Sections

After the standard dashboard sections have been rendered and BEFORE writing the file to `dashboard_file`, append each entry in `{workflow.extra_sections}` to the end of the markdown buffer, in order. Each entry is either a literal markdown block or a `file:{project-root}/...` reference whose contents are inlined verbatim. Sections render in the listed order.

## On Completion

After `dashboard_file` (and, since v0.8, `digest.md`) has been written and the confirmation message displayed, execute the `{workflow.on_complete}` scalar if non-empty. Override wins; an empty value means no custom post-completion behavior.

**Posting the digest (thin delivery, v0.8).** PULSE **never calls Slack/Linear (or any external) APIs itself** — it stays local-first and passive. To deliver the digest, the user sets `on_complete` to a command that posts the generated `digest.md`, e.g. a Slack incoming webhook:

```bash
on_complete = "curl -s -X POST -H 'Content-type: application/json' --data \"{\\\"text\\\": \\\"$(cat {pulse_dashboard_folder}/digest.md)\\\"}\" $PULSE_SLACK_WEBHOOK"
```

The webhook URL / token lives in the user's environment, never in PULSE. Linear or any other channel works the same way — the channel and credentials are the user's; the digest is PULSE's. PULSE generates the artifact and hands off; it does not own the integration.
