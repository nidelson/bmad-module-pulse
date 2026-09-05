# RFC — PULSE token telemetry

> **Status:** Draft for Party Mode
> **Author:** Nidelson Gimenez (with Claude Opus 4.7)
> **Date opened:** 2026-05-23
> **Target Party Mode session:** Phase 1 (structural decisions) + Phase 2 (surface/UX)
> **Related work:** v0.4.10 auto-tracking fix ([#47](https://github.com/nidelson/bmad-module-pulse/issues/47), [PR #48](https://github.com/nidelson/bmad-module-pulse/pull/48))

---

## 0. TL;DR

Can PULSE measure the number of AI tokens consumed during the implementation window (between `track-start` and `track-done`)? Technically yes — by parsing Claude Code's per-session JSONL transcripts. But it introduces real architectural tradeoffs that need cross-role debate before any code lands.

This RFC frames the tensions and produces a decision record. **Do not start implementation before Party Mode closes the open questions in §6.**

---

## 1. Context

PULSE today records two timestamps per story (`start_ts` from `bmad-pulse-track-start`, `end_ts` from `bmad-pulse-track-done`) and derives `actual_hours = end_ts - start_ts`. Combined with `estimated_hours` (or BCP-derived hours via the optional `pulse_estimation_method=bcp` integration), PULSE computes the **AI Leverage Ratio**.

The current contract:

- **Tool-agnostic core.** PULSE skills make no assumption about which AI assistant the developer used (Claude Code, Cursor, Cline, Aider, Copilot, plain ChatGPT). The metric works the same way regardless.
- **Read-only on story frontmatter.** PULSE never writes to the story file; it only reads status/id and writes to its own `pulse_metrics:` block.
- **Zero-coupling boundary with `bmad-module-bcp`.** PULSE may consume BCP data but never writes `bcp-baseline.yaml`.
- **Deterministic auto-tracking** (post v0.4.10): trigger lives in `activation_steps_append` (executed), never in `persistent_facts` (passive). Pinned by `tests/test_auto_tracking_trigger.py`.

The proposal under discussion is whether to add a **token-usage measurement** on top of time-based leverage.

---

## 2. Source of truth for the token data

Claude Code persists every session as a JSON-Lines transcript at:

```
~/.claude/projects/<cwd-encoded>/<session-id>.jsonl
```

where `<cwd-encoded>` is the project's working directory with `/` replaced by `-` (e.g. `-Users-nidelson-Projects-nidelson-sip`).

Each assistant message contains a `usage` block:

```json
{
  "usage": {
    "input_tokens": 1234,
    "output_tokens": 567,
    "cache_creation_input_tokens": 320,
    "cache_read_input_tokens": 8900
  },
  "model": "claude-opus-4-7",
  "timestamp": "2026-05-23T14:32:11Z"
}
```

Summing over the window `[start_ts, end_ts]` yields tokens consumed during the implementation. Multi-session implementations require globbing across files.

---

## 3. Proposed design (strawman — to be challenged in Party Mode)

A new opt-in skill `bmad-pulse-token-telemetry`, OR a hook in `bmad-pulse-track-done`, that:

1. Resolves the story's `cwd` → encodes the path → locates the transcripts directory.
2. Globs all `.jsonl` files in that directory.
3. For each line, parses JSON, filters by `timestamp ∈ [start_ts, end_ts]`.
4. Sums `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, grouped by `model`.
5. Writes a new block to `pulse_metrics[story].token_usage`:

```yaml
token_usage:
  input_fresh: 12340
  input_cached_read: 89000
  input_cache_creation: 3200
  output: 5670
  by_model:
    claude-opus-4-7: { in: 9000, out: 4200 }
    claude-sonnet-4-6: { in: 3340, out: 1470 }
  cost_usd_estimate: 1.23   # optional, requires pricing table
  sources: [".claude/projects/<encoded>/<sess-id-1>.jsonl", "<sess-id-2>.jsonl"]
  collected_at: 2026-05-23T15:00:00Z
```

6. Stays **opt-in** behind a config flag (e.g. `pulse_telemetry_adapter=claude_code` in `bmad/config.yaml` or `_bmad/custom/pulse.toml`).
7. Preserves the read-only invariant on story frontmatter (writes only to `pulse_metrics:`).

---

## 4. Tensions

### 4.1. Agnosticism vs concrete value

PULSE's tool-agnostic positioning is load-bearing — it's part of why it can be adopted by squads using different AI tools. A token adapter that only works with Claude Code threatens that positioning, even if scoped as opt-in.

**Counter-position:** an opt-in adapter pattern is precisely the escape hatch. Cursor/Cline/etc. can have their own adapters later; the core stays agnostic.

### 4.2. Window contains noise

The wall-clock window `[start_ts, end_ts]` already includes pauses, lunch, meetings, parallel work on other stories, off-topic conversations. `actual_hours` lives with this. **Token totals amplify it** — every chat message within the window counts, even unrelated ones.

**Mitigation options:**
- Filter by `cwd` matching the story's project (excludes off-project chat) — partial fix.
- Require the user to confirm/scope the window manually — defeats automation.
- Accept the noise as the price of automation — same compromise as `actual_hours`.

### 4.3. Multi-session reality

Two-day implementations span `N` JSONL files. Glob + merge is straightforward computationally, but adds I/O cost and edge cases (session that started before `start_ts` and ended after).

### 4.4. Tokens ≠ cost

Same total token count costs differently depending on model (Opus 4.7 vs Sonnet 4.6 vs Haiku 4.5). And `cache_read_input_tokens` cost ~10× less than fresh input. Reporting raw totals without splitting masks the actual economic signal.

**Question:** does PULSE expose `cost_usd_estimate`? If yes, who maintains the pricing table and how often? If no, raw token counts are misleading.

### 4.5. Integration with BCP

Bruno's BCP rule card produces a complexity score that drives `estimated_hours`. Adding token data raises a derived-metric question: is `tokens_per_BCP` meaningful?

- Pro: ties cognitive complexity to AI cost — could surface "complex stories cost N tokens per BCP point" patterns.
- Con: tokens are noisy; dividing by BCP doesn't denoise; may produce a metric that looks rigorous but isn't.

### 4.6. Surface saturation

PULSE already surfaces leverage ratio + actual_hours + estimated_hours. Adding tokens + cost + by_model adds three more dimensions. **At what point does the dashboard stop helping and start hiding?**

This is Levi's territory (Phase 2 of Party Mode).

---

## 5. Cast for Party Mode

### Phase 1 — Structural decisions (mandatory)

| Agent | Role in this RFC | Why |
|---|---|---|
| **BMad Builder (BMB)** | Module architecture authority | Owns the contract — zero-coupling, opt-in pattern, customize.toml shape, skill boundaries. Final say on whether this becomes a PULSE skill or a separate module. |
| **Architect** | Technical design | Adapter isolation, JSONL parsing, multi-session merge, invariants, performance, edge cases. |
| **Bruno (bcp-agent)** | Consumer of the metric | Whether `tokens_per_BCP` is signal or noise. Whether the new block should appear in BCP recalibration loops. |

### Phase 2 — Surface/UX (after Phase 1 closes)

| Agent | Role | Why |
|---|---|---|
| **Levi (pulse-agent)** | PULSE persona / surface owner | How to narrate `token_usage` to the user. New menu code? Where in dashboard? When to hide vs surface? Privacy framing. |
| **PM** | Scope arbiter | Feature in core vs separate module vs deferred-to-backlog. Sequencing with other PULSE work. |

### Optional (call if Phase 1 deadlocks)

- **Analyst** — prior-art research: `ccusage`, Cline telemetry, OpenAI usage API formats, what other dev-tracking modules do.

### Cut

- **Pulse agent (Levi) in Phase 1** — Levi is the executor/voice, not the designer. Including Levi too early risks UX debates before the data shape is settled.

---

## 6. Open questions for Party Mode to decide

Numbered for tracking. Each Party Mode output should reference these.

1. **Adapter pattern**: opt-in `pulse_telemetry_adapter=claude_code` config flag, or core feature, or separate module `bmad-module-pulse-telemetry`?
2. **Data location**: new `pulse_metrics[story].token_usage` block, or separate file `pulse_token_telemetry.yaml`, or external (no persistence)?
3. **Window semantics**: raw `[start_ts, end_ts]`, or filtered by `cwd`/project match, or user-confirmed window?
4. **Multi-session**: glob-and-merge automatically, or limit to one session, or require explicit session-id list?
5. **Pricing**: include `cost_usd_estimate` with maintained pricing table, or ship raw tokens only?
6. **Derived metrics**: expose `tokens_per_BCP`, `cost_per_estimated_hour`, both, neither?
7. **Invariants**: confirm read-only on story frontmatter still holds. Confirm zero-coupling with BCP still holds. Any new invariants this introduces?
8. **Privacy/framing**: how is "AI used N tokens" surfaced? Voluntary disclosure? Default off? Per-squad config?
9. **Trigger**: hook in existing `track-done` (always runs) vs new skill `track-tokens` (manual invocation) vs both?
10. **Test surface**: which invariants need regression tests pinned (similar to `test_auto_tracking_trigger.py`)?

---

## 7. Pre-reads for Party Mode participants

- `skills/bmad-pulse-track-start/workflow.md` — current track-start contract (Step 1 decoupled from `in-progress` status, v0.4.10).
- `skills/bmad-pulse-track-done/workflow.md` — current track-done flow + on_complete hook.
- `skills/bmad-pulse-setup/assets/customize-templates/bmad-dev-story.toml` — current activation trigger surface.
- `tests/test_auto_tracking_trigger.py` — invariants pinned in v0.4.10 (model for what token-telemetry tests should look like).
- `docs/MIGRATION.md` — v0.4.0 and v0.4.9 migration patterns.
- `~/.claude/projects/-Users-nidelson-Projects-nidelson-sip/<session>.jsonl` — sample transcript with `usage` blocks (Phase 1 Architect reference).
- `bmad-module-bcp` issue [#1](https://github.com/nidelson/bmad-module-bcp/issues/1) — BCP scope and Bruno's role (Bruno reference).

---

## 8. Decision record (to be filled by Party Mode output)

Phase 1 output goes here as a numbered decision list mapped to §6 questions:

```
D1. Adapter pattern: <decision> — <one-line rationale>
D2. Data location:   <decision> — <one-line rationale>
...
D10. Test surface:   <decision> — <one-line rationale>
```

Phase 2 output (after Phase 1):

```
S1. Menu code: <code> — <one-line rationale>
S2. Dashboard placement: <where> — <one-line rationale>
S3. Narration template: <text>
S4. Hide/surface threshold: <rule>
S5. Privacy framing: <text>
```

Once both phases are filled in, this RFC moves from `Status: Draft` to `Status: Decided` and a GitHub issue is opened referencing this file as the design spec.

---

## 9. Non-goals (do not let Party Mode drift into these)

- Implementing the feature in this RFC — design only.
- Building token telemetry for tools other than Claude Code in v1 — adapter pattern allows this later.
- Refactoring `bmad-pulse-track-done` beyond what this RFC requires.
- Changing the leverage ratio formula — token data is **additive**, not a replacement.
- BCP scoring changes — Bruno is a consumer here, not a redesign target.

---

## 10. Footer

After Party Mode closes Phase 1 and Phase 2, open a GitHub issue titled `feat(pulse): token telemetry adapter (Claude Code) — see docs/rfcs/2026-05-23-pulse-token-telemetry.md` and assign based on whichever decision §6 produces.
