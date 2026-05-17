#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Self-heal PULSE skills deployed in a consumer project.

The upstream BMAD installer performs an *additive* deploy when a custom
module is already installed: brand-new files are copied, but pre-existing
files are never overwritten and renamed/removed skills are never pruned.
The result is a mixed state where `module.yaml`/`SKILL.md` stay frozen at
the previous version while newly-added files (e.g. customize.toml) are
present — and orphan folders from renamed skills linger.

This script reconciles the deployed skill tree against an authoritative
source (the freshly-fetched BMAD custom-module cache, or an explicit
`--source`). It force-syncs every PULSE skill directory and prunes known
renamed/removed folders. It is idempotent: when the deployed tree already
matches the source, it makes no writes and reports `up_to_date`.

It is also safe on fresh installs: if no source can be located, it exits 0
with `skipped_no_source` so the caller (bmad-pulse-setup) can continue.

Exit codes: 0=success (including up_to_date / skipped_no_source),
1=validation error, 2=runtime error.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

# Folders shipped by a previous PULSE version that were renamed/removed and
# must be pruned from the consumer project once their canonical replacement
# is in place. Maps legacy folder name -> canonical folder name (both under
# .claude/skills/). The legacy folder is removed only when the canonical
# folder exists in the source skill set AND is deployed in the project, so a
# partial-state install is never stranded without the replacement.
LEGACY_SKILL_FOLDERS = {
    "bmad-pulse-agent-levi": "bmad-agent-pulse",
}

DEFAULT_CACHE_ROOT = Path.home() / ".bmad" / "cache" / "custom-modules"

_MODULE_VERSION_RE = re.compile(r"^\s*module_version:\s*([^\s#]+)", re.MULTILINE)
_REPO_URL_RE = re.compile(r"^\s*repoUrl:\s*(\S+)\s*$")
_MODULE_ITEM_RE = re.compile(r"^\s*-\s+name:\s*(\S+)\s*$")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reconcile deployed PULSE skills against an authoritative source."
    )
    parser.add_argument(
        "--project-root",
        required=True,
        help="Path to the consumer project root",
    )
    parser.add_argument(
        "--source",
        help="Path to a fresh PULSE source tree (a directory containing "
        "skills/). When omitted, the BMAD custom-module cache is discovered "
        "from {project-root}/_bmad/_config/manifest.yaml",
    )
    parser.add_argument(
        "--cache-root",
        help=f"Base dir for the BMAD custom-module cache "
        f"(default: {DEFAULT_CACHE_ROOT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the planned actions without writing anything",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress to stderr",
    )
    return parser.parse_args()


def _fail(message: str, code: int = 1):
    print(json.dumps({"status": "error", "error": message}, indent=2))
    sys.exit(code)


def read_module_version(module_yaml: Path):
    """Return the module_version string from a module.yaml, or None."""
    if not module_yaml.is_file():
        return None
    match = _MODULE_VERSION_RE.search(module_yaml.read_text())
    return match.group(1).strip() if match else None


def discover_source(project_root: Path, cache_root: Path, verbose: bool):
    """Locate the BMAD custom-module cache for PULSE from the manifest.

    Parses {project-root}/_bmad/_config/manifest.yaml without a YAML
    dependency: finds the `- name: pulse` module item and reads its
    `repoUrl`, then maps it to <cache-root>/<host>/<owner>/<repo>.

    Returns the resolved source path, or None when discovery is not
    possible (fresh install, no manifest, no cache on disk).
    """
    manifest = project_root / "_bmad" / "_config" / "manifest.yaml"
    if not manifest.is_file():
        if verbose:
            print(f"No manifest at {manifest}", file=sys.stderr)
        return None

    repo_url = None
    in_pulse = False
    for line in manifest.read_text().splitlines():
        item = _MODULE_ITEM_RE.match(line)
        if item:
            in_pulse = item.group(1) == "pulse"
            continue
        if in_pulse:
            url = _REPO_URL_RE.match(line)
            if url:
                repo_url = url.group(1)
                break
    if not repo_url or repo_url == "null":
        if verbose:
            print("No pulse repoUrl in manifest", file=sys.stderr)
        return None

    # https://github.com/owner/repo(.git) -> github.com/owner/repo
    stripped = re.sub(r"^[a-z]+://", "", repo_url)
    stripped = re.sub(r"\.git$", "", stripped)
    parts = [p for p in stripped.split("/") if p]
    if len(parts) < 3:
        if verbose:
            print(f"Unparseable repoUrl: {repo_url}", file=sys.stderr)
        return None

    candidate = cache_root.joinpath(*parts)
    if not (candidate / "skills").is_dir():
        if verbose:
            print(f"Cache not found at {candidate}", file=sys.stderr)
        return None
    return candidate


