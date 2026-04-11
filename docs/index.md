# PULSE — Documentation

## Quick Start

1. Install the module: `npx bmad-method install --custom-source https://github.com/nidelson/bmad-module-pulse`
2. Configure: `/pulse-setup`
3. When starting a story: `/pulse-track-start`
4. When completing: `/pulse-track-done`
5. To view the dashboard: `/pulse-dashboard`

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

## Advanced Configuration

See [module.yaml](../skills/pulse-setup/assets/module.yaml) for the full list of configurable variables.
