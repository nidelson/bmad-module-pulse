"""Tests for register-party-agent.py — re-run must not flatten local edits.

`_bmad/custom/config.toml` is the team-owned, committed layer: people comment
it and tune the agent entry by hand. Re-running the setup used to `del` the
entry and re-append it, which (a) moved the block to the end of `[agents]`,
orphaning the comments written above it, and (b) overwrote editorial fields
with the fragment's values, dropping local wording.

These tests pin the fixed contract: in-place update, structural fields
refreshed, editorial fields preserved unless `--force`.

With one carve-out added in v0.9 (#84): an editorial value that still matches
what an *older version of this script* wrote is not a team edit — it is our own
stale default. Preserving it would pin the retired persona into the roster
forever, since `name` is editorial and a re-run would never touch it.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import tomlkit

REPO_ROOT = Path(__file__).parents[1]
SKILLS = REPO_ROOT / "skills"
REGISTER = SKILLS / "bmad-pulse-setup/scripts/register-party-agent.py"
FRAGMENT = SKILLS / "bmad-pulse-setup/assets/agent-manifest-fragment.csv"

AGENT_KEY = "bmad-agent-pulse"

# Editorial wording a team may have tuned by hand — deliberately different from
# whatever the fragment ships, so a regression is unambiguous.
CUSTOM_DESCRIPTION = "Transforma dado de eficiencia em narrativa de melhoria."
CUSTOM_TITLE = "Analista de Eficiencia (SIP)"

LEADING_COMMENT = "# Levi (PULSE) no roster do party-mode — modulo custom nao entra no [agents] base."
TRAILING_SECTION_COMMENT = "# BCP: valores custom pinados (fonte unica)."

# Mirrors a real consumer file: the agent entry sits between two commented
# blocks, so any reordering is visible.
EXISTING_CONFIG = f"""\
[agents.bmad-agent-other]
module = "other"
team = "software-development"
name = "Someone"

{LEADING_COMMENT}
[agents.{AGENT_KEY}]
module = "pulse"
team = "software-development"
name = "Levi"
title = "{CUSTOM_TITLE}"
icon = "⚡"
description = "{CUSTOM_DESCRIPTION}"

