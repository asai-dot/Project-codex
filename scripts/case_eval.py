#!/usr/bin/env python3
"""case_eval.py — 判例同一性(名寄せ)の精度スコアラ (DD-CASEEVAL §metrics)。

clustering eval: gold クラスタ(真の case_key) と pred クラスタ(採番結果)を
*ペア単位* で比較する。最重要指標は false_merge(別判断を1本化した誤り = AN-4 の危険)。

定義 (全 observation の無順序ペアについて):
  same_gold = 真に同一 case / same_pred = 採番上同一 case
  TP = same_pred ∧ same_gold
  FP = same_pred ∧ ¬same_gold  ← *false merge* (危険)
  FN = ¬same_pred ∧ same_gold  ← *false split*
  precision = TP/(TP+FP)   recall = TP/(TP+FN)
  false_merge_rate = FP/(TP+FP) = 1 - precision   (precision優先運用の主指標)
  per_tier_precision: 採番された(same_pred)ペアを、より高リスク側の Tier で層別した precision。
                      (Tier A 自動bind の安全性、Tier C の危険度を分離して見る)

read-only。DB/DDL なし。合成 gold での自己検証は test_case_eval.py。
"""
from __future__ import annotations
from itertools import combinations
from collections import defaultdict


def _pairs(items):
    return combinations(sorted(items), 2)


def bcubed(gold: dict, pred: dict) -> dict:
    """cluster-level B-cubed precision/recall (CASEEVAL v0.2 note: pairwise と併用)。

    各 element について precision=|pred∩gold|/|pred cluster|、recall=|pred∩gold|/|gold cluster|
    を平均。singleton や大クラスタの偏りを pairwise と別角度で捉える。
    """
    gc = defaultdict(set)
    pc = defaultdict(set)
    for o in gold:
        gc[gold[o]].add(o)
    for o in pred:
        pc[pred[o]].add(o)
    n = len(gold)
    if n == 0:
        return {"bcubed_precision": 1.0, "bcubed_recall": 1.0}
    P = R = 0.0
    for o in gold:
        inter = len(pc[pred[o]] & gc[gold[o]])
        P += inter / len(pc[pred[o]])
        R += inter / len(gc[gold[o]])
    return {"bcubed_precision": round(P / n, 4), "bcubed_recall": round(R / n, 4)}


def score(gold: dict, pred: dict, tiers: dict | None = None) -> dict:
    """gold[obs]=true_case_key, pred[obs]=assigned_case_key, tiers[obs]=A|B|C。

    gold と pred は同一の observation 集合を持つ前提(差集合は ValueError)。
    """
    if set(gold) != set(pred):
        raise ValueError("gold と pred の observation 集合が不一致")
    obs = list(gold)
    tp = fp = fn = 0
    tier_pos = {}   # tier -> [tp, fp]  (same_pred ペアのみ)
    RISK = {"A": 0, "B": 1, "C": 2}
    for a, b in _pairs(obs):
        sg = gold[a] == gold[b]
        sp = pred[a] == pred[b]
        if sp and sg:
            tp += 1
        elif sp and not sg:
            fp += 1
        elif not sp and sg:
            fn += 1
        if sp and tiers is not None:
            # ペアの Tier = より高リスク側 (C>B>A)
            ta, tb = tiers.get(a, "A"), tiers.get(b, "A")
            pt = ta if RISK[ta] >= RISK[tb] else tb
            slot = tier_pos.setdefault(pt, [0, 0])
            slot[0 if sg else 1] += 1

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    per_tier = {}
    for t, (t_tp, t_fp) in sorted(tier_pos.items()):
        per_tier[t] = {
            "precision": t_tp / (t_tp + t_fp) if (t_tp + t_fp) else 1.0,
            "merged_pairs": t_tp + t_fp, "false_merge": t_fp,
        }
    return {
        "tp": tp, "false_merge": fp, "false_split": fn,
        "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
        "false_merge_rate": round(fp / (tp + fp), 4) if (tp + fp) else 0.0,
        "per_tier_precision": per_tier,
        "bcubed": bcubed(gold, pred),
    }


if __name__ == "__main__":
    import sys, json
    # 引数: gold.jsonl pred.jsonl (各行 {observation_id, case_key[, tier]})
    def load(p):
        g, t = {}, {}
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            g[r["observation_id"]] = r["case_key"]
            if "tier" in r:
                t[r["observation_id"]] = r["tier"]
        return g, t
    gold, _ = load(sys.argv[1])
    pred, tiers = load(sys.argv[2])
    print(json.dumps(score(gold, pred, tiers or None), ensure_ascii=False, indent=2))
