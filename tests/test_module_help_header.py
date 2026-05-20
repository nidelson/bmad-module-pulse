"""Regression test for issue #42: module-help.csv header must match the
BMAD canonical schema.

BMAD ≥6.7.x emits an install-time warning and falls back to positional
loading when the header diverges. The root cause was two files drifting
together: the shipped CSV header and the HEADER constant in
merge-help-csv.py both used the non-canonical `after`/`before` instead of
`preceded-by`/`followed-by`. This test pins both to the canonical schema
so the debt cannot silently return.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
MODULE_HELP = REPO_ROOT / "skills/bmad-pulse-setup/assets/module-help.csv"
MERGE_SCRIPT = REPO_ROOT / "skills/bmad-pulse-setup/scripts/merge-help-csv.py"

CANONICAL_HEADER = [
    "module",
    "skill",
    "display-name",
    "menu-code",
    "description",
    "action",
    "args",
    "phase",
    "preceded-by",
    "followed-by",
    "required",
    "output-location",
    "outputs",
]


def test_shipped_csv_header_is_canonical():
    header = MODULE_HELP.read_text().splitlines()[0].strip()
    assert header.split(",") == CANONICAL_HEADER, (
        f"module-help.csv header diverges from the BMAD canonical schema.\n"
        f"Expected: {','.join(CANONICAL_HEADER)}\nFound:    {header}"
    )


def test_merge_script_header_constant_is_canonical():
    """The HEADER constant the script writes must equal the canonical
    schema, so a freshly merged consumer CSV is conformant."""
    text = MERGE_SCRIPT.read_text()
    quoted = re.findall(r'"([a-z-]+)",', text)
    # The HEADER list is the first contiguous run of these 13 tokens.
    assert CANONICAL_HEADER == quoted[: len(CANONICAL_HEADER)], (
        "merge-help-csv.py HEADER constant diverges from the canonical "
        f"schema. First tokens found: {quoted[: len(CANONICAL_HEADER)]}"
    )


def test_no_legacy_after_before_tokens_remain():
    """Belt-and-suspenders: the legacy column names must not appear as a
    header pair in either file."""
    for path in (MODULE_HELP, MERGE_SCRIPT):
        assert "phase,after,before" not in path.read_text(), (
            f"{path.name} still contains the legacy 'after,before' header pair"
        )
