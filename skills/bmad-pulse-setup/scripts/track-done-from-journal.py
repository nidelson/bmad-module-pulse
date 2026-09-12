#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Fecha a medição PULSE de uma story a partir do journal do `bmad-loop`.

WHY THIS EXISTS. The `on_complete` hook of `bmad-build-auto` fires at the end of
the DEV session. Under `bmad-loop` the review runs AFTER that, as independent
orchestrator sessions, so a `track-done` anchored there stamps `end_ts` before
review has started. Measured on story 23.3 of the SIP: `end_ts` landed at
02:45:25 while review ran 02:48:07 -> 04:45:01, recording 1.05h against a real
span of 3.05h — under-measured by 2.9x, with `first_pass: true` on a story that
took three review cycles.

That is worse than not measuring: the numbers look plausible and enter the
per-category baseline that prices every story scored afterwards.

The premise was inherited from `bmad-build.toml`, where it is TRUE — that
template says so explicitly: "review has already run inside this workflow via
workflow.review_layers". Under the loop it is false, and copying the hook
carried the premise across an architecture boundary where it does not hold.

WHY DETERMINISTIC, not a `claude -p` invocation of the track-done skill. Three
reasons, in order of how much they cost when ignored:

  1. The journal already knows every answer. `end_ts` is the `story-done` event,
     `review_cycles` is the count of review sessions, halts do not exist in an
     unattended run. Asking an agent to report what a file states is asking it to
     paraphrase, which is where invention enters.
  2. No auth, no tokens. An OAuth session expiring mid-run killed two processes
     during the SIP work, each time with a silent 73-byte stderr. A measurement
     step that can fail that way is a measurement step that will be missing
     exactly when the run was long enough to matter.
  3. It runs at `post_commit`, which the engine emits from
     `_finalize_commit_phase` right after the journal records `story-done`,
     reached only via `_commit` — so the review loop has converged and the task
     is COMMITTING, which cannot defer back into review. NOT `post_story`: that
     fires after `unit-merged` has deleted the worktree, and the loop launches
     declarative hooks with the worktree as cwd, so the process dies with ENOENT
     before this file is read (bmad-loop#779).

WHAT IT DELIBERATELY DOES NOT DO. It never writes `start_ts` — that belongs to
`track-start`, which fires inside step-03 when the workflow marks `in-progress`.
Anchoring the start at `pre_story` would be the same bug at the other end:
`pre_story` fires before the planning leg, so a `spec_checkpoint` run would book
the human approval wait as development time.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    sys.exit("track-done-from-journal: requires pyyaml (run via `uv run`)")

EXIT_OK = 0
EXIT_SKIP = 0  # a missing measurement is not a build failure
EXIT_BAD = 1


def log(msg: str) -> None:
    print(f"pulse/track-done: {msg}", file=sys.stderr)


def read_journal(run_dir: Path, story_key: str) -> list[dict]:
    p = run_dir / "journal.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        # story_key is absent on run-level events; keep those out
        if str(e.get("story_key", "")) == str(story_key):
            out.append(e)
    return out


def facts(events: list[dict]) -> dict | None:
    """The three things the journal knows better than anyone.

    `end_ts` is `story-done`, not `session-end` of the last review: the story is
    finished when the orchestrator says so, and that event sits after the final
    review verdict.

    `review_cycles` counts review SESSIONS, not `review-result` events. A session
    that times out produced no verdict but consumed real work — 90 minutes and
    2.15M weighted tokens on story 23.3. Counting verdicts would hide it, and the
    hours it burned are already inside `actual_hours`, so the cycle count has to
    account for them or the two fields contradict each other.
    """
    done = [e for e in events if e.get("kind") == "story-done"]
    if not done:
        return None
    reviews = [
        e for e in events
        if e.get("kind") == "session-start" and e.get("role") == "review"
    ]
    devs = [
        e for e in events
        if e.get("kind") == "session-start" and e.get("role") == "dev"
    ]
    return {
        "end_ts": datetime.fromtimestamp(done[-1]["ts"]).replace(microsecond=0),
        "review_cycles": len(reviews),
        "dev_sessions": len(devs),
        "commit": done[-1].get("commit", ""),
    }


def find_entry(metrics: dict, story_key: str, spec_folder: str) -> str | None:
    """The pulse_metrics key is historic identity, not the story slug.

    Story 23.1 froze that as invariant 1 of the ruler contract: the key
    identifies the measurement, the `identity` block identifies the story. So the
    lookup goes through `identity`.

    WHICH MODE ARE WE IN. The two queue modes key the journal differently, and
    the difference decides the whole lookup:

    * sprint-status mode: the journal `story_key` IS the full pulse_metrics
      key (e.g. `22-1-fundacao-orchestrator-contrato-leitura` — SIP run
      20260907-183942). Exact match, no disambiguation ever needed, and the
      trailing-id match below must NOT run: a suffix match here is exactly
      the 319-hour bug.
    * stories mode (spec folder): the journal key is a bare ordinal (`3`),
      which is not unique across the repo. The pair (spec folder, trailing
      id) is what disambiguates.

    THE MATCH MUST BE ANCHORED ON THE SPEC FOLDER IN STORIES MODE, not on the
    story key alone. A first version of this function compared
    `story_id.split(".")[-1]` and, run against the real SIP status file,
    closed `0-4-3-limpeza-gate-neutral` with **319.54 hours** — a story from
    another epic that had a stale `start_ts`. It would have written a
    plausible-looking row into the baseline that prices every later story.

    So: same spec folder AND same trailing id. A story from a spec folder is
    only ever closed by the run that owns that folder. Without a spec folder
    in stories mode there is no way to disambiguate, and the function refuses
    rather than guessing.
    """
    want = str(story_key)
    # sprint-status mode: the journal key is the pulse_metrics key itself
    if want in metrics and isinstance(metrics.get(want), dict):
        return want
    if not spec_folder:
        return None
    for k, v in metrics.items():
        if not isinstance(v, dict):
            continue
        ident = v.get("identity") or {}
        folder = str(ident.get("spec_folder", ""))
        if not folder or folder not in spec_folder:
            continue
        if str(ident.get("story_id", "")).split(".")[-1] == want:
            return k
    return None


def write_fields(path: Path, key: str, updates: dict) -> None:
    """Rewrite only the touched fields, in place, leaving the rest byte-identical.

    A `yaml.safe_dump` round-trip of this file produces a 388/476-line diff: it
    renormalises quoting, flow style and key order across every entry. Nothing is
    lost — the file carries no comments — but the diff hides which value actually
    changed, in a file three separate tools read and a human curates by hand. The
    SIP `CLAUDE.md` calls `sprint-status.yaml` the source of truth for progress
    and warns that no CI validates it; a reviewer who cannot see the one changed
    line has no way to catch a bad write.

    So the update is textual and anchored: find the entry, then replace or append
    each field inside its block. Indentation is read from the block rather than
    assumed, because the writer is a consumer of someone else's file.

    THE SEARCH STOPS AT THE `pulse_metrics:` SECTION. The same key legitimately
    exists in `development_status` — 21 of 36 entries in the real SIP file do,
    and `development_status` comes first in the file. The first version matched
    the first line starting with the key anywhere, appended fields under the
    scalar status value (`... in-progress`), and produced YAML that no longer
    parsed while the caller printed `closed` and exited 0. The preflight of
    2026-09-11 reproduced it byte-for-byte on a copy of the real file.
    """
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    # locate the `pulse_metrics:` section, then `  <key>:` INSIDE it
    section = None
    start = None
    indent = ""
    for i, ln in enumerate(lines):
        stripped = ln.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if not ln.startswith((" ", "\t")):
            # a top-level key: track whether we are inside the section
            section = stripped.split(":", 1)[0] if stripped.endswith(":\n") or ":" in stripped else None
            continue
        if section != "pulse_metrics":
            continue
        if stripped.startswith(f"{key}:"):
            indent = ln[: len(ln) - len(stripped)]
            start = i
            break
    if start is None:
        raise KeyError(f"entry {key!r} not found inside pulse_metrics in {path}")

    field_indent = indent + "  "
    end = len(lines)
    for j in range(start + 1, len(lines)):
        ln = lines[j]
        if ln.strip() and not ln.startswith(field_indent):
            end = j
            break

    block = lines[start:end]
    for field, value in updates.items():
        rendered = f"{field_indent}{field}: {yaml_scalar(value)}\n"
        for j, ln in enumerate(block):
            if ln.startswith(f"{field_indent}{field}:"):
                block[j] = rendered
                break
        else:
            block.append(rendered)

    path.write_text("".join(lines[:start] + block + lines[end:]), encoding="utf-8")


def yaml_scalar(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    # timestamps and plain identifiers need no quoting; anything else gets it
    return s if s.replace("-", "").replace(":", "").replace("T", "").replace(".", "").replace("_", "").isalnum() else repr(s)


def resolve_spec_folder(run_dir: Path) -> str:
    """The spec folder for a stories-mode run, from wherever it actually is.

    The plugin bus (`plugins/bus.py`, bmad-loop 0.11.1) exports run identity
    fields to the hook env but NOT `BMAD_LOOP_SPEC_FOLDER` — the gap reported
    upstream as bmad-loop#779. Reading it from the environment worked only when
    the operator's shell happened to carry it, which the SIP preflight of
    2026-09-11 proved is not something the bus provides.

    The run's own `state.json` carries the spec folder at top level, and the bus
    DOES export `BMAD_LOOP_RUN_DIR`. For sprint-status runs the field is an
    empty string, which is the correct answer there: model A keys the journal
    by the full pulse_metrics key and needs no folder.
    """
    env_folder = os.environ.get("BMAD_LOOP_SPEC_FOLDER", "")
    if env_folder:
        return env_folder
    state = run_dir / "state.json"
    if not state.exists():
        return ""
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(data.get("spec_folder") or "")


def main() -> int:
    run_dir = Path(os.environ.get("BMAD_LOOP_RUN_DIR", ""))
    story_key = os.environ.get("BMAD_LOOP_STORY_KEY", "")
    repo = Path(os.environ.get("BMAD_LOOP_REPO_ROOT", "."))
    status_rel = os.environ.get(
        "BMAD_LOOP_SETTING_SPRINT_STATUS",
        "_bmad-output/implementation-artifacts/sprint-status.yaml",
    )

    if not run_dir.exists() or not story_key:
        log("no run dir or story key in env — nothing to close")
        return EXIT_SKIP

    events = read_journal(run_dir, story_key)
    f = facts(events)
    if f is None:
        # Deferred, escalated or stopped: there is no completion to record, and
        # inventing one would put a finished-looking row on unfinished work.
        log(f"story {story_key} never reached story-done — skipping")
        return EXIT_SKIP

    status_path = repo / status_rel
    if not status_path.exists():
        log(f"sprint status not found at {status_path} — skipping")
        return EXIT_SKIP

    text = status_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    metrics = data.get("pulse_metrics") or {}
    spec_folder = resolve_spec_folder(run_dir)
    key = find_entry(metrics, story_key, spec_folder)
    if key is None:
        if metrics:
            log(
                f"story {story_key} not identified in pulse_metrics "
                f"(spec_folder={spec_folder or 'none'}) — refusing to guess"
            )
        else:
            log(f"no pulse_metrics entry for story {story_key} — track-start never ran")
        return EXIT_SKIP

    entry = metrics[key]
    start_raw = entry.get("start_ts")
    if not start_raw:
        log(f"entry {key} has no start_ts — nothing to close against")
        return EXIT_SKIP

    start = datetime.fromisoformat(str(start_raw))
    hours = round((f["end_ts"] - start).total_seconds() / 3600, 2)
    if hours <= 0:
        log(f"end_ts {f['end_ts']} is not after start_ts {start} — refusing to write")
        return EXIT_BAD

    est = entry.get("estimated_hours")
    ref = entry.get("estimated_hours_reference")

    updates = {
        "end_ts": f["end_ts"].isoformat(),
        "actual_hours": hours,
        "review_cycles": f["review_cycles"],
        "first_pass": f["review_cycles"] <= 1,
        "dev_count": f["dev_sessions"],
        "measured_by": "bmad-loop-journal",
    }
    if isinstance(est, (int, float)) and est > 0:
        updates["leverage_ratio"] = round(est / hours, 1)
        updates["estimate_error_pct"] = round(abs(hours - est) / est * 100, 1)
    if isinstance(ref, (int, float)) and ref > 0:
        updates["leverage_vs_reference"] = round(ref / hours, 1)

    write_fields(status_path, key, updates)
    log(
        f"closed {key}: {hours}h, {f['review_cycles']} review cycle(s), "
        f"first_pass={updates['first_pass']}"
    )

    recalibrate(repo, entry, key, hours)
    return EXIT_OK


def recalibrate(repo: Path, entry: dict, key: str, hours: float) -> None:
    """Feed the finished measurement into the per-category baseline.

    This runs HERE, and not from the workflow's `on_complete`, for a reason
    beyond tidiness: recalibration reads `actual_hours`, and `actual_hours` only
    becomes correct a few lines above. Left in `on_complete` it would read the
    value written before review ran — and a wrong sample does not stay wrong in
    one place. It sets the category rate that prices every story scored
    afterwards, so one bad row quietly re-prices the backlog.

    Every failure path is a warning, never a non-zero exit. The story is already
    done and merged; refusing to finish the run because a baseline sample did not
    land would trade a small measurement gap for a large process one. The skill
    is idempotent (samples are deduped by story id), so a missed pass can be
    re-run by hand.
    """
    import subprocess

    bcp = entry.get("bcp_at_start") or {}
    total = bcp.get("total")
    category = entry.get("category")
    if not total or not category:
        log(f"no bcp_at_start/category on {key} — no baseline sample to add")
        return

    script = repo / ".claude/skills/bmad-bcp-recalibrate/scripts/recalibrate.py"
    if not script.exists():
        log("bmad-bcp-recalibrate not installed — skipping baseline sample")
        return

    story_file = (entry.get("identity") or {}).get("story_file", "")
    cmd = [
        "uv", "run", "--no-cache", str(script),
        "--actual-hours", str(hours),
        "--category", str(category),
        "--id", key,
    ]
    if story_file:
        cmd += ["--story", str(repo / story_file)]

    try:
        r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=60)
    except Exception as e:  # noqa: BLE001 — a broken recalibrate must not fail the run
        log(f"recalibrate could not run ({e}) — sample not added")
        return
    if r.returncode != 0:
        log(f"recalibrate exited {r.returncode} — sample not added: {r.stderr.strip()[:200]}")
        return
    log(f"baseline sample added for category {category} ({hours}h / {total} BCP)")


if __name__ == "__main__":
    raise SystemExit(main())
