"""Unit tests for skills/bmad-pulse-setup/scripts/inject_customize.py."""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "skills/bmad-pulse-setup/scripts/inject_customize.py"
GOLDEN = Path(__file__).parents[1] / "fixtures/golden"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(consumer: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(consumer), *args],
        capture_output=True,
        text=True,
    )


# --- BCP variant: the recalibrate step is opt-in, and ordered ---------------


def test_without_with_bcp_no_recalibrate_step(bmad_build_consumer: Path):
    """The opt-in lock, at the file level.

    A project that does not enable scoring must not receive the recalibrate
    instruction at all — not even as an instruction that checks and skips.
    Inert text in `on_complete` is still text the agent reads every run.
    """
    run(bmad_build_consumer, "--skill", "bmad-build")
    body = (bmad_build_consumer / "_bmad/custom/bmad-build.toml").read_text(encoding="utf-8")
    assert "bmad-bcp-recalibrate" not in body
    assert "bmad-pulse-track-done" in body


def test_with_bcp_emits_the_variant(bmad_build_consumer: Path):
    result = run(bmad_build_consumer, "--skill", "bmad-build", "--with-bcp")
    assert result.returncode == 0, result.stderr
    out = bmad_build_consumer / "_bmad/custom/bmad-build.toml"
    assert sha256(out) == sha256(GOLDEN / "customize-bmad-build-bcp.toml")


def test_variant_shares_the_destination(bmad_build_consumer: Path):
    """Same destination either way — the two templates are alternatives, not
    additions. Writing both would leave whichever ran last in place, which is
    the cross-module coordination this replaces."""
    run(bmad_build_consumer, "--skill", "bmad-build", "--with-bcp")
    custom = bmad_build_consumer / "_bmad/custom"
    assert (custom / "bmad-build.toml").exists()
    assert not (custom / "bmad-build.bcp.toml").exists()


def test_recalibrate_comes_after_track_done(bmad_build_consumer: Path):
    """The whole point of authoring one sequence.

    Recalibrate reads `actual_hours`, which only exists after track-done has
    finished its interactive prompts. Previously this ordering was a sentence
    inside a string appended by a second module; now it is the file itself.
    """
    run(bmad_build_consumer, "--skill", "bmad-build", "--with-bcp")
    body = (bmad_build_consumer / "_bmad/custom/bmad-build.toml").read_text(encoding="utf-8")
    assert body.index("bmad-pulse-track-done") < body.index("bmad-bcp-recalibrate")
    assert "STEP 1" in body and "STEP 2" in body


def test_with_bcp_rejects_a_skill_without_a_variant(bmad_64_consumer: Path):
    """bmad-dev-story carries track-start, which BCP does not extend. Silently
    falling back to the plain template would drop the recalibrate step and
    report success."""
    result = run(bmad_64_consumer, "--skill", "bmad-dev-story", "--with-bcp")
    assert result.returncode != 0
    assert "bmad-dev-story" in result.stderr


def test_code_review_variant_also_available(bmad_64_consumer: Path):
    result = run(bmad_64_consumer, "--skill", "bmad-code-review", "--with-bcp")
    assert result.returncode == 0, result.stderr
    body = (bmad_64_consumer / "_bmad/custom/bmad-code-review.toml").read_text(encoding="utf-8")
    assert body.index("bmad-pulse-track-done") < body.index("bmad-bcp-recalibrate")


def test_emits_build_override_on_unified_architecture(bmad_build_consumer: Path):
    result = run(bmad_build_consumer, "--skill", "bmad-build")
    assert result.returncode == 0, result.stderr
    out = bmad_build_consumer / "_bmad/custom/bmad-build.toml"
    assert out.exists()
    assert sha256(out) == sha256(GOLDEN / "customize-bmad-build.toml")


