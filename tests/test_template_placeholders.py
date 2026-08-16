"""bmad-build templates must not reference placeholders the workflow does not resolve.

The hook text was derived from the split-architecture bmad-dev-story template,
which exposes {{story_path}}. bmad-build has no such variable — its equivalent
is spec_file, declared in step-01-clarify-and-route.md frontmatter.

A plain rename to {spec_file} would also fail: the hook lives in
activation_steps_append, which runs before step-01, so spec_file is unresolved
at the moment the text is loaded. The text should describe the value the way
the workflow names it, without implying brace substitution.

This test anchors the attribution: the placeholder must not appear in the
template. The phrasing may be rewritten freely.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
TEMPLATES = REPO_ROOT / "skills/bmad-pulse-setup/assets/customize-templates"
GOLDEN = REPO_ROOT / "tests/fixtures/golden"

# Placeholders that bmad-build DOES NOT resolve. If any of these appear in
# a template, the instruction points at a variable that does not exist.
INVALID_PLACEHOLDERS = {"{story_path}", "{{story_path}}"}

# Placeholders that bmad-build DOES resolve (from step-01 and elsewhere).
# This allowlist exists for documentation; the test only blocks the invalid
# set above, not unknown patterns.
VALID_PLACEHOLDERS = {
    "{project-root}",
    "{spec_file}",
    "{diff_output}",
    "{skill-root}",
    "{{story_path}}",  # bmad-dev-story only, not bmad-build
}


@pytest.mark.parametrize(
    "filename",
    ["bmad-build.toml", "bmad-build.bcp.toml"],
)
def test_template_avoids_invalid_placeholders(filename: str):
    """Template must not name {story_path} — bmad-build does not expose it."""
    template = TEMPLATES / filename
    assert template.exists(), f"missing template: {template}"
    text = template.read_text(encoding="utf-8")

    offenders = [
        placeholder for placeholder in INVALID_PLACEHOLDERS if placeholder in text
    ]
    assert not offenders, (
        f"{filename} contains invalid placeholder(s): {offenders}. "
        f"bmad-build does not resolve these — the instruction points at nothing. "
        f"Describe the value using spec_file (the workflow's own variable) "
        f"without implying brace substitution."
    )


@pytest.mark.parametrize(
    "filename",
    ["customize-bmad-build.toml", "customize-bmad-build-bcp.toml"],
)
def test_golden_matches_template_placeholder_contract(filename: str):
    """Golden fixture must enforce the same placeholder contract as the template."""
    golden = GOLDEN / filename
    assert golden.exists(), f"missing golden: {golden}"
    text = golden.read_text(encoding="utf-8")

    offenders = [
        placeholder for placeholder in INVALID_PLACEHOLDERS if placeholder in text
    ]
    assert not offenders, (
        f"{filename} contains invalid placeholder(s): {offenders}. "
        f"Golden must match template. Regenerate with: "
        f"cp skills/bmad-pulse-setup/assets/customize-templates/{filename.replace('customize-', '')} "
        f"tests/fixtures/golden/{filename}"
    )
