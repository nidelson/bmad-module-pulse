#!/usr/bin/env python3
"""Detect whether the consumer's .gitignore allows `_bmad/custom/*.toml`,
and if not, print a copy-paste-ready snippet to stdout.

Read-only: never modifies any file.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SNIPPET = """\
# PULSE customizations — keep team .toml overrides versioned, .user.toml private
!_bmad/custom/
_bmad/custom/*
!_bmad/custom/*.toml
_bmad/custom/*.user.toml
"""


def is_allowlisted(gitignore: Path) -> bool:
    """Return True if the .gitignore has an active (non-commented) allowlist
    entry for `_bmad/custom/`. Comment lines starting with `#` are skipped
    so a commented-out rule does not mask a missing real one.
    """
    if not gitignore.exists():
        return False
    for raw in gitignore.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "!_bmad/custom/" or line == "!_bmad/custom/*.toml":
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    gitignore = args.project_root / ".gitignore"
    if is_allowlisted(gitignore):
        sys.stdout.write("Allowlist already present in .gitignore — nothing to do.\n")
        return 0
    if not gitignore.exists():
        sys.stdout.write(
            "No .gitignore found at project root. "
            "Create one and append the snippet below:\n\n"
        )
    else:
        sys.stdout.write(
            f"Append the snippet below to {gitignore} to version PULSE customize overrides:\n\n"
        )
    sys.stdout.write(SNIPPET)
    sys.stdout.write("\nVerify with: grep -q '!_bmad/custom/' .gitignore && echo OK\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
