#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Remove legacy module directories from _bmad/ after config migration.

After merge-config.py and merge-help-csv.py have migrated config data and
deleted individual legacy files, this script removes the now-redundant
directory trees. These directories contain skill files that are already
installed at .claude/skills/ (or equivalent) — only the config files at
_bmad/ root need to persist.

When --skills-dir is provided, the script verifies that every skill found
in the legacy directories exists at the installed location before removing
anything. Directories without skills (like _config/) are removed directly.

Exit codes: 0=success (including nothing to remove), 1=validation error, 2=runtime error
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

# Matches a complete PULSE auto-inject block, including a single surrounding
# newline on each side so the resulting text does not accumulate blank lines.
_PULSE_BLOCK_RE = re.compile(
    r"\n?<!-- PULSE:auto-inject:start -->.*?<!-- PULSE:auto-inject:end -->\n?",
    re.DOTALL,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Remove legacy module directories from _bmad/ after config migration."
    )
    parser.add_argument(
        "--bmad-dir",
        help="Path to the _bmad/ directory (required for legacy directory cleanup)",
    )
    parser.add_argument(
        "--module-code",
        help="Module code being cleaned up, e.g. 'bmb' "
        "(required for legacy directory cleanup)",
    )
    parser.add_argument(
        "--also-remove",
        action="append",
        default=[],
        help="Additional directory names under _bmad/ to remove (repeatable)",
    )
    parser.add_argument(
        "--skills-dir",
        help="Path to .claude/skills/ — enables safety verification that skills "
        "are installed before removing legacy copies",
    )
    parser.add_argument(
        "--remove-pulse-markers",
        action="store_true",
        help="Strip legacy PULSE auto-inject blocks from "
        ".claude/skills/bmad-dev-story/workflow.md "
        "under --project-root (standalone mode)",
    )
    parser.add_argument(
        "--project-root",
        help="Path to the consumer project root "
        "(required when --remove-pulse-markers is set)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress to stderr",
    )
    return parser.parse_args()


def find_skill_dirs(base_path: str) -> list:
    """Find directories that contain a SKILL.md file.

    Walks the directory tree and returns the leaf directory name for each
    directory containing a SKILL.md. These are considered skill directories.

    Returns:
        List of skill directory names (e.g. ['bmad-agent-builder', 'bmad-builder-setup'])
    """
    skills = []
    root = Path(base_path)
    if not root.exists():
        return skills
    for skill_md in root.rglob("SKILL.md"):
        skills.append(skill_md.parent.name)
    return sorted(set(skills))


def verify_skills_installed(
    bmad_dir: str, dirs_to_check: list, skills_dir: str, verbose: bool = False
) -> list:
    """Verify that skills in legacy directories exist at the installed location.

    Scans each directory in dirs_to_check for skill folders (containing SKILL.md),
    then checks that a matching directory exists under skills_dir. Directories
    that contain no skills (like _config/) are silently skipped.

    Returns:
        List of verified skill names.

    Raises SystemExit(1) if any skills are missing from skills_dir.
    """
    all_verified = []
    missing = []

    for dirname in dirs_to_check:
        legacy_path = Path(bmad_dir) / dirname
        if not legacy_path.exists():
            continue

        skill_names = find_skill_dirs(str(legacy_path))
        if not skill_names:
            if verbose:
                print(
                    f"No skills found in {dirname}/ — skipping verification",
                    file=sys.stderr,
                )
            continue

        for skill_name in skill_names:
            installed_path = Path(skills_dir) / skill_name
            if installed_path.is_dir():
                all_verified.append(skill_name)
                if verbose:
                    print(
                        f"Verified: {skill_name} exists at {installed_path}",
                        file=sys.stderr,
                    )
            else:
                missing.append(skill_name)
                if verbose:
                    print(
                        f"MISSING: {skill_name} not found at {installed_path}",
                        file=sys.stderr,
                    )

    if missing:
        error_result = {
            "status": "error",
            "error": "Skills not found at installed location",
            "missing_skills": missing,
            "skills_dir": str(Path(skills_dir).resolve()),
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)

    return sorted(set(all_verified))


def count_files(path: Path) -> int:
    """Count all files recursively in a directory."""
    count = 0
    for item in path.rglob("*"):
        if item.is_file():
            count += 1
    return count


