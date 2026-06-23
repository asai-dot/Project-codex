"""scripts.eval — gold vs producer-output evaluation harness (DD-LAWSUBTRANS-001, plan L1).

Stdlib only. Computes per-label precision / recall / F1 and a confusion matrix
by joining a gold JSONL and a prediction JSONL on a shared *key* field and
comparing a *label* field.

Design intent (PLAN_lawobject_precision_v0.1 §2 / L1):
  - This is the *measuring stick*. Producer thresholds (lawdelta SUBST_MIN /
    RENUMBER_SIM, drafter/treatment cue confidence) are currently fixture
    guesses; nothing is scored. This harness makes precision/recall visible at
    pattern_id / delta_kind / treatment granularity so any later change can be
    accepted or rejected on a number, not a vibe.
  - It must run green on an EMPTY gold set (so it can live in CI from day one
    and only start failing once real labels — seeded with real e-Gov revisions
    / judgments under L3 — are filled in and a threshold is set).
"""
from .metrics import Eval, evaluate, load_labeled

__all__ = ["Eval", "evaluate", "load_labeled"]
