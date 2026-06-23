# handoff_proto — fixture-bound prototype (offline)

Prototype for the **HEAD_HAND handoff** design, GO'd after owner ratify
(2026-06-23) under `HANDOFF_PASS_WITH_NOTES` (result 2302723874091).

Normative source: `../HANDOFF_SCHEMA_APPENDIX_v0.5_20260619.md`.

## What this is

A **pure, offline** schema validator + test harness. It computes verdicts over
in-memory packets and proves the implementation-unique rules the auditor
confirmed:

- invalid assignee → validation block (`invalid_assignee`)
- `ratify` → not dispatchable
- mutating ∧ no lease → `lease_required_but_unavailable`
- resource permit required ∧ no permit subsystem → `resource_permit_unavailable`
- confidential egress → `egress_forbidden`
- unknown access class → `access_class_unknown`
- source digest unavailable on integrity-required gate → `stale_packet`
- 3-axis effect derivation (mutation / egress / resource) + `external_audit_logging`
- JCS-style `packet_hash`: `runtime_envelope` excluded; normative field change changes hash
- per-attempt reconciliation: representative / duplicate / invalid / conflict;
  conflict & all-invalid → `representative_attempt_id=null` + `needs_head_resolution`

## NOT in scope (HOLD — do not add here)

No external calls. No queue/index/ledger writes. No Box move or metadata
mutation. No file moves. No operational dispatch / worklist / RESULT close. No
paid/quota/rate-limited calls. No mutating lease path. No DB/DDL/canonical.
These remain HOLD behind a separate gate per `RATIFY_head_hand_handoff_v0.5_20260623.md`.

## Run (non-operational test command)

```bash
cd tools/gpt_audit/handoff_proto
python3 -m unittest test_handoff_proto -v
```

## Files

- `validator.py` — effect derivation, dispatch validation, JCS hash, reconcile.
- `fixtures.json` — input + expected verdict (appendix §10): F1–F15.
- `test_handoff_proto.py` — offline harness (dispatch table + hash + reconcile).
- `reconciliation_canonical_example.json` — canonical local-closer output example
  (audit §7 must_fix #4): mixed representative + duplicate + invalid.

## Notes carried for operational implementation (still HOLD)

See `../RATIFY_head_hand_handoff_v0.5_20260623.md` §must_fix / §should_fix.
The old `patch` → `design_patch/doc_patch/code_patch/test_patch/refactor`
migration and a single-canon lint land when operational implementation is
itself ratified.
