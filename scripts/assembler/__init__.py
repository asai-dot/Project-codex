"""assembler — forms disputes across DD-LAWSUBTRANS-001 producers.

Ties together the Phase-3/4 producers (drafterintent = tier-2 drafter claims,
casetreatment / scholarship = tier-3 court / tier-4 scholar interpretation) and
detects, for each provision, whether the sources DISAGREE about whether the
substantive meaning / doctrine persisted across an amendment.

Core discipline (DD §2.5 / §4, audited PASS_WITH_NOTES):
- It NEVER picks a winner. Tier is evidence strength, not an auto-resolver.
- A conflict (continuity-claim vs change-claim on the same provision) becomes a
  `disputed` disposition recorded as an append-only review-event (T6); both
  sides get a mutual counter_assertion link.
- `disputed` => claim_support_eligible stays False (gate disputed_blocks_claim).
- `accepted` is never set here — that needs a human review-event with a
  review_basis (gate accepted_requires_review_event).
"""

ASSEMBLER_VERSION = "assembler/0.1.0"
