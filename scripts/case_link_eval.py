#!/usr/bin/env python3
"""case_link_eval.py — 評釈→判例リンクの精度計測 (DD-CASEEVAL 拡張 / DD-CASELINK-001 v0.2)。

gold(記事→期待エッジ)に対し extract→map パイプラインを流し、edge_type 別 precision と
stance 正解率、route 分布を出す。**evaluates(評釈対象)は誤リンクが最も有害=最高目標**。

合成テンプレ上の数値は決定的パイプラインの *自己無矛盾* の確認に過ぎない
(identity の false_merge=0 と同じ性質)。実数は実 corpus=Mac CC で測る。read-only。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import case_vocab as V
from case_link_extract import extract_mentions
from case_link_map import map_article

GOLD = Path(__file__).resolve().parent.parent / "app" / "data" / "case_identity" / "case_link_gold_template.jsonl"


def _pred_edges(article: dict) -> list[dict]:
    """記事→予測エッジ(slot 順=masthead, body0, body1, ...)。gold と位置整列する。"""
    return map_article(extract_mentions(article))


def score(gold_articles: list[dict]) -> dict:
    # edge_type 別 precision(予測がその型のうち、gold と一致した割合)
    pred_by_type: dict[str, int] = {}
    correct_by_type: dict[str, int] = {}
    stance_total = stance_correct = 0
    route_pred: dict[str, int] = {}

    for art in gold_articles:
        exp = art.get("expected_edges", [])
        pred = _pred_edges(art)
        for e, p in zip(exp, pred):
            pt = p["edge_type"]
            route_pred[p["route"]] = route_pred.get(p["route"], 0) + 1
            if pt:  # 予測がエッジを張ったとき
                pred_by_type[pt] = pred_by_type.get(pt, 0) + 1
                if pt == e.get("edge_type") and p["route"] == e.get("route"):
                    correct_by_type[pt] = correct_by_type.get(pt, 0) + 1
            # stance 正解率(gold が stance を持つ行のみ)
            if e.get("stance"):
                stance_total += 1
                if p.get("stance") == e.get("stance"):
                    stance_correct += 1

    precision = {}
    for t in sorted(pred_by_type):
        c, n = correct_by_type.get(t, 0), pred_by_type[t]
        precision[t] = {"predicted": n, "correct": c, "precision": round(c / n, 4) if n else None,
                        "target": V.LINK_PRECISION_TARGET.get(t)}
    return {
        "precision_by_edge_type": precision,
        "stance_accuracy": {"n": stance_total,
                            "accuracy": round(stance_correct / stance_total, 4) if stance_total else None,
                            "target": V.LINK_STANCE_ACCURACY_TARGET},
        "route_distribution": route_pred,
    }


def load_gold(path: Path = GOLD) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


if __name__ == "__main__":
    print(json.dumps(score(load_gold()), ensure_ascii=False, indent=2))
    sys.exit(0)
