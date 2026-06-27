#!/usr/bin/env python3
"""case_review_sample.py — サンプル監査 frame (DD-CASEREVIEW-001)。

生きた精度をサンプル抽出で監視しドリフトを検知する。
- 層化抽出: tier(A/B/C/prov) × corroboration で stratified sample。
- worksheet: 人手確認の最小表示項目(CASEID-001 should_fix①)を出す。
- 精度推定: reviewer label から per-stratum precision を推定し、目標未達(drift)を旗。

read-only・決定的(seed)。DB/DDL なし。検証は test_case_review_sample.py。
"""
from __future__ import annotations
import math
import random
from collections import defaultdict


def required_sample_size(p: float = 0.99, margin: float = 0.02, z: float = 1.96) -> int:
    """目標 precision p を ±margin・信頼 z(既定95%) で推定するのに要する標本数 (v0.2 note)。

    正規近似 n = z^2 p(1-p) / margin^2。owner が margin/信頼を調整(既定は提案値)。
    """
    return math.ceil(z * z * p * (1 - p) / (margin * margin))


def wilson_ci(correct: int, n: int, z: float = 1.96):
    """precision の Wilson 信頼区間 (小標本でも安定)。n=0 は (None,None)。"""
    if n == 0:
        return (None, None)
    ph = correct / n
    d = 1 + z * z / n
    center = (ph + z * z / (2 * n)) / d
    half = (z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))) / d
    return (round(center - half, 4), round(center + half, 4))

# 人手レビュー最小表示項目 (CASEID-001 should_fix①)
DISPLAY_FIELDS = ["forum_code", "decision_date", "case_number_raw", "case_number_norm",
                  "external_id", "source_system", "content_grade"]
# 層別 precision 目標 (split寄り: A は高精度要求、prov は監査対象外)
PRECISION_TARGET = {"A": 0.99, "B": 0.95, "C": 0.90}


def stratum_of(b: dict) -> str:
    return f'{b.get("tier","?")}/{b.get("corroboration_level","na")}'


def sample_for_review(bindings: list[dict], n_per_stratum: int = 5, seed: int = 0) -> list[dict]:
    """tier×corroboration で層化し各層 n 件を決定的抽出 → worksheet 行。"""
    strata = defaultdict(list)
    for b in bindings:
        strata[stratum_of(b)].append(b)
    rng = random.Random(seed)
    out = []
    for st in sorted(strata):
        items = sorted(strata[st], key=lambda x: x["observation_id"])
        picked = items if len(items) <= n_per_stratum else rng.sample(items, n_per_stratum)
        for b in sorted(picked, key=lambda x: x["observation_id"]):
            row = {"observation_id": b["observation_id"], "case_key": b.get("case_key"),
                   "stratum": st, "tier": b.get("tier")}
            for f in DISPLAY_FIELDS:
                row[f] = b.get(f, "")
            row["reviewer_label"] = ""   # correct | false_merge | false_split | unsure
            out.append(row)
    return out


def estimate_precision(reviewed: list[dict]) -> dict:
    """reviewed 行(reviewer_label 付)から per-stratum / Tier precision を推定し drift 判定。

    precision = correct / (correct + false_merge)  (unsure/false_split は分母外)。
    """
    by_tier = defaultdict(lambda: {"correct": 0, "false_merge": 0, "false_split": 0, "unsure": 0})
    by_stratum = defaultdict(lambda: {"correct": 0, "false_merge": 0, "false_split": 0, "unsure": 0})
    for r in reviewed:
        lab = r.get("reviewer_label")
        if lab not in ("correct", "false_merge", "false_split", "unsure"):
            continue
        by_tier[r.get("tier", "?")][lab] += 1
        by_stratum[r.get("stratum", "?")][lab] += 1

    def prec(c):
        d = c["correct"] + c["false_merge"]
        return round(c["correct"] / d, 4) if d else None

    tiers = {}
    drift = []
    total = {"correct": 0, "false_merge": 0, "false_split": 0, "unsure": 0}
    for t, c in sorted(by_tier.items()):
        p = prec(c)
        nd = c["correct"] + c["false_merge"]
        for k in total:
            total[k] += c[k]
        tiers[t] = {"precision": p, "n_decisive": nd, "false_merge": c["false_merge"],
                    "ci95": wilson_ci(c["correct"], nd), "target": PRECISION_TARGET.get(t),
                    "recommended_n": required_sample_size(PRECISION_TARGET[t]) if t in PRECISION_TARGET else None}
        tgt = PRECISION_TARGET.get(t)
        if tgt is not None and p is not None and p < tgt:
            drift.append({"tier": t, "precision": p, "target": tgt})
    n_all = sum(total.values())
    return {"by_tier": tiers,
            "by_stratum": {s: prec(c) for s, c in sorted(by_stratum.items())},
            "unsure_rate": round(total["unsure"] / n_all, 4) if n_all else 0.0,
            "drift": drift, "drift_detected": bool(drift)}
