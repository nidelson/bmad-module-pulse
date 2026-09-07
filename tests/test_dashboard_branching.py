"""The dashboard branches on `pulse_estimation_method`, not on field presence (#66).

There are two leverage metrics and they are not interchangeable:

| metric                  | denominator                    | needs BCP | under calibration  |
| ----------------------- | ------------------------------ | --------- | ------------------ |
| `leverage_ratio`        | `estimated_hours` (PLAN)       | no        | collapses to ~1.0x |
| `leverage_vs_reference` | frozen reference rate          | yes       | stays stable       |

Before this, the dashboard rendered only the vs-REFERENCE one, gated on the
field existing. On the default `hours` path no story carries that field, so the
gate never opened and the dashboard reported **no leverage at all** — the metric
PULSE was born with, missing from the configuration most projects run.

These are markdown invariants: the dashboard is agent instructions, so what is
pinned is that the instructions say the right thing.
"""
from __future__ import annotations

from pathlib import Path

import pytest

SKILLS = Path(__file__).parents[1] / "skills"
DASHBOARD = SKILLS / "bmad-pulse-dashboard/workflow.md"


@pytest.fixture(scope="module")
def text() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


# ── the branch exists and is fed ─────────────────────────────────────────────


def test_dashboard_loads_the_config_key_it_branches_on(text: str):
    """The gap that made the branch impossible rather than merely absent.

    `pulse_estimation_method` was not among the keys the workflow resolves, so
    the instructions had no way to know which path the project is on even if
    they had asked.
    """
    keys_section = text.split("The keys this workflow uses:", 1)[1].split("###", 1)[0]
    assert "pulse_estimation_method" in keys_section


def test_both_leverage_metrics_are_computed(text: str):
    """`leverage_ratio` is persisted on both paths and stays available in the
    detail view even where it is not the headline. Computing only the headline
    would make the detail table lie by omission on the bcp path."""
    assert "avg_leverage_ratio" in text
    assert "avg_leverage_vs_reference" in text


def test_headline_row_exists_for_each_path(text: str):
    assert "Alavancagem (vs PLANO)" in text
    assert "Alavancagem (vs REFERÊNCIA)" in text


def test_branch_is_on_the_configured_method_not_field_presence(text: str):
    """Field presence answers "did this story record it", not "what does this
    project measure". A project can carry a stray field from an experiment, or
    have its first BCP story land mid-sprint, and neither should flip the
    dashboard's headline."""
    assert "BRANCH ON pulse_estimation_method" in text


def test_exactly_one_headline_renders(text: str):
    """Both rows live in the template; the instruction that only one renders is
    the thing keeping them from both appearing."""
    assert "Never render both" in text


# ── neither path is described as lacking ─────────────────────────────────────


def test_hours_path_is_not_framed_as_degraded(text: str):
    """The default configuration is the baseline product. A dashboard that
    notes what it cannot show teaches the reader they are missing something,
    which is how an opt-in feature becomes an implied default."""
    assert "not a degraded one" in text
    assert "never render the vs-PLANO ratio as a headline on the `bcp` path" in text


# ── thresholds belong to one path ────────────────────────────────────────────


def test_thresholds_are_scoped_to_the_plan_denominator(text: str):
    """A band calibrated against human judgement means nothing against a frozen
    market rate. Applied there, a converged 0.9 — the plan matching reality —
    reads as "weak leverage", which is the exact mislabel #66 was filed over."""
    assert "pulse_leverage_threshold_exceptional" in text
    assert "band the **vs-PLANO** row only" in text


# ── predictability is framed per path ────────────────────────────────────────


def test_predictability_is_not_a_team_property_without_a_comparable_unit(text: str):
    """On the hours path, estimate error measures whoever wrote the estimate.
    Reporting it as a team property makes the metric a stick, and a team
    measured to be punished learns to lie to the metric."""
    assert "measures the estimator" in text
    assert "must **not** be framed as a property of the team" in text
