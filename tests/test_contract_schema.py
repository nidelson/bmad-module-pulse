"""The BCP↔PULSE contract is data, not code (Approach A, schema-mediated).

BCP writes `estimated_hours`, `estimated_hours_pre_bcp`,
`estimated_hours_basis` and the `bcp.*` block. PULSE reads `estimated_hours`
writer-agnostically and owns `pulse_metrics`. Neither imports the other.
The only thing keeping them compatible is the frontmatter schema
(`bcp-frontmatter-1.0`) and a handful of write invariants. These tests are
that contract's executable specification — break one and the integration
silently rots.
"""
from __future__ import annotations

import json

import pytest
import yaml
from jsonschema import Draft202012Validator

from .conftest import APPLY_SCORE, COLD_START_SEED, run_script


def _validator(schema: dict) -> Draft202012Validator:
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_schema_is_valid_draft_2020_12(schema):
    """A malformed contract schema would pass nothing — guard the guard."""
    Draft202012Validator.check_schema(schema)
    assert schema["$id"].endswith("bcp-frontmatter-1.0")


def test_canonical_scored_frontmatter_validates(schema):
    fm = {
        "estimated_hours": 33.04,
        "estimated_hours_pre_bcp": 10,
        "estimated_hours_basis": "bcp",
        "hours_per_bcp": 4.13,
        "hours_per_bcp_source": "seed",
        "bcp": {
            "schema_version": "1.0",
            "rule_version": "1.0",
            "total": 8,
            "scored_at": "2026-05-17T12:00:00Z",
            "scored_by": "bruno",
            "breakdown": {
                "business_rules": [{"size": "M", "points": 3}],
                "interface_elements": [
                    {"size": "S", "points": 2},
                    {"size": "M", "points": 3, "note": "form"},
                ],
            },
            "history": [],
        },
    }
    _validator(schema).validate(fm)


@pytest.mark.parametrize("source", [
    "seed",                          # cold start: category has no samples
    "baseline:backend",              # calibrated
    "baseline:frontend:provisional",  # measured, still under min_samples
    "baseline:mcp-data",             # hyphens are legal in category names
])
def test_schema_accepts_every_real_source_form(schema, source):
    """The three states a factor can come from, plus a hyphenated category.

    A reader that branches on this string needs the full set pinned: the
    pattern is the only thing telling `baseline:x:provisional` apart from a
    typo, and a category name with a hyphen must not read as malformed.
    """
    fm = {
        "estimated_hours": 12, "estimated_hours_basis": "bcp",
        "hours_per_bcp": 0.0598, "hours_per_bcp_source": source,
        "bcp": {
            "schema_version": "1.0", "rule_version": "1.0", "total": 3,
            "scored_at": "2026-05-17T12:00:00Z", "scored_by": "manual",
            "breakdown": {"business_rules": [{"size": "M", "points": 3}]},
        },
    }
    _validator(schema).validate(fm)


def test_schema_still_validates_without_the_new_fields(schema):
    """Additive, not required: stories scored before this contract version have
    neither field, and must keep validating. A reader upgrades by treating
    absence as `unknown`, not by demanding a backfill."""
    fm = {
        "estimated_hours": 12, "estimated_hours_basis": "bcp",
        "bcp": {
            "schema_version": "1.0", "rule_version": "1.0", "total": 3,
            "scored_at": "2026-05-17T12:00:00Z", "scored_by": "manual",
            "breakdown": {"business_rules": [{"size": "M", "points": 3}]},
        },
    }
    _validator(schema).validate(fm)


@pytest.mark.parametrize("mutate,reason", [
    (lambda fm: fm["bcp"].pop("total"), "missing required bcp.total"),
    (lambda fm: fm["bcp"]["breakdown"]["business_rules"][0].update(
        {"size": "XXL", "points": 13}), "size outside the Fibonacci enum"),
    (lambda fm: fm["bcp"]["breakdown"]["business_rules"][0].update(
        {"points": 4}), "points outside {1,2,3,5,8}"),
    (lambda fm: fm.update({"estimated_hours_basis": "guess"}),
     "basis outside {bcp,agent}"),
    (lambda fm: fm["bcp"].update({"scored_by": "robot"}),
     "scored_by outside the allowed enum"),
    (lambda fm: fm.update({"estimated_hours": -1}),
     "negative estimated_hours"),
    (lambda fm: fm.update({"hours_per_bcp_source": "baseline"}),
     "source naming no category"),
    (lambda fm: fm.update({"hours_per_bcp_source": "guess"}),
     "source outside {seed, baseline:*}"),
    (lambda fm: fm.update({"hours_per_bcp_source": "baseline:backend:draft"}),
     "qualifier other than :provisional"),
    (lambda fm: fm.update({"hours_per_bcp": 0}),
     "zero factor — every story would plan at 0h"),
])
def test_schema_rejects_contract_violations(schema, mutate, reason):
    fm = {
        "estimated_hours": 12,
        "estimated_hours_basis": "bcp",
        "bcp": {
            "schema_version": "1.0", "rule_version": "1.0", "total": 3,
            "scored_at": "2026-05-17T12:00:00Z", "scored_by": "manual",
            "breakdown": {"business_rules": [{"size": "M", "points": 3}]},
        },
    }
    mutate(fm)
    with pytest.raises(Exception):
        _validator(schema).validate(fm)


