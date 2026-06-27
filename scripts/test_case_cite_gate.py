#!/usr/bin/env python3
"""test_case_cite_gate.py — 引用検証ゲートの検証 (DD-CASECITE-001)。

正常 bundle は ok / 各違反型(ハルシネーション cite・無根拠・OOB pointer・非canonical源・
global で非open引用)は fail-closed で弾く。
実行: python3 scripts/test_case_cite_gate.py  (exit 0 = 全PASS)。
"""
import sys
from case_cite_gate import validate_bundle

U_OPEN = "alo:case:jp:tokyo-chisai:2021-03-15:R3-ワ-123"
U_CONF = "alo:case:jp:tokyo-chisai:2021-04-01:_prov"
KNOWN = {
    U_OPEN: {"full_text_len": 1000, "confidentiality_class": "open", "redistribution": "public"},
    U_CONF: {"full_text_len": 500, "confidentiality_class": "lawyer_client_confidential", "redistribution": "restricted"},
}
CANON = {"D1-Law", "saikousai-hp"}


def good_bundle(scope="global", uri=U_OPEN):
    return {"serve_scope": scope, "annotation_used": {"source": "D1-Law"},
            "claims": [{"id": "c1", "text": "判旨...", "cites": [uri],
                        "evidence": [{"case_uri": uri, "pointer_uri": "p1",
                                      "range_start": 10, "range_end": 50}]}]}


def run() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    def codes(b):
        return {x["code"] for x in validate_bundle(b, KNOWN, CANON)["violations"]}

    check("正常 bundle → ok", validate_bundle(good_bundle(), KNOWN, CANON)["ok"])

    # V2 ハルシネーション cite
    b = good_bundle(); b["claims"][0]["cites"] = ["alo:case:jp:nowhere:2099-01-01:X"]
    b["claims"][0]["evidence"] = []
    check("V2 未解決cite→reject", not validate_bundle(b, KNOWN, CANON)["ok"]
          and "V2_cite_unresolved" in codes(b))

    # V1 cite 無し
    b = good_bundle(); b["claims"][0]["cites"] = []
    check("V1 cite無→reject", "V1_no_cite" in codes(b))

    # V3 evidence 無し
    b = good_bundle(); b["claims"][0]["evidence"] = []
    check("V3 evidence無→reject", "V3_no_evidence" in codes(b))

    # V5 pointer OOB
    b = good_bundle(); b["claims"][0]["evidence"][0]["range_end"] = 99999
    check("V5 pointer OOB→reject", "V5_pointer_range_oob" in codes(b))

    # V4 evidence が cite に無い
    b = good_bundle(); b["claims"][0]["evidence"][0]["case_uri"] = U_CONF
    check("V4 evidence≠cite→reject", "V4_evidence_not_in_cites" in codes(b))

    # V6 非 canonical 源
    b = good_bundle(); b["annotation_used"]["source"] = "manual"
    check("V6 非canonical源→reject", "V6_annotation_source_not_canonical" in codes(b))

    # V7 global で非open(機密)を引用
    b = good_bundle(scope="global", uri=U_CONF)
    check("V7 global×機密cite→reject", "V7_egress_non_open_cited" in codes(b))
    # 同じ機密 cite も matter scope なら egress 違反は出ない(解決はする)
    b2 = good_bundle(scope="matter", uri=U_CONF)
    check("matter scope では egress違反なし",
          "V7_egress_non_open_cited" not in codes(b2))

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}): {fails}")
        return 1
    print("RESULT: PASS (V1-V7 fail-closed; ハルシネーションcite/無根拠/OOB/機密egress を遮断)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
