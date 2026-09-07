"""`seed_baseline.py` — the file every scoring run reads.

Ported from the standalone module's installer (issue #84). It looked like setup
scaffolding, which is why it was nearly left behind, but `apply_score.py` errors
when `bcp-baseline.yaml` is missing — so creating it is part of the runtime
contract, not of installation.
"""
from __future__ import annotations

import json

import yaml

from .conftest import COLD_START_SEED, SEED_BASELINE, run_script


def seed(path, *extra: str):
    return run_script(
        SEED_BASELINE,
        "--baseline-path", str(path),
        "--seed", str(COLD_START_SEED),
        "--min-samples", "5",
        "--rolling-window", "10",
        *extra,
    )


def test_creates_a_cold_start_baseline(tmp_path):
    dest = tmp_path / "bcp-baseline.yaml"
    proc = seed(dest)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["action"] == "created"

    written = yaml.safe_load(dest.read_text(encoding="utf-8"))
    assert written["config_snapshot"]["seed"] == COLD_START_SEED
    assert written["config_snapshot"]["min_samples"] == 5
    assert written["config_snapshot"]["rolling_window"] == 10
    # Empty on purpose: categories are earned from real actual_hours by
    # bmad-bcp-recalibrate, never guessed at setup time.
    assert written["categories"] == {}


def test_existing_baseline_is_left_untouched(tmp_path):
    """The migration guard.

    A project moving off the standalone module already has a baseline holding
    every sample its team accumulated. Setup runs again on that project, and a
    seeding step that overwrote by default would silently discard the
    calibration — replacing measured rates with the cold-start seed while
    reporting success.
    """
    dest = tmp_path / "bcp-baseline.yaml"
    calibrated = {
        "schema_version": "1.0",
        "config_snapshot": {"seed": 0.06, "min_samples": 5, "rolling_window": 10},
        "categories": {
            "backend": {"h_per_bcp": 0.42, "n_samples": 9, "is_seed": False},
        },
    }
    dest.write_text(yaml.dump(calibrated), encoding="utf-8")
    before = dest.read_bytes()

    proc = seed(dest)

    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["action"] == "skipped_exists"
    assert dest.read_bytes() == before, "an existing baseline MUST be byte-stable"


def test_force_overwrites_and_says_so(tmp_path):
    """`--force` is the explicit start-over. The reported action has to name what
    happened: it previously asked whether the file existed *after* writing it,
    when the answer is always yes, so a fresh path reported `overwritten`."""
    dest = tmp_path / "bcp-baseline.yaml"
    dest.write_text(yaml.dump({"categories": {"backend": {"h_per_bcp": 0.42}}}),
                    encoding="utf-8")

    proc = seed(dest, "--force")

    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["action"] == "overwritten"
    assert yaml.safe_load(dest.read_text(encoding="utf-8"))["categories"] == {}


def test_force_on_a_fresh_path_reports_created(tmp_path):
    proc = seed(tmp_path / "nested" / "bcp-baseline.yaml", "--force")
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["action"] == "created"


def test_default_seed_matches_the_module_default(tmp_path):
    """The argparse default and `_BCP_DEFAULTS` are two copies of one number.

    A caller that omits `--seed` must land on the same rate the scoring skills
    resolve when nothing is configured; otherwise a project's cold start and its
    resolved config disagree about what the seed is.
    """
    dest = tmp_path / "bcp-baseline.yaml"
    proc = run_script(SEED_BASELINE, "--baseline-path", str(dest))
    assert proc.returncode == 0, proc.stderr
    written = yaml.safe_load(dest.read_text(encoding="utf-8"))
    assert written["config_snapshot"]["seed"] == COLD_START_SEED


def test_scoring_works_end_to_end_against_a_seeded_baseline(
    tmp_path, story_file, breakdown_file
):
    """The gap this port closes, stated as a test.

    Before it, a PULSE-only project that enabled scoring had no baseline and
    nothing that made one; `apply_score.py` answered with
    `status: error` and a missing-file path.
    """
    from .conftest import APPLY_SCORE

    dest = tmp_path / "bcp-baseline.yaml"
    assert seed(dest).returncode == 0

    story = story_file({"story_id": "1.1", "category": "backend"})
    bd = breakdown_file({"business_rules": [{"size": "L", "points": 5}]})
    proc = run_script(
        APPLY_SCORE,
        "--story", str(story), "--breakdown", str(bd),
        "--baseline", str(dest),
        "--rule", "skills/bmad-bcp-rule-card/assets/bcp-rule.yaml",
        "--scored-by", "manual", "--now", "2026-05-17T12:00:00Z",
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["estimated_hours"] == round(5 * COLD_START_SEED, 2)
    assert out["hours_per_bcp_source"] == "seed"
