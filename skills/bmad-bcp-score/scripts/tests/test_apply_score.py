#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml", "pytest"]
# ///
"""Unit tests for apply_score.py — the deterministic BCP scoring engine.

Run: uv run --with pytest --with pyyaml pytest skills/bmad-bcp-score/scripts/tests/
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parent.parent / "apply_score.py"
# Vendored copy of BMAD core's resolver. The BCP module carried it at
# `_bmad/scripts/` because that repo had BMAD installed into itself; PULSE does
# not, and would not gain anything from pretending to. What these tests need is
# a real resolver to seed a fake consumer project with — that is a fixture, and
# naming it one keeps it from being mistaken for an installed toolchain.
CORE_RESOLVER = (
    Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "bmad-core" / "resolve_config.py"
)


def _rule(tmp: Path) -> Path:
    p = tmp / "bcp-rule.yaml"
    p.write_text(yaml.dump({
        "rule_version": "1.0",
        "sizes": {"XS": 1, "S": 2, "M": 3, "L": 5, "XL": 8},
        "elements": [
            {"slug": "business_rules"}, {"slug": "audits"},
            {"slug": "domain_entities"},
        ],
    }))
    return p


def _baseline(tmp: Path, categories=None) -> Path:
    p = tmp / "bcp-baseline.yaml"
    p.write_text(yaml.dump({
        "schema_version": "1.0",
        "config_snapshot": {"seed": 4.13, "min_samples": 5, "rolling_window": 10},
        "categories": categories or {},
    }))
    return p


def _story(tmp: Path, fm: dict, body="# Story\n\nCorpo.\n") -> Path:
    p = tmp / "story.md"
    p.write_text(f"---\n{yaml.dump(fm, sort_keys=False)}---\n{body}")
    return p


def _bd(tmp: Path, breakdown: dict) -> Path:
    p = tmp / "bd.json"
    p.write_text(json.dumps({"breakdown": breakdown}))
    return p


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True)


def test_score_and_derive_seed(tmp_path: Path):
    story = _story(tmp_path, {"story_id": "1.1", "category": "backend",
                              "estimated_hours": 80})
    bd = _bd(tmp_path, {"business_rules": [{"size": "XL", "points": 8}],
                        "audits": [{"size": "XS", "points": 1}]})
    r = run("--story", str(story), "--breakdown", str(bd),
            "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual", "--now", "2026-05-17T00:00:00Z")
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["total"] == 9
    assert out["hours_per_bcp"] == 4.13
    assert out["hours_per_bcp_source"] == "seed"
    assert out["estimated_hours"] == round(9 * 4.13, 2)
    fm, _, _ = _split(story.read_text())
    assert fm["estimated_hours_pre_bcp"] == 80          # original captured
    assert fm["estimated_hours_basis"] == "bcp"
    # The factor reaches the FILE, not just the JSON. Before this, a reader
    # holding only the story had to divide and guess which rate produced it.
    assert fm["hours_per_bcp"] == 4.13
    assert fm["hours_per_bcp_source"] == "seed"
    assert fm["bcp"]["total"] == 9
    assert fm["bcp"]["scored_at"] == "2026-05-17T00:00:00Z"


def test_written_factor_reproduces_the_written_hours(tmp_path: Path):
    """`estimated_hours == bcp.total × hours_per_bcp`, checkable from the story
    alone. This is the point of writing the factor: the baseline is mutable and
    will have moved on by the time anyone audits an old story."""
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10})
    bd = _bd(tmp_path, {"business_rules": [{"size": "L", "points": 5}]})
    base = _baseline(tmp_path, {"backend": {"h_per_bcp": 0.0691, "is_seed": False}})
    r = run("--story", str(story), "--breakdown", str(bd), "--baseline",
            str(base), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual", "--now", "2026-05-17T00:00:00Z")
    assert r.returncode == 0, r.stdout + r.stderr
    fm, _, _ = _split(story.read_text())
    assert fm["hours_per_bcp_source"] == "baseline:backend"
    assert fm["estimated_hours"] == round(fm["bcp"]["total"] * fm["hours_per_bcp"], 2)


def test_provisional_source_is_marked_in_the_file(tmp_path: Path):
    """A provisional factor is used, and says so. Same number either way, so
    the string is the only thing a reader can branch on."""
    story = _story(tmp_path, {"category": "frontend", "estimated_hours": 10})
    bd = _bd(tmp_path, {"business_rules": [{"size": "L", "points": 5}]})
    base = _baseline(tmp_path, {"frontend": {"h_per_bcp": 0.0598, "is_seed": True}})
    r = run("--story", str(story), "--breakdown", str(bd), "--baseline",
            str(base), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual", "--now", "2026-05-17T00:00:00Z")
    assert r.returncode == 0, r.stdout + r.stderr
    fm, _, _ = _split(story.read_text())
    assert fm["hours_per_bcp"] == 0.0598
    assert fm["hours_per_bcp_source"] == "baseline:frontend:provisional"


def test_baseline_category_overrides_seed(tmp_path: Path):
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})
    base = _baseline(tmp_path, {"backend": {"h_per_bcp": 6.0, "is_seed": False}})
    r = run("--story", str(story), "--breakdown", str(bd), "--baseline",
            str(base), "--rule", str(_rule(tmp_path)), "--scored-by", "manual")
    out = json.loads(r.stdout)
    assert out["hours_per_bcp"] == 6.0
    assert out["hours_per_bcp_source"] == "baseline:backend"
    assert out["estimated_hours"] == 18.0


def test_pre_bcp_set_once_idempotent(tmp_path: Path):
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 80})
    bd = _bd(tmp_path, {"audits": [{"size": "S", "points": 2}]})
    common = ("--baseline", str(_baseline(tmp_path)), "--rule",
              str(_rule(tmp_path)), "--scored-by", "manual")
    run("--story", str(story), "--breakdown", str(bd), *common)
    fm1, _, _ = _split(story.read_text())
    assert fm1["estimated_hours_pre_bcp"] == 80
    # re-run: pre_bcp must NOT become the BCP-derived value
    run("--story", str(story), "--breakdown", str(bd), *common)
    fm2, _, _ = _split(story.read_text())
    assert fm2["estimated_hours_pre_bcp"] == 80


def test_pulse_metrics_untouched(tmp_path: Path):
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 40,
                              "pulse_metrics": {"actual_hours": 33, "x": [1, 2]}})
    bd = _bd(tmp_path, {"business_rules": [{"size": "L", "points": 5}]})
    run("--story", str(story), "--breakdown", str(bd), "--baseline",
        str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
        "--scored-by", "manual")
    fm, body, _ = _split(story.read_text())
    assert fm["pulse_metrics"] == {"actual_hours": 33, "x": [1, 2]}
    assert "Corpo." in body


def test_rescore_history_and_delta_advisory(tmp_path: Path):
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 8})
    rule, base = _rule(tmp_path), _baseline(tmp_path)
    run("--story", str(story), "--breakdown",
        str(_bd(tmp_path, {"business_rules": [{"size": "S", "points": 2}]})),
        "--baseline", str(base), "--rule", str(rule), "--scored-by", "manual")
    # rescore much bigger -> >50% delta advisory + history grows
    bd2 = tmp_path / "bd2.json"
    bd2.write_text(json.dumps({"breakdown":
        {"business_rules": [{"size": "XL", "points": 8}]}}))
    r = run("--story", str(story), "--breakdown", str(bd2), "--baseline",
            str(base), "--rule", str(rule), "--scored-by", "rescore",
            "--rescore")
    out = json.loads(r.stdout)
    assert out["history_len"] == 1
    assert any("split" in a for a in out["advisories"])
    fm, _, _ = _split(story.read_text())
    assert fm["bcp"]["history"][0]["total"] == 2
    assert fm["bcp"]["total"] == 8


def test_dry_run_does_not_write(tmp_path: Path):
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 50})
    before = story.read_text()
    bd = _bd(tmp_path, {"audits": [{"size": "XS", "points": 1}]})
    r = run("--story", str(story), "--breakdown", str(bd), "--baseline",
            str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual", "--dry-run")
    out = json.loads(r.stdout)
    assert out["dry_run"] is True
    assert "preview_frontmatter" in out
    assert story.read_text() == before          # untouched


def test_invalid_points_rejected(tmp_path: Path):
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 1})
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"breakdown":
        {"business_rules": [{"size": "M", "points": 99}]}}))
    r = run("--story", str(story), "--breakdown", str(bad), "--baseline",
            str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual")
    assert r.returncode == 1
    assert "Fibonacci" in json.loads(r.stdout)["error"]


def test_unknown_slug_rejected(tmp_path: Path):
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 1})
    bad = _bd(tmp_path, {"not_an_element": [{"size": "M", "points": 3}]})
    r = run("--story", str(story), "--breakdown", str(bad), "--baseline",
            str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual")
    assert r.returncode == 1
    assert "unknown element slug" in json.loads(r.stdout)["error"]


# minimal frontmatter splitter mirroring the script (test helper)
def _split(text: str):
    parts = text.split("---", 2)
    return yaml.safe_load(parts[1]), parts[2], "\n"


if __name__ == "__main__":
    sys.exit(subprocess.call(
        ["uv", "run", "--with", "pytest", "--with", "pyyaml",
         "pytest", "-q", str(Path(__file__).parent)]))


# ── Reference rate / estimated_hours_reference (issue #32) ───────────────────

def test_reference_defaults_to_seed(tmp_path: Path):
    """Sem --reference-h-per-bcp: a âncora usa o seed do baseline."""
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 80})
    bd = _bd(tmp_path, {"business_rules": [{"size": "XL", "points": 8}]})
    r = run("--story", str(story), "--breakdown", str(bd),
            "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual")
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["reference_h_per_bcp"] == 4.13
    assert out["reference_source"] == "seed"
    assert out["estimated_hours_reference"] == round(8 * 4.13, 2)
    fm, _, _ = _split(story.read_text())
    assert fm["estimated_hours_reference"] == round(8 * 4.13, 2)


def test_reference_explicit_rate_distinct_from_plan(tmp_path: Path):
    """--reference-h-per-bcp fixa a âncora; o plano segue o fator (seed) — números distintos."""
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})
    r = run("--story", str(story), "--breakdown", str(bd),
            "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual", "--reference-h-per-bcp", "5.0")
    out = json.loads(r.stdout)
    assert out["reference_h_per_bcp"] == 5.0
    assert out["reference_source"] == "config"
    assert out["estimated_hours_reference"] == 15.0      # 3 × 5.0 (âncora frozen)
    assert out["estimated_hours"] == round(3 * 4.13, 2)  # plano via seed


def test_reference_frozen_while_plan_recalibrates(tmp_path: Path):
    """Categoria calibrada: plano usa o fator vivo; âncora fica na reference rate."""
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})
    base = _baseline(tmp_path, {"backend": {"h_per_bcp": 0.5, "is_seed": False}})
    r = run("--story", str(story), "--breakdown", str(bd), "--baseline",
            str(base), "--rule", str(_rule(tmp_path)), "--scored-by", "manual",
            "--reference-h-per-bcp", "5.0")
    out = json.loads(r.stdout)
    assert out["hours_per_bcp"] == 0.5                   # plano: fator recalibrado
    assert out["estimated_hours"] == 1.5                 # 3 × 0.5
    assert out["reference_h_per_bcp"] == 5.0             # âncora: reference rate
    assert out["estimated_hours_reference"] == 15.0      # 3 x 5.0 (does not collapse)


def test_reference_recomputes_on_rescore(tmp_path: Path):
    """Rescore muda o total → a âncora reflete o novo total × mesma reference rate."""
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 8})
    rule, base = _rule(tmp_path), _baseline(tmp_path)
    run("--story", str(story), "--breakdown",
        str(_bd(tmp_path, {"business_rules": [{"size": "S", "points": 2}]})),
        "--baseline", str(base), "--rule", str(rule), "--scored-by", "manual",
        "--reference-h-per-bcp", "5.0")
    fm1, _, _ = _split(story.read_text())
    assert fm1["estimated_hours_reference"] == 10.0      # 2 × 5.0
    bd2 = tmp_path / "bd2.json"
    bd2.write_text(json.dumps({"breakdown":
        {"business_rules": [{"size": "XL", "points": 8}]}}))
    run("--story", str(story), "--breakdown", str(bd2), "--baseline", str(base),
        "--rule", str(rule), "--scored-by", "rescore", "--rescore",
        "--reference-h-per-bcp", "5.0")
    fm2, _, _ = _split(story.read_text())
    assert fm2["estimated_hours_reference"] == 40.0      # 8 × 5.0


def test_reference_dry_run_not_written(tmp_path: Path):
    """--dry-run shows the anchor in the preview but does not write the file."""
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 50})
    before = story.read_text()
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})
    r = run("--story", str(story), "--breakdown", str(bd), "--baseline",
            str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual", "--reference-h-per-bcp", "5.0", "--dry-run")
    out = json.loads(r.stdout)
    assert out["estimated_hours_reference"] == 15.0
    assert out["preview_frontmatter"]["estimated_hours_reference"] == 15.0
    assert story.read_text() == before


# ── Sprint-status history store (issue #19) ──────────────────────────────────

def test_sprint_status_flag_writes_history_there(tmp_path: Path):
    """With --sprint-status: history goes to sprint-status, not story frontmatter."""
    sprint = tmp_path / "sprint-status.yaml"
    sprint.write_text("development_status: {}\n", encoding="utf-8")

    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10,
                               "bcp": {"schema_version": "1.0", "rule_version": "1.0",
                                       "total": 2, "scored_at": "2026-01-01T00:00:00Z",
                                       "scored_by": "manual", "breakdown": {},
                                       "history": []}})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})
    r = run("--story", str(story), "--breakdown", str(bd),
            "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "rescore", "--rescore",
            "--sprint-status", str(sprint))
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["history_store"] == "sprint-status"

    fm = yaml.safe_load(story.read_text().split("---", 2)[1])
    assert "history" not in fm.get("bcp", {}), "history should not be in story frontmatter"

    ss = yaml.safe_load(sprint.read_text())
    story_key = story.stem
    hist = ss["bcp_metrics"][story_key]["history"]
    assert len(hist) == 1
    assert hist[0]["total"] == 2


def test_sprint_status_history_store_field(tmp_path: Path):
    """Without --sprint-status: history_store is 'story-frontmatter'."""
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})
    r = run("--story", str(story), "--breakdown", str(bd),
            "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual")
    assert r.returncode == 0
    assert json.loads(r.stdout)["history_store"] == "story-frontmatter"


def test_sprint_status_idempotent_history(tmp_path: Path):
    """Rescoring twice via sprint-status accumulates history without duplication."""
    sprint = tmp_path / "sprint-status.yaml"
    sprint.write_text("development_status: {}\n", encoding="utf-8")

    bcp_block = {"schema_version": "1.0", "rule_version": "1.0",
                 "total": 2, "scored_at": "2026-01-01T00:00:00Z",
                 "scored_by": "manual", "breakdown": {}}
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10,
                               "bcp": bcp_block})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})

    base_args = ["--story", str(story), "--breakdown", str(bd),
                 "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
                 "--scored-by", "rescore", "--rescore",
                 "--sprint-status", str(sprint)]

    r1 = run(*base_args)
    assert r1.returncode == 0

    # Update story's bcp.total to simulate a new current score before second rescore
    fm = yaml.safe_load(story.read_text().split("---", 2)[1])
    fm["bcp"]["total"] = 3
    fm["bcp"]["scored_at"] = "2026-02-01T00:00:00Z"
    story.write_text(f"---\n{yaml.dump(fm)}---\n# body\n", encoding="utf-8")

    r2 = run(*base_args)
    assert r2.returncode == 0

    ss = yaml.safe_load(sprint.read_text())
    hist = ss["bcp_metrics"][story.stem]["history"]
    assert len(hist) == 2
    assert hist[0]["total"] == 2
    assert hist[1]["total"] == 3


# ── --project-root auto-detection (issue #25) ────────────────────────────────

def _bmad_config(tmp_path: Path, output_folder: str | None = None) -> Path:
    """Write a minimal _bmad/config.yaml with pulse section."""
    bmad = tmp_path / "_bmad"
    bmad.mkdir(exist_ok=True)
    of = output_folder or f"{tmp_path}/_bmad-output"
    cfg = {
        "output_folder": of,
        "pulse": {
            "pulse_data_folder": "{output_folder}/implementation-artifacts",
            "pulse_sprint_status_filename": "sprint-status.yaml",
        },
    }
    p = bmad / "config.yaml"
    p.write_text(yaml.dump(cfg), encoding="utf-8")
    return p


def test_project_root_auto_detects_sprint_status(tmp_path: Path):
    """--project-root resolves sprint-status path from config token chain."""
    # Create sprint-status at the derived location
    impl = tmp_path / "_bmad-output/implementation-artifacts"
    impl.mkdir(parents=True)
    sprint = impl / "sprint-status.yaml"
    sprint.write_text("development_status: {}\n", encoding="utf-8")
    _bmad_config(tmp_path)

    bcp_block = {"schema_version": "1.0", "rule_version": "1.0",
                 "total": 2, "scored_at": "2026-01-01T00:00:00Z",
                 "scored_by": "manual", "breakdown": {}}
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10,
                               "bcp": bcp_block})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})

    r = run("--story", str(story), "--breakdown", str(bd),
            "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "rescore", "--rescore",
            "--project-root", str(tmp_path))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["history_store"] == "sprint-status"

    fm = yaml.safe_load(story.read_text().split("---", 2)[1])
    assert "history" not in fm.get("bcp", {})

    ss = yaml.safe_load(sprint.read_text())
    assert story.stem in ss.get("bcp_metrics", {})


def test_project_root_falls_back_to_legacy_when_sprint_status_missing(tmp_path: Path):
    """--project-root with no sprint-status file → legacy mode, no error."""
    _bmad_config(tmp_path)  # config exists but sprint-status does not

    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})

    r = run("--story", str(story), "--breakdown", str(bd),
            "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual",
            "--project-root", str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["history_store"] == "story-frontmatter"


def test_explicit_sprint_status_overrides_project_root(tmp_path: Path):
    """--sprint-status explicit path wins over --project-root auto-detection."""
    # Config points to wrong location
    wrong = tmp_path / "wrong/sprint-status.yaml"
    wrong.parent.mkdir(parents=True)
    wrong.write_text("development_status: {}\n", encoding="utf-8")
    _bmad_config(tmp_path, output_folder=str(wrong.parent.parent))

    # Explicit sprint-status at a different path
    correct = tmp_path / "correct-sprint-status.yaml"
    correct.write_text("development_status: {}\n", encoding="utf-8")

    bcp_block = {"schema_version": "1.0", "rule_version": "1.0",
                 "total": 2, "scored_at": "2026-01-01T00:00:00Z",
                 "scored_by": "manual", "breakdown": {}}
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10,
                               "bcp": bcp_block})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})

    r = run("--story", str(story), "--breakdown", str(bd),
            "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "rescore", "--rescore",
            "--project-root", str(tmp_path),
            "--sprint-status", str(correct))
    assert r.returncode == 0, r.stderr

    # History should be in the explicit file, not the auto-detected one
    ss_correct = yaml.safe_load(correct.read_text())
    ss_wrong = yaml.safe_load(wrong.read_text())
    assert story.stem in ss_correct.get("bcp_metrics", {})
    assert "bcp_metrics" not in ss_wrong


def test_project_root_without_bmad_config_falls_back_to_legacy(tmp_path: Path):
    """--project-root with no _bmad/config.{toml,yaml} → legacy mode gracefully."""
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})

    r = run("--story", str(story), "--breakdown", str(bd),
            "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "manual",
            "--project-root", str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["history_store"] == "story-frontmatter"


# ── toml-first sprint-status resolution (issue #36) ──────────────────────────

needs_py311 = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="core resolve_config.py needs stdlib tomllib (Python 3.11+)",
)


def _install_resolver(tmp_path: Path) -> None:
    scripts = tmp_path / "_bmad" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    assert CORE_RESOLVER.exists(), f"core resolver missing at {CORE_RESOLVER}"
    shutil.copy(CORE_RESOLVER, scripts / "resolve_config.py")


def _bmad_config_toml(tmp_path: Path, output_folder: str,
                      data_folder: str = "{output_folder}/implementation-artifacts") -> None:
    """Write a minimal config.toml with [core] + [modules.pulse]."""
    bmad = tmp_path / "_bmad"
    bmad.mkdir(parents=True, exist_ok=True)
    (bmad / "config.toml").write_text(
        "[core]\n"
        f'output_folder = "{output_folder}"\n\n'
        "[modules.pulse]\n"
        f'pulse_data_folder = "{data_folder}"\n'
        'pulse_sprint_status_filename = "sprint-status.yaml"\n',
        encoding="utf-8",
    )


@needs_py311
def test_project_root_auto_detects_sprint_status_from_toml(tmp_path: Path):
    """config.toml-only install resolves sprint-status via the core resolver."""
    impl = tmp_path / "_bmad-output/implementation-artifacts"
    impl.mkdir(parents=True)
    sprint = impl / "sprint-status.yaml"
    sprint.write_text("development_status: {}\n", encoding="utf-8")

    _install_resolver(tmp_path)
    _bmad_config_toml(tmp_path, output_folder=f"{tmp_path}/_bmad-output")

    bcp_block = {"schema_version": "1.0", "rule_version": "1.0",
                 "total": 2, "scored_at": "2026-01-01T00:00:00Z",
                 "scored_by": "manual", "breakdown": {}}
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10,
                               "bcp": bcp_block})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})

    r = run("--story", str(story), "--breakdown", str(bd),
            "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "rescore", "--rescore",
            "--project-root", str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["history_store"] == "sprint-status"
    ss = yaml.safe_load(sprint.read_text())
    assert story.stem in ss.get("bcp_metrics", {})


@needs_py311
def test_toml_wins_over_yaml_for_sprint_status(tmp_path: Path):
    """When both config sources exist, the toml chain wins (per-key)."""
    # toml points at the CORRECT location
    good = tmp_path / "_bmad-output/implementation-artifacts"
    good.mkdir(parents=True)
    (good / "sprint-status.yaml").write_text("development_status: {}\n", encoding="utf-8")
    _install_resolver(tmp_path)
    _bmad_config_toml(tmp_path, output_folder=f"{tmp_path}/_bmad-output")

    # yaml (legacy bridge) points at a WRONG/stale location
    wrong = tmp_path / "stale/implementation-artifacts"
    wrong.mkdir(parents=True)
    (wrong / "sprint-status.yaml").write_text("development_status: {}\n", encoding="utf-8")
    (tmp_path / "_bmad/config.yaml").write_text(
        f"output_folder: '{tmp_path}/stale'\n"
        "pulse:\n"
        "  pulse_data_folder: '{output_folder}/implementation-artifacts'\n"
        "  pulse_sprint_status_filename: sprint-status.yaml\n",
        encoding="utf-8",
    )

    bcp_block = {"schema_version": "1.0", "rule_version": "1.0",
                 "total": 2, "scored_at": "2026-01-01T00:00:00Z",
                 "scored_by": "manual", "breakdown": {}}
    story = _story(tmp_path, {"category": "backend", "estimated_hours": 10,
                               "bcp": bcp_block})
    bd = _bd(tmp_path, {"business_rules": [{"size": "M", "points": 3}]})

    r = run("--story", str(story), "--breakdown", str(bd),
            "--baseline", str(_baseline(tmp_path)), "--rule", str(_rule(tmp_path)),
            "--scored-by", "rescore", "--rescore",
            "--project-root", str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["history_store"] == "sprint-status"
    # history landed in the toml-resolved (correct) file, not the yaml (stale) one
    assert story.stem in yaml.safe_load((good / "sprint-status.yaml").read_text()).get("bcp_metrics", {})
    assert "bcp_metrics" not in yaml.safe_load((wrong / "sprint-status.yaml").read_text())
