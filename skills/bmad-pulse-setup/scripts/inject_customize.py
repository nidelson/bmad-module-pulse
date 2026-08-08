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
SUPPORTED_SKILLS = {
    "bmad-build", "bmad-dev-story", "bmad-code-review", "bmad-create-story",
}

# Skills whose template has a BCP variant. Two different reasons:
#
# `bmad-build` and `bmad-code-review` own `on_complete`, which recalibration
# extends. Their variant REPLACES the plain template at the same destination —
# the two are alternatives, never both, so a project with scoring disabled never
# receives the recalibrate instruction at all, not even as text that checks and
# skips. `bmad-dev-story` carries track-start, which recalibration does not
# extend, so it has no variant.
#
# `bmad-create-story` is the scoring trigger and has NO plain template: PULSE has
# nothing to say to story authoring unless scoring is on. See BCP_ONLY_SKILLS.
BCP_VARIANT_SKILLS = {"bmad-build", "bmad-code-review", "bmad-create-story"}

# Skills that exist ONLY as a BCP variant. Emitting one without `--with-bcp` is
# an error rather than a fallback, because the fallback would be a missing-file
# traceback for a file that is absent on purpose.
BCP_ONLY_SKILLS = {"bmad-create-story"}

EXIT_OK = 0
EXIT_BAD_ARGS = 2
EXIT_CONFLICT = 3


def emit(project_root: Path, skill: str, force: bool, with_bcp: bool = False) -> int:
    if with_bcp and skill not in BCP_VARIANT_SKILLS:
        sys.stderr.write(
            f"error: --with-bcp is not valid for skill '{skill}'. "
            f"Only {sorted(BCP_VARIANT_SKILLS)} have a BCP variant.\n"
        )
        return EXIT_BAD_ARGS
    if skill in BCP_ONLY_SKILLS and not with_bcp:
        sys.stderr.write(
            f"error: '{skill}' has no plain template — it exists only to trigger "
            f"BCP scoring. Re-run with --with-bcp, or skip it entirely when "
            f"pulse_estimation_method is not 'bcp'.\n"
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