def test_apply_score_output_validates_against_contract(
    schema, seeded_baseline, story_file, breakdown_file
):
    story = story_file({"story_id": "1.1", "category": "backend",
                         "estimated_hours": 10})
    bd = breakdown_file({"business_rules": [{"size": "L", "points": 5}],
                         "audits": [{"size": "XS", "points": 1}]})
    proc = run_script(
        APPLY_SCORE,
        "--story", str(story), "--breakdown", str(bd),
        "--baseline", str(seeded_baseline),
        "--rule", "skills/bmad-bcp-rule-card/assets/bcp-rule.yaml",
        "--scored-by", "manual",
        "--now", "2026-05-17T12:00:00Z",
    )
    assert proc.returncode == 0, proc.stderr
    written = yaml.safe_load(story.read_text().split("---")[1])
    _validator(schema).validate(written)
    assert written["bcp"]["total"] == 6
    assert written["estimated_hours"] == round(6 * COLD_START_SEED, 2)
    assert written["estimated_hours_basis"] == "bcp"


def test_bcp_never_writes_pulse_metrics_and_preserves_it(
    seeded_baseline, story_file, breakdown_file
):
    """The hard ownership boundary: BCP must leave `pulse_metrics`
    byte-for-byte untouched and never introduce it."""
    sentinel = {"actual_hours": 4, "leverage": 2.5, "_owner": "pulse"}
    story = story_file({"story_id": "2.1", "category": "frontend",
                         "estimated_hours": 8, "pulse_metrics": sentinel})
    bd = breakdown_file({"business_rules": [{"size": "M", "points": 3}]})
    proc = run_script(
        APPLY_SCORE,
        "--story", str(story), "--breakdown", str(bd),
        "--baseline", str(seeded_baseline),
        "--rule", "skills/bmad-bcp-rule-card/assets/bcp-rule.yaml",
        "--scored-by", "manual", "--now", "2026-05-17T12:00:00Z",
    )
    assert proc.returncode == 0, proc.stderr
    written = yaml.safe_load(story.read_text().split("---")[1])
    assert written["pulse_metrics"] == sentinel, (
        "BCP mutated PULSE-owned pulse_metrics — ownership boundary breach"
    )


def test_estimated_hours_pre_bcp_is_write_once(
    seeded_baseline, story_file, breakdown_file
):
    """The original (pre-BCP) estimate is audit data captured exactly
    once. A rescore must not clobber it with the now-BCP value."""
    story = story_file({"story_id": "3.1", "category": "backend",
                         "estimated_hours": 10})
    bd1 = breakdown_file({"business_rules": [{"size": "M", "points": 3}]})
    rule_arg = ("--rule", "skills/bmad-bcp-rule-card/assets/bcp-rule.yaml")

    p1 = run_script(APPLY_SCORE, "--story", str(story),
                    "--breakdown", str(bd1), "--baseline",
                    str(seeded_baseline), *rule_arg, "--scored-by",
                    "manual", "--now", "2026-05-17T12:00:00Z")
    assert p1.returncode == 0, p1.stderr
    first = yaml.safe_load(story.read_text().split("---")[1])
    assert first["estimated_hours_pre_bcp"] == 10

    bd2 = (story.parent / "bd2.json")
    bd2.write_text(json.dumps({"breakdown": {
        "business_rules": [{"size": "XL", "points": 8}]}}))
    p2 = run_script(APPLY_SCORE, "--story", str(story),
                    "--breakdown", str(bd2), "--baseline",
                    str(seeded_baseline), *rule_arg, "--scored-by",
                    "rescore", "--rescore", "--now",
                    "2026-05-18T12:00:00Z")
    assert p2.returncode == 0, p2.stderr
    second = yaml.safe_load(story.read_text().split("---")[1])
    assert second["estimated_hours_pre_bcp"] == 10, (
        "estimated_hours_pre_bcp overwritten on rescore — audit trail lost"
    )
    assert second["bcp"]["history"], "rescore must archive prior score"
