"""lawdelta — Phase 2 producer for DD-LAWSUBTRANS-001 (T1 alo_law_textual_delta).

Computes per-article textual deltas between two consolidated revisions of a law
and classifies them with the Akoma Ntoso textualMod-aligned taxonomy:
substitution / insertion / repeal / renumber / relocate / split / join / no_change.

This package observes FORM only. It never emits substantive-change assertions
(gate_no_substantive_fields). DB writes: none — JSONL artifacts only.
"""

DETECTOR_VERSION = "lawdelta/0.1.0"
