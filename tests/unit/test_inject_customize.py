"""Unit tests for skills/pulse-setup/scripts/inject_customize.py."""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "skills/pulse-setup/scripts/inject_customize.py"
GOLDEN = Path(__file__).parents[1] / "fixtures/golden"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(consumer: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(consumer), *args],
        capture_output=True,
        text=True,
    )


def test_emits_dev_story_override_on_fresh_install(bmad_64_consumer: Path):
    result = run(bmad_64_consumer, "--skill", "bmad-dev-story")
    assert result.returncode == 0, result.stderr
    out = bmad_64_consumer / "_bmad/custom/bmad-dev-story.toml"
    assert out.exists()
    assert sha256(out) == sha256(GOLDEN / "customize-bmad-dev-story.toml")


def test_emits_code_review_override_on_fresh_install(bmad_64_consumer: Path):
    result = run(bmad_64_consumer, "--skill", "bmad-code-review")
    assert result.returncode == 0, result.stderr
    out = bmad_64_consumer / "_bmad/custom/bmad-code-review.toml"
    assert out.exists()
    assert sha256(out) == sha256(GOLDEN / "customize-bmad-code-review.toml")


def test_aborts_on_pre_existing_override_byte_stable(bmad_64_consumer: Path):
    out = bmad_64_consumer / "_bmad/custom/bmad-dev-story.toml"
    out.parent.mkdir(parents=True, exist_ok=True)
    user_content = b"# user override, do not destroy\n[workflow]\n"
    out.write_bytes(user_content)
    before_hash = sha256(out)

    result = run(bmad_64_consumer, "--skill", "bmad-dev-story")

    assert result.returncode == 3
    assert "already exists" in result.stderr
    assert "--force" in result.stderr
    assert sha256(out) == before_hash, "file MUST be byte-stable when conflict detected"
    assert out.read_bytes() == user_content


def test_force_overwrites_pre_existing_override(bmad_64_consumer: Path):
    out = bmad_64_consumer / "_bmad/custom/bmad-dev-story.toml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"# previous\n")

    result = run(bmad_64_consumer, "--skill", "bmad-dev-story", "--force")

    assert result.returncode == 0, result.stderr
    assert sha256(out) == sha256(GOLDEN / "customize-bmad-dev-story.toml")


def test_force_is_idempotent_sha256_stable(bmad_64_consumer: Path):
    run(bmad_64_consumer, "--skill", "bmad-dev-story")
    out = bmad_64_consumer / "_bmad/custom/bmad-dev-story.toml"
    first_hash = sha256(out)
    run(bmad_64_consumer, "--skill", "bmad-dev-story", "--force")
    second_hash = sha256(out)
    assert first_hash == second_hash
