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
# `bmad-build` is the unified architecture's single target; the other two are the
# split architecture's pair. Which set applies comes from `detect_bmad_capability.py`
# (`inject_targets` in its payload) — never assume, the deprecated `bmad-dev-story`
# shim survives on disk next to `bmad-build`.
SUPPORTED_SKILLS = {"bmad-build", "bmad-dev-story", "bmad-code-review"}

# Skills whose template has a BCP variant carrying the recalibrate step. Only
# the ones that own `on_complete`: `bmad-dev-story` carries track-start, which
# recalibration does not extend.
#
# The variant REPLACES the plain template at the same destination — the two are
# alternatives, never both. A project with scoring disabled therefore never
# receives the recalibrate instruction at all, not even as text that checks and
# skips. That is the opt-in expressed in the filesystem rather than in prose.
BCP_VARIANT_SKILLS = {"bmad-build", "bmad-code-review"}

EXIT_OK = 0
EXIT_BAD_ARGS = 2
EXIT_CONFLICT = 3


def emit(project_root: Path, skill: str, force: bool, with_bcp: bool = False) -> int:
    if with_bcp and skill not in BCP_VARIANT_SKILLS:
        sys.stderr.write(
            f"error: --with-bcp is not valid for skill '{skill}'. "
            f"Only {sorted(BCP_VARIANT_SKILLS)} own the on_complete hook that "
            f"BCP recalibration extends.\n"
        )
        return EXIT_BAD_ARGS
    suffix = ".bcp.toml" if with_bcp else ".toml"
    template = TEMPLATES_DIR / f"{skill}{suffix}"
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
    parser.add_argument("--with-bcp", action="store_true",
                        help="emit the variant that chains BCP recalibrate after "
                             "track-done; only when pulse_estimation_method is 'bcp'")
    args = parser.parse_args()
    return emit(args.project_root, args.skill, args.force, args.with_bcp)


if __name__ == "__main__":
    sys.exit(main())
