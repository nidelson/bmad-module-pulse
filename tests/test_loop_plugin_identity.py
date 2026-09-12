"""Identity resolution and write scope — the two defects the preflight caught.

WHY THIS FILE EXISTS. The SIP preflight (2026-09-11) drove the REAL `HookBus`
of bmad-loop 0.11.1 through `post_commit` with the installed plugin and found
two defects that no existing test caught, because every behavioural test
hand-injects `BMAD_LOOP_SPEC_FOLDER` — a variable the bus does not export:

1. IDENTITY. `_hook_env` (plugins/bus.py) exports run identity fields but not
   the spec folder. In stories mode the story key is a bare ordinal, so
   `find_entry` cannot disambiguate and skips with a message that blames
   track-start ("track-start never ran") when track-start had run. Model A
   (sprint-status mode) is NEVER ambiguous — the journal key IS the
   pulse_metrics key, full slug — yet it was skipped too.

2. WRITE SCOPE. `write_fields` matched the first line starting with the key
   anywhere in the file. 21 of 36 entries in the real SIP file exist in BOTH
   `development_status` and `pulse_metrics` (development_status comes first),
   so the writer appended fields under the scalar status value in
   development_status, produced invalid YAML ("mapping values are not allowed
   here", line 222), printed "closed", and exited 0.

The fix under test: model A matches by exact key; model B resolves the spec
folder from the run's `state.json` (top-level `spec_folder`), which the script
already reaches via BMAD_LOOP_RUN_DIR — no upstream dependency (bmad-loop#779
stays open for the env gap). The writer only ever touches the block under
`pulse_metrics:`.

Provenance of the fixtures: the events are the shape of SIP run
20260910-213338-52e4 (story 22.2, one dev session, one review, story-done);
the model-A journal shape is SIP run 20260907-183942-fc65, whose story key is
the full slug `22-1-fundacao-orchestrator-contrato-leitura`.
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import yaml

from tests.test_loop_plugin import EVENTS, REPO_ROOT, SCRIPT

# ── fixtures: both models, key present in BOTH sections (the real risk) ──────

STATUS_BOTH_SECTIONS = textwrap.dedent(
    """\
    development_status:
      22-1-fundacao-orchestrator-contrato-leitura: in-progress
      backlog: []
    pulse_metrics:
      22-1-fundacao-orchestrator-contrato-leitura:
        identity:
          epic: 22
          story_id: '22.1'
          story_file: _bmad-output/implementation-artifacts/22-1-fundacao-orchestrator-contrato-leitura.md
          source: sprint-status
        start_ts: '2026-09-07T01:35:00'
        estimated_hours: 2.0
        end_ts: '2026-09-07T03:00:00'
        actual_hours: 1.33
        review_cycles: 1
        first_pass: true
    """
)

STATUS_MODEL_B = textwrap.dedent(
    """\
    development_status:
      backlog: []
    pulse_metrics:
      22-2-caixa-aprovacao-escalacoes:
        identity:
          epic: 22
          story_id: '22.2'
          story_file: _bmad-output/planning-artifacts/epics/spec-epic-22/stories/2-caixa-aprovacao-escalacoes.md
          source: spec-folder
          spec_folder: _bmad-output/planning-artifacts/epics/spec-epic-22
        start_ts: '2026-09-07T01:35:39'
        estimated_hours: 2.71
        end_ts: '2026-09-07T03:19:15'
        actual_hours: 1.73
        review_cycles: 1
        first_pass: true
    """
)

# model A: the journal story_key IS the full slug (SIP run 20260907-183942)
EVENTS_A = [
    {"ts": 1788759729.0, "kind": "session-start", "story_key": "22-1-fundacao-orchestrator-contrato-leitura", "role": "dev"},
    {"ts": 1788763687.0, "kind": "session-start", "story_key": "22-1-fundacao-orchestrator-contrato-leitura", "role": "review"},
    {"ts": 1788770710.0, "kind": "story-done", "story_key": "22-1-fundacao-orchestrator-contrato-leitura", "commit": "abc123"},
]

# model B: journal key is the bare ordinal; spec folder lives in state.json
EVENTS_B = [
    {"ts": 1788759729.0, "kind": "session-start", "story_key": "2", "role": "dev"},
    {"ts": 1788763687.0, "kind": "session-start", "story_key": "2", "role": "review"},
    {"ts": 1788770710.0, "kind": "story-done", "story_key": "2", "commit": "abc123"},
]


def make_run(tmp: Path, events: list[dict], spec_folder: str | None) -> Path:
    run = tmp / "run"
    run.mkdir(parents=True, exist_ok=True)
    (run / "journal.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events), encoding="utf-8"
    )
    if spec_folder is not None:
        (run / "state.json").write_text(
            json.dumps({"spec_folder": spec_folder, "source": "stories"}), encoding="utf-8"
        )
    return run


def make_status(tmp: Path, content: str) -> Path:
    p = tmp / "_bmad-output/implementation-artifacts"
    p.mkdir(parents=True, exist_ok=True)
    f = p / "sprint-status.yaml"
    f.write_text(content, encoding="utf-8")
    return f


def run_hook(run_dir: Path, repo: Path, story: str) -> subprocess.CompletedProcess:
    """Drives the script exactly as the bus does: identity fields only.

    No BMAD_LOOP_SPEC_FOLDER — the bus does not export it (the gap reported as
    bmad-loop#779). Everything else the script needs must come from the run dir.
    """
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        env={
            "PATH": "/usr/bin:/bin",
            "BMAD_LOOP_RUN_DIR": str(run_dir),
            "BMAD_LOOP_STORY_KEY": story,
            "BMAD_LOOP_REPO_ROOT": str(repo),
        },
        capture_output=True,
        text=True,
    )


# ── model A: exact-key match, no spec folder needed ──────────────────────────


def test_model_a_closes_by_exact_journal_key(tmp_path: Path):
    """Model A was skipped entirely: without a spec folder `find_entry` returned
    None and the hook logged a wrong message blaming track-start. In
    sprint-status mode the journal key is the FULL slug — the exact
    pulse_metrics key — so no disambiguation is ever needed."""
    f = make_status(tmp_path, STATUS_BOTH_SECTIONS)
    r = run_hook(make_run(tmp_path, EVENTS_A, spec_folder=None), tmp_path, story="22-1-fundacao-orchestrator-contrato-leitura")
    assert r.returncode == 0, r.stderr
    m = yaml.safe_load(f.read_text())["pulse_metrics"]["22-1-fundacao-orchestrator-contrato-leitura"]
    assert m["actual_hours"] != 1.33, "model A was not closed"
    assert m["review_cycles"] == 1
    assert m["first_pass"] is True
    assert m["measured_by"] == "bmad-loop-journal"


def test_model_a_never_matches_by_suffix(tmp_path: Path):
    """The 319-hour bug: a bare ordinal `1` must NOT close
    `22-1-fundacao-orchestrator-contrato-leitura` — trailing-id matching is
    what wrote 319.54h onto an unrelated story once already. A sprint-status
    journal key always arrives in full, so anything that does not match
    exactly is not this run's story."""
    f = make_status(tmp_path, STATUS_BOTH_SECTIONS)
    r = run_hook(make_run(tmp_path, EVENTS_A, spec_folder=None), tmp_path, story="1")
    assert r.returncode == 0, r.stderr
    m = yaml.safe_load(f.read_text())["pulse_metrics"]["22-1-fundacao-orchestrator-contrato-leitura"]
    assert m["actual_hours"] == 1.33, "closed an unrelated story by suffix"


# ── model B: spec folder from state.json, not from the environment ───────────


def test_model_b_resolves_spec_folder_from_state_json(tmp_path: Path):
    """The bus does not export BMAD_LOOP_SPEC_FOLDER (bmad-loop#779), so
    resolving it from the environment works only when the operator's shell
    happens to carry it. The run's own `state.json` — reached via
    BMAD_LOOP_RUN_DIR, which the bus DOES export — carries the spec folder at
    top level. The journal in this mode keys stories by bare ordinal, and the
    pair (spec_folder, trailing id) is what disambiguates."""
    f = make_status(tmp_path, STATUS_MODEL_B)
    r = run_hook(
        make_run(tmp_path, EVENTS_B, spec_folder="_bmad-output/planning-artifacts/epics/spec-epic-22"),
        tmp_path,
        story="2",
    )
    assert r.returncode == 0, r.stderr
    m = yaml.safe_load(f.read_text())["pulse_metrics"]["22-2-caixa-aprovacao-escalacoes"]
    assert m["actual_hours"] != 1.73, "model B was not closed"
    assert m["measured_by"] == "bmad-loop-journal"


def test_model_b_without_spec_folder_nor_state_still_refuses(tmp_path: Path):
    """Refusing to guess stays correct: with a bare ordinal and no resolvable
    spec folder (no env, no state.json), closing would risk writing onto an
    unrelated story. But the refusal message must not blame track-start when
    the entry exists — the preflight's wrong-message finding."""
    f = make_status(tmp_path, STATUS_MODEL_B)
    r = run_hook(make_run(tmp_path, EVENTS_B, spec_folder=None), tmp_path, story="2")
    assert r.returncode == 0, r.stderr
    m = yaml.safe_load(f.read_text())["pulse_metrics"]["22-2-caixa-aprovacao-escalacoes"]
    assert m["actual_hours"] == 1.73, "closed a story it could not identify"
    assert m.get("measured_by") is None
    assert "track-start never ran" not in r.stderr, (
        "the skip message blamed track-start; the entry exists — the honest "
        "message is that the story could not be identified"
    )


# ── write scope: the corruption the preflight reproduced ─────────────────────


def test_write_never_escapes_the_pulse_metrics_section(tmp_path: Path):
    """21 of 36 entries in the real SIP file exist in BOTH sections, with
    development_status first. The writer used to match the first line starting
    with the key, appended fields under the scalar `in-progress` status and
    produced YAML that no longer parses — while printing `closed` and exiting
    0. The write must stay inside the `pulse_metrics:` block, and the file
    must still parse afterwards."""
    f = make_status(tmp_path, STATUS_BOTH_SECTIONS)
    r = run_hook(make_run(tmp_path, EVENTS_A, spec_folder=None), tmp_path, story="22-1-fundacao-orchestrator-contrato-leitura")
    assert r.returncode == 0, r.stderr
    data = yaml.safe_load(f.read_text())  # the preflight corruption: raise here
    assert data["development_status"]["22-1-fundacao-orchestrator-contrato-leitura"] == "in-progress", (
        "development_status was rewritten — the write escaped pulse_metrics"
    )
    assert data["pulse_metrics"]["22-1-fundacao-orchestrator-contrato-leitura"]["actual_hours"] != 1.33


def test_a_file_with_only_pulse_metrics_still_closes(tmp_path: Path):
    """Isolation control: with no development_status at all, both the old and
    the new writer behave identically. If this passes while the both-sections
    case fails, the defect is the section collision — not the writer itself."""
    f = make_status(tmp_path, STATUS_MODEL_B)
    r = run_hook(
        make_run(tmp_path, EVENTS_B, spec_folder="_bmad-output/planning-artifacts/epics/spec-epic-22"),
        tmp_path,
        story="2",
    )
    assert r.returncode == 0, r.stderr
    data = yaml.safe_load(f.read_text())
    m = data["pulse_metrics"]["22-2-caixa-aprovacao-escalacoes"]
    assert m["actual_hours"] != 1.73 and m["measured_by"] == "bmad-loop-journal"
