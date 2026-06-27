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
- mutating ∧ no lease → `lease_required_but_unavailable` (G0); when the lease lane
  is enabled, the full `G_schema..L` gate runs in `lease.py` (see below)
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
paid/quota/rate-limited calls. No DB/DDL/canonical. The lease lane computes only
the **dispatch-card decision** (`lease.py`); real grant/release/mutation and
feature-flag rollout remain HOLD behind a separate gate per
`RATIFY_head_hand_handoff_v0.5_20260623.md` and `../LEASE_SUBSYSTEM_DESIGN_v0.5_20260625.md` §6.

## Lease mutating-dispatch gate (LEASE_SUBSYSTEM_DESIGN v0.5)

`lease.py` implements the **dispatch-card decision** for the mutating lane —
ratified design `../LEASE_SUBSYSTEM_DESIGN_v0.5_20260625.md` (GPT Pro
`LEASE_PASS_WITH_NOTES`, result 2312201353719, owner-ratified 2026-06-27). Still
**offline/pure**: every input (ledger events, Box current state, policy registry,
trusted holder/principal, `now_utc`) is injected via `LeaseContext`; nothing here
performs Box reads/writes, grant/release, or real mutation.

`validate_dispatch` delegates the mutating branch to
`lease.validate_mutating_dispatch`, which runs §4 fail-closed in order:
`G0 → G_schema → G1 → G2 → G_args → G_payload → G3 → G4 → G_chain → GA → L0 → L`.
The ledger view (`build_ledger_view`) enforces §1.5/§1.6: event-sourcing
transitions, record-hash chain, HMAC verify + key availability, sequence/ordinal
gap & fork, partial-tail block. Default `Env()` leaves `lease_subsystem_available`
False, so the operational rollout boundary stays closed.

§10 binding notes (PASS conditions) map to gates: payload digest canonicalization
(`canonical_digest`, G_payload) · immutable-ref version/hash binding · expected-
state required (G2) · policy registry not hardcoded (GA / `PolicyRegistry`) ·
unratified schema cannot emit (G_schema) · HMAC lifecycle (ledger) · §8 pre-exec
re-verification documented as a forward contract (next gate, not run here).

## Run (non-operational test command)

```bash
cd tools/gpt_audit/handoff_proto
python3 -m unittest test_handoff_proto test_lease -v
```

## Files

- `validator.py` — effect derivation, dispatch validation, JCS hash, reconcile,
  egress redirect re-evaluation, weak-equivalence tagging, active-generation
  selection, and `migrate_next_action_type` (legacy `patch` → v0.5 enum).
  Delegates the mutating lane to `lease.py`.
- `lease.py` — lease mutating-dispatch gate (§4 G0..L), op registry +
  `required_lock_domains` / scopes, `PolicyRegistry`, payload/lease-set digests,
  and the event-sourced `LedgerView` (`build_chain` / `build_ledger_view`).
- `fixtures.json` — input + expected verdict (appendix §10): F1–F18 (incl.
  redirect in/out F16/F17 and an `audit_sensitive` logging-profile example F18).
- `test_handoff_proto.py` — offline harness (dispatch table + hash + reconcile +
  redirect + patch migration).
- `test_lease.py` — offline lease fixtures: reference positive (metadata_set +
  file_move) + one-perturbation negatives covering every G0..L block reason and
  the ledger-integrity rejections (HMAC, fork, gap, partial tail, bad transition).
- `reconciliation_canonical_example.json` — canonical local-closer output example
  (audit §7 must_fix #4): mixed representative + duplicate + invalid.

## should_fix (v0.5 audit §8) — addressed in this prototype

1. `external_audit_logging=sensitive` logging-profile example → F18.
2. redirect re-evaluation with allowlist in/out → F16 / F17.
3. weak equivalence must be tagged → `basis_codes` carries `weak_equivalence`
   (`test_weak_equivalence_tagged`).
4. `stale_generation` (reconciliation, cross-generation) vs `stale_packet`
   (dispatch digest failure, F13) named apart
   (`test_stale_generation_distinct_from_stale_packet`).
5. legacy `patch` migration → `migrate_next_action_type` + `TestPatchMigration`.

## Notes carried for operational implementation (still HOLD)

See `../RATIFY_head_hand_handoff_v0.5_20260623.md` §must_fix / §should_fix.
The old `patch` → `design_patch/doc_patch/code_patch/test_patch/refactor`
migration and a single-canon lint land when operational implementation is
itself ratified.
