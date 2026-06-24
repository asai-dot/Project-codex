#!/usr/bin/env python3
"""test_case_pipeline_e2e.py — 判例精度チェーンの統合(end-to-end)テスト。

「測る①→防ぐ②→回収③→出力④→監視⑤」を *1本の共有 fixture* で実際に通し、
部品が連結して破綻しないこと(安定性)を確認する。実データ流入前のゲート。
実行: python3 scripts/test_case_pipeline_e2e.py  (exit 0 = チェーン健全)。
"""
import sys
from case_bind_guard import decide_bindings, auto_bound_assignment, detect_cross_source_conflicts
from case_eval import score
from case_corroborate import corroborate
from case_cite_gate import validate_bundle
from case_review_sample import sample_for_review, estimate_precision

# 共有 fixture: 同一事件(D1+NII) / 同番号別forum(ハード負例) / 併合 / provisional
OBS = [
    {"observation_id": "o1", "forum_code": "tokyo-chisai", "decision_date": "2021-03-15",
     "case_number_norm": "R3-ワ-123", "external_id": "111", "source": "D1-Law", "external_source": "D1-Law"},
    {"observation_id": "o2", "forum_code": "tokyo-chisai", "decision_date": "2021-03-15",
     "case_number_norm": "R3-ワ-123", "external_id": "222", "source": "NII", "external_source": "NII"},
    {"observation_id": "o3", "forum_code": "osaka-chisai", "decision_date": "2021-03-15",
     "case_number_norm": "R3-ワ-123", "external_id": "333", "source": "D1-Law", "external_source": "D1-Law"},
    {"observation_id": "o4", "forum_code": "tokyo-chisai", "decision_date": "2021-04-01",
     "case_number_norm": None, "external_id": "", "source": "jufu", "external_source": "jufu"},
]
GOLD = {"o1": "K1", "o2": "K1", "o3": "K2", "o4": "K3-prov"}  # 真の正解


def run() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    # ② bind → ① eval: チェーン先頭で false_merge=0
    assign, tiers, review = decide_bindings(OBS)
    pred = auto_bound_assignment(OBS)
    m = score(GOLD, pred, {o: tiers[o] for o in tiers})
    check("②→① bind 結果 false_merge=0", m["false_merge"] == 0)
    check("②→① precision=1.0 / bcubed 同梱", m["precision"] == 1.0 and "bcubed" in m)
    check("②→① eval が prov tier を処理(KeyError無し)", isinstance(m["per_tier_precision"], dict))

    # ② cross-source conflict は空(矛盾なし)
    check("② cross-source conflict 無し", detect_cross_source_conflicts(pred, {o["observation_id"]: o for o in OBS}) == [])

    # ③ corroborate: K1 は D1+NII の2源で multi_source_agree
    conf, find = corroborate(pred, {o["observation_id"]: o for o in OBS}, [
        {"a": "D1-Law:111", "b": "NII:222", "type": "caselaw_same_case"},
    ])
    k1 = pred["o1"]
    check("③ K1 multi_source_agree", conf[k1]["identity_corroboration"] == "multi_source_agree")
    check("③ identity_corroborated finding", any(f["status"] == "identity_corroborated" for f in find))

    # ④ cite-gate: confirmed 公開 case を引用する bundle は通過、機密(jufu)global は reject
    uri_pub = "alo:case:jp:tokyo-chisai:2021-03-15:R3-ワ-123"
    uri_jufu = "alo:case:jp:tokyo-chisai:2021-04-01:_prov"
    known = {uri_pub: {"full_text_len": 500, "confidentiality_class": "open", "redistribution": "public"},
             uri_jufu: {"full_text_len": 100, "confidentiality_class": "lawyer_client_confidential", "redistribution": "restricted"}}
    good = {"serve_scope": "global", "annotation_used": {"source": "D1-Law"},
            "claims": [{"id": "c1", "cites": [uri_pub],
                        "evidence": [{"case_uri": uri_pub, "range_start": 0, "range_end": 40}]}]}
    bad = {"serve_scope": "global", "annotation_used": {"source": "D1-Law"},
           "claims": [{"id": "c1", "cites": [uri_jufu],
                       "evidence": [{"case_uri": uri_jufu, "range_start": 0, "range_end": 40}]}]}
    check("④ 公開 case の bundle は通過", validate_bundle(good, known, {"D1-Law"})["ok"])
    check("④ jufu の global bundle は reject", not validate_bundle(bad, known, {"D1-Law"})["ok"])

    # ⑤ review: bindings を層化抽出 → worksheet → precision 推定
    bindings = [{"observation_id": o["observation_id"], "case_key": pred[o["observation_id"]],
                 "tier": tiers[o["observation_id"]], "corroboration_level": "multi_source_agree",
                 "forum_code": o["forum_code"], "decision_date": o["decision_date"],
                 "case_number_raw": "", "case_number_norm": o["case_number_norm"] or "",
                 "external_id": o["external_id"], "source_system": o["source"], "content_grade": "full"}
                for o in OBS]
    ws = sample_for_review(bindings, n_per_stratum=5, seed=0)
    check("⑤ worksheet 生成(全件抽出)", len(ws) == len(bindings))
    est = estimate_precision([dict(r, reviewer_label="correct") for r in ws])
    check("⑤ 全correct→drift無し・unsure_rate=0", not est["drift_detected"] and est["unsure_rate"] == 0.0)

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}): {fails}")
        return 1
    print("RESULT: PASS (①〜⑤ チェーンが共有fixtureで連結・破綻なし)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
