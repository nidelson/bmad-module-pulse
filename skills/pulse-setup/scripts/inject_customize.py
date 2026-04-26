#!/usr/bin/env python3
"""Emit a `_bmad/custom/<skill>.toml` override from a packaged template.

Conflict policy: abort with exit 3 if the destination file already exists,
unless `--force` is passed (then overwrite).

Idempotent under `--force`: rerunning produces a byte-identical file
(sha256 stable) as long as the template has not changed.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "assets/customize-templates"
SUPPORTED_SKILLS = {"bmad-dev-story", "bmad-code-review"}

EXIT_OK = 0
EXIT_BAD_ARGS = 2
EXIT_CONFLICT = 3


def emit(project_root: Path, skill: str, force: bool) -> int:
    template = TEMPLATES_DIR / f"{skill}.toml"
    if not template.exists():
        sys.stderr.write(f"error: template missing for skill '{skill}': {template}\n")
        return EXIT_BAD_ARGS
    dest_dir = project_root / "_bmad/custom"
    dest = dest_dir / f"{skill}.toml"
    if dest.exists() and not force:
        sys.stderr.write(
            f"error: {dest} already exists. "
            f"Re-run with --force to overwrite, or remove the file manually.\n"
        )
        return EXIT_CONFLICT
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template, dest)
    sys.stdout.write(f"wrote {dest}\n")
    return EXIT_OK


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--skill", choices=sorted(SUPPORTED_SKILLS), required=True)
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing destination file")
    args = parser.parse_args()
    return emit(args.project_root, args.skill, args.force)


if __name__ == "__main__":
    sys.exit(main())
