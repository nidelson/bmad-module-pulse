#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Resolve BCP configuration toml-first, with per-key yaml fallback and defaults.

Post-#2285 BMAD, the canonical config is ``_bmad/config.toml`` — resolved by
``_bmad/scripts/resolve_config.py`` (core) across four layers (base +
``config.user.toml`` + ``custom/config.toml`` + ``custom/config.user.toml``).
``_bmad/config.yaml`` is a legacy bridge. Reading only the yaml is a split-brain:
overrides pinned in ``custom/config.toml`` are never seen.

This helper resolves the ``bcp_*`` settings with a strict per-key precedence:

  1. **toml-first** — ``[modules.bcp]`` from the merged config, obtained by
     shelling out to the core ``resolve_config.py --key modules.bcp`` (which
     honours the ``custom/config.toml`` overrides). We reuse the core resolver
     rather than re-implementing the four-layer merge.
  2. **yaml fallback (per key)** — for any key the toml layer does not carry,
     fall back to the legacy ``bcp:`` section of ``_bmad/config.yaml``.
  3. **default (last)** — for anything still missing, the ``module.yaml`` default.

Degrades gracefully: when the core resolver is absent (or the Python running it
predates 3.11 / there is no ``config.toml``), the toml layer is empty and the
yaml fallback + defaults keep every consumer working (legacy-mode-friendly).

Values are coerced to the string contract the consumers expect (booleans that
sneak in via the YAML 1.1 ``yes``/``no`` footgun become the ``"yes"``/``"no"``
strings; everything else is stringified). Path values keep their literal
``{output_folder}`` / ``{project-root}`` tokens — the caller resolves those.

CLI: ``python3 bcp_config.py --project-root <path>`` prints the resolved
``bcp_*`` map as JSON on stdout (markdown consumers read it from there).

Exit codes: 0=success, 2=runtime error
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: pyyaml is required (PEP 723 dependency)", file=sys.stderr)
    sys.exit(2)

# module.yaml defaults, mirrored here so resolution is self-contained in an
# installed consumer (where module.yaml is not deployed — only the scripts are).
# Keep in sync with skills/bmad-bcp-setup/assets/module.yaml.
_BCP_DEFAULTS = {
    "bcp_overwrite_estimated_hours": "yes",
    "bcp_non_interactive_default": "yes",
    "bcp_confidence_threshold": "0.75",
    "bcp_estimation_basis": "bcp",
    "bcp_baseline_seed": "4.13",
    "bcp_baseline_min_samples": "5",
    "bcp_baseline_rolling_window": "10",
    "bcp_reference_h_per_bcp": "4.13",
    "bcp_data_folder": "{output_folder}/implementation-artifacts",
    "bcp_baseline_path": "{output_folder}/implementation-artifacts/bcp-baseline.yaml",
}

# Defaults for the sprint-status token chain (core + PULSE sister-module keys).
_SPRINT_DEFAULTS = {
    "output_folder": "{project-root}/_bmad-output",
    "pulse_data_folder": "{output_folder}/implementation-artifacts",
    "pulse_sprint_status_filename": "sprint-status.yaml",
}


