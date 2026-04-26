"""Meta-test: ensure golden snapshots stay byte-identical to packaged templates.

If this test fails, a template was edited without regenerating its golden
snapshot — or vice versa. Either fix:
  cp skills/bmad-pulse-setup/assets/customize-templates/<skill>.toml \
     tests/fixtures/golden/customize-<skill>.toml
or, if the golden was the intended source of truth, copy in the other
direction.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
TEMPLATES = REPO_ROOT / "skills/bmad-pulse-setup/assets/customize-templates"
GOLDEN = REPO_ROOT / "tests/fixtures/golden"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "skill",
    ["bmad-dev-story", "bmad-code-review"],
)
def test_template_matches_golden(skill: str):
    template = TEMPLATES / f"{skill}.toml"
    golden = GOLDEN / f"customize-{skill}.toml"
    assert template.exists(), f"missing template: {template}"
    assert golden.exists(), f"missing golden: {golden}"
    assert sha256(template) == sha256(golden), (
        f"template/golden divergence for {skill!r}: "
        f"template sha256 != golden sha256. "
        f"Regenerate goldens with: cp {template} {golden}"
    )
