# PULSE

[![BMAD Module](https://img.shields.io/badge/BMAD-Module-blue)](https://docs.bmad-method.org/)
[![BMAD Version](https://img.shields.io/badge/BMAD-%3E%3D6.4.0-blue)](https://docs.bmad-method.org/)
[![Tests](https://github.com/nidelson/bmad-module-pulse/actions/workflows/test.yaml/badge.svg)](https://github.com/nidelson/bmad-module-pulse/actions/workflows/test.yaml)
[![GitHub release](https://img.shields.io/github/v/release/nidelson/bmad-module-pulse)](https://github.com/nidelson/bmad-module-pulse/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/nidelson/bmad-module-pulse?style=social)](https://github.com/nidelson/bmad-module-pulse/stargazers)

> **Delivery-predictability signals for BMAD teams.**

**Don't just prove you're 10x faster — prove your plan was right, and miss by less sprint after sprint.**

🌐 [Português 🇧🇷](README.md)

> *Sample output of `/bmad-pulse-dashboard` — based on a real BMAD project:*

### 🏆 General Statistics

| Metric                | Value     |
| --------------------- | --------- |
| Stories measured      | 12        |
| Avg AI Leverage       | **6.9x**  |
| Human estimated hours | 152h      |
| Actual AI hours       | 22h       |
| Hours saved           | **130h**  |
| First-pass rate       | 83%       |

> **Read this honestly:** the **6.9x** is the *scaffolding* number — it's large only while your estimates still use an uncalibrated baseline. Calibrate, and leverage collapses toward **1.0x by construction**. That collapse is the product working, not failing. The durable signal underneath is **predictability** — are your estimates converging on reality? The dashboard is being inverted to lead with that (see the [Roadmap](#roadmap)).

### 📈 Leverage Trend by Epic

```text
Epic  1: ████████░░░░░░░░░░░░  4.2x (3 stories)
Epic  4: ██████████░░░░░░░░░░  5.1x (2 stories)
Epic  5: ████████████████░░░░  7.8x (3 stories)
Epic 14: ██████████████░░░░░░  6.9x (3 stories)
Epic 15: ████████████████████  8.4x (1 story)
```

📊 **[View full dashboard →](examples/dashboards/mature-bmad-team.md)** *(category breakdown, capacity forecast, Maxine's insights, story-by-story breakdown)*

Browse [more dashboard scenarios](examples/dashboards/) for different team sizes and adoption stages.

---

## The Problem

At some point, every developer who works with AI has lived this moment: looked at the clock, realized they did in two hours what they estimated for two days, and didn't quite know what to do with that feeling.

PULSE was built for that moment. To turn that feeling into a number. That number into a story. And that story into evidence.

You adopted BMAD. You wired up Claude Code or Cursor. Your team feels faster — but when leadership asks **"how much faster?"**, you're guessing.

Every AI productivity tool measures **lines of code**, **commits**, or **token spend**. None of those answer the question your CTO is actually asking: *are we shipping more user-visible value per engineering hour?*

There are two kinds of teams in 2026: **the team that uses AI, and the team that has AI using AI.** The difference doesn't show up in lines of code. It shows up in stories shipped per estimated hour.

PULSE measures that!

---

## What you get

- **A defensible predictability number for your SDLC** — how close your estimates land to reality, sprint over sprint, ready for your stakeholder deck. (Leverage too — but as the first-month signal, not the headline.)
- **Early warning on stalled work** — capacity forecasts and halt alerts before a sprint slips.
- **A coach, not just a dashboard** — Maxine (PULSE's agent) reads your signals and tells you *where* the leverage is leaking.

---

## Why PULSE

**The market measures lines. PULSE measures stories.**

It's the difference between **scale weight and body fat percentage**. LOC tells you something is moving. Leverage tells you whether it's muscle or bloat.

A story is the smallest unit of value your users feel. Tracking AI leverage at the story level — estimated hours vs. real hours, planning to done — gives you the only metric that survives a board meeting.

PULSE is also the **first BMAD-native observability plugin** on the marketplace. There is no incumbent. There is no second place yet. If you're running BMAD and you want SDLC analytics that speak BMAD's vocabulary (epics, stories, agents, workflows), this is the tool.

> Stories, not lines.
> Outcomes, not output.
> Predictability, not bragging.

---

## What PULSE measures

| Metric | What it is | Why it matters |
|---|---|---|
| **AI Leverage Ratio** | `estimated_hours / actual_hours` | First-month signal; collapses toward ~1.0x as you calibrate (that's healthy) |
| **First-Pass Rate** | % of stories approved without revision | Quality of the development process |
| **Process Health** | Adherence to the BMAD workflow | Halts, underused skills, drift |

---

## Quick start

```bash
npx bmad-method install --custom-source https://github.com/nidelson/bmad-module-pulse
```

> **Production: pin a released version.** The command above tracks
> `main` (the manifest records `version: main`), so every re-run pulls
> whatever has since landed on `main` — non-deterministic across a team
> and across CI. For production projects, pin an explicit released tag:
>
> ```bash
> npx bmad-method install \
>   --custom-source https://github.com/nidelson/bmad-module-pulse \
>   --version v0.4.5
> ```
>
> Bump the tag deliberately when you want a new version. Pick one from
> the [releases](https://github.com/nidelson/bmad-module-pulse/releases).
> Upgrading over an existing install self-heals automatically — see
> [MIGRATION.md](docs/MIGRATION.md#upgrading-over-an-existing-install--automatic-self-heal).

Then in your BMAD project:

```bash
/bmad-pulse-setup            # Configure once
/bmad-pulse-track-start      # When you start a story
/bmad-pulse-track-done       # When you finish — leverage is computed
/bmad-pulse-track-backfill   # Forgot to track? Recover HI/HF after the fact
/bmad-pulse-dashboard        # See the cumulative trend
```

PULSE attaches to your existing BMAD story files — no schema migrations, no separate database.

---

## Included Skills

> ⚠ **Upgrading from v0.3.x?** Slash commands were renamed from `pulse-*` to `bmad-pulse-*` in v0.4.0. Read **[MIGRATION.md](docs/MIGRATION.md)** before upgrading — v0.4.0 has BREAKING CHANGES.

| Skill | Command | Function |
|---|---|---|
| `bmad-pulse-setup` | `/bmad-pulse-setup` | Configure the module in your project |
| `bmad-pulse-track-start` | `/bmad-pulse-track-start [story_id]` | Register story start |
| `bmad-pulse-track-done` | `/bmad-pulse-track-done [story_id]` | Register completion + calculate metrics |
| `bmad-pulse-track-backfill` | `/bmad-pulse-track-backfill [story_id] --hi <ts> --hf <ts>` | Retroactively record HI/HF + metrics for a story tracked too late |
| `bmad-pulse-dashboard` | `/bmad-pulse-dashboard` | Generate cumulative dashboard |

---

## Maxine — your coach agent

**Maxine** is PULSE's Delivery Predictability Analyst. She reads your metrics and tells you, in plain English, where the squad is losing time: estimation drift, BMAD steps being skipped, agents being misused. She leads with whichever number the current configuration can honestly defend — leverage while estimates are in hours, predictability once a canonical ruler makes them comparable across teams.

She measures the system, never the person. And she never gives you a number without the band around it.

---

## How it works

PULSE instruments three points in the BMAD story lifecycle:

1. **Story start** — captures estimated hours from the story file.
2. **Story done** — captures real hours and computes the leverage ratio.
3. **Sprint rollup** — aggregates leverage across the active sprint and projects capacity.

### Leverage thresholds

| Ratio | Signal | What it means |
|-------|--------|---------------|
| **≥ 3.0x** | Exceptional | AI is materially compressing your SDLC. Document the pattern, replicate it. |
| **1.8x – 2.9x** | Solid | Healthy AI leverage. The norm for mature BMAD teams. |
| **1.2x – 1.7x** | Caution | Marginal gain. Investigate where the AI is slowing down. |
| **< 1.2x** | Warning | AI is not pulling its weight. Maxine will surface the likely cause. |

### Capabilities

- **Track** — per-story estimated vs. real hours, start/done timestamps, agent attribution.
- **Aggregate** — cumulative dashboard with weekly and sprint-level trends.
- **Forecast** — capacity projection based on rolling leverage and team velocity.
- **Audit** — process health checks for stories without estimates, halted work, missing artifacts.
- **Alert** — halt detection when a story stalls beyond its estimate.
- **Coach** — Maxine reads the metrics and pinpoints bottlenecks in plain English.

### Halt categories — separating dev work from wait time

Wall-clock time can be inflated by latencies that aren't dev work. PULSE captures these as structured halts in `process_health.halts` and subtracts them from `actual_hours` so leverage reflects real engineering effort.

| `kind`           | What it represents                                                                                  |
| ---------------- | --------------------------------------------------------------------------------------------------- |
| `approval_wait`  | Paused waiting for explicit user approval (admin merge, scope expansion, irreversible action).      |
| `incident`       | External infra outage, GitHub down, dependency unavailable.                                         |
| `external_pause` | User-initiated break that should not count as dev work.                                             |
| `other`          | Anything else — document with `note`.                                                               |

**Threshold:** only document halts longer than 2 minutes. Below that is conversational latency, not a halt.

**Pre-approved batch decisions:** when a prior story granted durable approval covering the current one (e.g., "Admin merge applies to the entire epic-setup batch"), set `pre_approved_batch: true` on the halt entry. PULSE reports it but does not subtract — this rewards batch-decision behavior, which is operationally correct for human-in-the-loop AI workflows.

```yaml
process_health:
  halts:
    - kind: approval_wait
      context: admin_merge_decision
      duration_min: 7
      pre_approved_batch: false
```

Why it matters: AI dev rate >> human review rate. Without this, every "AI does 5min of work, human takes 5min to approve" cycle gets logged as 0.5x leverage instead of the real number.

---

## Configuration

PULSE offers 25 configurable variables with opinionated defaults. During setup (`/bmad-pulse-setup`), you can customize:

- **Estimation methodology** — hours, story points, or t-shirt sizes
- **Field mapping** — adapts field names from your project
- **Work categories** — backend/web/mobile/fullstack or custom
- **Leverage thresholds** — when to consider exceptional, solid, or warning
- **Dashboard** — format, sections, and forecasts
- **Process Health** — level of checks and alerts

---

## Auto-dashboard

PULSE can regenerate the cumulative dashboard automatically after every `track-done` — closing the loop "story done → state consistent" without a manual `/bmad-pulse-dashboard` invocation. The trigger is **opt-in** via a config flag:

```yaml
# _bmad/config.yaml — pulse section
pulse:
  # ... other PULSE settings ...
  pulse_auto_dashboard: yes   # default: 'no' (manual regen, preserves pre-flag behavior)
```

When set to `yes`, the default `on_complete` hook in `bmad-pulse-track-done` invokes `/bmad-pulse-dashboard` right after the Efficiency Pulse card is shown. When `no`, missing, or any other value, the hook is a silent no-op.

### Trade-off: merge conflicts on parallel PRs

Auto-regenerating `dashboard.md` on every track-done **guarantees merge conflicts** in workflows with parallel pull requests — each track-done rewrites the file in full. Three documented mitigation strategies:

**1. `dashboard.md` in `.gitignore`** (recommended for repos with parallel work)

The source of truth lives in `sprint-status.yaml` under `pulse_metrics:`. Each developer regenerates locally on demand. Zero conflicts, zero loss of historical data.

```gitignore
# .gitignore
implementation-artifacts/pulse-dashboards/dashboard.md
```

**2. CI workflow on post-merge `main`**

Dashboard is regenerated by a serialized GitHub Action and committed back to `main` with `[skip ci]`. Local devs leave `pulse_auto_dashboard: no` — the central CI owns the file.

```yaml
# .github/workflows/pulse-dashboard.yml
on:
  push:
    branches: [main]
    paths: ['**/sprint-status.yaml']
jobs:
  regen:
    runs-on: ubuntu-latest
    concurrency:
      group: pulse-dashboard
      cancel-in-progress: false
    # ... invoke /bmad-pulse-dashboard via your runner ...
```

**3. Accept conflict as a trivial resolution**

For small teams (1–2 devs working serially), `git checkout --theirs dashboard.md && /bmad-pulse-dashboard` resolves in ~5 seconds. Acceptable when parallel work is rare.

### Disabling the default hook

To leave `pulse_auto_dashboard: yes` but replace the dashboard regen with your own post-completion behavior (Grafana push, Slack notification, etc.), override `on_complete` in `_bmad/custom/bmad-pulse-track-done.toml`. To disable entirely, set `on_complete = ""` in the same override file.

---

## Customizing PULSE skills

Every PULSE skill ships a `customize.toml` exposing the same override surface as bmm-shipped skills. Overrides live in `_bmad/custom/{skill-name}.toml` (team-shared, committed) and `_bmad/custom/{skill-name}.user.toml` (gitignored). Empty defaults preserve current behavior — nothing to do until you want to extend.

**Merge rules (by value shape):**

- Scalars: override wins (`icon = "🔥"` replaces the default).
- Arrays: append (base → team → user concatenate).
- Arrays of tables with `code` or `id`: replace matching entries, append new ones.

### Example 1 — give Maxine a persistent fact

`_bmad/custom/bmad-agent-pulse.toml`:

```toml
[agent]
persistent_facts = [
  "Always celebrate leverage above 4x with an exclamation; below 1.2x, request a halt review.",
]
```

### Example 2 — push metrics to a webhook on every track-done

`_bmad/custom/bmad-pulse-track-done.toml`:

```toml
[workflow]
metric_post_hooks = [
  "curl -X POST -H 'Content-Type: application/json' -d @{pulse_data_folder}/last-pulse.json https://hooks.slack.com/services/AAA/BBB/CCC",
]
```

### Example 3 — register a custom halt category

`_bmad/custom/bmad-pulse-track-done.toml`:

```toml
[workflow]
halt_categories_extra = [
  "security_review_wait",
  "ux_review_wait",
]
```

These values become valid selections in the halt prompt and are persisted alongside the built-in kinds.

### Example 4 — append a team-glossary to every dashboard

`_bmad/custom/bmad-pulse-dashboard.toml`:

```toml
[workflow]
extra_sections = [
  "file:{project-root}/docs/team-glossary.md",
]
```

### Example 5 — override Maxine's standout cutoff

`_bmad/custom/bmad-agent-pulse.toml`:

```toml
[agent]
celebration_threshold_override = "4.5"
```

The full surface for each skill is documented in the skill's `customize.toml` shipped under `.claude/skills/<skill>/`. The header line `# DO NOT EDIT -- overwritten on every update.` marks defaults; your overrides go in `_bmad/custom/` instead.

---

## Proven leverage

Sustained leverage of **6.9x** measured on a production BMAD project (SIP — local-first survey platform, monorepo with mobile, web, backend, and worker apps). The number reflects shipped stories with estimated and real hours captured by PULSE itself across multiple sprints.

PULSE eats its own dog food.

That number isn't the ceiling. It's a data point. PULSE exists so your team can find theirs.

---

## Roadmap

> PULSE is shifting its north-star metric from a leverage multiplier to **predictability**. Each milestone below operationalizes that shift.

- **v0.5 — Honest measurement engine.** Geometric-mean (not arithmetic) `h/BCP` estimator, micro vs story-size segmentation, a confidence band instead of a point estimate, and an anti-Goodhart contract test.
- **v0.6 — Invert the speedometer.** The hero metric becomes convergence/accuracy (a stable ~1.0x is healthy; a high multiplier flags inflated estimates, not speed) plus self-referential `h/BCP` drift. Regime detection via `estimated_hours_basis`. Multipliers always read "vs PLAN", never "vs human".
- **v0.7 — The action that matters.** A drift alert at estimation time — _"stories like X have missed by +N% over the last K — re-estimate?"_ — interrupting a bad estimate before it becomes a commitment.
- **v0.8 — Predictability for pricing.** Project forecast `BCP × h/BCP ± CI(90%)` for teams that bill by the hour; per-developer/agent breakdowns and Slack/Linear digests fold in here.
- **v1.0 — Pitch to BMAD core** for native adoption.

> **Why the shift?** PULSE's own data showed leverage measures the *estimate's basis*, not the work — calibration drives any multiplier toward 1.0x by construction, so a leverage target literally rewards never calibrating. The durable signal is predictability: _did you ship what you promised, and can you prove it?_ The 10x→1x graph isn't the problem — it's the moat. (Token-usage telemetry is parked as a possible separate module.)

---

## Requirements

- **BMAD Method** >= 6.4.0 (see [MIGRATION.md](docs/MIGRATION.md) if upgrading from v0.3.x)
- **Python** >= 3.9 (for setup scripts)
- **AI assistant** tool-agnostic — Claude Code, Cursor, Copilot, or anything else. PULSE measures the squad, not the IDE.

---

## Community

- [Discord](https://discord.gg/gk8jAdXWmj) — BMad Method community
- [Issues](https://github.com/nidelson/bmad-module-pulse/issues) — Bug reports and feature requests

## Star history

[View star history on star-history.com](https://star-history.com/#nidelson/bmad-module-pulse)

## License

MIT — see [LICENSE](LICENSE).

---

_PULSE — Against facts, there are no arguments._
