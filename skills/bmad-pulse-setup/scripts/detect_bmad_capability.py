#!/usr/bin/env python3
"""Detect which BMAD architecture the consumer project runs, and where to inject.

Capability probe by filesystem inspection. Returns:
  exit 0 - BMAD supports TOML customization, either architecture:
           "bmad-build"  unified (bmad-build/customize.toml present)
           "bmad-6.4.0+" split   (bmad-dev-story/customize.toml present)
  exit 1 - BMAD <=6.3.x (workflow.md present, customize.toml absent)
  exit 2 - BMAD not installed (neither file present)

The payload carries `inject_targets`: the skills whose `customize.toml` the
setup must write. This is the probe's real job — both supported architectures
exit 0, so the exit code alone never says where the hooks belong.

Detection order matters and is not cosmetic. BMAD keeps `bmad-dev-story` on
disk as a deprecated shim after the unified architecture lands, so checking it
first reports the old tier on a project that runs `/bmad-build`. The setup then
writes its overrides into a workflow the user never invokes: the probe passes,
the setup reports success, and auto-tracking silently never fires.

Outputs JSON to stdout describing the result.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CAPABILITY_BUILD = "bmad-build"
CAPABILITY_64 = "bmad-6.4.0+"
CAPABILITY_63 = "bmad-6.3.x"
CAPABILITY_NONE = "bmad-not-installed"

# Skills whose `customize.toml` receives the PULSE hooks, per architecture.
# Under `bmad-build` the review step runs in-process through
# `workflow.review_layers` rather than delegating to `bmad-code-review`, so the
# unified architecture has a single target: injecting into both would record
# track-done twice.
INJECT_TARGETS = {
    CAPABILITY_BUILD: ["bmad-build"],
    CAPABILITY_64: ["bmad-dev-story", "bmad-code-review"],
    CAPABILITY_63: [],
    CAPABILITY_NONE: [],
}


def detect(project_root: Path) -> dict:
    skills = project_root / ".claude/skills"

    # Checked first on purpose — see the module docstring. `bmad-dev-story`
    # outlives the migration as a shim and would otherwise win.
    build_customize = skills / "bmad-build/customize.toml"
    if build_customize.exists():
        return {
            "capability": CAPABILITY_BUILD,
            "customize_toml_path": str(build_customize),
            "inject_targets": INJECT_TARGETS[CAPABILITY_BUILD],
        }

    dev_story = skills / "bmad-dev-story"
    customize = dev_story / "customize.toml"
    workflow = dev_story / "workflow.md"
    if customize.exists():
        return {
            "capability": CAPABILITY_64,
            "customize_toml_path": str(customize),
            "inject_targets": INJECT_TARGETS[CAPABILITY_64],
        }
    if workflow.exists():
        return {
            "capability": CAPABILITY_63,
            "workflow_md_path": str(workflow),
            "inject_targets": INJECT_TARGETS[CAPABILITY_63],
        }
    return {"capability": CAPABILITY_NONE, "inject_targets": INJECT_TARGETS[CAPABILITY_NONE]}


CAPABILITY_TO_EXIT = {
    CAPABILITY_BUILD: 0,
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