def remove_pulse_markers(project_root: Path) -> dict:
    """Strip legacy PULSE auto-inject blocks from bmad-dev-story workflow.md.

    The legacy installer (pre-customize.toml) injected PULSE step blocks into
    `.claude/skills/bmad-dev-story/workflow.md` between
    `<!-- PULSE:auto-inject:start -->` and `<!-- PULSE:auto-inject:end -->`
    markers. This function removes every such block, preserving all surrounding
    content. The file is rewritten only when at least one block was removed,
    making repeated invocations idempotent.

    Args:
        project_root: Path to the consumer project root.

    Returns:
        Dict with keys:
            path: Resolved path to the workflow file (string).
            removed: Number of marker blocks removed (0 if file absent or clean).
            skipped: Optional reason string when nothing was done.
    """
    workflow = project_root / ".claude/skills/bmad-dev-story/workflow.md"
    if not workflow.exists():
        return {
            "removed": 0,
            "skipped": "workflow.md not found",
            "path": str(workflow),
        }

    original = workflow.read_text()
    # Substitute by a single newline (not the empty string) so that user
    # content immediately above and below the PULSE block stays separated
    # by at least one line break. Collapse runs of 3+ newlines (which would
    # arise when the surrounding lines were already separated by a blank
    # line) back to the standard "blank line" of two newlines.
    cleaned, count = _PULSE_BLOCK_RE.subn("\n", original)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    if count > 0 and cleaned != original:
        workflow.write_text(cleaned)
    return {
        "removed": count,
        "path": str(workflow),
    }


def cleanup_directories(
    bmad_dir: str, dirs_to_remove: list, verbose: bool = False
) -> tuple:
    """Remove specified directories under bmad_dir.

    Returns:
        (removed, not_found, total_files_removed) tuple
    """
    removed = []
    not_found = []
    total_files = 0

    for dirname in dirs_to_remove:
        target = Path(bmad_dir) / dirname
        if not target.exists():
            not_found.append(dirname)
            if verbose:
                print(f"Not found (skipping): {target}", file=sys.stderr)
            continue

        if not target.is_dir():
            if verbose:
                print(f"Not a directory (skipping): {target}", file=sys.stderr)
            not_found.append(dirname)
            continue

        file_count = count_files(target)
        if verbose:
            print(
                f"Removing {target} ({file_count} files)",
                file=sys.stderr,
            )

        try:
            shutil.rmtree(target)
        except OSError as e:
            error_result = {
                "status": "error",
                "error": f"Failed to remove {target}: {e}",
                "directories_removed": removed,
                "directories_failed": dirname,
            }
            print(json.dumps(error_result, indent=2))
            sys.exit(2)

        removed.append(dirname)
        total_files += file_count

    return removed, not_found, total_files


def main():
    args = parse_args()

    # Standalone mode: strip PULSE auto-inject blocks from workflow.md.
    # This branch is mutually exclusive with the legacy directory cleanup.
    if args.remove_pulse_markers:
        if not args.project_root:
            print(
                json.dumps(
                    {
                        "status": "error",
                        "error": "--project-root is required with --remove-pulse-markers",
                    },
                    indent=2,
                )
            )
            sys.exit(1)
        result = remove_pulse_markers(Path(args.project_root))
        print(json.dumps(result, indent=2))
        return

    # Legacy directory cleanup mode requires --bmad-dir and --module-code.
    if not args.bmad_dir or not args.module_code:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": "--bmad-dir and --module-code are required for legacy directory cleanup",
                },
                indent=2,
            )
        )
        sys.exit(1)

    bmad_dir = args.bmad_dir
    module_code = args.module_code

    # Build the list of directories to remove
    dirs_to_remove = [module_code, "core"] + args.also_remove
    # Deduplicate while preserving order
    seen = set()
    unique_dirs = []
    for d in dirs_to_remove:
        if d not in seen:
            seen.add(d)
            unique_dirs.append(d)
    dirs_to_remove = unique_dirs

    if args.verbose:
        print(f"Directories to remove: {dirs_to_remove}", file=sys.stderr)

    # Safety check: verify skills are installed before removing
    verified_skills = None
    if args.skills_dir:
        if args.verbose:
            print(
                f"Verifying skills installed at {args.skills_dir}",
                file=sys.stderr,
            )
        verified_skills = verify_skills_installed(
            bmad_dir, dirs_to_remove, args.skills_dir, args.verbose
        )

    # Remove directories
    removed, not_found, total_files = cleanup_directories(
        bmad_dir, dirs_to_remove, args.verbose
    )

    # Build result
    result = {
        "status": "success",
        "bmad_dir": str(Path(bmad_dir).resolve()),
        "directories_removed": removed,
        "directories_not_found": not_found,
        "files_removed_count": total_files,
    }

    if args.skills_dir:
        result["safety_checks"] = {
            "skills_verified": True,
            "skills_dir": str(Path(args.skills_dir).resolve()),
            "verified_skills": verified_skills,
        }
    else:
        result["safety_checks"] = None

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
