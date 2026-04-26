#!/usr/bin/env python3
"""Detect whether the consumer project has BMAD >=6.4.0 installed.

Capability probe by filesystem inspection. Returns:
  exit 0 - BMAD >=6.4.0 (customize.toml present in bmad-dev-story)
  exit 1 - BMAD <=6.3.x (workflow.md present, customize.toml absent)
  exit 2 - BMAD not installed (neither file present)

Outputs JSON to stdout describing the result.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CAPABILITY_64 = "bmad-6.4.0+"
CAPABILITY_63 = "bmad-6.3.x"
CAPABILITY_NONE = "bmad-not-installed"


def detect(project_root: Path) -> dict:
    dev_story = project_root / ".claude/skills/bmad-dev-story"
    customize = dev_story / "customize.toml"
    workflow = dev_story / "workflow.md"
    if customize.exists():
        return {"capability": CAPABILITY_64, "customize_toml_path": str(customize)}
    if workflow.exists():
        return {"capability": CAPABILITY_63, "workflow_md_path": str(workflow)}
    return {"capability": CAPABILITY_NONE}


CAPABILITY_TO_EXIT = {
    CAPABILITY_64: 0,
    CAPABILITY_63: 1,
    CAPABILITY_NONE: 2,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    payload = detect(args.project_root)
    sys.stdout.write(json.dumps(payload) + "\n")
    return CAPABILITY_TO_EXIT[payload["capability"]]


if __name__ == "__main__":
    sys.exit(main())
