from pathlib import Path


def test_bmad_64_fixture_loads(bmad_64_consumer: Path):
    assert (bmad_64_consumer / ".claude/skills/bmad-dev-story/customize.toml").exists()
    assert (bmad_64_consumer / ".claude/skills/bmad-code-review/customize.toml").exists()


def test_bmad_63_fixture_loads(bmad_63_consumer: Path):
    workflow = bmad_63_consumer / ".claude/skills/bmad-dev-story/workflow.md"
    assert workflow.exists()
    assert "<!-- PULSE:auto-inject:start -->" in workflow.read_text()
