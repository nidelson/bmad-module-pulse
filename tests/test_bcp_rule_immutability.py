"""The BCP ruler may not change without a `rule_version` bump.

Under MIT the ruler is legally modifiable — CI&T released it as open source in
May 2026, so nothing legal stops an edit. What an edit destroys is the only
property that makes a BCP score meaningful outside the team that produced it:
10 BCP from one squad must be 10 BCP from another, or recalibration converges on
nothing and predictability measures the estimator instead of the delivery.

So immutability is a design decision, and a design decision without a test is a
preference. This module pins the canonical content — sizes and the 10 elements
with their definitions and descriptors — to a digest recorded per
`rule_version`. Changing the ruler is allowed; changing it silently is not.

**When this test fails and the change was intentional:** bump `rule_version` in
`assets/bcp-rule.yaml`, add the new digest to `EXPECTED_DIGESTS`, and keep the
old entry. Scores produced under different rule versions do not compare, and the
history of digests is what lets a reader tell which ruler a past score used.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
RULE = REPO_ROOT / "skills/bmad-bcp-rule-card/assets/bcp-rule.yaml"

# Digest of the canonical content per rule_version. Never edit an existing
# entry — add a new one. An edited entry hides exactly the divergence this
# module exists to surface.
EXPECTED_DIGESTS = {
    "1.0": "5ab95fea8bdccace60c3d256c6e220f420a366a19fdca275b622313e3fb310c1",
}

FIBONACCI_SCALE = {"XS": 1, "S": 2, "M": 3, "L": 5, "XL": 8}
CANONICAL_ELEMENT_COUNT = 10
ALWAYS_THERE_COUNT = 4

# The ten element slugs, frozen. `test_golden_scoring` generates its 50-case
# matrix from this set, so a slug renamed in the rule without being renamed here
# fails as a missing element rather than silently dropping the case.
FROZEN_SLUGS = {
    "business_rules", "interface_elements", "roles_permissions",
    "solution_variabilities", "boundaries", "domain_entities",
    "new_domain_entities", "background_processes", "notifications",
    "audits",
}


@pytest.fixture(scope="module")
def rule() -> dict:
    return yaml.safe_load(RULE.read_text(encoding="utf-8"))


def canonical_digest(rule: dict) -> str:
    """Digest the parts that must not drift.

    Deliberately excludes `license`, comments and any editorial `hints`: those
    may be corrected or expanded without affecting what a score means. Only the
    scale and the elements decide the number a team produces.
    """
    payload = {
        "sizes": rule["sizes"],
        "elements": [
            {
                "name": el["name"],
                "slug": el["slug"],
                "always_there": el["always_there"],
                "definition": el["definition"],
                "descriptors": el["descriptors"],
            }
            for el in rule["elements"]
        ],
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def test_rule_version_is_registered(rule: dict):
    version = rule["rule_version"]
    assert version in EXPECTED_DIGESTS, (
        f"rule_version {version!r} has no registered digest. If you bumped the "
        f"version deliberately, add its digest to EXPECTED_DIGESTS."
    )


def test_canonical_content_matches_registered_digest(rule: dict):
    version = rule["rule_version"]
    actual = canonical_digest(rule)
    expected = EXPECTED_DIGESTS.get(version)
    assert actual == expected, (
        f"The BCP ruler changed while rule_version stayed at {version!r}.\n"
        f"  expected {expected}\n  actual   {actual}\n"
        f"Scores are only comparable across teams when the ruler is identical. "
        f"If the change is intentional, bump rule_version and register the new "
        f"digest — do not overwrite the existing entry."
    )


def test_scale_is_the_canonical_fibonacci(rule: dict):
    assert rule["sizes"] == FIBONACCI_SCALE


def test_element_count_and_always_there_bracket(rule: dict):
    elements = rule["elements"]
    assert len(elements) == CANONICAL_ELEMENT_COUNT
    always = [el for el in elements if el["always_there"]]
    assert len(always) == ALWAYS_THERE_COUNT, (
        "the canonical ruler brackets exactly four elements under ALWAYS THERE"
    )


def test_every_element_covers_every_size(rule: dict):
    """A missing key is not the same as an empty cell.

    `null` means the canonical ruler leaves the cell blank, and the rule card
    renders it as a dash. A key that is simply absent would render as an error
    or, worse, be silently invented by the model.
    """
    for el in rule["elements"]:
        assert set(el["descriptors"]) == set(FIBONACCI_SCALE), (
            f"{el['slug']} does not declare all five sizes"
        )


def test_attribution_is_present_and_names_the_copyright_holder(rule: dict):
    """MIT requires preserving the copyright notice, and the rule card renders
    this block verbatim as a mandatory footer."""
    lic = rule["license"]
    assert lic["spdx"] == "MIT"
    assert "CI&T HyperX" in lic["attribution"]
    assert lic["url"].startswith("https://")
