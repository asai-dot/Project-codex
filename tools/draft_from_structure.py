#!/usr/bin/env python3
"""
draft_from_structure: 構造化書式データ(template_e2e.v0)から「弁護士が起案できる」出力を生成する。
= 壮大計画のレベル4(ドキュメンテーション)の最小実証。

入力: docs/tmplstruct/poc_e2e/seizo_kihon.e2e.json (+ MAP_*.json)
出力(標準出力):
  A 書式マップ      … この書式が所蔵のどの本のどこにあるか(L1)
  B 起案スケルトン  … 条項＋埋めるべきslot【...】(L2読取+L3構造)
  C 記載事項レビュー … 条項→記載事項区分/推奨/有利不利/法的根拠/接地(L4意味)
  D ギャップ警告     … 標準条項のうち捕捉範囲に無いもの
  E 接地サマリ       … grounded / provisional の内訳(自己採点でなく接地の有無を明示)

設計のみ・DB書込みなし。 python3 tools/draft_from_structure.py [e2e.json]
"""
import json, os, sys

HERE = os.path.dirname(__file__)
DEFAULT = os.path.join(HERE, "..", "docs/tmplstruct/poc_e2e/seizo_kihon.e2e.json")

CLASS_LABEL = {
    "essentialia": "★法的本質要素(無いと契約不成立)",
    "default_modifying": "任意的記載事項(任意規定の修正)",
    "risk_allocation": "任意的記載事項(リスク配分)",
    "regulatory": "法令上の要請事項",
}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def render(e2e, mp=None):
    out = []
    w = out.append
    w(f"# 起案ブリーフ: {e2e['template_label_ja']}")
    w(f"_法的性質_: {e2e.get('contract_type_legal','')}")
    w("")

    # A. MAP
    w("## A. 書式マップ(この雛形はどこにあるか)")
    if mp:
        for it in mp["instances"]:
            scan = "自炊済" if it.get("self_scanned") else "TOCのみ"
            w(f"- {it['author']}／{it['publisher']}: 書式p{it.get('form_print_page','?')} [{scan}] — {it['role']}")
    w("")

    # B. SKELETON
    w("## B. 起案スケルトン(条項＋要記入欄)")
    for c in e2e["clauses"]:
        w(f"### {c['no']} {c['title']}")
        w(f"> {c['read_excerpt']}")
        slots = c.get("structure", {}).get("slots", [])
        if slots:
            fills = "  ".join(f"【{s['id']}:{s['type']}】" for s in slots)
            w(f"  記入: {fills}")
        w("")

    # C. 記載事項レビュー
    w("## C. 記載事項レビュー(区分・有利不利・根拠・接地)")
    w("| 条項 | 記載事項区分 | 推奨 | 有利不利 | 接地 | 法的根拠 |")
    w("|---|---|---|---|---|---|")
    for c in e2e["clauses"]:
        m = c.get("meaning", {})
        cls = CLASS_LABEL.get(m.get("requisite_class"), m.get("requisite_class", "?"))
        lb = "; ".join(m.get("legal_backing", []))[:60]
        w(f"| {c['no']} {c['title']} | {cls} | {m.get('advisability','')} | {m.get('favors','')} | {m.get('grounding','')} | {lb} |")
    w("")

    # D. GAP
    w("## D. ギャップ警告(標準条項のうち捕捉範囲に無いもの)")
    gaps = [g for g in e2e.get("expected_clauses_beyond_capture", []) if g.get("meaning", {}).get("gap_flag")]
    for g in gaps:
        m = g["meaning"]
        cls = CLASS_LABEL.get(m.get("requisite_class"), m.get("requisite_class", "?"))
        w(f"- ⚠ **{g['label_ja']}**({cls} / 推奨={m.get('advisability','')} / 有利不利={m.get('favors','')} / 接地={m.get('grounding','')})")
    w("")

    # E. 接地サマリ
    all_m = [c["meaning"] for c in e2e["clauses"]] + [g["meaning"] for g in e2e.get("expected_clauses_beyond_capture", [])]
    grounded = sum(1 for m in all_m if str(m.get("grounding", "")).startswith("grounded"))
    prov = sum(1 for m in all_m if str(m.get("grounding", "")).startswith("provisional"))
    w("## E. 接地サマリ(自己採点でなく接地の有無)")
    w(f"- grounded(法令/解説に接地)= {grounded} / provisional(要解説接地)= {prov}")
    w(f"- ★essentialia(本質要素)= {sum(1 for c in e2e['clauses'] if c['meaning'].get('requisite_class')=='essentialia')} 条 …これらが揃えば契約は成立する")
    w("- provisional 項目は解説OCR接地で grounded へ昇格(no_blind_tagging)。")
    return "\n".join(out)


def selftest():
    e2e = load(DEFAULT)
    ok = [0, 0]

    def chk(name, cond):
        ok[1] += 1
        ok[0] += bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    chk("schema", e2e.get("schema") == "template_e2e.v0")
    chk("has clauses", len(e2e.get("clauses", [])) >= 5)
    chk("every clause has read+structure+meaning",
        all("read_excerpt" in c and "structure" in c and "meaning" in c for c in e2e["clauses"]))
    chk("every meaning has requisite_class+grounding",
        all(c["meaning"].get("requisite_class") and c["meaning"].get("grounding") for c in e2e["clauses"]))
    chk("essentialia present (>=1)",
        any(c["meaning"].get("requisite_class") == "essentialia" for c in e2e["clauses"]))
    chk("gap detection nonempty",
        any(g.get("meaning", {}).get("gap_flag") for g in e2e.get("expected_clauses_beyond_capture", [])))
    chk("grounded subcontracting present",
        any(g["term"] == "subcontracting" and str(g["meaning"]["grounding"]).startswith("grounded")
            for g in e2e.get("expected_clauses_beyond_capture", [])))
    print(f"self-test: {ok[0]}/{ok[1]} passed")
    return ok[0] == ok[1]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.exit(0 if selftest() else 1)
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    e2e = load(path)
    mp_path = os.path.join(os.path.dirname(path), "MAP_seizo_kihon.json")
    mp = load(mp_path) if os.path.exists(mp_path) else None
    print(render(e2e, mp))
