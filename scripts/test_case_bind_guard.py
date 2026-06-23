#!/usr/bin/env python3
"""test_case_bind_guard.py — false-merge ガードの検証 (DD-CASEBIND-001)。

肝: DD-CASEEVAL の gold テンプレ(ハード負例4型)に対し、ガードの自動bind結果が
    **false_merge=0** であることを case_eval スコアラで実証する。
実行: python3 scripts/test_case_bind_guard.py  (exit 0 = 全PASS)。
"""
import sys
import json
from pathlib import Path
from case_bind_guard import decide_bindings, auto_bound_assignment
from case_eval import score

GOLD = Path(__file__).resolve().parent.parent / "app" / "data" / "case_identity" / "case_eval_gold_template.jsonl"


def _obs(rows):
    return [{"observation_id": r["observation_id"], "forum_code": r["forum_code"],
             "decision_date": r["decision_date"], "case_number_norm": r["case_number_norm"],
             "external_id": r.get("external_id", ""), "external_source": r.get("source", "")}
            for r in rows]


def run() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    rows = [json.loads(l) for l in GOLD.open(encoding="utf-8") if l.strip()]
    gold = {r["observation_id"]: r["true_case_key"] for r in rows}
    obs = _obs(rows)

    # 核心: gold テンプレ(ハード負例含む)で false_merge=0
    pred = auto_bound_assignment(obs)
    m = score(gold, pred)
    check(f"gold template: false_merge=0 (実測 {m['false_merge']})", m["false_merge"] == 0)
    check(f"gold template: precision=1.0 (実測 {m['precision']})", m["precision"] == 1.0)
    check(f"gold template: recall=1.0 (実測 {m['recall']})", m["recall"] == 1.0)

    # G1 同番号別forum → 別 case_key
    a, _, _ = decide_bindings([
        {"observation_id": "x", "forum_code": "tokyo-chisai", "decision_date": "2021-03-15", "case_number_norm": "R3-ワ-1"},
        {"observation_id": "y", "forum_code": "osaka-chisai", "decision_date": "2021-03-15", "case_number_norm": "R3-ワ-1"},
    ])
    check("G1 同番号別forum→別case_key", a["x"] != a["y"])

    # G1 同forum同番号同日 → 同 case_key (Tier A)
    a, t, _ = decide_bindings([
        {"observation_id": "p", "forum_code": "tokyo-chisai", "decision_date": "2021-03-15", "case_number_norm": "R3-ワ-1", "external_id": "d1:1", "external_source": "D1"},
        {"observation_id": "q", "forum_code": "tokyo-chisai", "decision_date": "2021-03-15", "case_number_norm": "R3-ワ-1", "external_id": "nii:9", "external_source": "NII"},
    ])
    check("G1 同forum同番号→同case_key/TierA", a["p"] == a["q"] and t["p"] == "A")

    # G2 norm null → provisional・別key・review
    a, t, rv = decide_bindings([
        {"observation_id": "n1", "forum_code": "tokyo-chisai", "decision_date": "2021-04-01", "case_number_norm": None},
        {"observation_id": "n2", "forum_code": "tokyo-chisai", "decision_date": "2021-04-01", "case_number_norm": None},
    ])
    check("G2 null norm→prov別key・非merge", a["n1"] != a["n2"] and t["n1"] == "prov"
          and any(r["reason"] == "provisional_no_natural_key" for r in rv))

    # G3 同source内の外部ID衝突 → Tier B review、自動bindしない(split)
    obs3 = [
        {"observation_id": "c1", "forum_code": "tokyo-chisai", "decision_date": "2021-03-15", "case_number_norm": "R3-ワ-2", "external_id": "d1:100", "external_source": "D1"},
        {"observation_id": "c2", "forum_code": "tokyo-chisai", "decision_date": "2021-03-15", "case_number_norm": "R3-ワ-2", "external_id": "d1:999", "external_source": "D1"},
    ]
    _, t3, rv3 = decide_bindings(obs3)
    p3 = auto_bound_assignment(obs3)
    check("G3 外部ID衝突→TierB review・自動bind回避(split)",
          t3["c1"] == "B" and any(r["reason"] == "external_id_conflict_same_source" for r in rv3)
          and p3["c1"] != p3["c2"])

    # G2 元号未解決 → provisional
    a, t, _ = decide_bindings([
        {"observation_id": "e1", "forum_code": "saikosai", "decision_date": "2019-11-11", "case_number_norm": "X", "era_resolution_status": "unresolved"},
    ])
    check("G2 era未解決→prov", t["e1"] == "prov")

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}): {fails}")
        return 1
    print("RESULT: PASS (gold template false_merge=0; G1-G5 guard green)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
