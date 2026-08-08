#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "pytest"]
# ///
"""Unit matrix for bcp_config.resolve_bcp_config — toml-first resolution.

Issue #36: BCP must read ``bcp_*`` from ``config.toml`` (the ``modules.bcp``
table, resolved through the core ``resolve_config.py`` so ``custom/config.toml``
overrides are honoured) when present, fall back **per key** to the legacy
``bcp:`` section of ``config.yaml``, and use the ``module.yaml`` default only
when neither has the key.

Matrix required by the acceptance criteria:
  - toml-only      → toml values
  - yaml-only      → yaml fallback
  - both           → toml wins (per key); yaml fills keys toml lacks
  - none           → module defaults
  - custom layer   → custom/config.toml overrides the installer base
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent
REPO = Path(__file__).resolve().parents[4]
# Vendored under tests/fixtures — see the note in test_apply_score.py. PULSE has
# no `_bmad/` of its own; the resolver here is test scaffolding, not an install.
CORE_RESOLVER = REPO / "tests" / "fixtures" / "bmad-core" / "resolve_config.py"

sys.path.insert(0, str(SCRIPTS))
import bcp_config  # noqa: E402

needs_py311 = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="core resolve_config.py needs stdlib tomllib (Python 3.11+)",
)


def _install_resolver(project_root: Path) -> None:
    """Copy the real core resolver into the fake project (reuse, not replicate)."""
    scripts = project_root / "_bmad" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    assert CORE_RESOLVER.exists(), f"core resolver missing at {CORE_RESOLVER}"
    shutil.copy(CORE_RESOLVER, scripts / "resolve_config.py")


def _write_toml(project_root: Path, body: str, name: str = "config.toml") -> None:
    bmad = project_root / "_bmad"
    (bmad / "custom").mkdir(parents=True, exist_ok=True)
    target = bmad / name if name == "config.toml" else bmad / "custom" / name
    target.write_text(body, encoding="utf-8")


def _write_yaml(project_root: Path, body: str) -> None:
    bmad = project_root / "_bmad"
    bmad.mkdir(parents=True, exist_ok=True)
    (bmad / "config.yaml").write_text(body, encoding="utf-8")


# ── none → defaults ──────────────────────────────────────────────────────────

def test_none_yields_module_defaults(tmp_path: Path):
    cfg = bcp_config.resolve_bcp_config(tmp_path)
    assert cfg["bcp_confidence_threshold"] == "0.75"
    assert cfg["bcp_reference_h_per_bcp"] == "4.13"
    assert cfg["bcp_baseline_seed"] == "4.13"
    assert cfg["bcp_baseline_path"] == "{output_folder}/implementation-artifacts/bcp-baseline.yaml"


# ── yaml-only → fallback ─────────────────────────────────────────────────────

def test_yaml_only_falls_back_per_key(tmp_path: Path):
    _write_yaml(
        tmp_path,
        "bcp:\n"
        "  name: BCP\n"  # metadata ignored
        "  bcp_confidence_threshold: '0.9'\n"
        "  bcp_reference_h_per_bcp: '5.5'\n",
    )
    cfg = bcp_config.resolve_bcp_config(tmp_path)
    assert cfg["bcp_confidence_threshold"] == "0.9"   # from yaml
    assert cfg["bcp_reference_h_per_bcp"] == "5.5"    # from yaml
    assert cfg["bcp_baseline_seed"] == "4.13"         # default (absent in yaml)


def test_yaml_bool_footgun_coerced(tmp_path: Path):
    # Unquoted yaml yes/no parse as booleans — must present as "yes"/"no".
    _write_yaml(tmp_path, "bcp:\n  bcp_non_interactive_default: no\n")
    cfg = bcp_config.resolve_bcp_config(tmp_path)
    assert cfg["bcp_non_interactive_default"] == "no"


# ── toml-only → toml values ──────────────────────────────────────────────────

@needs_py311
def test_toml_only_reads_modules_bcp(tmp_path: Path):
    _install_resolver(tmp_path)
    _write_toml(
        tmp_path,
        "[core]\n"
        'output_folder = "{project-root}/_bmad-output"\n\n'
        "[modules.bcp]\n"
        'bcp_confidence_threshold = "0.9"\n'
        'bcp_reference_h_per_bcp = "6.0"\n',
    )
    cfg = bcp_config.resolve_bcp_config(tmp_path)
    assert cfg["bcp_confidence_threshold"] == "0.9"
    assert cfg["bcp_reference_h_per_bcp"] == "6.0"
    assert cfg["bcp_baseline_seed"] == "4.13"  # default (absent in toml)


@needs_py311
def test_toml_custom_key_survives(tmp_path: Path):
    _install_resolver(tmp_path)
    _write_toml(
        tmp_path,
        "[core]\noutput_folder = \"x\"\n\n"
        "[modules.bcp]\n"
        'bcp_custom_taxonomy = "frontend,backend,security"\n',
    )
    cfg = bcp_config.resolve_bcp_config(tmp_path)
    assert cfg["bcp_custom_taxonomy"] == "frontend,backend,security"


# ── both → toml wins per key, yaml fills the gaps ────────────────────────────

@needs_py311
def test_both_toml_wins_yaml_fills_gaps(tmp_path: Path):
    _install_resolver(tmp_path)
    _write_toml(
        tmp_path,
        "[core]\noutput_folder = \"x\"\n\n"
        "[modules.bcp]\n"
        'bcp_confidence_threshold = "0.9"\n',  # only this key in toml
    )
    _write_yaml(
        tmp_path,
        "bcp:\n"
        "  bcp_confidence_threshold: '0.6'\n"   # shadowed by toml
        "  bcp_reference_h_per_bcp: '7.7'\n",   # only in yaml → fallback
    )
    cfg = bcp_config.resolve_bcp_config(tmp_path)
    assert cfg["bcp_confidence_threshold"] == "0.9"  # toml wins
    assert cfg["bcp_reference_h_per_bcp"] == "7.7"   # yaml fallback


# ── custom/config.toml overrides the installer base (honoured via resolver) ──

@needs_py311
def test_custom_layer_overrides_base(tmp_path: Path):
    _install_resolver(tmp_path)
    _write_toml(
        tmp_path,
        "[core]\noutput_folder = \"x\"\n\n"
        "[modules.bcp]\n"
        'bcp_reference_h_per_bcp = "4.13"\n',  # installer base default
    )
    # team override lands in the higher-priority custom layer
    (tmp_path / "_bmad" / "custom" / "config.toml").write_text(
        "[modules.bcp]\nbcp_reference_h_per_bcp = \"9.9\"\n", encoding="utf-8"
    )
    cfg = bcp_config.resolve_bcp_config(tmp_path)
    assert cfg["bcp_reference_h_per_bcp"] == "9.9"  # custom layer wins


# ── sprint-status inputs (used by apply_score.py) ────────────────────────────

def test_sprint_status_none_without_config(tmp_path: Path):
    assert bcp_config.resolve_sprint_status_inputs(tmp_path) is None


def test_sprint_status_yaml_fallback(tmp_path: Path):
    _write_yaml(
        tmp_path,
        "output_folder: '{project-root}/out'\n"
        "pulse:\n"
        "  pulse_data_folder: '{output_folder}/impl'\n"
        "  pulse_sprint_status_filename: sprint-status.yaml\n",
    )
    got = bcp_config.resolve_sprint_status_inputs(tmp_path)
    assert got["output_folder"] == "{project-root}/out"
    assert got["pulse_data_folder"] == "{output_folder}/impl"
    assert got["pulse_sprint_status_filename"] == "sprint-status.yaml"


@needs_py311
def test_sprint_status_toml_first(tmp_path: Path):
    _install_resolver(tmp_path)
    _write_toml(
        tmp_path,
        "[core]\n"
        'output_folder = "{project-root}/tout"\n\n'
        "[modules.pulse]\n"
        'pulse_data_folder = "{output_folder}/tomlimpl"\n'
        'pulse_sprint_status_filename = "sprint-status.yaml"\n',
    )
    got = bcp_config.resolve_sprint_status_inputs(tmp_path)
    assert got["output_folder"] == "{project-root}/tout"
    assert got["pulse_data_folder"] == "{output_folder}/tomlimpl"


# ── the new home: [modules.pulse] ────────────────────────────────────────────
#
# Issue #84 Phase 4 folds BCP into PULSE and archives the BCP module. Once that
# module is uninstalled the installer stops writing `[modules.bcp]`, so any
# `bcp_*` value pinned there disappears. Resolution silently fell through to the
# hardcoded defaults — `status: success`, exit 0, no warning — which on a project
# whose seed was calibrated well away from the default rewrites every derived
# `estimated_hours` by that ratio. `[modules.pulse]` is the surviving home;
# `[modules.bcp]` stays readable for the migration window.


@needs_py311
def test_modules_pulse_is_the_new_home(tmp_path: Path):
    _install_resolver(tmp_path)
    _write_toml(
        tmp_path,
        "[core]\n"
        'output_folder = "{project-root}/_bmad-output"\n\n'
        "[modules.pulse]\n"
        'pulse_estimation_method = "bcp"\n'
        'bcp_baseline_seed = "0.06"\n'
        'bcp_reference_h_per_bcp = "5.0"\n',
    )
    cfg = bcp_config.resolve_bcp_config(tmp_path)
    assert cfg["bcp_baseline_seed"] == "0.06"
    assert cfg["bcp_reference_h_per_bcp"] == "5.0"
    assert cfg["bcp_confidence_threshold"] == "0.75"  # default, absent in toml


@needs_py311
def test_modules_pulse_wins_over_legacy_modules_bcp(tmp_path: Path):
    """Both tables present — the migration window. The new home wins per key.

    The other order would let a stale `[modules.bcp]`, regenerated by the
    installer from the archived module's defaults, quietly override the value a
    team moved into `[modules.pulse]` on purpose.
    """
    _install_resolver(tmp_path)
    _write_toml(
        tmp_path,
        "[core]\n"
        'output_folder = "{project-root}/_bmad-output"\n\n'
        "[modules.pulse]\n"
        'bcp_baseline_seed = "0.06"\n\n'
        "[modules.bcp]\n"
        'bcp_baseline_seed = "4.13"\n'
        'bcp_confidence_threshold = "0.9"\n',
    )
    cfg = bcp_config.resolve_bcp_config(tmp_path)
    assert cfg["bcp_baseline_seed"] == "0.06"        # pulse wins
    assert cfg["bcp_confidence_threshold"] == "0.9"  # legacy fills what pulse lacks


@needs_py311
def test_pulse_keys_never_leak_into_the_bcp_map(tmp_path: Path):
    """`[modules.pulse]` carries ~26 `pulse_*` keys that are not BCP settings.

    Reading the whole table without filtering would hand every consumer a map
    where `pulse_dashboard_format` sits beside `bcp_baseline_seed`.
    """
    _install_resolver(tmp_path)
    _write_toml(
        tmp_path,
        "[core]\n"
        'output_folder = "{project-root}/_bmad-output"\n\n'
        "[modules.pulse]\n"
        'pulse_dashboard_format = "markdown"\n'
        'pulse_estimation_method = "bcp"\n'
        'bcp_baseline_seed = "0.06"\n',
    )
    cfg = bcp_config.resolve_bcp_config(tmp_path)
    assert cfg["bcp_baseline_seed"] == "0.06"
    assert not any(k.startswith("pulse_") for k in cfg), sorted(cfg)


@needs_py311
def test_custom_layer_reaches_the_new_home(tmp_path: Path):
    """`custom/config.toml` is where a team pins the set; the installer never
    touches it, so it is what survives a reinstall as well as an uninstall."""
    _install_resolver(tmp_path)
    _write_toml(
        tmp_path,
        "[core]\n"
        'output_folder = "{project-root}/_bmad-output"\n\n'
        "[modules.pulse]\n"
        'bcp_baseline_seed = "4.13"\n',
    )
    # `_write_toml` routes any non-"config.toml" name into custom/, so the
    # custom layer's real filename has to be written directly.
    (tmp_path / "_bmad" / "custom" / "config.toml").write_text(
        "[modules.pulse]\n" 'bcp_baseline_seed = "0.06"\n', encoding="utf-8"
    )
    cfg = bcp_config.resolve_bcp_config(tmp_path)
    assert cfg["bcp_baseline_seed"] == "0.06"


# ── telling silence apart from configuration ─────────────────────────────────


def test_sources_mark_defaults_as_default(tmp_path: Path):
    """A default is not a setting. Consumers (and the setup skill) need to tell
    "the team chose 4.13" from "nothing was found, so 4.13"."""
    sources = bcp_config.resolve_bcp_sources(tmp_path)
    assert set(sources.values()) == {"default"}


@needs_py311
def test_sources_name_the_layer_each_key_came_from(tmp_path: Path):
    _install_resolver(tmp_path)
    _write_toml(
        tmp_path,
        "[core]\n"
        'output_folder = "{project-root}/_bmad-output"\n\n'
        "[modules.pulse]\n"
        'bcp_baseline_seed = "0.06"\n\n'
        "[modules.bcp]\n"
        'bcp_confidence_threshold = "0.9"\n',
    )
    _write_yaml(tmp_path, "bcp:\n  bcp_estimation_basis: legacy\n")
    sources = bcp_config.resolve_bcp_sources(tmp_path)
    assert sources["bcp_baseline_seed"] == "modules.pulse"
    assert sources["bcp_confidence_threshold"] == "modules.bcp"
    assert sources["bcp_estimation_basis"] == "config.yaml"
    assert sources["bcp_baseline_min_samples"] == "default"
