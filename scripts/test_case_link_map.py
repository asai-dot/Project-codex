#!/usr/bin/env python3
"""test_case_link_map.py — 本文 mention→alo_edges 写像の検証 (DD-CASELINK-001 v0.2)。

肝:
- 1記事:N判例 を **同格に潰さず** edge_type/stance で型付けする。
- 自動エッジは masthead由来(vendor_explicit)+決定的 bind のみ。本文/fuzzy/未解決は review。
- emit する edge_type/assertion_mode/stance が **正典 case_vocab の部分集合**。llm_inferred 不発生。
- merge は決して emit しない(関係は edge / CASE-001)。未知シグナルは fail-closed。
実行: python3 scripts/test_case_link_map.py  (exit 0 = 全PASS)。
"""
import sys
import case_vocab as V
from case_link_map import map_mention, map_article, EMITTABLE_EDGE_TYPES


def run() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    # --- 評釈記事: masthead 主1 + 本文 同旨1 + 本文 反対1 (1記事:3判例, 1:1でない) ---
    essay = map_article([
        {"article_type": "commentary", "source": "masthead", "role": "primary", "resolved": "deterministic"},
        {"article_type": "commentary", "source": "body", "role": "supporting", "resolved": "deterministic"},
        {"article_type": "commentary", "source": "body", "role": "contrasting", "resolved": "fuzzy"},
    ])
    main, sup, con = essay
    check("評釈 主=evaluates・vendor_explicit・auto",
          main["edge_type"] == "evaluates" and main["assertion_mode"] == "vendor_explicit"
          and main["route"] == "auto" and main["stance"] is None)
    check("評釈 同旨=compares・stance=supporting・本文implicit・review",
          sup["edge_type"] == "compares" and sup["stance"] == "supporting"
          and sup["assertion_mode"] == "vendor_implicit" and sup["strength"] == "implicit"
          and sup["route"] == "review")
    check("評釈 反対=compares・stance=contrasting・review",
          con["edge_type"] == "compares" and con["stance"] == "contrasting" and con["route"] == "review")
    check("1記事:N が同格に潰れていない(edge_type/stance が役割で分化)",
          {(e["edge_type"], e["stance"]) for e in essay}
          == {("evaluates", None), ("compares", "supporting"), ("compares", "contrasting")})

    # --- 正式評釈シリーズ → review_chain ---
    rc = map_mention({"article_type": "commentary", "source": "masthead", "role": "primary",
                      "resolved": "deterministic", "is_formal_review": True})
    check("正式評釈 主=review_chain", rc["edge_type"] == "review_chain" and rc["route"] == "auto")

    # --- 論文: 評釈対象を持たない。主指定でも evaluates にせず compares 降格 + 中心判例ヒント ---
    art = map_mention({"article_type": "article", "source": "body", "role": "primary", "resolved": "deterministic"})
    check("論文は主を作らない(evaluates 不発生)・compares + central_case_hint",
          art["edge_type"] == "compares" and art["central_case_hint"] is True and art["route"] == "review")

    # --- 未解決引用 → エッジ無し・review ---
    unres = map_mention({"article_type": "commentary", "source": "body", "role": "supporting", "resolved": None})
    check("未解決引用は edge を作らず review", unres["edge_type"] is None and unres["route"] == "review")

    # --- fail-closed: 未知シグナルは drop ---
    bad = map_mention({"article_type": "blog", "source": "body", "role": "primary", "resolved": "deterministic"})
    check("未知 article_type は fail-closed(drop)", bad["route"] == "drop" and bad["edge_type"] is None)
    bad2 = map_mention({"article_type": "commentary", "source": "masthead", "role": "??", "resolved": "deterministic"})
    check("未知 role は fail-closed(drop)", bad2["route"] == "drop")

    # --- 正典整合: emit 値域 ⊆ case_vocab、llm_inferred/merge 不発生 ---
    corpus = essay + [rc, art, unres, bad, bad2]
    etypes = {e["edge_type"] for e in corpus if e["edge_type"]}
    amodes = {e["assertion_mode"] for e in corpus if e["assertion_mode"]}
    stances = {e["stance"] for e in corpus if e["stance"]}
    routes = {e["route"] for e in corpus}
    check("edge_type ⊆ vocab.COMMENTARY_TO_CASE_EDGE_TYPES ⊆ LINK_EDGE_TYPES",
          etypes <= V.COMMENTARY_TO_CASE_EDGE_TYPES <= V.LINK_EDGE_TYPES)
    check("assertion_mode ⊆ POC許可(llm_inferred 不発生)",
          amodes <= V.ASSERTION_MODES_POC_ALLOWED and "llm_inferred" not in amodes)
    check("stance ⊆ vocab.LINK_STANCES", stances <= V.LINK_STANCES)
    check("merge を emit しない(route は auto/review/drop のみ)", routes <= {"auto", "review", "drop"})
    check("自動エッジは vendor_explicit のみ",
          all(e["assertion_mode"] == "vendor_explicit" for e in corpus if e["route"] == "auto"))

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}): {fails}")
        return 1
    print("RESULT: PASS (本文採掘 mention が正典 alo_edges 語彙へ決定的に型付けされる)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