{TRAILING_SECTION_COMMENT}
[modules.bcp]
bcp_reference_h_per_bcp = "5.0"
"""


def _custom_path(root: Path) -> Path:
    return root / "_bmad" / "custom" / "config.toml"


@pytest.fixture
def consumer_with_custom_entry(tmp_path: Path) -> Path:
    """Consumer project whose config.toml already has a hand-tuned entry."""
    dest = _custom_path(tmp_path)
    dest.parent.mkdir(parents=True)
    dest.write_text(EXISTING_CONFIG, encoding="utf-8")
    return tmp_path


def _run(root: Path, *extra: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(REGISTER), "--project-root", str(root),
         "--fragment", str(FRAGMENT), *extra],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _entry(root: Path) -> dict:
    doc = tomlkit.parse(_custom_path(root).read_text(encoding="utf-8"))
    return doc["agents"][AGENT_KEY]


def test_creates_entry_on_fresh_install(tmp_path: Path):
    """No prior config: the entry is written in full from the fragment."""
    payload = _run(tmp_path)

    assert payload["action"] == "created"
    entry = _entry(tmp_path)
    assert entry["name"] == "Maxine"
    assert entry["module"] == "pulse"
    assert entry["team"] == "software-development"
    assert entry["description"]


def test_rerun_preserves_editorial_fields(consumer_with_custom_entry: Path):
    """The regression: re-running must not overwrite hand-tuned wording."""
    payload = _run(consumer_with_custom_entry)

    # "migrated" rather than "updated": the fixture's `name`/`icon` still hold
    # the retired defaults, so this run also carries the v0.9 persona swap.
    assert payload["action"] == "migrated"
    entry = _entry(consumer_with_custom_entry)
    assert entry["description"] == CUSTOM_DESCRIPTION
    assert entry["title"] == CUSTOM_TITLE


def test_rerun_keeps_block_position_and_comments(consumer_with_custom_entry: Path):
    """Entry stays in place; the comments around it survive."""
    _run(consumer_with_custom_entry)
    text = _custom_path(consumer_with_custom_entry).read_text(encoding="utf-8")

    assert LEADING_COMMENT in text
    assert TRAILING_SECTION_COMMENT in text

    # The comment must still sit immediately above its own block, and the
    # entry must still precede [modules.bcp] — i.e. it was not re-appended.
    assert text.index(LEADING_COMMENT) < text.index(f"[agents.{AGENT_KEY}]")
    assert text.index(f"[agents.{AGENT_KEY}]") < text.index(TRAILING_SECTION_COMMENT)
    assert text.index(TRAILING_SECTION_COMMENT) < text.index("[modules.bcp]")


def test_rerun_refreshes_structural_fields(consumer_with_custom_entry: Path):
    """module/team are owned by the fragment and always rewritten."""
    path = _custom_path(consumer_with_custom_entry)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            'team = "software-development"\nname = "Levi"',
            'team = "stale-team"\nname = "Levi"',
        ),
        encoding="utf-8",
    )

    _run(consumer_with_custom_entry)

    entry = _entry(consumer_with_custom_entry)
    assert entry["team"] == "software-development"
    assert entry["description"] == CUSTOM_DESCRIPTION  # still preserved


def test_force_restores_fragment_values(consumer_with_custom_entry: Path):
    """--force is the explicit opt-in to discard local wording."""
    payload = _run(consumer_with_custom_entry, "--force")

    assert payload["action"] == "forced"
    entry = _entry(consumer_with_custom_entry)
    assert entry["description"] != CUSTOM_DESCRIPTION
    assert entry["title"] != CUSTOM_TITLE


def test_rerun_leaves_other_sections_untouched(consumer_with_custom_entry: Path):
    """Sibling agents and unrelated module sections are not disturbed."""
    _run(consumer_with_custom_entry)
    doc = tomlkit.parse(_custom_path(consumer_with_custom_entry).read_text(encoding="utf-8"))

    assert doc["agents"]["bmad-agent-other"]["name"] == "Someone"
    assert doc["modules"]["bcp"]["bcp_reference_h_per_bcp"] == "5.0"


def test_stale_default_name_is_migrated_not_preserved(consumer_with_custom_entry: Path):
    """The fixture carries `name = "Levi"` and `icon = "⚡"` — the exact values
    an older release of this script wrote. Nobody typed those, so refreshing
    them restores the truth rather than flattening a customization."""
    payload = _run(consumer_with_custom_entry)

    assert set(payload["migrated_fields"]) == {"name", "icon"}
    entry = _entry(consumer_with_custom_entry)
    assert entry["name"] == "Maxine"
    assert entry["icon"] == "💓"


def test_a_hand_written_name_is_still_preserved(consumer_with_custom_entry: Path):
    """The counterweight: migration must key on the *exact* retired value. A
    team that renamed the agent themselves keeps their name — otherwise the
    carve-out is just --force by another route."""
    path = _custom_path(consumer_with_custom_entry)
    path.write_text(
        path.read_text(encoding="utf-8").replace('name = "Levi"', 'name = "Analista"'),
        encoding="utf-8",
    )

    payload = _run(consumer_with_custom_entry)

    assert "name" not in payload["migrated_fields"]
    assert _entry(consumer_with_custom_entry)["name"] == "Analista"


def test_team_comments_are_never_rewritten(consumer_with_custom_entry: Path):
    """A comment mentioning the retired persona is the team's prose, not our
    data. tomlkit round-trips it untouched, and it must stay that way — the
    migration reaches values, never the file's commentary."""
    _run(consumer_with_custom_entry)

    assert LEADING_COMMENT in _custom_path(consumer_with_custom_entry).read_text(encoding="utf-8")
