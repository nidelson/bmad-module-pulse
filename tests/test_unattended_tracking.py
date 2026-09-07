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
def test_track_done_fires_on_complete(path: Path):
    assert "bmad-pulse-track-done" in workflow(path).get("on_complete", "")


@BOTH
def test_story_id_is_not_read_back_from_sprint_status(path: Path):
    """The workflow writes `in-progress` to sprint-status moments earlier, so
    reading it back to learn which story this is would be circular — it would
    confirm what was just written rather than establish identity."""
    assert "spec_file" in steps_text(path)


# ── 2. nobody is asked a question there is no one to answer ──────────────────


@BOTH
def test_review_cycles_comes_from_the_triage_log(path: Path):
    """The count is recorded in the spec, one entry per review pass. Reading it
    is measurement; asking an agent to recall it is estimation wearing the same
    field name."""
    text = workflow(path).get("on_complete", "")
    assert "Review Triage Log" in text
    assert "review_cycles" in text


@BOTH
def test_effective_hours_is_declined_rather_than_guessed(path: Path):
    """`effective_hours` overrides the wall-clock derivation. It exists to strip
    human idle time, which an unattended run does not have — so supplying any
    value replaces a real measurement with an invented one."""
    text = workflow(path).get("on_complete", "")
    assert "effective_hours" in text
    assert "do NOT supply" in text


@BOTH
def test_halts_may_not_be_invented(path: Path):
    """The asymmetry: halts are SUBTRACTED from actual_hours. A missing halt
    costs precision on one story; a fabricated one inflates that story's
    leverage and then poisons the category baseline behind it."""
    text = workflow(path).get("on_complete", "")
    assert "Never invent" in text
    assert "SUBTRACTED" in text


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


def test_only_the_bcp_variant_carries_scoring():
    """Same rule as every other template pair here: a project with scoring off
    never receives the instruction at all, not even as text that checks and
    skips."""
    assert "bmad-bcp-score" in steps_text(BCP)
    assert "bmad-bcp-score" not in all_text(PLAIN)
    assert "bmad-bcp-recalibrate" in workflow(BCP).get("on_complete", "")
    assert "bmad-bcp-recalibrate" not in all_text(PLAIN)


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
    """`actual_hours` is written by track-done. Recalibrating before it lands
    reads a field that does not exist yet, and the sample is silently skipped —
    the baseline simply never learns from the story."""
    text = workflow(BCP).get("on_complete", "")
    assert "actual_hours" in text
    assert "STEP 1" in text and "STEP 2" in text
    assert text.index("STEP 1") < text.index("STEP 2")
