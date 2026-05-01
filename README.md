# PULSE

[![BMAD Module](https://img.shields.io/badge/BMAD-Module-blue)](https://docs.bmad-method.org/)
[![BMAD Version](https://img.shields.io/badge/BMAD-%3E%3D6.4.0-blue)](https://docs.bmad-method.org/)
[![Tests](https://github.com/nidelson/bmad-module-pulse/actions/workflows/test.yaml/badge.svg)](https://github.com/nidelson/bmad-module-pulse/actions/workflows/test.yaml)
[![GitHub release](https://img.shields.io/github/v/release/nidelson/bmad-module-pulse)](https://github.com/nidelson/bmad-module-pulse/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/nidelson/bmad-module-pulse?style=social)](https://github.com/nidelson/bmad-module-pulse/stargazers)

> **AI leverage signals for BMAD teams.**

**Prove your AI is actually shipping faster — or find where it stalls.**

🌐 [Português 🇧🇷](README.pt-BR.md)

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

### 📈 Leverage Trend by Epic

```text
Epic  1: ████████░░░░░░░░░░░░  4.2x (3 stories)
Epic  4: ██████████░░░░░░░░░░  5.1x (2 stories)
Epic  5: ████████████████░░░░  7.8x (3 stories)
Epic 14: ██████████████░░░░░░  6.9x (3 stories)
Epic 15: ████████████████████  8.4x (1 story)
```

📊 **[View full dashboard →](examples/dashboards/mature-bmad-team.md)** *(category breakdown, capacity forecast, Levi's insights, story-by-story breakdown)*

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

- **A defensible ROI number for AI in your SDLC** — leverage ratio, computed sprint over sprint, ready for your stakeholder deck.
- **Early warning on stalled work** — capacity forecasts and halt alerts before a sprint slips.
- **A coach, not just a dashboard** — Levi (PULSE's agent) reads your signals and tells you *where* the leverage is leaking.

---

## Why PULSE

**The market measures lines. PULSE measures stories.**

It's the difference between **scale weight and body fat percentage**. LOC tells you something is moving. Leverage tells you whether it's muscle or bloat.

A story is the smallest unit of value your users feel. Tracking AI leverage at the story level — estimated hours vs. real hours, planning to done — gives you the only metric that survives a board meeting.

PULSE is also the **first BMAD-native observability plugin** on the marketplace. There is no incumbent. There is no second place yet. If you're running BMAD and you want SDLC analytics that speak BMAD's vocabulary (epics, stories, agents, workflows), this is the tool.

> Stories, not lines.
> Outcomes, not output.
> Leverage, not activity.

---

## What PULSE measures

| Metric | What it is | Why it matters |
|---|---|---|
| **AI Leverage Ratio** | `estimated_hours / actual_hours` | How much AI multiplied your capacity |
| **First-Pass Rate** | % of stories approved without revision | Quality of the development process |
| **Process Health** | Adherence to the BMAD workflow | Halts, underused skills, drift |

---

## Quick start

```bash
npx bmad-method install --custom-source https://github.com/nidelson/bmad-module-pulse
```

Then in your BMAD project:

```bash
/bmad-pulse-setup            # Configure once
/bmad-pulse-track-start      # When you start a story
/bmad-pulse-track-done       # When you finish — leverage is computed
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
| `bmad-pulse-dashboard` | `/bmad-pulse-dashboard` | Generate cumulative dashboard |

---

## Levi — your coach agent

**Levi** is PULSE's Hyper-Efficiency Analyst. He reads your metrics and tells you, in plain English, where the squad is losing time: estimation drift, BMAD steps being skipped, agents being misused. He celebrates real wins, calls out drift, and suggests process fixes.

He doesn't moralize. He points.

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
| **< 1.2x** | Warning | AI is not pulling its weight. Levi will surface the likely cause. |

### Capabilities

- **Track** — per-story estimated vs. real hours, start/done timestamps, agent attribution.
- **Aggregate** — cumulative dashboard with weekly and sprint-level trends.
- **Forecast** — capacity projection based on rolling leverage and team velocity.
- **Audit** — process health checks for stories without estimates, halted work, missing artifacts.
- **Alert** — halt detection when a story stalls beyond its estimate.
- **Coach** — Levi reads the metrics and pinpoints bottlenecks in plain English.

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

## Proven leverage

Sustained leverage of **6.9x** measured on a production BMAD project (SIP — local-first survey platform, monorepo with mobile, web, backend, and worker apps). The number reflects shipped stories with estimated and real hours captured by PULSE itself across multiple sprints.

PULSE eats its own dog food.

That number isn't the ceiling. It's a data point. PULSE exists so your team can find theirs.

---

## Roadmap

- **v0.5** — Period-navigable dashboard (week / sprint / quarter views, side-by-side comparison)
- **v0.6** — Per-developer and per-agent leverage breakdowns, with privacy guards on by default
- **v0.7** — Slack and Linear digests so signals reach leadership without a meeting
- **v1.0** — Pitch to BMAD core for native adoption.

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
