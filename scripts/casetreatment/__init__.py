"""casetreatment — Phase 4 candidate producer for DD-LAWSUBTRANS-001.

Extracts Japanese case-law citations from judgment/literature text and
classifies the *treatment relation* (DD §2.6 controlled vocabulary,
citator-style) by cue phrases — emitted strictly as CANDIDATES with evidence
spans. Never asserted truth, never claim_support-eligible
(gate_treatment_no_claim_support).

The citator lesson (Shepard's/KeyCite/BCite): the system never says in its
own voice that law is dead — it reports what a treating authority said,
attributed and quoted. This extractor follows that contract.
"""

EXTRACTOR_VERSION = "casetreatment/0.1.0"