def list_source_skills(source_skills: Path):
    """Immediate subdirectories of source/skills that contain a SKILL.md."""
    return sorted(
        p.name
        for p in source_skills.iterdir()
        if p.is_dir() and (p / "SKILL.md").is_file()
    )


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def sync_skill(src: Path, dst: Path, dry_run: bool):
    """Mirror src -> dst. Returns (written, deleted) file path lists.

    Only files whose content differs are written; files present in dst but
    absent in src are deleted (prune-within). This keeps the operation a
    no-op when the tree already matches, which makes the script idempotent.
    """
    written = []
    deleted = []

    src_files = {
        p.relative_to(src) for p in src.rglob("*") if p.is_file()
    }
    dst_files = (
        {p.relative_to(dst) for p in dst.rglob("*") if p.is_file()}
        if dst.exists()
        else set()
    )

    for rel in sorted(src_files):
        s = src / rel
        d = dst / rel
        if d.is_file() and _digest(s) == _digest(d):
            continue
        written.append(str(rel))
        if dry_run:
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)

    for rel in sorted(dst_files - src_files):
        deleted.append(str(rel))
        if dry_run:
            continue
        (dst / rel).unlink()
        # Drop now-empty directories left behind by the prune.
        parent = (dst / rel).parent
        while parent != dst and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent

    return written, deleted


def prune_legacy_folders(skills_dir: Path, source_skills: list, dry_run: bool):
    """Remove renamed/removed legacy skill folders from the project.

    A legacy folder is removed only when its canonical replacement is part
    of the source skill set (so we know the rename actually happened in this
    version) AND the canonical folder is deployed in the project (so we
    never strand the project without the replacement).
    """
    removed = []
    for legacy, canonical in LEGACY_SKILL_FOLDERS.items():
        legacy_dir = skills_dir / legacy
        if not legacy_dir.is_dir():
            continue
        if canonical not in source_skills:
            continue
        if not (skills_dir / canonical).is_dir():
            continue
        removed.append(legacy)
        if not dry_run:
            shutil.rmtree(legacy_dir)
    return removed


def main():
    args = parse_args()

    project_root = Path(args.project_root)
    if not project_root.is_dir():
        _fail(f"--project-root does not exist: {project_root}")

    cache_root = (
        Path(args.cache_root) if args.cache_root else DEFAULT_CACHE_ROOT
    )

    if args.source:
        source = Path(args.source)
        if not (source / "skills").is_dir():
            _fail(f"--source has no skills/ directory: {source}")
    else:
        source = discover_source(project_root, cache_root, args.verbose)

    skills_dir = project_root / ".claude" / "skills"
    deployed_version = read_module_version(
        skills_dir / "bmad-pulse-setup" / "assets" / "module.yaml"
    )

    if source is None:
        # Fresh install or cache unavailable — not an error. The BMAD
        # installer deploys a clean tree on a first install; reconcile only
        # matters when updating over a pre-existing install.
        print(
            json.dumps(
                {
                    "status": "success",
                    "action": "skipped_no_source",
                    "deployed_version": deployed_version,
                    "notice": (
                        "No PULSE source/cache located — nothing to "
                        "reconcile (expected on a fresh install)."
                    ),
                },
                indent=2,
            )
        )
        return

    source_skills_dir = source / "skills"
    source_version = read_module_version(
        source_skills_dir / "bmad-pulse-setup" / "assets" / "module.yaml"
    )
    source_skills = list_source_skills(source_skills_dir)
    if not source_skills:
        _fail(f"No skills found under {source_skills_dir}", code=2)

    per_skill = {}
    total_written = 0
    total_deleted = 0
    try:
        for name in source_skills:
            written, deleted = sync_skill(
                source_skills_dir / name,
                skills_dir / name,
                args.dry_run,
            )
            if written or deleted:
                per_skill[name] = {
                    "written": written,
                    "deleted": deleted,
                }
            total_written += len(written)
            total_deleted += len(deleted)

        legacy_removed = prune_legacy_folders(
            skills_dir, source_skills, args.dry_run
        )
    except OSError as e:
        _fail(f"Filesystem error during reconcile: {e}", code=2)

    converged = bool(per_skill) or bool(legacy_removed)
    result = {
        "status": "success",
        "action": "reconciled" if converged else "up_to_date",
        "dry_run": args.dry_run,
        "source": str(source.resolve()),
        "from_version": deployed_version,
        "to_version": source_version,
        "skills_synced": sorted(per_skill.keys()),
        "files_written": total_written,
        "files_deleted": total_deleted,
        "legacy_folders_removed": legacy_removed,
        "details": per_skill,
    }
    if converged and deployed_version != source_version:
        result["notice"] = (
            f"PULSE reconciled {deployed_version} -> {source_version}. "
            f"bmad-pulse-setup may have been updated in place; re-run "
            f"/bmad-pulse-setup once more to execute the current version."
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
