"""drafterintent — Phase 3 producer for DD-LAWSUBTRANS-001.

Connects 立案担当者解説 / 一問一答 / 逐条解説 / 所管庁資料 / 国会審議録 to the
substantive layer: it extracts, per statute reference, the DRAFTER'S CLAIM about
whether a provision changed substantively, and emits it as a tier-2
substantive_change_assertion CANDIDATE (T2) plus its evidence pointer (T5).

Hard rules (DD §2.4 / §4 / §5, audited PASS_WITH_NOTES notes):
- Drafter commentary is *persuasive, not binding* → source_tier = 2, never tier 1
  (tier 1 = official_legal_data, which lives in DD-LAWTIME, not here).
- Never auto-accepted: assertion_status='candidate', and accepted-promotion is a
  curator/review-event job (gate accepted_requires_review_event in the DD).
- claim_support_eligible is always False; rule confidence is capped at medium.
- A claim is emitted ONLY when a substantive-claim cue matches; a bare article
  mention does not fabricate a change_type (ingest no-auto-generation policy).
- The connector reports WHAT THE DRAFTER SAID, with an evidence span — it never
  asserts in its own voice that the meaning did/did not change.
"""

PRODUCER_VERSION = "drafterintent/0.1.0"