def _coerce(value):
    """Coerce a resolved value to the string contract (bool → yes/no, else str)."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def _resolve_via_core(project_root, dotted_keys) -> dict:
    """Resolve dotted keys through the core ``resolve_config.py``.

    Returns a ``{dotted_key: value}`` dict for the keys that exist. Returns an
    empty dict when the resolver is absent, the Python running it cannot load
    it (pre-3.11), ``config.toml`` is missing, or anything else goes wrong —
    every failure mode degrades to the yaml fallback.
    """
    resolver = Path(project_root) / "_bmad" / "scripts" / "resolve_config.py"
    if not resolver.exists():
        return {}
    cmd = [sys.executable, str(resolver), "--project-root", str(project_root)]
    for key in dotted_keys:
        cmd += ["--key", key]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return {}
    if proc.returncode != 0:
        return {}
    try:
        parsed = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _load_yaml_config(project_root) -> dict:
    """Parse ``_bmad/config.yaml`` (legacy bridge). Empty dict if absent/invalid."""
    path = Path(project_root) / "_bmad" / "config.yaml"
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def _has_config(project_root) -> bool:
    """True if either canonical config source is present."""
    root = Path(project_root) / "_bmad"
    return (root / "config.toml").exists() or (root / "config.yaml").exists()


def resolve_bcp_config(project_root) -> dict:
    """Return the resolved ``bcp_*`` config: toml-first, yaml fallback, default.

    Per-key precedence: ``[modules.bcp]`` (toml, via resolve_config.py) wins,
    then the legacy ``bcp:`` section of config.yaml, then the module default.
    Keys a team added under ``[modules.bcp]`` or the legacy section but not in
    the defaults survive (custom taxonomy/values are honoured). Every value is
    coerced to the string contract.
    """
    toml = _resolve_via_core(project_root, ["modules.bcp"])
    toml_bcp = toml.get("modules.bcp") or {}
    if not isinstance(toml_bcp, dict):
        toml_bcp = {}

    yaml_all = _load_yaml_config(project_root)
    yaml_section = yaml_all.get("bcp") or {}
    yaml_bcp = {
        k: v for k, v in yaml_section.items() if isinstance(k, str) and k.startswith("bcp_")
    } if isinstance(yaml_section, dict) else {}

    resolved = {}
    for key in set(_BCP_DEFAULTS) | set(toml_bcp) | set(yaml_bcp):
        if key in toml_bcp:
            value = toml_bcp[key]
        elif key in yaml_bcp:
            value = yaml_bcp[key]
        else:
            value = _BCP_DEFAULTS[key]
        resolved[key] = _coerce(value)
    return resolved


def resolve_sprint_status_inputs(project_root):
    """Resolve the sprint-status token chain toml-first, yaml fallback, default.

    Returns ``{output_folder, pulse_data_folder, pulse_sprint_status_filename}``
    (raw, tokens literal) or ``None`` when no config source exists at all — the
    caller treats ``None`` as legacy mode (history stays in story frontmatter).

    ``output_folder`` is a core key (``[core]`` in toml, root in yaml); the
    ``pulse_*`` keys belong to the sister PULSE module (``[modules.pulse]`` in
    toml, ``pulse:`` section in yaml) because sprint-status is a PULSE artifact
    that BCP only reads.
    """
    if not _has_config(project_root):
        return None

    toml = _resolve_via_core(
        project_root,
        [
            "core.output_folder",
            "modules.pulse.pulse_data_folder",
            "modules.pulse.pulse_sprint_status_filename",
        ],
    )
    yaml_all = _load_yaml_config(project_root)
    pulse_yaml = yaml_all.get("pulse") or {}
    if not isinstance(pulse_yaml, dict):
        pulse_yaml = {}

    def pick(toml_key, yaml_value, default_key):
        if toml_key in toml:
            return toml[toml_key]
        if yaml_value is not None:
            return yaml_value
        return _SPRINT_DEFAULTS[default_key]

    return {
        "output_folder": pick(
            "core.output_folder", yaml_all.get("output_folder"), "output_folder"
        ),
        "pulse_data_folder": pick(
            "modules.pulse.pulse_data_folder",
            pulse_yaml.get("pulse_data_folder"),
            "pulse_data_folder",
        ),
        "pulse_sprint_status_filename": pick(
            "modules.pulse.pulse_sprint_status_filename",
            pulse_yaml.get("pulse_sprint_status_filename"),
            "pulse_sprint_status_filename",
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project-root", type=Path, required=True,
                   help="BMAD project root (contains _bmad/)")
    args = p.parse_args()
    resolved = resolve_bcp_config(args.project_root)
    print(json.dumps({"status": "success", "bcp": resolved},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
