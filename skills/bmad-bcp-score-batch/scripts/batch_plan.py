#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Plan a retroactive batch BCP scoring run.

Resolves a glob of story files, classifies each (unscored vs already has a
`bcp.*` block), and emits a plan JSON with a rough token-cost estimate so
the user can preview spend before running (`--dry-run-cost`).

This script is deterministic and side-effect free. The per-story judgment
(auto-score) is done by the LLM; the actual frontmatter write is done by
`bmad-bcp-score`'s `apply_score.py` with `--scored-by retroactive`.

Exit codes: 0=success, 1=validation error, 2=runtime error
"""
from __future__ import annotations

import argparse
import glob as globlib
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: pyyaml is required (PEP 723 dependency)", file=sys.stderr)
    sys.exit(2)

# Rough, clearly-labelled heuristic. ~4 chars/token. Fixed scaffolding =
# resolved rule (~2000 tok) + auto-score template (~900 tok) + system glue.
SCAFFOLD_INPUT_TOKENS = 3200
EST_OUTPUT_TOKENS_PER_STORY = 450  # structured breakdown JSON + rationale


def has_bcp_block(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if not text.startswith("---"):
        return False
    parts = text.split("---", 2)
    if len(parts) < 3:
        return False
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return False
    return isinstance(fm, dict) and isinstance(fm.get("bcp"), dict)


def est_input_tokens(path: Path) -> int:
    try:
        chars = len(path.read_text(encoding="utf-8"))
    except OSError:
        chars = 0
    return SCAFFOLD_INPUT_TOKENS + chars // 4


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project-root", type=Path, required=True)
    p.add_argument("--glob", required=True,
                   help="glob relative to project-root, e.g. docs/stories/*.md")
    p.add_argument("--rescore", action="store_true",
                   help="include stories that already have a bcp.* block")
    args = p.parse_args()

    root: Path = args.project_root
    matches = sorted(
        Path(m) for m in globlib.glob(str(root / args.glob), recursive=True)
        if Path(m).is_file()
    )
    if not matches:
        print(json.dumps({
            "status": "error",
            "error": f"no files matched glob {args.glob!r} under {root}",
        }, indent=2))
        return 1

    stories = []
    sel_in = sel_out = 0
    for m in matches:
        scored = has_bcp_block(m)
        selected = (not scored) or args.rescore
        ein = est_input_tokens(m)
        rel = str(m.relative_to(root)) if root in m.parents else str(m)
        stories.append({
            "path": rel,
            "status": "already_scored" if scored else "unscored",
            "selected": selected,
            "est_input_tokens": ein,
            "est_output_tokens": EST_OUTPUT_TOKENS_PER_STORY,
        })
        if selected:
            sel_in += ein
            sel_out += EST_OUTPUT_TOKENS_PER_STORY

    selected_n = sum(1 for s in stories if s["selected"])
    print(json.dumps({
        "status": "success",
        "matched": len(stories),
        "selected": selected_n,
        "skipped_already_scored": len(stories) - selected_n,
        "rescore": bool(args.rescore),
        "cost_estimate": {
            "note": "Estimativa grosseira (~4 chars/token + scaffold fixo). "
                    "Não é cobrança real — use para ordem de grandeza.",
            "est_input_tokens": sel_in,
            "est_output_tokens": sel_out,
            "est_total_tokens": sel_in + sel_out,
        },
        "stories": stories,
        "scored_by": "retroactive",
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
