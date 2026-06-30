# person_roles_v1 — DDL proposal (2026-06-29)

**Status: DRAFT proposal. DDL is HOLD pending audit gate. Nothing applied.**

## Problem
`authority.person.person_type` is a single-value column (CHECK:
`scholar` / `judge` / `lawyer_practitioner` / `unknown`; 128,081 rows).
For dual-title people the single value discards the other attested roles:

- 平田 厚 → 大学教授(現) **and** 弁護士(兼業) — single value drops one
- 時井 真 → **弁理士**(本務) + 弁護士 + 研究者 — `person_type` enum can't even
  express 弁理士
- 六車 明 → 判事 → 検事 → 公害等調整委員会 → 教授 → 弁護士 (5 roles)

Pilot over 223 adjudication authors → **98 distinct persons, 42 hold ≥2 roles.**
Evidence: `person_multirole_profiles_20260629.{tsv,json}`.

## Proposal
Add `authority.person_role` (one row per person×role). Keep `person.person_type`
as a backward-compatible cache of the **primary** role.

| column | purpose |
|--------|---------|
| `person_role_id` | PK |
| `person_id` | FK → authority.person (ON DELETE CASCADE) |
| `role` | scholar / lawyer_practitioner / judge / **prosecutor** / **patent_attorney** / **bureaucrat** / **other** / unknown |
| `role_status` | current / former / concurrent / unknown |
| `is_primary` | mirrors person_type; partial-unique → at most one per person |
| `detail` | 所属・専門・時期 (free text) |
| `confidence` | high / medium / low |
| `claim_status` | candidate / needs_review / accepted / rejected (default **candidate**) |
| `decision_method`, `evidence_source` | provenance |

Constraints: `UNIQUE(person_id, role)`, partial-unique `is_primary`,
compatibility view `authority.person_primary_role` exposing `person_type`
unchanged for legacy readers.

## Backfill (separate gated steps, not executed)
- **B1 lossless seed**: one `person_role` per existing person mirroring current
  `person_type` as `is_primary, claim_status='accepted'`. Loses nothing.
- **B2 enrich**: load the 98 profiles as `claim_status='candidate'`. ⚠ Must run
  **after person dedup** — the same name maps to many `person_id` rows today, so
  role attachment needs the dedup resolved first (or attach to all duplicates and
  let merge fold them). No auto-accept.
- **B3 sync/deprecate** `person_type`: trigger vs view — decide at gate.

## Gate decisions needed
1. **Widen `person.person_type` CHECK** to the 4 new roles? Required to let
   primary be patent_attorney/bureaucrat/other (pilot has all three).
2. ID scheme: surrogate vs `<person_id>:<role>` natural key.
3. Multiple `scholar` rows (institution history) — v1 collapses to one + detail;
   relax `UNIQUE` only if affiliation/period tracking is wanted.
4. Promotion bar to `accepted` = ≥2 independent origin_family + adjudication
   (same as `publication_author_claim`). Confirm.

## Governance
candidate ≠ confirmed preserved (default `claim_status='candidate'`).
No DDL/backfill/promote executed. Read-only schema inspection only.
Artifacts are local isolated outputs.
