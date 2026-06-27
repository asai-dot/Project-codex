#!/usr/bin/env python3
"""case_link_corpus_dryrun.py — 評釈→判例リンクの corpus dry-run ランナー (DD-CASELINK-001 accepted)。

D1-LIC 形状の記事 JSONL を span検出→extract→map に流し、**何が auto エッジ化され何が review に
落ちるか**(route 分布)・edge_type/stance 分布を集計する。GO「read-only corpus dry run」の実体。
**read-only・production write なし**。実 corpus(D1-LIC 5,475)は Mac CC が `--corpus PATH` で差すだけ。

使い方:
  python3 scripts/case_link_corpus_dryrun.py                 # 同梱合成サンプルで動作確認
  python3 scripts/case_link_corpus_dryrun.py --corpus a.jsonl # 実 corpus(Mac CC)

入力 JSONL の各行(record): case_citation_span.build_article が受ける形
  {"article_type","masthead_citation"?,"is_formal_review"?,"body_text"}
"""
from __future__ import annotations
import json
import sys
from case_citation_span import build_article
from case_link_extract import extract_mentions
from case_link_map import map_article

# 同梱合成サンプル(実データ非依存の自己検証用)
SAMPLE = [
    {"article_type": "commentary", "masthead_citation": "令和3年(ワ)第123号",
     "body_text": "本判決は妥当。同旨、最判平成20年3月10日。これに対し東京高判令和2年5月1日は異なる。"},
    {"article_type": "commentary", "masthead_citation": "平成29年(受)第1234号", "is_formal_review": True,
     "body_text": "なお原審(東京地判平成28年4月1日)は結論を異にした。"},
    {"article_type": "article",
     "body_text": "本稿は複数の裁判例を横断する。最判平成20年3月10日、令和3年(ワ)第123号 等を参照。"},
]


def run(records: list[dict]) -> dict:
    n_art = len(records)
    edge_types: dict[str, int] = {}
    routes: dict[str, int] = {}
    stances: dict[str, int] = {}
    n_edges = 0
    n_drop = 0
    for rec in records:
        art = build_article(rec)
        edges = map_article(extract_mentions(art))
        for e in edges:
            routes[e["route"]] = routes.get(e["route"], 0) + 1
            if e["route"] == "drop" or not e["edge_type"]:
                n_drop += 1
                continue
            n_edges += 1
            edge_types[e["edge_type"]] = edge_types.get(e["edge_type"], 0) + 1
            if e.get("stance"):
                stances[e["stance"]] = stances.get(e["stance"], 0) + 1
    return {
        "articles": n_art,
        "edges_emitted": n_edges,
        "dropped_or_unresolved": n_drop,
        "edge_type_counts": edge_types,
        "route_distribution": routes,
        "stance_counts": stances,
        "note": "auto=構造由来(masthead/vendor_explicit) のみ。review=本文由来(vendor_implicit)。"
                "実 precision は gold 突合が要る(Mac CC)。本 dry-run は分布のみ。",
    }


def load_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--corpus" in args:
        path = args[args.index("--corpus") + 1]
        records = load_jsonl(path)
        src = path
    else:
        records, src = SAMPLE, "(同梱合成サンプル)"
    rep = run(records)
    print(f"# CASELINK corpus dry-run  source={src}")
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    sys.exit(0)
