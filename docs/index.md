# PULSE — Documentation

## Quick Start

1. Install the module: `npx bmad-method install --custom-source https://github.com/nidelson/bmad-module-pulse`
2. Configure: `/bmad-pulse-setup`
3. When starting a story: `/bmad-pulse-track-start`
4. When completing: `/bmad-pulse-track-done`
5. To view the dashboard: `/bmad-pulse-dashboard`

> **Missed tracking a story?** Early-adoption stories or workflow
> interruptions sometimes skip track-start/track-done. Recover the lost
> measurement after the fact:
> `/bmad-pulse-track-backfill 1.2 --hi "2026-05-18 14:00" --hf "2026-05-18 15:00"`.
> Backfilled entries are flagged `retroactive: true` for traceability and
> deliberately omit `process_health` — halts and BMAD flow cannot be
> reconstructed honestly after the fact.

## Metrics Reference

### AI Leverage Ratio

```text
leverage = estimated_hours / actual_hours
```

- \>= 3.0x: Exceptional
- \>= 1.8x: Solid
- < 1.2x: Warning

### First-Pass Rate

Percentage of stories approved with `review_cycles == 1`.

### Process Health

Composite score based on:

- Complete BMAD flow (create-story → dev-story → code-review → done)
- HALT count
- Available skills that were not used

## Integrations

- [BCP — Business Complexity Points](integration/bcp.md) — opt-in
  `pulse_estimation_method=bcp` for teams estimating in BCP via the companion
  [`bmad-module-bcp`](https://github.com/nidelson/bmad-module-bcp) module.

## Advanced Configuration

See [module.yaml](../module.yaml) for the full list of configurable variables. The file at the repository root is a symlink to the canonical manifest shipped inside the setup skill (`skills/bmad-pulse-setup/assets/module.yaml`), so the BMAD installer can copy it to the consumer project at install time while keeping the file discoverable from the repo root.
