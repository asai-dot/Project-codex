#!/usr/bin/env python3
"""
compare_templates: 同一書式が複数の本でどう条項構成が違うかを機械比較する。
= 地図(L1)の複数インスタンスを term_id で突き合わせ、著者・版の差分を surface する。

入力: docs/tmplstruct/poc_e2e/clause_inventory_seizo.json (clause_inventory.v0)
出力:
  - カバレッジ行列 (term × book)
  - 共通条項 / 各本ユニーク条項
  - granularity=coarse の本は「比較不能(本文OCR要)」と明示
設計のみ。 python3 tools/compare_templates.py [inventory.json]
"""
import json, os, sys
from collections import OrderedDict

HERE = os.path.dirname(__file__)
DEFAULT = os.path.join(HERE, "..", "docs/tmplstruct/poc_e2e/clause_inventory_seizo.json")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def analyze(inv):
    fine = [b for b in inv["books"] if b["granularity"] == "fine"]
    coarse = [b for b in inv["books"] if b["granularity"] != "fine"]
    sets = {b["key"]: set(b["terms"]) for b in fine}
    # 全term(出現順を維持)
    all_terms = list(OrderedDict((t, 1) for b in fine for t in b["terms"]).keys())
    shared = set.intersection(*sets.values()) if len(sets) >= 2 else set()
    unique = {k: (s - set.union(*[v for kk, v in sets.items() if kk != k]) if len(sets) >= 2 else s)
              for k, s in sets.items()}
    return fine, coarse, sets, all_terms, shared, unique


def render(inv):
    L = inv["term_labels"]
    fine, coarse, sets, all_terms, shared, unique = analyze(inv)
    out = []
    w = out.append
    w(f"# 条項構成の機械比較: {inv['template_label_ja']}")
    w(f"比較可能(fine)= {len(fine)}冊 / 比較不能(coarse=本文OCR要)= {len(coarse)}冊")
    w("")
    # matrix
    hdr = "term".ljust(20) + " ".join(b["key"][:8].ljust(9) for b in fine)
    w("## カバレッジ行列 (● = その本が当該条項を立てている)")
    w("```")
    w(hdr)
    for t in all_terms:
        row = "".join(("●" if t in sets[b["key"]] else "·").ljust(9) for b in fine)
        w(f"{(L.get(t, t))[:18].ljust(20)}{row}")
    w("```")
    w(f"各本の条項数: " + " / ".join(f"{b['key']}={len(b['terms'])}" for b in fine))
    w("")
    # shared / unique
    w("## 共通条項(全fine本が立てる)")
    w("  " + "、".join(L.get(t, t) for t in all_terms if t in shared) + f"  ({len(shared)}件)")
    w("")
    w("## 各本ユニーク条項(その本だけが立てる)= 著者の力点")
    for b in fine:
        u = [L.get(t, t) for t in b["terms"] if t in unique[b["key"]]]
        emph = f" 〈{b.get('emphasis','')}〉" if b.get("emphasis") else ""
        w(f"- **{b['author']}**({b['publisher']}){emph}: " + ("、".join(u) if u else "(ユニークなし)"))
    w("")
    # coarse
    if coarse:
        w("## 比較不能(地図にはあるがTOC粗・本文OCR待ち)")
        for b in coarse:
            w(f"- {b['author']}({b['publisher']}): {b['source']}")
    w("")
    w("## 読み筋(機械が surface した差分)")
    w("- 同じ『製造委託基本契約書』でも、**網羅型(全標準条項を解説)** と **審査特化型(下請法・人権に力点)** で構成が大きく異なる。")
    w("- 共通コア(代金・検収・担保/契約不適合・再委託・秘密保持)は雛形横断で安定 → registry の accepted 候補母集団。")
    w("- coarse 本は地図に載るが条項比較に乗らない → 本文OCRの優先対象(R1の具体ターゲット)。")
    return "\n".join(out)


def selftest():
    inv = load(DEFAULT)
    ok = [0, 0]

    def chk(n, c):
        ok[1] += 1
        ok[0] += bool(c)
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")

    fine, coarse, sets, all_terms, shared, unique = analyze(inv)
    chk("has >=2 fine books", len(fine) >= 2)
    chk("shared nonempty", len(shared) >= 1)
    chk("subcontracting shared", "subcontracting" in shared)
    chk("takigawa unique has 下請法/人権", {"subcontract_law_compliance", "human_rights"} & unique.get("takigawa", set()) != set())
    chk("kondo unique has 損害賠償系", {"damages", "force_majeure", "antisocial_forces"} & unique.get("kondo", set()) != set())
    chk("coarse flagged", len(coarse) == 2)
    chk("all terms have labels", all(t in inv["term_labels"] for t in all_terms))
    print(f"self-test: {ok[0]}/{ok[1]} passed")
    return ok[0] == ok[1]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.exit(0 if selftest() else 1)
    print(render(load(sys.argv[1] if len(sys.argv) > 1 else DEFAULT)))