def test_build_override_carries_both_hooks(bmad_build_consumer: Path):
    """One file, both hooks — bmad-build implements and reviews in one workflow.

    The split architecture needs two files because bmad-dev-story ends at
    "review"; here the review layers run in-process, so a single on_complete is
    the honest completion point.
    """
    run(bmad_build_consumer, "--skill", "bmad-build")
    body = (bmad_build_consumer / "_bmad/custom/bmad-build.toml").read_text(encoding="utf-8")
    assert "bmad-pulse-track-start" in body
    assert "bmad-pulse-track-done" in body


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


# --- the scoring trigger: architecture-independent, BCP-only ----------------


def test_create_story_variant_carries_the_scoring_call(bmad_build_consumer: Path):
    """The gap this closes.

    The scoring hook lived in the standalone module's `bmad-create-story.toml`
    and had no counterpart here, so after that module was deprecated nothing
    invoked `bmad-bcp-score`. Recalibration then skipped forever — silently, and
    correctly, because it checks for `bcp.total` before running.
    """
    result = run(bmad_build_consumer, "--skill", "bmad-create-story", "--with-bcp")
    assert result.returncode == 0, result.stderr
    body = (bmad_build_consumer / "_bmad/custom/bmad-create-story.toml").read_text(
        encoding="utf-8"
    )
    assert "bmad-bcp-score" in body
    assert "persistent_facts" in body


def test_create_story_hook_appends_rather_than_replaces(bmad_build_consumer: Path):
    """`persistent_facts` is a list. Using `on_complete` here would silently
    clobber whatever the workflow or another module already put there.

    Asserted on the assigned keys, not on the text: the header explains at
    length why `on_complete` is the wrong instrument, and a substring check
    would read that explanation as the mistake it warns about.
    """
    run(bmad_build_consumer, "--skill", "bmad-create-story", "--with-bcp")
    body = (bmad_build_consumer / "_bmad/custom/bmad-create-story.toml").read_text(
        encoding="utf-8"
    )
    keys = {
        line.split("=", 1)[0].strip()
        for line in body.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }
    assert "persistent_facts" in keys
    assert "on_complete" not in keys


def test_create_story_is_not_tier_dependent(bmad_build_consumer: Path):
    """Story authoring did not move when implementation did.

    `bmad-build` does not replace `bmad-create-story` — it writes a spec, whose
    frontmatter carries no `estimated_hours` to derive. So this hook is the same
    file on both architectures, and it must NOT appear in the probe's per-tier
    `inject_targets`: putting it there would encode a difference that does not
    exist, and would drop the hook on whichever tier the list forgot.
    """
    import importlib.util

    probe_path = (Path(__file__).parents[2]
                  / "skills/bmad-pulse-setup/scripts/detect_bmad_capability.py")
    spec = importlib.util.spec_from_file_location("detect_probe", probe_path)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)

    for targets in probe.INJECT_TARGETS.values():
        assert "bmad-create-story" not in targets

    result = run(bmad_build_consumer, "--skill", "bmad-create-story", "--with-bcp")
    assert result.returncode == 0, result.stderr
    emitted = bmad_build_consumer / "_bmad/custom/bmad-create-story.toml"
    packaged = (Path(__file__).parents[2]
                / "skills/bmad-pulse-setup/assets/customize-templates"
                / "bmad-create-story.bcp.toml")
    assert sha256(emitted) == sha256(packaged)


def test_create_story_without_with_bcp_is_rejected(bmad_build_consumer: Path):
    """This template exists only in a BCP variant: PULSE has nothing to say to
    story authoring unless scoring is on. Falling back to a plain template that
    does not exist must be an explicit error, not a missing-file traceback."""
    result = run(bmad_build_consumer, "--skill", "bmad-create-story")
    assert result.returncode != 0
    assert "bmad-create-story" in result.stderr
    assert "--with-bcp" in result.stderr
    assert not (bmad_build_consumer / "_bmad/custom/bmad-create-story.toml").exists()
