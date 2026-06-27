#!/usr/bin/env python3
"""test_case_consistency.py — 横断語彙の統一性検査 (実データ流入前のゲート)。

各モジュール/データの語彙が case_vocab(正本) と一致することを検査。
時系列で別々に書いた DD のドリフトをここで止める。
実行: python3 scripts/test_case_consistency.py  (exit 0 = 統一済)。
"""
import csv
import sys
import json
from pathlib import Path
import case_vocab as V

D = Path(__file__).resolve().parent.parent
DATA = D / "app" / "data" / "case_identity"


def run() -> int:
    issues = []

    def chk(name, cond, detail=""):
        print(f"  {'OK  ' if cond else 'DRIFT'} {name}{'' if cond else '  ← '+detail}")
        if not cond:
            issues.append(name)

    # 1. confidentiality 4値
    import registry_negative_test as rnt
    chk("confidentiality: registry_negative_test ⊆ vocab",
        set(rnt.CONFIDENTIALITY_CLASSES) == set(V.CONFIDENTIALITY_CLASSES),
        f"{set(rnt.CONFIDENTIALITY_CLASSES) ^ set(V.CONFIDENTIALITY_CLASSES)}")
    import case_cite_gate as cg
    chk("egress sinks: cite_gate ⊆ vocab",
        set(cg.MATTER_CLASSES) <= set(V.CONFIDENTIALITY_CLASSES))

    # 2. egress sinks 3コピーが一致
    import jufu_intake as jf
    chk("egress sinks: jufu_intake == vocab", tuple(jf.GLOBAL_SINKS) == V.EGRESS_SINKS,
        f"{jf.GLOBAL_SINKS} vs {V.EGRESS_SINKS}")
    chk("egress sinks: registry_negative_test == vocab", tuple(rnt.GLOBAL_SINKS) == V.EGRESS_SINKS,
        f"{rnt.GLOBAL_SINKS} vs {V.EGRESS_SINKS}")

    # 3. forum_type
    import check_forum_registry_seed as cfr
    chk("forum_type: checker == vocab.FORUM_TYPES",
        set(cfr.VALID_FORUM_TYPES) == set(V.FORUM_TYPES),
        f"{set(cfr.VALID_FORUM_TYPES) ^ set(V.FORUM_TYPES)}")

    # 4. forum_level(符号 semantics)
    sem = list(csv.DictReader((DATA / "case_symbol_semantics.csv").open(encoding="utf-8")))
    levels = {r["forum_level"] for r in sem}
    chk("forum_level: semantics ⊆ vocab.FORUM_LEVELS", levels <= set(V.FORUM_LEVELS),
        f"{levels - set(V.FORUM_LEVELS)}")

    # 5. Tier: guard が emit する tier ⊆ vocab、eval/review が全 tier を扱える
    import case_bind_guard as bg
    _, tiers, _ = bg.decide_bindings([
        {"observation_id": "a", "forum_code": "f", "decision_date": "d", "case_number_norm": "N"},
        {"observation_id": "b", "forum_code": "f", "decision_date": "d", "case_number_norm": None},
    ])
    emitted = set(tiers.values())
    chk("tier: bind_guard emit ⊆ vocab.BIND_TIERS", emitted <= set(V.BIND_TIERS),
        f"{emitted - set(V.BIND_TIERS)}")
    import case_eval as ce
    # eval が prov tier ペアで KeyError を起こさないか(実害テスト)
    try:
        ce.score({"a": "X", "b": "X"}, {"a": "1", "b": "1"}, {"a": "prov", "b": "prov"})
        prov_ok = True
    except Exception as e:
        prov_ok = False
    chk("tier: eval が prov を処理できる(KeyError無し)", prov_ok, "RISK表に prov 無し")
    import case_review_sample as rs
    chk("tier: review PRECISION_TARGET ⊆ vocab.BIND_TIERS",
        set(rs.PRECISION_TARGET) <= set(V.BIND_TIERS))

    # 6. source_system: corroborate CASELAW ⊆ 登録 source、seed ⊆ 登録、gold ⊆ 登録
    import case_corroborate as cc
    chk("source: corroborate.CASELAW_SOURCES == vocab.CASELAW_SOURCES",
        set(cc.CASELAW_SOURCES) == set(V.CASELAW_SOURCES),
        f"{set(cc.CASELAW_SOURCES) ^ set(V.CASELAW_SOURCES)}")
    chk("source: vocab.CASELAW_SOURCES ⊆ vocab.REGISTERED_SOURCES",
        set(V.CASELAW_SOURCES) <= set(V.REGISTERED_SOURCES))
    seed_src = {json.loads(l)["source_system"]
                for l in (D / "docs" / "alo_source_registry_seed_v0.1-recon_20260619.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    chk("source: seed ⊆ vocab.REGISTERED_SOURCES", seed_src <= set(V.REGISTERED_SOURCES),
        f"{seed_src - set(V.REGISTERED_SOURCES)}")
    gold_src = {json.loads(l)["source"]
                for l in (DATA / "case_eval_gold_template.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    chk("source: gold ⊆ vocab.REGISTERED_SOURCES", gold_src <= set(V.REGISTERED_SOURCES),
        f"{gold_src - set(V.REGISTERED_SOURCES)}")

    # 7. リンク層(DD-CASELINK): map が emit する語彙 ⊆ vocab、llm_inferred 不発生
    import case_link_map as lm
    chk("link: case_link_map edge_type ⊆ vocab.COMMENTARY_TO_CASE_EDGE_TYPES",
        set(lm.EMITTABLE_EDGE_TYPES) <= set(V.COMMENTARY_TO_CASE_EDGE_TYPES),
        f"{set(lm.EMITTABLE_EDGE_TYPES) - set(V.COMMENTARY_TO_CASE_EDGE_TYPES)}")
    chk("link: vocab.COMMENTARY_TO_CASE_EDGE_TYPES ⊆ vocab.LINK_EDGE_TYPES",
        set(V.COMMENTARY_TO_CASE_EDGE_TYPES) <= set(V.LINK_EDGE_TYPES))
    chk("link: case_link_map assertion_mode ⊆ POC許可(llm_inferred 禁止)",
        set(lm.EMITTABLE_ASSERTION_MODES) <= set(V.ASSERTION_MODES_POC_ALLOWED)
        and "llm_inferred" not in lm.EMITTABLE_ASSERTION_MODES)
    chk("link: case_link_map stance == vocab.LINK_STANCES",
        set(lm.EMITTABLE_STANCES) == set(V.LINK_STANCES),
        f"{set(lm.EMITTABLE_STANCES) ^ set(V.LINK_STANCES)}")
    link_gold = {e["edge_type"]
                 for l in (DATA / "case_link_gold_template.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()
                 for e in json.loads(l)["expected_edges"] if e.get("edge_type")}
    chk("link: link gold edge_type ⊆ vocab.COMMENTARY_TO_CASE_EDGE_TYPES",
        link_gold <= set(V.COMMENTARY_TO_CASE_EDGE_TYPES),
        f"{link_gold - set(V.COMMENTARY_TO_CASE_EDGE_TYPES)}")
    chk("link: precision target keys ⊆ vocab.COMMENTARY_TO_CASE_EDGE_TYPES",
        set(V.LINK_PRECISION_TARGET) <= set(V.COMMENTARY_TO_CASE_EDGE_TYPES))

    print()
    if issues:
        print(f"RESULT: DRIFT DETECTED ({len(issues)}): {issues}")
        return 1
    print("RESULT: PASS (全モジュールが case_vocab 正本に統一)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
