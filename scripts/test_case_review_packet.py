#!/usr/bin/env python3
"""test_case_review_packet.py — Q1 reviewer packet 生成＋集計の検証 (L-RV / S5)。

肝:
- flags→層化が frame 通り(S-A/B/C/D/E)。
- 負例control が注入され、accept すると過剰検出として検知される。
- 記入済→集計で decisions_made>0(0→N の証拠)・validator 不備検出。
実行: python3 scripts/test_case_review_packet.py  (exit 0 = 全PASS)。
"""
import json
import sys
from pathlib import Path
from case_review_packet import (build_worksheet, derive_stratum, tally,
                                 DECISION_VOCAB, N_NEGATIVE_CONTROL, FRAME_VERSION)

CANDS = Path(__file__).resolve().parent.parent / "app" / "data" / "case_identity" / "caserev_q1_sample_candidates.jsonl"


def run() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    cands = [json.loads(l) for l in CANDS.read_text(encoding="utf-8").splitlines() if l.strip()]
    check("候補fixture 読込(12件)", len(cands) == 12)

    # 層化
    check("multi_law_token→S-C", derive_stratum({"flags": ["multi_law_token"]}) == "S-C")
    check("suffix→S-D", derive_stratum({"flags": ["suffix"]}) == "S-D")
    check("cross_root→S-B", derive_stratum({"flags": ["cross_root"]}) == "S-B")
    check("provisional_kos→S-E", derive_stratum({"flags": ["provisional_kos"]}) == "S-E")
    check("p1→S-A", derive_stratum({"flags": ["p1_top_root_aligned"]}) == "S-A")

    rows = build_worksheet(cands)
    strata = {r["stratum"] for r in rows}
    check("worksheet に S-A/B/C/D/E + S-NEG が出る",
          {"S-A", "S-B", "S-C", "S-D", "S-E", "S-NEG"} <= strata)
    check("負例control が注入されている", sum(1 for r in rows if r["is_negative_control"] == "1") == N_NEGATIVE_CONTROL)
    check("全行 decision 空欄(reviewer未記入)", all(r["decision"] == "" for r in rows))
    check("frame_version 刻印", all(r["frame_version"] == FRAME_VERSION for r in rows))
    check("raw本文を持たない(表示は正規化キーのみ)", all("body_text" not in r and "raw" not in r for r in rows))

    # --- reviewer が記入したと仮定して集計 ---
    filled = [dict(r) for r in rows]
    actor = "asai"
    for r in filled:
        if r["is_negative_control"] == "1":
            r["decision"] = "reject_not_same_statute_context"; r["reason_code"] = "different_root"; r["decision_actor"] = actor
        elif r["stratum"] == "S-A":
            r["decision"] = "accept_d1kos_statute_ref_context"; r["decision_actor"] = actor
        else:
            r["decision"] = "accept_d1kos_statute_ref_context"; r["review_note"] = "article側支持を確認"; r["decision_actor"] = actor
    rep = tally(filled)
    check("decisions_made > 0 (decision overlay 0→N の証拠)", rep["decisions_made"] > 0)
    check("負例control 全 reject = 健全", rep["negative_control"]["healthy"])
    check("不備なし(actor/note/reason 完備)", rep["ok"])

    # --- バグ注入: 負例にaccept → 過剰検出として検知 ---
    bad = [dict(r) for r in filled]
    for r in bad:
        if r["is_negative_control"] == "1":
            r["decision"] = "accept_d1kos_statute_ref_context"; r["review_note"] = "x"
            break
    rep_bad = tally(bad)
    check("負例accept を過剰検出バグとして検知", not rep_bad["ok"] and not rep_bad["negative_control"]["healthy"])

    # --- 不備検知: actor 欠落 ---
    miss = [dict(r) for r in filled]
    miss[0]["decision_actor"] = ""
    check("decision_actor 欠落を検知", not tally(miss)["ok"])

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}): {fails}")
        return 1
    print("RESULT: PASS (Q1 reviewer packet 生成・負例・集計・validator が機能)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
