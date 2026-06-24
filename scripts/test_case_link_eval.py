#!/usr/bin/env python3
"""test_case_link_eval.py — リンク精度計測の検証 (DD-CASELINK-001 v0.2 / DD-CASEEVAL 拡張)。

肝:
- gold テンプレ上で決定的パイプラインが期待エッジと一致(自己無矛盾=precision 1.0)。
- evaluates/review_chain/compares が計測対象、stance 正解率が出る。
- gold の edge_type が正典語彙の部分集合(ドリフト無し)。
実行: python3 scripts/test_case_link_eval.py  (exit 0 = 全PASS)。
"""
import sys
import case_vocab as V
from case_link_eval import score, load_gold


def run() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    gold = load_gold()
    check("gold テンプレ読込(3記事)", len(gold) == 3)

    # gold の edge_type ⊆ 正典(ドリフト検出)
    gold_types = {e["edge_type"] for a in gold for e in a["expected_edges"] if e.get("edge_type")}
    check("gold edge_type ⊆ vocab.COMMENTARY_TO_CASE_EDGE_TYPES",
          gold_types <= set(V.COMMENTARY_TO_CASE_EDGE_TYPES))

    r = score(gold)
    prec = r["precision_by_edge_type"]

    # 自己無矛盾: 合成 gold 上で全 edge_type precision = 1.0
    check("evaluates が計測対象", "evaluates" in prec)
    check("review_chain が計測対象", "review_chain" in prec)
    check("compares が計測対象", "compares" in prec)
    check("全 edge_type precision=1.0(決定的パイプラインの自己無矛盾)",
          all(v["precision"] == 1.0 for v in prec.values()))
    check("evaluates 目標が最高(0.97)", prec["evaluates"]["target"] == 0.97)

    # stance 正解率(同旨/反対/中立 を gold が持つ)
    check("stance 正解率=1.0", r["stance_accuracy"]["accuracy"] == 1.0)
    check("stance 目標が定義(0.85)", r["stance_accuracy"]["target"] == 0.85)

    # route 分布(masthead 主は auto、本文は review)
    check("route 分布に auto と review が存在",
          r["route_distribution"].get("auto", 0) >= 1 and r["route_distribution"].get("review", 0) >= 1)

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}): {fails}")
        return 1
    print("RESULT: PASS (リンク精度の gold スキーマと scorer が機能。実数は実corpus=Mac CC)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
