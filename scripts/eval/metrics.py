"""Per-label precision/recall/F1 + confusion, joining gold & pred on a key.

No third-party deps. The label universe is whatever appears in gold or pred;
a key present on one side only is treated as a missing label (sentinel
``__absent__``) on the other — i.e. an unmatched prediction is a false
positive for its label, and an unmatched gold row is a false negative for its.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

ABSENT = "__absent__"


def load_labeled(path: str, key: str, label: str) -> Dict[str, str]:
    """Read a JSONL file into {key_value: label_value}.

    Rows missing the key are skipped; rows missing the label use ``ABSENT``.
    Returns an empty dict for a missing/empty file (so an unlabeled task is a
    no-op rather than an error — see module docstring).
    """
    out: Dict[str, str] = {}
    try:
        fh = open(path, encoding="utf-8")
    except FileNotFoundError:
        return out
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if key not in row or row[key] is None:
                continue
            out[str(row[key])] = str(row.get(label, ABSENT))
    return out


@dataclass
class LabelScore:
    label: str
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def support(self) -> int:
        return self.tp + self.fn

    @property
    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 0.0

    @property
    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def to_dict(self) -> dict:
        return {"label": self.label, "support": self.support,
                "tp": self.tp, "fp": self.fp, "fn": self.fn,
                "precision": round(self.precision, 4),
                "recall": round(self.recall, 4),
                "f1": round(self.f1, 4)}


@dataclass
class Eval:
    labels: Dict[str, LabelScore] = field(default_factory=dict)
    confusion: Dict[Tuple[str, str], int] = field(default_factory=dict)
    n_keys: int = 0
    n_gold: int = 0
    n_pred: int = 0

    @property
    def empty(self) -> bool:
        return self.n_gold == 0

    def micro(self) -> dict:
        # Exclude the ABSENT sentinel: a gold-only key already counts as the
        # real label's FN, and a pred-only key as the real label's FP — adding
        # ABSENT's mirror tallies would double-count.
        scored = [s for s in self.labels.values() if s.label != ABSENT]
        tp = sum(s.tp for s in scored)
        fp = sum(s.fp for s in scored)
        fn = sum(s.fn for s in scored)
        p = tp / (tp + fp) if (tp + fp) else 0.0
        r = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0
        return {"precision": round(p, 4), "recall": round(r, 4),
                "f1": round(f1, 4), "tp": tp, "fp": fp, "fn": fn}

    def macro(self) -> dict:
        scored = [s for s in self.labels.values()
                  if s.label != ABSENT and s.support > 0]
        if not scored:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        return {"precision": round(sum(s.precision for s in scored) / len(scored), 4),
                "recall": round(sum(s.recall for s in scored) / len(scored), 4),
                "f1": round(sum(s.f1 for s in scored) / len(scored), 4)}

    def to_dict(self) -> dict:
        return {
            "n_keys": self.n_keys, "n_gold": self.n_gold, "n_pred": self.n_pred,
            "empty_gold": self.empty,
            "micro": None if self.empty else self.micro(),
            "macro": None if self.empty else self.macro(),
            "per_label": [self.labels[k].to_dict()
                          for k in sorted(self.labels) if k != ABSENT],
            "confusion": [{"gold": g, "pred": p, "n": n}
                          for (g, p), n in sorted(self.confusion.items())],
        }


def evaluate(gold: Dict[str, str], pred: Dict[str, str]) -> Eval:
    ev = Eval(n_gold=len(gold), n_pred=len(pred))
    keys = set(gold) | set(pred)
    ev.n_keys = len(keys)

    def score(label: str) -> LabelScore:
        return ev.labels.setdefault(label, LabelScore(label))

    for k in keys:
        g = gold.get(k, ABSENT)
        p = pred.get(k, ABSENT)
        ev.confusion[(g, p)] = ev.confusion.get((g, p), 0) + 1
        if g == p:
            score(g).tp += 1
        else:
            score(p).fp += 1   # predicted p where truth was not p
            score(g).fn += 1   # truth g was not recovered
    return ev
