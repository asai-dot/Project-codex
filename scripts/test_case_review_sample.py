#!/usr/bin/env python3
"""test_case_review_sample.py — サンプル監査 frame の検証 (DD-CASEREVIEW-001)。"""
import sys
from case_review_sample import sample_for_review, estimate_precision, DISPLAY_FIELDS


def mk(i, tier, corr):
    return {"observation_id": f"o{i:03d}", "case_key": f"K{i}", "tier": tier,
            "corroboration_level": corr, "forum_code": "tokyo-chisai",
            "decision_date": "2021-03-15", "case_number_raw": f"令和3年(ワ)第{i}号",
            "case_number_norm": f"R3-ワ-{i}", "external_id": f"d1:{i}",
            "source_system": "D1-Law", "content_grade": "full"}


def run() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    bindings = ([mk(i, "A", "multi_source_agree") for i in range(20)]
                + [mk(i, "B", "single_source") for i in range(20, 30)]
                + [mk(i, "C", "single_source") for i in range(30, 33)])

    ws = sample_for_review(bindings, n_per_stratum=5, seed=0)
    # 層化: A/multi(5) + B/single(5) + C/single(3) = 13
    check("層化抽出数 = 5+5+3 = 13", len(ws) == 13)
    check("全表示項目を含む", all(all(f in r for f in DISPLAY_FIELDS) for r in ws))
    check("reviewer_label 空欄を用意", all(r["reviewer_label"] == "" for r in ws))

    # 決定性(同seed→同結果)
    check("決定的(同seed)", [r["observation_id"] for r in sample_for_review(bindings, 5, 0)]
          == [r["observation_id"] for r in ws])

    # 精度推定 + drift: Tier A に false_merge を混ぜ目標(0.99)未達にする
    reviewed = []
    for r in ws:
        r2 = dict(r)
        if r2["tier"] == "A":
            r2["reviewer_label"] = "correct"
        elif r2["tier"] == "B":
            r2["reviewer_label"] = "correct"
        else:
            r2["reviewer_label"] = "false_split"
        reviewed.append(r2)
    # A の1件を false_merge に
    for r in reviewed:
        if r["tier"] == "A":
            r["reviewer_label"] = "false_merge"
            break
    est = estimate_precision(reviewed)
    check("Tier A precision = 4/5 = 0.8", est["by_tier"]["A"]["precision"] == 0.8)
    check("Tier A drift 検知(<0.99)", est["drift_detected"]
          and any(d["tier"] == "A" for d in est["drift"]))

    # 全て correct なら drift なし
    clean = [dict(r, reviewer_label="correct") for r in ws if r["tier"] in ("A", "B", "C")]
    est2 = estimate_precision(clean)
    check("全correct→drift無し", not est2["drift_detected"])

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}): {fails}")
        return 1
    print("RESULT: PASS (層化抽出・決定性・precision推定・drift検知 green)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
