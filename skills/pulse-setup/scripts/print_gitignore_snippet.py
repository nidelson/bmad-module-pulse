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
    if not gitignore.exists():
        return False
    text = gitignore.read_text()
    # Heuristic: presence of the un-ignore for the directory is the load-bearing line.
    return "!_bmad/custom/" in text


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
