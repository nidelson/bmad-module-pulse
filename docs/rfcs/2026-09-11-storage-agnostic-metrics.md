# RFC — Storage-agnostic metrics: frontmatter as the source of truth

> **Status:** Draft — not approved, no implementation
> **Author:** Nidelson Gimenez (with Claude Opus 5)
> **Date opened:** 2026-09-11
> **Related:** [#120](https://github.com/nidelson/bmad-module-pulse/issues/120) (token spend has no field), [#121](https://github.com/nidelson/bmad-module-pulse/issues/121) (money conversion), [#122](https://github.com/nidelson/bmad-module-pulse/issues/122) / [PR #123](https://github.com/nidelson/bmad-module-pulse/pull/123) (closing seam), [RFC token telemetry](2026-05-23-pulse-token-telemetry.md)

---

## 0. TL;DR

PULSE writes every measurement into `pulse_metrics:` inside the consumer's
`sprint-status.yaml`. That file is the **queue** of a specific BMAD workflow
shape. When a project migrates its epics to spec folders (`<spec-folder>/stories/<id>-*.md`),
the queue stops being the place where work is tracked — and PULSE's storage goes
with it, even though nothing about the measurement itself changed.

This RFC proposes splitting metric storage into three layers by **scope and
ownership**, so PULSE stops depending on any particular workflow's file:

```text
story frontmatter    per-story, final, written once      → truth
pulse-metrics.yaml   per-story index/cache, derived      → speed
bcp-baseline.yaml    cross-story aggregate (exists)      → calibration
```

It also records a naming boundary (§5) so it does not get relitigated.

**Nothing here is decided.** The open questions in §6 need to close first.

---

## 1. The measurement that started this

A real SIP repository, measured 2026-09-11:

```text
pulse_metrics       1,685 lines   76.5%
bcp_metrics           247 lines   11.2%
development_status    231 lines   10.5%   <- the queue the file is named after
action_items           34 lines    1.5%
```

`sprint-status.yaml` is already **88% PULSE data**. The queue that gives the file
its name is one tenth of it.

That repository is migrating epics to spec folders. Once that finishes, the 10.5%
disappears and the file is *only* PULSE — a metrics file with a workflow's name,
whose remaining readers (sprint planning, retrospective, a session hook) all read
the part that no longer exists.

The trigger is a consumer's migration, but the exposure is ours: PULSE tied its
storage to a file it does not own, describing a workflow it does not require.

---

## 2. What is already storage-agnostic, and what is not

PULSE **reading** is agnostic. The loop plugin resolves the story in either model
and records where it found it:

```yaml
identity:
  epic: 22
  story_id: '22.2'
  story_file: _bmad-output/planning-artifacts/epics/spec-epic-22/stories/2-caixa-aprovacao-escalacoes.md
  source: spec-folder                     # <- the model is already a first-class field
  spec_folder: _bmad-output/planning-artifacts/epics/spec-epic-22
```

PULSE **writing** is not. Every entry lands in one central file whose existence
is a property of the consumer's workflow, not of PULSE.

So the problem is not *where the story lives* — that is solved. It is *who owns
the destination of the write*.

---

## 3. Proposal — three layers, one rule

**The rule that separates them: if it can be recomputed from the frontmatters,
it is derived.** Derived files are disposable; truth is not.

### 3.1 Story frontmatter — the truth

Final, per-story facts live with the story, in whatever model the story is in:

```yaml
pulse:
  start_ts: '2026-09-10T21:35:39'
  end_ts: '2026-09-10T23:19:15'
  actual_hours: 1.73
  review_cycles: 1
  first_pass: true
  token_spend: { weighted: 7617810, raw: 61612078 }
```

Namespaced under a single `pulse:` key so the module owns one slot and cannot
collide with workflow keys.

The `identity` block disappears entirely: the file *is* the story, so epic, id
and path are implicit. That is ~6 of the ~46 lines per entry gone by construction.

### 3.2 `pulse-metrics.yaml` — the index

A derived file with a `generated_at` stamp, so the dashboard does not open 37
story files on every run. Regenerable: `pulse regen` rebuilds it from the
frontmatters. If it is lost or corrupted, nothing of value is lost.

Today the equivalent loss is permanent — a corrupted `sprint-status.yaml` takes
the history with it.

### 3.3 `bcp-baseline.yaml` — the aggregate (unchanged)

Cross-story calibration (`h_per_bcp` per category, sample windows) cannot live in
any single story by definition. It already exists as a separate file, which is
the precedent this whole proposal follows. Only the source of its samples changes.

---

## 4. ⚠️ This breaks a declared invariant

The token-telemetry RFC states a contract that this proposal violates head-on:

> **Read-only on story frontmatter.** PULSE never writes to the story file; it
> only reads status/id and writes to its own `pulse_metrics:` block.
> — [RFC 2026-05-23, §1](2026-05-23-pulse-token-telemetry.md)

This must be an explicit, argued reversal — not a silent drift. Two observations
that bear on it:

1. **The invariant has no test.** Grep finds it in the RFC prose twice and
   nowhere in `tests/`. It has been doctrine, not an enforced boundary.
2. **The agent is already additive, not destructive.** Measured on SIP story 22.2:
   the frontmatter went in with 14 keys and came out with 18 — `bmad-build-auto`
   added its own (`status`, `baseline_revision`, `review_loop_iteration`,
   `deferred`) and preserved every key it did not recognise, including a
   12-line prose note. The fear that a writer would clobber unknown keys did not
   reproduce.

Neither point makes the reversal automatically right. They establish that the
cost is lower than the invariant assumed, and that the invariant was never
load-bearing in code.

**If the reversal is accepted, it needs a test in the same PR** — the one thing
the original invariant never had.

---

## 5. Naming boundary (decided, recorded to avoid relitigation)

**`bcp-baseline.yaml` keeps its name. It is not renamed to `pulse-baseline.yaml`.**

Considered and rejected on 2026-09-11:

- BCP scoring is **opt-in** (`pulse_estimation_method = "bcp"`; the default is
  `hours`). A user on the default never creates this file. A `pulse-` prefix
  would promise every PULSE user has one.
- The name is **hardcoded**, not configurable: 118 references across two
  repositories, including tests that build the path literally
  (`tmp_path / "bcp-baseline.yaml"`).
- Renaming would break existing installs **silently**: `seed_baseline.py` would
  create a fresh empty file and each user's calibration history would be orphaned
  in the old one. That is the same silent-failure class as #122 and #124.

The prefixes carry information as they stand: `pulse-*` is what every user has,
`bcp-*` is what exists only with the opt-in.

**When this should be revisited:** if the baseline ever stores calibration that
is not BCP-derived (e.g. `h_per_story_size` for the hours method), the name
becomes wrong on the merits. Today it is 100% BCP.

---

## 6. Open questions — close before implementing

1. **Is `pulse-metrics.yaml` an index or a cache?**
   Index (paths only) means the dashboard opens N files per run. Cache (copied
   fields) means duplication and two sources that can disagree.
   *Leaning:* cache with `generated_at`, because the duplication is reconstructible.

2. **How much frontmatter is too much?**
   Entries average 46 lines today (max 71). In the spec-folder model the story
   file is what the **agent reads as its instructions** — telemetry there competes
   with the story's content for attention.
   *Leaning:* frontmatter carries only short final fields (~8-10, no prose); long
   notes live in the derived file.

3. **Migration for existing installs.** Reading `pulse_metrics:` from
   `sprint-status.yaml` must keep working. A one-way `pulse migrate` that copies
   into frontmatters, or dual-read indefinitely? Note this cannot be shipped as a
   silent change: see #124 — the loop plugin is installed by copy and a module
   update does not refresh it.

4. **Who writes the frontmatter?** The deterministic `post_commit` hook already
   writes measurements without an agent. Does it also write the story file, or
   does that stay with a skill? The hook is the only writer that cannot fail by
   running out of OAuth session.

5. **Does the hours-only user gain anything?** This RFC is motivated by a
   spec-folder migration. A user on plain BMAD with `sprint-status.yaml` sees
   churn with no benefit unless the reversal in §4 buys them something too.

---

## 7. Format: YAML, not TOML

Asked directly, since BMAD has been moving config to TOML. Measured on the real
22.2 entry, converting with `tomlkit`:

```text
longest line, TOML:  980 chars
longest line, YAML:  111 chars
lines, TOML:  49      lines, YAML:  66
```

TOML has no block scalar with folding, so the prose notes — which are half the
explanatory value of an entry — become one enormous line each. That destroys git
diffs: changing a word rewrites the whole line.

`[[array of tables]]` is the second problem: the baseline's sample lists become
one `[[...]]` header per sample (40+ headers for 4 categories × 10 samples).

The BMAD pattern points the same way: TOML for **human-authored config**
(`_bmad/custom/*.toml`), YAML for **script-written data** (`config.yaml`,
`bcp-baseline.yaml`, `sprint-status.yaml`). The only TOML writer in the module
needs `tomlkit` round-trip just to avoid destroying comments.

**YAML** — same as `bcp-baseline.yaml`, which is already the house precedent for
aggregated data.

---

## 8. Why this is not urgent

The current storage works. Nothing is broken today, and #120/#121 can land
inside `pulse_metrics:` as it stands.

What this RFC buys is that PULSE stops being coupled to one workflow's file
shape. That matters when the first consumer migrates — which is happening now in
one repository, and is a plausible direction for others.

Doing it badly is worse than not doing it: a half-migration leaves two sources of
truth for the same story, which is the failure mode PULSE exists to prevent in
the first place.
