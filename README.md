# PULSE — Process Utilization & Leverage Statistics Engine

> Prove the ROI of AI-Assisted Development

[![BMAD Module](https://img.shields.io/badge/BMAD-Module-blue)](https://docs.bmad-method.org/)
[![Python Version](https://img.shields.io/badge/python-%3E%3D3.9-blue?logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

At some point, every developer who works with AI has lived this moment: looked at the clock, realized they did in two hours what they estimated for two days, and didn't quite know what to do with that feeling.

PULSE was built for that moment. To turn that feeling into a number. That number into a story. And that story into evidence.

## What PULSE measures

| Metric | What it is | Why it matters |
|---|---|---|
| **AI Leverage Ratio** | `estimated_hours / actual_hours` | How much AI multiplied your capacity |
| **First-Pass Rate** | % of stories approved without revision | Quality of the development process |
| **Process Health** | Adherence to the BMAD workflow | Process health (HALTs, underused skills) |

## Installation

```bash
npx bmad-method install --custom-source https://github.com/nidelson/bmad-module-pulse
```

## Included Skills

| Skill | Command | Function |
|---|---|---|
| `pulse-setup` | `/pulse-setup` | Configure the module in your project |
| `pulse-track-start` | `/pulse-track-start [story_id]` | Register story start |
| `pulse-track-done` | `/pulse-track-done [story_id]` | Register completion + calculate metrics |
| `pulse-dashboard` | `/pulse-dashboard` | Generate cumulative dashboard |

## Agent

**Levi** — Hyper-Efficiency Analyst. Presents metrics with personality, celebrates achievements and suggests process improvements.

## Configuration

PULSE offers 25 configurable variables with opinionated defaults. During setup (`/pulse-setup`), you can customize:

- **Estimation methodology** — hours, story points or t-shirt sizes
- **Field mapping** — adapts field names from your project
- **Work categories** — backend/web/mobile/fullstack or custom
- **Leverage thresholds** — when to consider exceptional, solid or warning
- **Dashboard** — format, sections and forecasts
- **Process Health** — level of checks and alerts

## Requirements

- BMAD Method >= 6.3.0
- Python >= 3.9 (for setup scripts)

## Community

- [Discord](https://discord.gg/gk8jAdXWmj) — BMad Method community
- [Issues](https://github.com/nidelson/bmad-module-pulse/issues) — Bug reports and feature requests

## License

MIT

---

_PULSE — Against facts, there are no arguments._
