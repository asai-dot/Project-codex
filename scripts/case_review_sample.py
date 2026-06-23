#!/usr/bin/env python3
"""case_review_sample.py — サンプル監査 frame (DD-CASEREVIEW-001)。

生きた精度をサンプル抽出で監視しドリフトを検知する。
- 層化抽出: tier(A/B/C/prov) × corroboration で stratified sample。
- worksheet: 人手確認の最小表示項目(CASEID-001 should_fix①)を出す。
- 精度推定: reviewer label から per-stratum precision を推定し、目標未達(drift)を旗。

read-only・決定的(seed)。DB/DDL なし。検証は test_case_review_sample.py。
"""
from __future__ import annotations
import random
from collections import defaultdict

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
    for t, c in sorted(by_tier.items()):
        p = prec(c)
        tiers[t] = {"precision": p, "n_decisive": c["correct"] + c["false_merge"],
                    "false_merge": c["false_merge"], "target": PRECISION_TARGET.get(t)}
        tgt = PRECISION_TARGET.get(t)
        if tgt is not None and p is not None and p < tgt:
            drift.append({"tier": t, "precision": p, "target": tgt})
    return {"by_tier": tiers,
            "by_stratum": {s: prec(c) for s, c in sorted(by_stratum.items())},
            "drift": drift, "drift_detected": bool(drift)}
