"""Unit tests for the toml-first write path of merge-config.py.

Issue #73: PULSE is toml-first. The setup write-path (merge-config.py) must
write the module answers into ``_bmad/custom/config.toml`` under
``[modules.pulse]`` — the layer ``resolve_config.py`` reads with higher
priority than the installer defaults in ``config.toml`` — and must NOT write
the legacy ``pulse:`` section into ``config.yaml`` anymore (it strips a stale
one on re-run, which is the migration path). Core keys stay in ``config.yaml``.

Matrix required by the acceptance criteria: fresh toml write, yaml→toml
migration (strip), both (preserve human custom content), none (core-only).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml

REPO = Path(__file__).parents[2]
SCRIPT = REPO / "skills/bmad-pulse-setup/scripts/merge-config.py"
MODULE_YAML = REPO / "skills/bmad-pulse-setup/assets/module.yaml"


def run(project_root: Path, answers: dict) -> subprocess.CompletedProcess[str]:
    answers_file = project_root / "answers.json"
    answers_file.write_text(json.dumps(answers), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--config-path",
            str(project_root / "_bmad/config.yaml"),
            "--user-config-path",
            str(project_root / "_bmad/config.user.yaml"),
            "--module-yaml",
            str(MODULE_YAML),
            "--answers",
            str(answers_file),
        ],
        capture_output=True,
        text=True,
    )


def read_custom_pulse(project_root: Path) -> dict:
    path = project_root / "_bmad/custom/config.toml"
    with path.open("rb") as f:
        data = tomllib.load(f)
    return data.get("modules", {}).get("pulse", {})


def read_yaml(project_root: Path) -> dict:
    path = project_root / "_bmad/config.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


# The custom taxonomy that must survive the cutover (caveat crítico da issue).
CUSTOM_MODULE_ANSWERS = {
    "module": {
        "pulse_estimation_method": "bcp",
        "pulse_dev_categories": "frontend, backend, fullstack, mobile, security",
        "pulse_field_estimated_hours": "estimated_hours",
        "pulse_min_stories_for_trend": "3",
        "pulse_include_trend_chart": "yes",
    }
}


# --- fresh: writes toml, never a pulse: section in config.yaml ---

def test_fresh_writes_pulse_to_custom_toml(tmp_path: Path):
    result = run(tmp_path, CUSTOM_MODULE_ANSWERS)
    assert result.returncode == 0, result.stderr

    pinned = read_custom_pulse(tmp_path)
    assert pinned["pulse_estimation_method"] == "bcp"
    assert pinned["pulse_dev_categories"] == "frontend, backend, fullstack, mobile, security"


def test_fresh_never_writes_pulse_section_to_yaml(tmp_path: Path):
    assert run(tmp_path, CUSTOM_MODULE_ANSWERS).returncode == 0
    assert "pulse" not in read_yaml(tmp_path)


def test_metadata_not_pinned_only_pulse_values(tmp_path: Path):
    assert run(tmp_path, CUSTOM_MODULE_ANSWERS).returncode == 0
    pinned = read_custom_pulse(tmp_path)
    for meta in ("name", "description", "version", "default_selected"):
        assert meta not in pinned
    assert all(k.startswith("pulse_") for k in pinned)


def test_values_are_strings(tmp_path: Path):
    assert run(tmp_path, CUSTOM_MODULE_ANSWERS).returncode == 0
    pinned = read_custom_pulse(tmp_path)
    assert pinned["pulse_min_stories_for_trend"] == "3"
    assert pinned["pulse_include_trend_chart"] == "yes"
    assert all(isinstance(v, str) for v in pinned.values())


# --- migration: an existing legacy pulse: in config.yaml is stripped ---

def test_migration_strips_legacy_yaml_pulse_section(tmp_path: Path):
    (tmp_path / "_bmad").mkdir(parents=True)
    (tmp_path / "_bmad/config.yaml").write_text(
        "output_folder: '{project-root}/_bmad-output'\n"
        "pulse:\n"
        "  name: PULSE\n"
        "  pulse_estimation_method: hours\n"
        "  pulse_dev_categories: standard_4\n",
        encoding="utf-8",
    )
    assert run(tmp_path, CUSTOM_MODULE_ANSWERS).returncode == 0

    cfg = read_yaml(tmp_path)
    assert "pulse" not in cfg  # legacy section removed
    assert cfg.get("output_folder") == "{project-root}/_bmad-output"  # core preserved
    assert read_custom_pulse(tmp_path)["pulse_estimation_method"] == "bcp"


# --- both: existing custom/config.toml content + comments preserved ---

def test_preserves_existing_custom_toml_content(tmp_path: Path):
    custom = tmp_path / "_bmad/custom"
    custom.mkdir(parents=True)
    (custom / "config.toml").write_text(
        "# human-owned team config\n"
        "[core]\n"
        'user_name = "Ada"\n\n'
        "[modules.pulse]\n"
        'pulse_levi_verbosity = "verbose"\n',
        encoding="utf-8",
    )
    assert run(tmp_path, CUSTOM_MODULE_ANSWERS).returncode == 0

    text = (custom / "config.toml").read_text(encoding="utf-8")
    assert "# human-owned team config" in text  # comment preserved

    with (custom / "config.toml").open("rb") as f:
        data = tomllib.load(f)
    assert data["core"]["user_name"] == "Ada"  # other section preserved
    # human-only key under [modules.pulse] preserved, answered keys upserted
    assert data["modules"]["pulse"]["pulse_levi_verbosity"] == "verbose"
    assert data["modules"]["pulse"]["pulse_estimation_method"] == "bcp"


def test_rerun_overwrites_managed_keys(tmp_path: Path):
    assert run(tmp_path, CUSTOM_MODULE_ANSWERS).returncode == 0
    changed = {"module": dict(CUSTOM_MODULE_ANSWERS["module"], pulse_estimation_method="hours")}
    assert run(tmp_path, changed).returncode == 0
    assert read_custom_pulse(tmp_path)["pulse_estimation_method"] == "hours"


# --- none: core-only answers still land in config.yaml, no toml module noise ---

def test_core_keys_still_written_to_yaml(tmp_path: Path):
    answers = {"core": {"output_folder": "custom-out"}, "module": CUSTOM_MODULE_ANSWERS["module"]}
    assert run(tmp_path, answers).returncode == 0
    cfg = read_yaml(tmp_path)
    assert cfg["output_folder"] == "custom-out"
    assert "pulse" not in cfg
