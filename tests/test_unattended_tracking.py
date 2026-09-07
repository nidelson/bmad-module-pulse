"""The unattended route (`bmad-build-auto`) measures, and measures honestly.

WHY THIS FILE EXISTS. `bmad-build-auto` is the skill an orchestrator invokes to
run a story with nobody watching. It is a separate skill *directory* from
`bmad-build`, and BMAD resolves customization per skill name — `_bmad/custom/
<skill-name>.toml`. A project that installed the hooks for `bmad-build` and
never got a file for `bmad-build-auto` therefore ships stories that PULSE never
hears about, and the failure is silent in the worst way: an absent customization
file is a *valid* state, so nothing errors, nothing warns, and the gap only
surfaces later as a story with no `start_ts`.

That is the bug these templates close. The tests below pin the three properties
that make the closure worth having.

1. THE HOOKS EXIST AT ALL, and reach both halves of the cycle.

2. THE INSTRUCTIONS DO NOT ASK A HUMAN. `track-done` interactively prompts for
   `review_cycles`, `effective_hours` and halts, because in a session with a
   person only the person knows. Unattended, the workflow knows better than a
   person would — `review_cycles` is literally written down in the spec's
   `## Review Triage Log`, and the other two are *absent by construction*: both
   exist to account for human idle time, and there is no human. So the template
   must tell the workflow to report what it observed. A template that let an
   agent answer freely would invent numbers under a heading that reads like
   measurement.

3. THE PLANNING LEG DOES NOT COUNT AS IMPLEMENTATION. With `spec_checkpoint`,
   leg 1 plans and halts at `ready-for-dev` having written no code; leg 2
   implements. Both legs run the activation steps. Stamping `start_ts` on leg 1
   would fold the human checkpoint wait — minutes, or a weekend — into
   `actual_hours`, and every derived number (leverage, predictability, the
   category baseline) would inherit it.

The asymmetry in what the templates forbid is deliberate and worth stating: a
MISSING halt costs one story's precision, while an INVENTED halt is subtracted
from `actual_hours`, inflates that story's leverage ratio, and then enters the
per-category baseline that prices every story scored afterwards. The templates
are permissive about the first and absolute about the second.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
TEMPLATES = REPO_ROOT / "skills/bmad-pulse-setup/assets/customize-templates"

PLAIN = TEMPLATES / "bmad-build-auto.toml"
BCP = TEMPLATES / "bmad-build-auto.bcp.toml"

BOTH = pytest.mark.parametrize("path", [PLAIN, BCP], ids=["plain", "bcp"])


def workflow(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))["workflow"]


def steps_text(path: Path) -> str:
    return " ".join(workflow(path).get("activation_steps_append", []))


def all_text(path: Path) -> str:
    w = workflow(path)
    return steps_text(path) + " " + w.get("on_complete", "")


# ── 1. the route is wired at all ─────────────────────────────────────────────


@BOTH
def test_template_exists(path: Path):
    assert path.exists(), (
        f"{path.name} is missing — the unattended route silently records nothing"
    )


@BOTH
def test_track_start_fires_from_an_executed_activation_step(path: Path):
    """`activation_steps_append` is executed; `persistent_facts` is passive
    context. PULSE moved off the latter in #47 precisely because a hook parked
    there loaded but did not reliably fire."""
    assert "bmad-pulse-track-start" in steps_text(path)
    assert "bmad-pulse-track-start" not in " ".join(
        workflow(path).get("persistent_facts", [])
    )


@BOTH
def test_the_template_does_not_close_the_measurement(path: Path):
    """`on_complete` fires at the end of the DEV session. Under `bmad-loop` the
    review runs afterwards, as independent orchestrator sessions — so anything
    that closes a measurement here reads a story that is not finished.

    This assertion replaced four earlier ones that pinned the *wording* of a
    track-done instruction living in `on_complete`. The wording was fine; the
    firing point was not, and no phrasing fixes a hook that cannot observe a
    session which has not started. Measured on story 23.3 of the SIP: 1.05h
    recorded against a 3.05h span, `first_pass: true` on three review cycles.

    Closing now belongs to the loop plugin at `post_story` — see
    `assets/loop-plugin/` and `tests/test_loop_plugin.py`.
    """
    text = workflow(path).get("on_complete", "")
    assert "track-done" not in text, (
        "track-done is back in on_complete — it would stamp end_ts before review"
    )
    assert "recalibrate" not in text, (
        "recalibrate is back in on_complete — it would read the wrong actual_hours "
        "and feed it to the per-category baseline"
    )


@BOTH
def test_the_template_still_starts_the_measurement(path: Path):
    """Removing the closing half must not silently remove the opening one: a
    story with no `start_ts` is invisible to the plugin, which needs something
    to close against."""
    assert "bmad-pulse-track-start" in steps_text(path)


@BOTH
def test_the_template_says_where_closing_went(path: Path):
    """A reader who greps this file for `track-done` and finds nothing must not
    conclude that the unattended route does not measure. The comment header
    carries the pointer, and this test keeps it there."""
    raw = path.read_text(encoding="utf-8")
    assert "loop-plugin" in raw
    assert "post_story" in raw


@BOTH
def test_story_id_is_not_read_back_from_sprint_status(path: Path):
    """The workflow writes `in-progress` to sprint-status moments earlier, so
    reading it back to learn which story this is would be circular — it would
    confirm what was just written rather than establish identity."""
    assert "spec_file" in steps_text(path)


# ── 2. nobody is asked a question there is no one to answer ──────────────────


# ── the honest-measurement rules moved to the plugin, which enforces them ────
#
# Four tests lived here asserting the WORDING of the track-done instruction:
# that it read `review_cycles` off the Review Triage Log, declined
# `effective_hours`, and forbade inventing halts. They passed while the hook
# fired at the wrong moment and recorded 1.05h for a 3.05h story.
#
# That is the lesson worth keeping: an instruction's text can be perfectly
# correct and still be read at a point where the facts it describes do not exist
# yet. Prose asserted against prose proves only that both were written by the
# same person on the same day.
#
# The plugin does not phrase those rules — it makes them unnecessary. There is
# no `effective_hours` prompt to decline, because nothing prompts; no halt to
# invent, because nothing is asked; and `review_cycles` is counted from the
# journal instead of recalled. See `tests/test_loop_plugin.py`, which asserts
# behaviour against a fixture journal rather than wording against a template.


def test_only_the_bcp_variant_carries_scoring():
    """Same rule as every other template pair here: a project with scoring off
    never receives the instruction at all, not even as text that checks and
    skips.

    Scoring stayed in the template while closing moved to the plugin, and the
    asymmetry is the point: scoring must happen BEFORE implementation, which is
    a moment only the workflow can see (end of step-02, spec at
    `ready-for-dev`). Closing must happen AFTER review, which only the
    orchestrator can see. Each half sits where its moment is observable.
    """
    assert "bmad-bcp-score" in steps_text(BCP)
    assert "bmad-bcp-score" not in all_text(PLAIN)


# ── 3. planning is not implementation ────────────────────────────────────────


@BOTH
def test_track_start_skips_the_planning_leg(path: Path):
    """Leg 1 of a `spec_checkpoint` run ends at `ready-for-dev` with no code
    written, then waits on a human. Stamping `start_ts` there books that wait as
    development time.

    Asserted on the track-start step specifically, and on the *skip clause*
    inside it — not on the template as a whole. An earlier version of this test
    checked that `ready-for-dev` appeared anywhere in the file and passed even
    with the guard deleted, because the BCP scoring step mentions the same
    status for an unrelated reason.
    """
    step = next(
        s for s in workflow(path)["activation_steps_append"]
        if "bmad-pulse-track-start" in s
    )
    head, _, skip_clause = step.partition("SKIP")
    assert skip_clause, "track-start step has no SKIP clause at all"
    assert "ready-for-dev" in skip_clause, (
        "the SKIP clause does not name the planning leg — a leg-1 run would "
        "stamp start_ts before the checkpoint wait"
    )
    assert "without implementing" in skip_clause


@BOTH
def test_unresolved_story_key_skips_without_erroring(path: Path):
    """No key means nowhere to record the metric. A hard failure here would turn
    a measurement gap into a build failure, which is the wrong trade for an
    observability hook."""
    assert "story_key" in all_text(path)


# ── the BCP variant additionally scores, and scores before implementing ──────


def test_scoring_happens_before_implementation():
    """BCP is an a-priori estimate. Scored after the work, it anchors on how hard
    the story turned out to be — which is not an estimate at all, and it enters
    the baseline as though it were one."""
    text = steps_text(BCP)
    assert "step-02" in text
    assert "step-03" in text
    assert "before implement" in text.lower()


def test_an_already_scored_story_is_not_rescored():
    """Leg 2 re-runs the activation steps and finds `bcp.total` already present
    from leg 1. Re-scoring there would replace the a-priori estimate with a
    retrospective one and keep the field name."""
    assert "bcp.total" in steps_text(BCP)


def test_recalibrate_waits_for_actual_hours():
    """`actual_hours` is written when the measurement closes. Recalibrating
    before that reads a field that does not exist yet — or, worse, one written
    too early.

    The ordering used to be expressed as prose inside `on_complete` ("STEP 1
    ... STEP 2, only after STEP 1 has fully completed"), which made it a request
    an agent could misread. It is now structural: recalibration is a function
    call after the write, inside the same script, so there is no ordering left
    to get wrong.

    Asserted here rather than in the plugin tests because this is the template's
    obligation — it must NOT carry a recalibrate step of its own, which would
    run against the pre-review `actual_hours` and feed the category baseline a
    number that prices every story scored afterwards.
    """
    assert "recalibrate" not in all_text(BCP), (
        "the template still recalibrates — it would use the wrong actual_hours"
    )
    plugin = TEMPLATES.parent / "loop-plugin/track-done-from-journal.py"
    assert plugin.exists(), "the plugin that owns recalibration is missing"
    src = plugin.read_text(encoding="utf-8")
    assert "def recalibrate(" in src
    # the call has to come after the write, not before it
    assert src.index("write_fields(status_path") < src.index("recalibrate(repo")
