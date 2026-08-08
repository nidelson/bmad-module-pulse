"""The prose must agree with where the code lives (#84).

Scoring moved into this module in v0.9. The code moved in seven PRs; the
narrative did not move with it, and nothing failed — README, docs and the
workflow files kept telling readers that `estimated_hours_reference` is written
by a companion module, and one banner still announced a port as "in progress"
while pointing at a repository that had already been archived.

That drift was invisible for weeks precisely because no test read the prose.
These do. They are deliberately about *attribution* rather than wording: a
sentence may be rewritten freely, but it may not tell a reader to go install
something that no longer exists, and the workflow files may not name a module as
the owner of a field a sibling skill writes.

The instruction files matter more than the docs here — an agent reads
`workflow.md` and acts on it.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]

DEAD_MODULE = "bmad-module-bcp"

# Files allowed to name the standalone module, each for a reason that does not
# expire. Anything else naming it is drift.
ALLOWED = {
    # Schema identity URI. Not a navigation URL — changing it breaks the
    # identity of a contract already written into delivered stories.
    "skills/bmad-bcp-score/assets/bcp-frontmatter.schema.yaml",
    # MIT attribution line. Removing it is a licence violation.
    "skills/bmad-bcp-rule-card/assets/bcp-rule.yaml",
    # The copyright/provenance record, which is what attribution is for.
    "ATTRIBUTION.md",
    # Migration-window instruction: an upgrading project may still have the
    # standalone module installed, and the text tells the user what to do
    # about it. It reads correctly *because* the module is gone.
    "skills/bmad-pulse-setup/SKILL.md",
    # Why the two on_complete steps are authored as one string: they used to be
    # merged from two modules. Past tense, and the reason the file exists.
    "skills/bmad-pulse-setup/assets/customize-templates/bmad-build.bcp.toml",
    # Historical records — what shipped when. Rewriting history to look like it
    # was always this way is its own kind of lie.
    "CHANGELOG.md",
    "docs/MIGRATION.md",
    "README.md",  # the v0.6 roadmap bullet, kept as a dated record
    # These have to name it in order to forbid it: both assert its ABSENCE
    # (from the setup label, and from live prose respectively).
    "tests/test_bcp_integration.py",
    "tests/test_port_narrative.py",
}

# Where an agent reads instructions and acts on them.
WORKFLOWS = sorted((REPO_ROOT / "skills").glob("*/workflow.md"))
READMES = [REPO_ROOT / "README.md", REPO_ROOT / "README.en.md"]
BCP_DOC = REPO_ROOT / "docs/bcp.md"


def _live_files() -> list[Path]:
    """Every file that instructs, documents or renders — excluding .git."""
    patterns = ("*.md", "*.toml", "*.yaml", "*.csv", "*.py")
    out: list[Path] = []
    for pattern in patterns:
        out.extend(
            path
            for path in REPO_ROOT.rglob(pattern)
            if ".git" not in path.parts
            and ".venv" not in path.parts
            and ".pytest_cache" not in path.parts
        )
    return sorted(out)


def test_no_live_file_sends_readers_to_the_archived_module():
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in _live_files()
        if DEAD_MODULE in path.read_text(encoding="utf-8")
        and str(path.relative_to(REPO_ROOT)) not in ALLOWED
    ]
    assert not offenders, (
        f"these name the archived standalone module: {offenders}. Scoring ships "
        f"in this module now — naming it as the owner of a field or a place to "
        f"install from sends the reader to a repository that has no skills left."
    )


def test_workflows_never_attribute_the_reference_anchor_to_a_module():
    """`estimated_hours_reference` is written by `bmad-bcp-score`, in this repo.

    This is the specific sentence that survived the port unchanged in four
    workflow files, and it is load-bearing: an agent that believes the anchor
    comes from somewhere external has no reason to look for the skill that
    actually writes it.
    """
    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        if "estimated_hours_reference" not in text:
            continue
        assert DEAD_MODULE not in text, (
            f"{workflow.parent.name} still attributes the frozen anchor to the "
            f"standalone module"
        )


def test_no_workflow_claims_the_port_is_unfinished():
    """Phases 2 and 3 are merged. Nothing may still describe them as pending."""
    stale_phrases = ("Port in progress", "until Phase 3", "companion module")
    for path in [*WORKFLOWS, *READMES, BCP_DOC, REPO_ROOT / "docs/index.md"]:
        text = path.read_text(encoding="utf-8")
        found = [phrase for phrase in stale_phrases if phrase in text]
        assert not found, f"{path.relative_to(REPO_ROOT)} still says {found}"


def test_readmes_document_the_estimation_switch():
    """The feature is invisible if the front door does not mention it.

    Both READMEs must name the setting and reach the doc — a reader who never
    learns `pulse_estimation_method` exists cannot opt in to the thing the
    module was built to enable.
    """
    for readme in READMES:
        text = readme.read_text(encoding="utf-8")
        assert "pulse_estimation_method" in text, (
            f"{readme.name} must document the estimation switch"
        )
        assert "docs/bcp.md" in text, f"{readme.name} must link the BCP doc"


def test_readmes_list_every_bcp_skill():
    """Six skills shipped in the port. A reader should be able to find them."""
    expected = [
        "bmad-bcp-rule-card",
        "bmad-bcp-score",
        "bmad-bcp-score-batch",
        "bmad-bcp-rescore",
        "bmad-bcp-recalibrate",
        "bmad-bcp-backfill-baseline",
    ]
    for readme in READMES:
        text = readme.read_text(encoding="utf-8")
        missing = [skill for skill in expected if skill not in text]
        assert not missing, f"{readme.name} does not list {missing}"


def test_bcp_skills_exist_for_every_documented_name():
    """The list above is only honest while the directories are there."""
    for skill in (REPO_ROOT / "skills").glob("bmad-bcp-*"):
        assert (skill / "SKILL.md").is_file(), f"{skill.name} has no SKILL.md"
