# 学陽 headless reconciliation — design & return-leg

Implements **DISPATCH-HEADLESS-MIGRATE-001** Phase 2 (学陽 single-case, minimal).
This document doubles as the **return-leg report** to head.

---

## 0. Context the hand must know up front

This ticket was addressed to *Mac Claude Code (hand)* on the Mac Studio. It was
actually executed by a **cloud Claude Code container** on a fresh clone of
`asai-dot/Project-codex`. That changes what each phase could be done here:

| Phase | Nature | Doable from cloud? |
|-------|--------|--------------------|
| 0 — rescue stranded session | Mac-local session history | **No.** `claude --resume` only sees the *local* machine's sessions. Shipped as a runbook. |
| 1 — disable RC 15-min timeout | Mac-local Claude Code config | **No.** Config lives on the Mac. Shipped as a runbook. |
| 2 — headless reconciliation job | repo code | **Yes — built, self-tested, committed.** |

Phases 0 & 1: see [`rescue-and-config.md`](rescue-and-config.md). They need the
Mac; the steps are exact and copy-pasteable.

---

## 1. Architecture (Phase 2)

The job replaces "mobile *続けて!* drives a long batch" with a shell loop that
calls `claude -p` **once per processing unit**. Print mode keeps no conversation
state, so all state lives in files — never in model memory.

```
units.txt ──► [ for each unit not yet done ]
                   │ skip if results/<unit>.json exists & valid   (idempotency)
                   ▼
              slice_unit.sh  ── per-unit text from the 3 sources (granularity knob)
                   ▼
              claude -p "<prompt with embedded slices>"           (1-shot, no tools needed)
                   ▼
              capture stdout ► strip fences ► jq-validate ► atomic mv  (orchestrator owns the file)
                   ▼
              state.json update  +  publish_box.sh (canonical)
```

### Why these choices

- **Orchestrator owns persistence, not the model.** The shell captures stdout,
  validates JSON, and atomically moves the file into place. Idempotency and
  atomic writes are guaranteed by the orchestrator rather than by hoping the
  model uses a Write tool correctly. Consequence: the per-unit call needs **no
  tools at all** (slices are embedded in the prompt) → tightest privilege.
- **The slicer is the granularity knob.** Page vs. heading vs. 章 is *head's*
  decision (return-leg item). Encoding it in a swappable `slice_unit.sh` keeps
  that decision out of the orchestrator. Default slicer keys on `### <unit-id>`
  markers in each source file; swap the script via `SLICER=` once head fixes
  granularity, with zero changes to `gakuyo_reconcile.sh`.
- **Per-unit `claude -p`, not one giant prompt.** One huge prompt over all pages
  would blow context limits and lose everything on a mid-run death. Per-unit
  self-contained calls bound context and make partial progress durable.
- **Raw never overwritten.** Inputs under `inputs/` are read-only to the job;
  reconciliation is an added layer under `results/`.

### State & result schemas

`state.json` (`alo.gakuyo.state/v1`) — progress mirror; `done[]` is reconciled
from the actual valid files in `results/` at the start of every run, so the
on-disk results are the true source of truth:

```json
{
  "schema": "alo.gakuyo.state/v1", "source": "gakuyo",
  "created_at": "...", "updated_at": "...",
  "units_total": 3, "done": ["unit-001","unit-002"], "failed": [], "last_unit": "unit-002"
}
```

`results/<unit>.json` (`alo.gakuyo.result/v1`) — `unit`, `generated_at`,
`source` are stamped by the orchestrator; the model produces the rest
(`canonical_headings`, `sources_compared`, `discrepancies`, `reasoning`).

---

## 2. Verification done in-environment

### 2a. Idempotency / resume self-test — **16/16 PASS**

`scripts/selftest_resume.sh` runs the real orchestrator against a mock `claude`
(`examples/mock_claude.sh`), no API/Box. It proves:

