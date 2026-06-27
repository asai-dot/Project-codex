#!/usr/bin/env python3
"""test_case_eval.py — case_eval スコアラの自己検証 (DD-CASEEVAL)。

合成 gold/pred で false_merge / false_split / per-tier precision を *検出できる* ことを確認。
特に「Tier A 自動bind は安全・Tier C は危険」を分離計測できること(AN-4)。
実行: python3 scripts/test_case_eval.py  (exit 0 = 全PASS)。
"""
import sys
from case_eval import score

# gold: a,b,c=同一事件X / d,e=同一事件Y
GOLD = {"a": "X", "b": "X", "c": "X", "d": "Y", "e": "Y"}
# pred: d を X に誤統合(false merge) かつ e を分離(false split)
PRED = {"a": "1", "b": "1", "c": "1", "d": "1", "e": "3"}
# tier: X内は高信頼A、d は低信頼C で誤bind、e は B
TIERS = {"a": "A", "b": "A", "c": "A", "d": "C", "e": "B"}


def run() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    m = score(GOLD, PRED, TIERS)
    # 期待: gold同一ペア = ab,ac,bc(X) + de(Y) = 4。pred同一ペア = cluster1(abcd)=6。
    #   TP = ab,ac,bc = 3 / FP(false merge) = ad,bd,cd = 3 / FN(false split) = de = 1
    check("TP=3", m["tp"] == 3)
    check("false_merge(FP)=3 を検出", m["false_merge"] == 3)
    check("false_split(FN)=1 を検出", m["false_split"] == 1)
    check("precision=0.5", m["precision"] == 0.5)
    check("recall=0.75", m["recall"] == 0.75)
    check("false_merge_rate=0.5", m["false_merge_rate"] == 0.5)

    # per-tier: Tier A の merged ペア(ab,ac,bc)は全TP→precision 1.0。
    #           Tier C の merged ペア(ad,bd,cd)は全FP→precision 0.0。
    pt = m["per_tier_precision"]
    check("Tier A precision=1.0 (自動bind安全)", pt.get("A", {}).get("precision") == 1.0)
    check("Tier C precision=0.0 (危険を分離検出)", pt.get("C", {}).get("precision") == 0.0)
    check("Tier C false_merge=3", pt.get("C", {}).get("false_merge") == 3)

    # 完全一致 gold==pred は precision=recall=1.0、false_merge=0
    perfect = score(GOLD, {k: GOLD[k] for k in GOLD}, TIERS)
    check("完全一致→precision/recall=1.0, false_merge=0",
          perfect["precision"] == 1.0 and perfect["recall"] == 1.0 and perfect["false_merge"] == 0)

    # observation 集合不一致は ValueError
    try:
        score({"a": "X"}, {"b": "Y"})
        raised = False
    except ValueError:
        raised = True
    check("obs集合不一致→ValueError", raised)

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}): {fails}")
        return 1
    print("RESULT: PASS (false_merge/false_split/per-tier precision 検出 green)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
