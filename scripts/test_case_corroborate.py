#!/usr/bin/env python3
"""test_case_corroborate.py — 多源コロボの検証 (DD-CASECORROB-001)。

確認: L1 独立源一致で identity confidence 上昇 / L2 解説誌 crosswalk は注釈補強(非merge) /
L3 引用は edge 候補(非merge) / caselaw_same_case の採番割れは conflict_review /
コロボは決して merge を生まない(AN-2)。
実行: python3 scripts/test_case_corroborate.py  (exit 0 = 全PASS)。
"""
import sys
from case_corroborate import corroborate

OBS = {
    "o1": {"source": "D1-Law", "external_id": "111"},
    "o2": {"source": "NII", "external_id": "222"},
    "o3": {"source": "D1-Law", "external_id": "333"},
    "o4": {"source": "LIC", "external_id": "lic-9"},
    "o5": {"source": "D1-Law", "external_id": "555"},
}
# 採番(②ガード後): o1,o2=同一case(K1) / o3=K2 / o4=K3(解説誌) / o5=K4
ASSIGN = {"o1": "K1", "o2": "K1", "o3": "K2", "o4": "K3", "o5": "K4"}


def run() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    links = [
        {"a": "D1-Law:111", "b": "NII:222", "type": "caselaw_same_case"},   # K1 内 → 補強
        {"a": "D1-Law:333", "b": "D1-Law:555", "type": "caselaw_same_case"},# K2 vs K4 → 割れ
        {"a": "LIC:lic-9", "b": "D1-Law:111", "type": "literature_about_case"}, # L2 注釈
        {"a": "D1-Law:333", "b": "D1-Law:555", "type": "case_cites_case"},   # L3 引用 edge
    ]
    conf, find = corroborate(ASSIGN, OBS, links)

    # L1: K1 は D1+NII の2独立判例源 → multi_source_agree
    check("L1 K1 multi_source_agree (D1+NII)",
          conf["K1"]["identity_corroboration"] == "multi_source_agree"
          and conf["K1"]["distinct_caselaw_sources"] == ["D1-Law", "NII"])
    check("L1 K2 single_source", conf["K2"]["identity_corroboration"] == "single_source")
    # K3 は LIC のみ(非判例DB) → non_caselaw_only
    check("L1 K3 non_caselaw_only (解説誌のみ)",
          conf["K3"]["identity_corroboration"] == "non_caselaw_only")

    fmap = {tuple(sorted([f["link"]["a"], f["link"]["b"]])) + (f["link"]["type"],): f for f in find}
    f_same = fmap[("D1-Law:111", "NII:222", "caselaw_same_case")]
    check("identity_corroborated (K1内)", f_same["status"] == "identity_corroborated")
    f_split = fmap[("D1-Law:333", "D1-Law:555", "caselaw_same_case")]
    check("採番割れ→conflict_review(非merge)", f_split["status"] == "conflict_review"
          and f_split["action"] == "human_review")
    f_lit = fmap[("D1-Law:111", "LIC:lic-9", "literature_about_case")]
    check("L2 解説誌→annotation_corroboration(非merge)",
          f_lit["status"] == "annotation_corroboration_L2")
    f_cite = fmap[("D1-Law:333", "D1-Law:555", "case_cites_case")]
    check("L3 引用→relationship_edge_candidate(非merge)",
          f_cite["status"] == "relationship_edge_candidate_L3" and f_cite["action"] == "review_edge")

    # コロボは assignment を変えない(merge を生まない)
    check("コロボは merge を生まない(assignment不変)",
          set(ASSIGN.values()) == {"K1", "K2", "K3", "K4"})

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}): {fails}")
        return 1
    print("RESULT: PASS (L1/L2/L3 コロボ分離・conflict検出・非merge green)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
