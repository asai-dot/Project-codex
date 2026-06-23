#!/usr/bin/env python3
"""test_case_precision_v02.py — accepted 5本の non-blocking note 消化 (v0.2) の検証。

① CASEEVAL  : cluster-level B-cubed 指標
② CASEBIND  : cross-source conflict 検出 (G6)
④ CASECITE  : matter scope 認可 (V8)
⑤ CASEREVIEW: sample size / Wilson CI / unsure 率
実行: python3 scripts/test_case_precision_v02.py  (exit 0 = 全PASS)。
"""
import sys
from case_eval import score, bcubed
from case_bind_guard import detect_cross_source_conflicts
from case_cite_gate import validate_bundle
from case_review_sample import required_sample_size, wilson_ci, estimate_precision


def run() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    # ① B-cubed: 完全一致=1.0、1誤統合で precision<1
    g = {"a": "X", "b": "X", "c": "Y"}
    check("① bcubed 完全一致=1.0",
          bcubed(g, {"a": "1", "b": "1", "c": "2"}) == {"bcubed_precision": 1.0, "bcubed_recall": 1.0})
    bc = bcubed(g, {"a": "1", "b": "1", "c": "1"})  # c を X に誤統合
    check("① bcubed 誤統合で precision<1", bc["bcubed_precision"] < 1.0 and bc["bcubed_recall"] == 1.0)
    check("① score に bcubed 同梱", "bcubed" in score(g, {"a": "1", "b": "1", "c": "2"}))

    # ② cross-source conflict: 同一 source:id が2 case に跨る
    assign = {"o1": "K1", "o2": "K2"}
    obs = {"o1": {"source": "D1", "external_id": "X"}, "o2": {"source": "D1", "external_id": "X"}}
    conf = detect_cross_source_conflicts(assign, obs)
    check("② cross-source conflict 検出",
          len(conf) == 1 and conf[0]["reason"] == "same_extref_multi_case"
          and conf[0]["case_keys"] == ["K1", "K2"])
    # 衝突なし(同一 case)→空
    check("② 衝突なし→空", detect_cross_source_conflicts({"o1": "K1", "o2": "K1"}, obs) == [])

    # ④ V8 matter 認可
    KNOWN = {"u_m": {"full_text_len": 100, "confidentiality_class": "matter_scoped_only",
                     "redistribution": "restricted", "matter_id": "M-1"}}
    CANON = {"D1-Law"}
    bundle = {"serve_scope": "matter", "annotation_used": {"source": "D1-Law"},
              "claims": [{"id": "c1", "cites": ["u_m"],
                          "evidence": [{"case_uri": "u_m", "range_start": 0, "range_end": 10}]}]}
    codes_no = {x["code"] for x in validate_bundle(bundle, KNOWN, CANON, requester_matters=None)["violations"]}
    codes_ok = {x["code"] for x in validate_bundle(bundle, KNOWN, CANON, requester_matters={"M-1"})["violations"]}
    codes_other = {x["code"] for x in validate_bundle(bundle, KNOWN, CANON, requester_matters={"M-9"})["violations"]}
    check("④ V8 未認可(None)→reject", "V8_matter_not_authorized" in codes_no)
    check("④ V8 別matter認可→reject", "V8_matter_not_authorized" in codes_other)
    check("④ V8 正しいmatter認可→通過", "V8_matter_not_authorized" not in codes_ok)

    # ⑤ sample size / Wilson CI / unsure
    n99 = required_sample_size(0.99, margin=0.02)
    check("⑤ required_sample_size(0.99,±0.02)≈96", n99 == 96)
    lo, hi = wilson_ci(95, 100)
    check("⑤ Wilson CI(95/100) 妥当", lo is not None and 0.88 < lo < 0.96 and 0.96 < hi <= 1.0)
    reviewed = [{"tier": "A", "stratum": "A/x", "reviewer_label": "correct"} for _ in range(8)] \
        + [{"tier": "A", "stratum": "A/x", "reviewer_label": "unsure"}] \
        + [{"tier": "A", "stratum": "A/x", "reviewer_label": "false_merge"}]
    est = estimate_precision(reviewed)
    check("⑤ unsure_rate=0.1", est["unsure_rate"] == 0.1)
    check("⑤ by_tier に ci95/recommended_n", "ci95" in est["by_tier"]["A"]
          and est["by_tier"]["A"]["recommended_n"] == 96)

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}): {fails}")
        return 1
    print("RESULT: PASS (①bcubed ②cross-source ④V8 ⑤sample/CI/unsure green)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
