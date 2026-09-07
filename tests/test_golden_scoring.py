"""Golden set: deterministic scoring regression.

The LLM picks sizes (judgment, not tested here). Everything downstream of
the breakdown is deterministic and is the module's estimation contract:
`total = Σ Fibonacci(size)` and `estimated_hours = total × h_per_bcp`.

The golden set is the full 10-element × 5-size matrix (50 single-element
cases) plus realistic composites. Generating it from the frozen rule slugs
gives complete rule-mapping coverage for free and makes any drift in the
points table or the hours derivation fail loudly.
"""
from __future__ import annotations

import json

import pytest
import yaml

from .conftest import APPLY_SCORE, COLD_START_SEED, run_script
from .test_bcp_rule_immutability import FIBONACCI_SCALE as FIB, FROZEN_SLUGS

SEED = COLD_START_SEED
RULE_ARG = ("--rule", "skills/bmad-bcp-rule-card/assets/bcp-rule.yaml")

# 50-case golden matrix: every element at every size.
MATRIX = [
    (slug, size, pts)
    for slug in sorted(FROZEN_SLUGS)
    for size, pts in FIB.items()
]


@pytest.mark.parametrize("slug,size,pts", MATRIX,
                         ids=[f"{s}-{z}" for s, z, _ in MATRIX])
def test_single_element_golden(slug, size, pts, seeded_baseline,
                               story_file, breakdown_file):
    story = story_file({"story_id": "g", "category": "backend",
                        "estimated_hours": 1})
    bd = breakdown_file({slug: [{"size": size, "points": pts}]})
    proc = run_script(
        APPLY_SCORE, "--story", str(story), "--breakdown", str(bd),
        "--baseline", str(seeded_baseline), *RULE_ARG,
        "--scored-by", "manual", "--now", "2026-05-17T12:00:00Z",
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["total"] == pts
    assert out["estimated_hours"] == round(pts * SEED, 2)
    assert out["hours_per_bcp_source"] == "seed"


# Realistic composite stories — hand-curated golden expectations.
COMPOSITES = [
    pytest.param(
        {"business_rules": [{"size": "M", "points": 3}],
         "interface_elements": [{"size": "S", "points": 2},
                                {"size": "M", "points": 3}],
         "audits": [{"size": "XS", "points": 1}]},
        9, id="crud-with-audit"),
    pytest.param(
        {"business_rules": [{"size": "XL", "points": 8}],
         "background_processes": [{"size": "L", "points": 5}],
         "notifications": [{"size": "XS", "points": 1}],
         "roles_permissions": [{"size": "M", "points": 3}]},
        17, id="complex-workflow"),
    pytest.param(
        {"domain_entities": [{"size": "XS", "points": 1}]},
        1, id="trivial-single"),
]


@pytest.mark.parametrize("breakdown,expected_total", COMPOSITES)
def test_composite_golden(breakdown, expected_total, seeded_baseline,
                          story_file, breakdown_file):
    story = story_file({"story_id": "c", "category": "backend",
                        "estimated_hours": 20})
    bd = breakdown_file(breakdown)
    proc = run_script(
        APPLY_SCORE, "--story", str(story), "--breakdown", str(bd),
        "--baseline", str(seeded_baseline), *RULE_ARG,
        "--scored-by", "manual", "--now", "2026-05-17T12:00:00Z",
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["total"] == expected_total
    assert out["estimated_hours"] == round(expected_total * SEED, 2)


def test_calibrated_category_uses_rolling_mean_not_seed(
    tmp_path, story_file, breakdown_file
):
    """Once a category has left the seed, hours derive from its rolling
    mean, not the seed. Golden-pins the seed→calibrated switchover."""
    baseline = tmp_path / "bcp-baseline.yaml"
    baseline.write_text(yaml.dump({
        "schema_version": "1.0",
        "config_snapshot": {"seed": SEED, "min_samples": 5,
                            "rolling_window": 10},
        "categories": {
            "backend": {"h_per_bcp": 6.0, "n_samples": 7, "is_seed": False},
        },
    }))
    story = story_file({"story_id": "k", "category": "backend",
                        "estimated_hours": 5})
    bd = breakdown_file({"business_rules": [{"size": "L", "points": 5}]})
    proc = run_script(
        APPLY_SCORE, "--story", str(story), "--breakdown", str(bd),
        "--baseline", str(baseline), *RULE_ARG,
        "--scored-by", "manual", "--now", "2026-05-17T12:00:00Z",
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["total"] == 5
    assert out["estimated_hours"] == 30.0  # 5 × 6.0, not 5 × the seed
    assert out["hours_per_bcp_source"] == "baseline:backend"


def test_provisional_category_uses_its_rate_not_seed(
    tmp_path, story_file, breakdown_file
):
    """A provisional rate (`is_seed: true`, below min_samples) still beats the
    seed. The gate used to withhold it, which fell back to a market rate as if
    it were a delivery forecast -- a unit error ~80x wide, traded for a ~20%
    sampling error. The source string keeps the two distinguishable."""
    baseline = tmp_path / "bcp-baseline.yaml"
    baseline.write_text(yaml.dump({
        "schema_version": "1.0",
        "config_snapshot": {"seed": SEED, "min_samples": 5,
                            "rolling_window": 10},
        "categories": {
            "frontend": {"h_per_bcp": 0.0598, "n_samples": 3, "is_seed": True},
        },
    }))
    story = story_file({"story_id": "k", "category": "frontend",
                        "estimated_hours": 5})
    bd = breakdown_file({"business_rules": [{"size": "L", "points": 5}]})
    proc = run_script(
        APPLY_SCORE, "--story", str(story), "--breakdown", str(bd),
        "--baseline", str(baseline), *RULE_ARG,
        "--scored-by", "manual", "--now", "2026-05-17T12:00:00Z",
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["estimated_hours"] == 0.3  # 5 × 0.0598, not 5 × the seed
    assert out["hours_per_bcp_source"] == "baseline:frontend:provisional"


def test_category_without_any_rate_falls_back_to_seed(
    tmp_path, story_file, breakdown_file
):
    """No samples at all is genuine cold start. Measured rates diverge up to 2x
    between categories, so there is no valid cross-category proxy -- the seed
    is the only answer available."""
    baseline = tmp_path / "bcp-baseline.yaml"
    baseline.write_text(yaml.dump({
        "schema_version": "1.0",
        "config_snapshot": {"seed": SEED, "min_samples": 5,
                            "rolling_window": 10},
        "categories": {
            "backend": {"h_per_bcp": 6.0, "n_samples": 7, "is_seed": False},
        },
    }))
    story = story_file({"story_id": "k", "category": "mobile",
                        "estimated_hours": 5})
    bd = breakdown_file({"business_rules": [{"size": "L", "points": 5}]})
    proc = run_script(
        APPLY_SCORE, "--story", str(story), "--breakdown", str(bd),
        "--baseline", str(baseline), *RULE_ARG,
        "--scored-by", "manual", "--now", "2026-05-17T12:00:00Z",
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["estimated_hours"] == round(5 * SEED, 2)
    assert out["hours_per_bcp_source"] == "seed"  # not baseline:backend
