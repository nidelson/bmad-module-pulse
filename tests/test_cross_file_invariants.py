"""Meta-tests: cross-file semantic invariants.

These tests validate that string references across files actually resolve
to declared entities. They catch the class of bug where byte-equality tests
pass (template/golden agree) but cross-file consistency is broken (template
references a skill name that doesn't exist anywhere).

Lesson driving these tests: in v0.4.0's pre-release review, the global
reviewer found that customize-templates referenced one slash command while
SKILL.md frontmatter declared another. The 21-test suite missed it because
nothing validated cross-file symbol resolution. These tests close that gap
so the next rename — and there will be one — can't repeat the trap.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
TEMPLATES_DIR = SKILLS_DIR / "bmad-pulse-setup/assets/customize-templates"
LEVI_AGENT_YAML = SKILLS_DIR / "bmad-pulse-agent-levi/levi.agent.yaml"
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin/marketplace.json"


def _parse_frontmatter(skill_md: Path) -> dict:
    """Parse the YAML frontmatter block from a SKILL.md file."""
    text = skill_md.read_text()
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def _declared_skill_names() -> set[str]:
    """Collect every `name:` declared in any SKILL.md frontmatter."""
    names = set()
    for skill_md in SKILLS_DIR.glob("*/SKILL.md"):
        meta = _parse_frontmatter(skill_md)
        if "name" in meta:
            names.add(meta["name"])
    return names


def test_customize_templates_reference_real_skills():
    """Every `bmad-pulse-*` skill name mentioned in customize-templates/*.toml
    must match a real SKILL.md `name:` frontmatter.

    Catches: template renames that forget to update SKILL.md (or vice versa).
    """
    real_names = _declared_skill_names()
    assert real_names, "no SKILL.md frontmatter names found — sanity check failed"
    pattern = re.compile(r"\bbmad-pulse-[a-z-]+\b")
    for tmpl in TEMPLATES_DIR.glob("*.toml"):
        text = tmpl.read_text()
        for match in pattern.findall(text):
            assert match in real_names, (
                f"{tmpl.relative_to(REPO_ROOT)}: dangling skill reference "
                f"{match!r} — not declared in any SKILL.md `name:`. "
                f"Declared names: {sorted(real_names)}"
            )


def test_agent_yaml_skill_triggers_resolve():
    """Every `skill:` field in levi.agent.yaml's menu must resolve to a real
    SKILL.md frontmatter `name:`.

    Catches: agent triggers that point to skills that were renamed or removed.
    """
    real_names = _declared_skill_names()
    data = yaml.safe_load(LEVI_AGENT_YAML.read_text())
    menu = data.get("agent", {}).get("menu", [])
    referenced = [item["skill"] for item in menu if "skill" in item]
    assert referenced, "levi.agent.yaml menu has no skill triggers — sanity check failed"
    for ref in referenced:
        assert ref in real_names, (
            f"{LEVI_AGENT_YAML.relative_to(REPO_ROOT)}: dangling skill "
            f"reference {ref!r}. Declared names: {sorted(real_names)}"
        )


def test_marketplace_paths_exist_on_disk():
    """Every skill path listed in marketplace.json must exist on disk.

    Catches: skill folder renames that forget to update marketplace.json,
    which would make `claude plugin install` fail at runtime.
    """
    data = json.loads(MARKETPLACE_JSON.read_text())
    plugins = data.get("plugins", [])
    assert plugins, "marketplace.json has no plugins — sanity check failed"
    for plugin in plugins:
        skills = plugin.get("skills", [])
        assert skills, f"plugin {plugin.get('name')!r} lists no skills"
        for rel_path in skills:
            absolute = (REPO_ROOT / rel_path).resolve()
            assert absolute.is_dir(), (
                f"{MARKETPLACE_JSON.relative_to(REPO_ROOT)}: listed skill path "
                f"{rel_path!r} does not exist on disk."
            )
