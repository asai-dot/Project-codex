#!/usr/bin/env python3
"""test_case_citation_span.py — 規則ベース citation-span 検出 + corpus dry-run の検証 (DD-CASELINK-001)。

肝:
- 各種引用書式(完全番号 / 最判+日付 / 裁判所+日付)を span として拾う。
- cue 語(同旨/これに対し)が引用に飲み込まれず、直前 cue 窓に残る(役割分類が効く)。
- span→extract→map 連結で本文由来は review、masthead は auto。
- corpus dry-run が route/edge_type 分布を返す(実 precision は Mac CC)。
実行: python3 scripts/test_case_citation_span.py  (exit 0 = 全PASS)。
"""
import sys
from case_citation_span import find_body_citations, masthead_citation, build_article
from case_link_extract import extract_mentions
from case_link_map import map_article
from case_link_corpus_dryrun import run, SAMPLE


def run_tests() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    # --- span 検出: 書式バリエーション ---
    c1 = find_body_citations("同旨、最判平成20年3月10日。")
    check("最判+日付 を1件検出", len(c1) == 1 and c1[0]["citation"] == "最判平成20年3月10日")
    check("cue に『同旨』が残る(引用に飲み込まれない)", "同旨" in c1[0]["cue"])

    c2 = find_body_citations("これに対し東京高判令和2年5月1日は異なる。")
    check("裁判所+日付 を検出・cue に『これに対し』が残る",
          len(c2) == 1 and c2[0]["citation"] == "東京高判令和2年5月1日" and "これに対し" in c2[0]["cue"])

    c3 = find_body_citations("参照、令和3年(ワ)第123号。")
    check("完全事件番号 を検出", len(c3) == 1 and "令和3年(ワ)第123号" in c3[0]["citation"])

    c4 = find_body_citations("制度の沿革を述べる。")
    check("引用が無い本文は空", c4 == [])

    # --- masthead ---
    check("masthead 構造引用を取得", masthead_citation({"masthead_citation": "令和3年(ワ)第123号"}) == "令和3年(ワ)第123号")
    check("masthead 無しは None", masthead_citation({"body_text": "x"}) is None)

    # --- span→extract→map 連結 ---
    rec = {"article_type": "commentary", "masthead_citation": "令和3年(ワ)第123号",
           "body_text": "本判決は妥当。同旨、最判平成20年3月10日。これに対し東京高判令和2年5月1日。"}
    edges = map_article(extract_mentions(build_article(rec)))
    check("連結: 3 mention(masthead主+本文2)", len(edges) == 3)
    check("連結: masthead→evaluates/auto", edges[0]["edge_type"] == "evaluates" and edges[0]["route"] == "auto")
    check("連結: 同旨→compares/supporting/review",
          edges[1]["edge_type"] == "compares" and edges[1]["stance"] == "supporting" and edges[1]["route"] == "review")
    check("連結: 反対→compares/contrasting/review",
          edges[2]["edge_type"] == "compares" and edges[2]["stance"] == "contrasting" and edges[2]["route"] == "review")

    # --- corpus dry-run ---
    rep = run(SAMPLE)
    check("dry-run: 3記事を処理", rep["articles"] == 3)
    check("dry-run: auto エッジが存在(masthead由来)", rep["route_distribution"].get("auto", 0) >= 1)
    check("dry-run: review エッジが存在(本文由来)", rep["route_distribution"].get("review", 0) >= 1)
    check("dry-run: 論文記事は evaluates を生まない(edge_type_counts に evaluates 由来の過剰なし)",
          rep["edge_type_counts"].get("evaluates", 0) <= 1)  # サンプルの評釈1件のみ

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}): {fails}")
        return 1
    print("RESULT: PASS (規則ベース span 検出 + corpus dry-run が機能。実 corpus/precision は Mac CC)")
    return 0


if __name__ == "__main__":
    sys.exit(run_tests())
