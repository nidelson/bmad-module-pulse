"""The loop plugin closes the measurement AFTER review, and loads at all.

WHY THIS FILE EXISTS. `track-done` used to hang off the `on_complete` of
`bmad-build-auto`, which fires at the end of the DEV session. Under `bmad-loop`
the review runs after that, as independent orchestrator sessions, so the
measurement closed before review had started. On story 23.3 of the SIP that
recorded 1.05h against a real 3.05h span and `first_pass: true` on a story that
took three review cycles — under-measured by 2.9x.

The premise came from `bmad-build.toml`, where it is TRUE and says so:
"review has already run inside this workflow via workflow.review_layers".
Copying the hook carried that sentence across an architecture boundary where it
does not hold. The tests below pin the boundary itself, not the prose:
`post_commit` for closing, never `pre_story`, and never the dev-session hook.

The existing template tests assert the CONTENT of an instruction. They cannot
catch this class of bug, because the text was correct — the firing point was
not. These assert structure and behaviour instead.
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
PLUGIN_DIR = REPO_ROOT / "skills/bmad-pulse-setup/assets/loop-plugin"
MANIFEST = PLUGIN_DIR / "plugin.toml"
SCRIPT = PLUGIN_DIR / "track-done-from-journal.py"


@pytest.fixture(scope="module")
def manifest() -> dict:
    return tomllib.loads(MANIFEST.read_text(encoding="utf-8"))


# ── the seam: post_commit — after review, before the worktree is destroyed ───


def test_closing_hook_is_post_commit(manifest: dict):
    """`post_commit` is emitted from `_finalize` on the line right after the
    journal records `story-done` (`engine.py`), and it is reached only through
    `_review_and_commit` — so review has run and every field this plugin needs
    is already on disk.

    It replaced `post_story`, which is emitted later and is structurally unable
    to run: the loop launches a declarative hook with
    `cwd = ctx.worktree or ctx.repo_root` (`plugins/bus.py`), and by `post_story`
    the worktree has been deleted by `unit-merged`, so `subprocess.run` dies with
    ENOENT before the command's first byte. Measured on SIP story 22.2, run
    20260910-213338-52e4:

        23:18:53  review-result
        23:19:15  story-done       <- post_commit fires here, worktree alive
        23:19:15  unit-merged      <- worktree removed
        23:19:36  plugin-hook-error   "[Errno 2] ... /worktrees/2"

    The run still reported `1 done`. Reported upstream as bmad-loop#779; this
    hook does not wait for that fix, because `post_commit` is a correct seam on
    its own terms — it is simply earlier than the destruction.
    """
    assert list(manifest["hooks"]) == ["post_commit"]


def test_the_plugin_never_binds_a_stage_that_precedes_review(manifest: dict):
    """The bug this plugin exists to fix was a hook that closed the measurement
    before review had run. `post_dev_phase` and `post_review_result` both fire
    while the story can still take another review cycle — binding either would
    reintroduce the 2.9x under-measurement with a different name."""
    for stage in ("post_dev_phase", "post_review_result", "pre_commit"):
        assert stage not in manifest["hooks"], (
            f"{stage} can fire before the story is final — review_cycles and "
            "actual_hours would be captured mid-flight"
        )


def test_the_plugin_never_binds_post_story(manifest: dict):
    """Regression pin for bmad-loop#779. `post_story` reads as the natural seam
    and is what this plugin used to declare; the worktree is gone by then."""
    assert "post_story" not in manifest["hooks"]


def test_the_plugin_never_claims_pre_story(manifest: dict):
    """`pre_story` fires before everything, including the planning leg of a
    `spec_checkpoint` run. Anchoring track-start there would fold the human
    approval wait — minutes, or a weekend — into `actual_hours`: the same bug
    as the one this plugin fixes, at the other end."""
    assert "pre_story" not in manifest["hooks"]
    assert "pre_dev_phase" not in manifest["hooks"]
    assert "post_dev_phase" not in manifest["hooks"]


def test_hook_does_not_block_the_run(manifest: dict):
    """A missing measurement is a gap in the baseline; a failed build is a gap
    in the product. An observability hook never gets to cause the second."""
    h = manifest["hooks"]["post_commit"]
    assert h.get("blocking", False) is False
    assert h.get("fail_closed", False) is False


def test_command_is_deterministic_not_an_agent(manifest: dict):
    """No `claude -p`. An agent session costs tokens, needs auth, and can
    paraphrase a file into a wrong number. During the work that produced this
    plugin an expiring OAuth session killed four separate processes, each with
    a silent 73-byte stderr — a measurement that fails that way is missing
    exactly when the run was long enough to matter."""
    cmd = manifest["hooks"]["post_commit"]["cmd"]
    assert "claude" not in cmd
    assert "track-done-from-journal.py" in cmd
    assert "{scripts}" in cmd, "must use the loop's own placeholder for its dir"


# ── it actually loads: a plugin that does not is silent ──────────────────────


def test_manifest_parses_with_the_loops_own_loader(tmp_path: Path):
    """The registry rejects a bad plugin by DISABLING it and journalling —
    "the run survives". No console error, no `plugin-loaded` event, and the
    story ships unmeasured. A spike lost a whole run's measurement to exactly
    this before anyone noticed, so the load is asserted rather than assumed.

    Skipped when `bmad-loop` is not installed: this repo does not depend on it,
    and a skip is honest where a pass would not be.
    """
    loader = pytest.importorskip(
        "bmad_loop.plugins", reason="bmad-loop not installed in this environment"
    )
    dest = tmp_path / ".bmad-loop" / "plugins" / "pulse"
    dest.mkdir(parents=True)
    for f in PLUGIN_DIR.iterdir():
        (dest / f.name).write_bytes(f.read_bytes())

    found = loader.load_plugins(tmp_path)
    assert "pulse" in found, "the loop's loader did not discover the plugin"
    p = found["pulse"]
    assert [h.stage for h in p.hooks] == ["post_commit"]
    assert p.render(p.hooks[0].cmd).endswith("track-done-from-journal.py")


def test_manifest_declares_api_version(manifest: dict):
    """Required by the loader, and version-checked against the build. A
    third-party plugin on an unsupported api_version is SKIPPED silently."""
    assert manifest["plugin"]["api_version"] == 1


def test_the_two_copies_of_the_script_stay_identical():
    """The script lives twice on purpose: `scripts/` is where the module keeps
    its executables, `assets/loop-plugin/` is what gets copied into a consumer
    project. Two copies drift, and the drift is invisible — the installed one
    runs while the reviewed one is the other file.

    Compared by bytes rather than by mtime or size, so an edit to either side
    fails here instead of at someone's next run.
    """
    a = (REPO_ROOT / "skills/bmad-pulse-setup/scripts/track-done-from-journal.py").read_bytes()
    b = SCRIPT.read_bytes()
    assert a == b, (
        "scripts/ and assets/loop-plugin/ copies diverged — the installed plugin "
        "would run code nobody reviewed"
    )


# ── behaviour: the numbers come from the journal ─────────────────────────────


def journal(tmp: Path, events: list[dict]) -> Path:
    run = tmp / "run"
    run.mkdir(parents=True, exist_ok=True)
    (run / "journal.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events), encoding="utf-8"
    )
    return run


def status(tmp: Path, entry: str) -> Path:
    p = tmp / "_bmad-output/implementation-artifacts"
    p.mkdir(parents=True, exist_ok=True)
    f = p / "sprint-status.yaml"
    f.write_text(entry, encoding="utf-8")
    return f


def run_hook(run_dir: Path, repo: Path, story="3", folder="specs/e23"):
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        env={
            "PATH": "/usr/bin:/bin",
            "BMAD_LOOP_RUN_DIR": str(run_dir),
            "BMAD_LOOP_STORY_KEY": story,
            "BMAD_LOOP_REPO_ROOT": str(repo),
            "BMAD_LOOP_SPEC_FOLDER": folder,
        },
        capture_output=True,
        text=True,
    )


ENTRY = textwrap.dedent(
    """\
    pulse_metrics:
      23-3-piloto:
        identity:
          story_id: '23.3'
          spec_folder: specs/e23
        start_ts: '2026-09-07T01:42:09'
        estimated_hours: 0.72
        end_ts: '2026-09-07T02:45:25'
        actual_hours: 1.05
        review_cycles: 1
        first_pass: true
    """
)

# start 01:42:09 · dev + 3 review sessions · story-done 04:45:10
EVENTS = [
    {"ts": 1788759729.0, "kind": "session-start", "story_key": "3", "role": "dev"},
    {"ts": 1788763687.0, "kind": "session-start", "story_key": "3", "role": "review"},
    {"ts": 1788769088.0, "kind": "session-start", "story_key": "3", "role": "review"},
    {"ts": 1788769391.0, "kind": "session-start", "story_key": "3", "role": "review"},
    {"ts": 1788770710.0, "kind": "story-done", "story_key": "3", "commit": "abc123"},
]


def test_end_ts_comes_from_story_done_not_the_dev_session(tmp_path: Path):
    """The regression itself: the recorded span must cover review."""
    f = status(tmp_path, ENTRY)
    r = run_hook(journal(tmp_path, EVENTS), tmp_path)
    assert r.returncode == 0, r.stderr
    m = yaml.safe_load(f.read_text())["pulse_metrics"]["23-3-piloto"]
    assert m["actual_hours"] > 3.0, "the span still stops before review"
    assert m["review_cycles"] == 3
    assert m["first_pass"] is False


def test_a_story_that_never_finished_is_not_closed(tmp_path: Path):
    """Deferred, escalated or stopped: writing a completion there would put a
    finished-looking row on unfinished work. Exits 0 — not measuring is not a
    build failure."""
    status(tmp_path, ENTRY)
    r = run_hook(journal(tmp_path, EVENTS[:-1]), tmp_path)
    assert r.returncode == 0
    m = yaml.safe_load(
        (tmp_path / "_bmad-output/implementation-artifacts/sprint-status.yaml").read_text()
    )["pulse_metrics"]["23-3-piloto"]
    assert m["actual_hours"] == 1.05, "an unfinished story was closed anyway"


def test_it_refuses_to_guess_which_story_without_a_spec_folder(tmp_path: Path):
    """In stories mode the key is a bare ordinal (`3`), which is NOT unique:
    an epic story numbered `0.4.3` also ends in 3. A first version matched on
    the trailing id alone and, against the real SIP file, wrote 319.54 hours
    onto an unrelated story — a plausible row in the baseline that prices every
    story scored after it."""
    status(tmp_path, ENTRY)
    r = subprocess.run(
        [sys.executable, str(SCRIPT)],
        env={
            "PATH": "/usr/bin:/bin",
            "BMAD_LOOP_RUN_DIR": str(journal(tmp_path, EVENTS)),
            "BMAD_LOOP_STORY_KEY": "3",
            "BMAD_LOOP_REPO_ROOT": str(tmp_path),
            # no BMAD_LOOP_SPEC_FOLDER
        },
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    m = yaml.safe_load(
        (tmp_path / "_bmad-output/implementation-artifacts/sprint-status.yaml").read_text()
    )["pulse_metrics"]["23-3-piloto"]
    assert m["actual_hours"] == 1.05, "wrote without being able to identify the story"


def test_the_write_is_surgical(tmp_path: Path):
    """`sprint-status.yaml` is curated by hand and read by three tools, none of
    them validated in CI. A `yaml.safe_dump` round-trip renormalises the whole
    file — 388/476 lines — and a reviewer who cannot see the one changed line
    cannot catch a bad write.

    Compared as multisets, not by line index: appending a field shifts every
    later line, and an index-wise diff would report the untouched neighbour as
    changed. The question is which lines left and which arrived, not where.
    """
    f = status(tmp_path, ENTRY + "  outra-story:\n    actual_hours: 9.99\n")
    before = f.read_text().splitlines()
    run_hook(journal(tmp_path, EVENTS), tmp_path)
    after = f.read_text().splitlines()

    removed = [l for l in before if l not in after]
    added = [l for l in after if l not in before]

    assert all("outra-story" not in l and "9.99" not in l for l in removed + added), (
        f"an unrelated entry was touched: {removed + added}"
    )
    assert "  outra-story:" in after and "    actual_hours: 9.99" in after
    assert len(removed) + len(added) <= 12, (
        f"{len(removed)} removed / {len(added)} added — expected a handful"
    )


# ── the hook must survive a worktree that is already gone ────────────────────
#
# WHY. `bmad-loop` runs a declarative hook with `cwd = ctx.worktree or
# ctx.repo_root` (`plugins/bus.py`). At `post_story` the worktree has ALREADY
# been removed by `unit-merged`, so that cwd does not exist and the subprocess
# dies with ENOENT before the script runs a single line. Observed on SIP story
# 22.2, run 20260910-213338-52e4:
#
#     23:19:15  unit-merged          <- worktree removed here
#     23:19:36  plugin-hook-error    <- pulse, 21s too late
#     "[Errno 2] No such file or directory: .../worktrees/2"
#
# The measurement was lost and the run still reported "1 done". The script
# itself was never at fault — it resolves everything from BMAD_LOOP_REPO_ROOT,
# which outlives the merge. What matters is that it must not NEED the worktree
# as a working directory, and must not read anything relative to it.


def test_script_never_resolves_paths_relative_to_the_worktree():
    """The worktree is gone at `post_story`. Anything the script needs must be
    resolved from BMAD_LOOP_REPO_ROOT or BMAD_LOOP_RUN_DIR, both of which
    survive `unit-merged`. A `BMAD_LOOP_WORKTREE` read would reintroduce the
    ENOENT class even if cwd were fixed."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert "BMAD_LOOP_WORKTREE" not in src, (
        "the worktree does not exist when post_story fires — resolve from "
        "BMAD_LOOP_REPO_ROOT instead"
    )
