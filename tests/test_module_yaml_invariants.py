"""Invariant tests for skills/bmad-pulse-setup/assets/module.yaml.

Path resolution invariants — guard against double-interpolation regressions
where a `result` template prefixes a token (e.g. `{project-root}/`) onto a
`{value}` that already starts with another resolved token (e.g. `{output_folder}`,
which itself begins with `{project-root}`). That class of bug surfaces only
when the BMAD installer writes the resolved value into `_bmad/config.yaml`
and skills then expand it twice at runtime.

Reference: https://github.com/nidelson/bmad-module-pulse/issues/15
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[1]
MODULE_YAML = REPO_ROOT / "skills/bmad-pulse-setup/assets/module.yaml"


def _load_module_yaml() -> dict:
    return yaml.safe_load(MODULE_YAML.read_text())


def test_path_results_do_not_double_prefix_project_root():
    """`result` for path-typed entries must not prefix `{project-root}/` when
    the corresponding `default` already begins with `{output_folder}`.

    `{output_folder}` resolves to `{project-root}/_bmad-output` per BMAD core,
    so prefixing again produces `{project-root}/{project-root}/...` —
    invalid path at runtime.
    """
    data = _load_module_yaml()
    path_keys = ("pulse_data_folder", "pulse_dashboard_folder")

    for key in path_keys:
        entry = data.get(key)
        assert entry is not None, f"missing {key} in module.yaml"
        default = entry.get("default", "")
        result = entry.get("result", "")

        if default.startswith("{output_folder}"):
            assert "{project-root}" not in result, (
                f"{key}: result template '{result}' double-prefixes "
                f"{{project-root}} on top of default '{default}' which "
                f"already starts with {{output_folder}}"
            )


def test_path_results_use_value_token():
    """Path entries must propagate `{value}` so user customizations stick."""
    data = _load_module_yaml()
    for key in ("pulse_data_folder", "pulse_dashboard_folder"):
        entry = data[key]
        assert "{value}" in entry["result"], (
            f"{key}: result template must contain {{value}} to honor user input"
        )