- **A** partial run (`--limit 2`) → exactly 2 results, model invoked twice.
- **B** resume → completes the remainder; model invoked **3× total** (done units
  not re-invoked — idempotency proven via the mock's call log).
- **C** full re-run when all done → **0** new model calls (idempotent no-op).
- **D** delete one result → **only** that unit recomputed.
- **E** a failing unit → recorded in `state.failed`, then cleared on retry.

```
=== selftest summary: 16 passed, 0 failed ===
```

### 2b. Real `claude -p` subprocess — **works**

`claude -p '... reply with ONLY {"ok":true}' --output-format text` returned
clean `{"ok": true}` on stdout (exit 0) in this container. The capture →
fence-strip → `jq` validate → atomic-move pipeline therefore works against the
real CLI, not just the mock.

### 2c. Box MCP reachability — **reachable & authenticated**

`who_am_i` over the Box MCP returned the canonical account (`asai@asai-lo.com`,
ja / Asia/Tokyo). **Notable:** Box canonical is reachable via MCP **even from the
cloud headless environment**, not only from the Mac's Box Drive mount. This
widens the architecture options in §4.

### 2d. Sample artifacts (from a mock `--limit 2` run)

`state.json`:
```json
{ "schema":"alo.gakuyo.state/v1","source":"gakuyo","units_total":3,
  "done":["unit-001","unit-002"],"failed":[],"last_unit":"unit-002" }
```
`results/unit-001.json` (trimmed): orchestrator-stamped `unit`/`generated_at`/
`source` present; model fields (`canonical_headings`, `reasoning`, …) present.

---

## 3. 【未検証】 items — status

| Item (from ticket) | Status here | Still needs the Mac? |
|---|---|---|
| `claude --resume` restores local context | **Not testable from cloud** (no Mac sessions here) | **Yes** — record full vs. partial restore. |
| Phase-1 config key name + before/after | **Not testable from cloud** (Mac config) | **Yes** — `claude config list`, capture key + values. |
| headless `claude -p` reachable | **Verified** — runs, clean stdout capture (§2b) | No |
| Box reachable from headless | **Verified via MCP** (§2c) | Confirm the *Mac's* preferred path: Box Drive `cp` vs. MCP-bridge |
| `--allowedTools` exact spec | **Side-stepped** — default needs **no tools** (slices embedded). `ALLOWED_TOOLS` passthrough exists if a Read-based slicer is chosen later | Only if switching slicer strategy |

---

## 4. Decisions for head (the hand did NOT decide these)

1. **Unit granularity** — page / heading block / 章. The orchestrator is
   granularity-agnostic; the choice is encoded in `slice_unit.sh`. Pick one and
   I'll finalize the slicer + how `units.txt` is generated.
2. **Box canonical target** — supply the `folder_id` (for `BOX_MODE=mcp-bridge`)
   **or** the Box Drive synced path (for `BOX_MODE=drive`). Currently unset → the
   job logs a WARN and skips publish rather than inventing a ghost canonical.
   Given §2c, MCP-bridge is viable cloud-side too — your call which is canonical.
3. **Generalization to non-学陽 sources** — whether to raise a DD for a generic
   batch base (connecting DD-PROOF-001 / DD-DICT-008). This ticket stayed inside
   the 学陽 single-case envelope as instructed; the slicer/prompt seams are where
   generalization would attach.
4. **Scheduling** — launchd periodic self-drive vs. on-demand. The job is
   safe to re-run (idempotent), so a launchd timer that just re-invokes it would
   drain the queue and no-op when empty. Needs your call on cadence + alerting
   (the job exits non-zero if any unit failed this run, ready for launchd alerts).

---

## 5. Residual / open

- **Resolved here:** orchestration mechanics, real-CLI capture, Box reachability,
  self-test harness, sample artifacts.
- **Head-blocked:** the 4 items in §4 (cannot be decided hand-side per ticket).
- **Mac-blocked:** Phases 0 & 1 (runbook ready; need execution on the Mac and
  the two 【未検証】 readings recorded).
- **Not started (out of scope):** the real 学陽 inputs were not present in this
  environment, so the end-to-end 2–3-unit smoke against the *real* index + real
  Box write must be run on the Mac with `--limit 3` once §4.1/§4.2 are fixed.
