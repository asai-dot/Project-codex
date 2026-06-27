#!/usr/bin/env python3
"""test_case_link_extract.py — 抽出器の決定部 + extract→map 連結の検証 (DD-CASELINK-001 v0.2)。

肝:
- 役割分類(masthead=主 / 同旨=supporting / これに対し=contrasting / 無手掛かり=incidental)。
- 引用解決度(完全事件番号=deterministic / 日付のみ=fuzzy / 裁判所名のみ=None)。
- extract→map を連結し、記事→正典 alo_edges candidate が破綻なく出ることを確認(自己無矛盾)。
実行: python3 scripts/test_case_link_extract.py  (exit 0 = 全PASS)。
"""
import sys
from case_link_extract import classify_role, resolve_citation, extract_mentions
from case_link_map import map_article


def run() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    # --- 役割分類 ---
    check("masthead→primary", classify_role("masthead") == "primary")
    check("本文 同旨→supporting", classify_role("body", "同旨、最判…") == "supporting")
    check("本文 これに対し→contrasting", classify_role("body", "これに対し最判…") == "contrasting")
    check("本文 反対→contrasting", classify_role("body", "反対説として") == "contrasting")
    check("本文 手掛かり無し→incidental", classify_role("body", "なお制度の沿革は") == "incidental")

    # --- 引用解決度 ---
    check("完全事件番号→deterministic", resolve_citation("令和3年(ワ)第123号") == "deterministic")
    check("日付のみ→fuzzy", resolve_citation("最判平成20年3月10日") == "fuzzy")
    check("裁判所名のみ→None", resolve_citation("東京地裁") is None)
    check("空→None", resolve_citation("") is None)

    # --- extract→map 連結(評釈 1主+同旨+反対, 1記事:3判例) ---
    article = {"article_type": "commentary",
               "masthead": {"citation": "令和3年(ワ)第123号"},
               "body": [{"citation": "最判平成20年3月10日", "cue": "同旨"},
                        {"citation": "令和2年(ネ)第45号", "cue": "これに対し"}]}
    mentions = extract_mentions(article)
    check("抽出: 1記事から3 mention(N判例を潰さない)", len(mentions) == 3)
    edges = map_article(mentions)
    main, sup, con = edges
    check("連結: 主→evaluates/vendor_explicit/auto",
          main["edge_type"] == "evaluates" and main["route"] == "auto")
    check("連結: 同旨(日付のみ)→compares/supporting/vendor_implicit/review",
          sup["edge_type"] == "compares" and sup["stance"] == "supporting"
          and sup["assertion_mode"] == "vendor_implicit" and sup["route"] == "review")
    check("連結: 反対(完全番号but本文)→compares/contrasting/review",
          con["edge_type"] == "compares" and con["stance"] == "contrasting"
          and con["route"] == "review")

    # --- 論文: masthead 無し、本文のみ → 主が生まれない ---
    paper = {"article_type": "article", "masthead": None,
             "body": [{"citation": "令和3年(ワ)第123号", "cue": "参照"},
                      {"citation": "最判平成20年3月10日", "cue": ""}]}
    pedges = map_article(extract_mentions(paper))
    check("論文: evaluates/review_chain が一切出ない",
          all(e["edge_type"] not in ("evaluates", "review_chain") for e in pedges))

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}): {fails}")
        return 1
    print("RESULT: PASS (記事→mention→正典 alo_edges candidate が破綻なく連結)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
