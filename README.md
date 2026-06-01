# Project Codex — ALO gakuyo headless reconciliation

Implements **DISPATCH-HEADLESS-MIGRATE-001**: move the 学陽 3-source index
reconciliation off the "tap *続けて!* from mobile to drive a long batch"
workflow and onto a **re-runnable, idempotent, resumable headless job**.

This repo contains the **Phase 2** deliverable (the headless job, scoped to the
single 学陽 case). Phases 0 (rescue the stranded local session) and 1 (disable
the Remote Control 15-min timeout) are **machine-local actions on the Mac
Studio** — see [`docs/rescue-and-config.md`](docs/rescue-and-config.md).

> ⚠️ This work was produced in an ephemeral **cloud** Claude Code container, not
> on the Mac. The cloud agent cannot reach the Mac's local session history or its
> Claude Code config, so Phases 0 & 1 ship as exact runbooks for the Mac to
> execute. Phase 2 is code + a verified self-test. See
> [`docs/gakuyo-headless.md`](docs/gakuyo-headless.md) for the full return-leg.

## Quick start

```bash
# 1. install inputs (raw, never overwritten) under the spool
mkdir -p ~/.alo_spool/gakuyo/inputs
cp gemini_index.txt paddle_index.txt json1.txt ~/.alo_spool/gakuyo/inputs/
# 2. write the units manifest (one unit id per line; ids match "### <id>" markers)
$EDITOR ~/.alo_spool/gakuyo/units.txt
# 3. configure (Box folder_id / canonical path are head-supplied)
cp config/gakuyo.env.example config/gakuyo.env && $EDITOR config/gakuyo.env
# 4. smoke test 2–3 units, then run the whole thing (resume = just run it again)
scripts/gakuyo_reconcile.sh --config config/gakuyo.env --limit 3
scripts/gakuyo_reconcile.sh --config config/gakuyo.env
```

Kill it anytime. Re-running continues from the first unprocessed unit; already
completed units are skipped. State lives in `~/.alo_spool/gakuyo/state.json`;
per-unit results in `~/.alo_spool/gakuyo/results/<unit>.json`.

## Verify it yourself (no API calls, no Box)

```bash
scripts/selftest_resume.sh   # 16 assertions: idempotency, resume, retry
```

## Layout

| Path | Purpose |
|------|---------|
| `scripts/gakuyo_reconcile.sh` | main resumable orchestrator |
| `scripts/slice_unit.sh` | **the granularity knob** (default: `### <unit>` markers) |
| `scripts/publish_box.sh` | canonical output to Box (`drive` / `mcp-bridge` / `none`) |
| `scripts/lib/common.sh` | state.json + atomic-write + portable-lock helpers |
| `scripts/selftest_resume.sh` | deterministic idempotency/resume proof (uses a mock) |
| `config/prompt.gakuyo.tmpl` | the reconciliation prompt (tune without touching code) |
| `config/gakuyo.env.example` | config template |
| `examples/` | tiny sample inputs + mock claude for the self-test |
| `docs/` | design + return-leg report, and the Mac Phase 0/1 runbook |

## Design invariants (from the ticket §2-1)

1. **Idempotent** — one result file per unit; existing valid results are skipped.
2. **Resumable** — die anytime, re-run continues from the unprocessed units.
3. **Persistent progress** — `state.json` records done/failed/last position.
4. **Canonical output** — results go to a head-supplied Box location (no ghosts).
5. **Raw preserved** — reconciliation is an added layer; inputs are never edited.
