#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_synthetic_toc.py — スケール実証用の合成TOCデータ生成（本番Box非依存）

本番（事務所蔵書 5,206冊 / 124k+ノード）の形・規模を模した toc/*.json と books.json を
吐き、build_toc_search_index.py → server.js の取込・検索を実測できるようにする。
個人情報や実書誌は含まない、純粋な合成データ。ノードは本番の正規キーに合わせる:
  toc_node_id / parent_toc_node_id / page_start / depth / toc_source / t

使い方:
  python3 scripts/gen_synthetic_toc.py --out-dir /tmp/scale/toc \
      --books-json /tmp/scale/books.json --n 5206 [--seed 7]
"""
import argparse
import json
import os
import random
from pathlib import Path

# 検索が当たるよう、法律書らしい語彙でタイトルを合成する。
BRANCH = ["民法", "刑法", "商法", "民事訴訟法", "刑事訴訟法", "会社法", "労働法", "行政法", "憲法", "知的財産法"]
CH = ["総則", "債権", "物権", "時効", "契約", "不法行為", "親族", "相続", "手続", "証拠",
      "消滅時効", "取得時効", "起算点", "効力", "意義と目的", "援用と放棄", "完成猶予と更新"]
SEC = ["総説", "客観的起算点", "主観的起算点", "基本的な考え方", "各種債権の時効の起算点",
       "安全配慮義務違反による損害賠償請求権", "要件", "効果", "判例の展開", "学説の対立"]
SRC = ["bengo4", "legal_library", "self_scan", "publisher", "ndl"]


def gen_book(book_no, rng):
    """1冊分の TOC ノード配列（章→節→項の3階層）を返す。"""
    nodes = []
    nid = 0
    page = rng.randint(1, 20)
    n_ch = rng.randint(3, 8)
    branch = rng.choice(BRANCH)
    for _ in range(n_ch):
        nid += 1
        ch_id = f"b{book_no}_n{nid}"
        page += rng.randint(8, 40)
        nodes.append({
            "toc_node_id": ch_id, "parent_toc_node_id": None,
            "t": f"第{_+1}章 {rng.choice(CH)}", "depth": 1,
            "page_start": page, "toc_source": rng.choice(SRC),
        })
        for s in range(rng.randint(0, 4)):
            nid += 1
            sec_id = f"b{book_no}_n{nid}"
            page += rng.randint(3, 15)
            nodes.append({
                "toc_node_id": sec_id, "parent_toc_node_id": ch_id,
                "t": f"第{s+1}節 {rng.choice(SEC)}", "depth": 2,
                "page_start": page, "toc_source": rng.choice(SRC),
            })
            for it in range(rng.randint(0, 3)):
                nid += 1
                page += rng.randint(1, 8)
                nodes.append({
                    "toc_node_id": f"b{book_no}_n{nid}", "parent_toc_node_id": sec_id,
                    "t": f"{it+1} {rng.choice(SEC)}", "depth": 3,
                    "page_start": page, "toc_source": rng.choice(SRC),
                })
    return branch, nodes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True, help="toc/*.json 出力先")
    ap.add_argument("--books-json", required=True, help="books.json 出力先")
    ap.add_argument("--n", type=int, default=5206, help="冊数")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    books = []
    total_nodes = 0
    for i in range(args.n):
        # 合成ISBN（13桁・実在しない 978-4-00 帯）。
        isbn = f"97840{i:08d}"
        book_id = f"isbn_{isbn}"
        branch, nodes = gen_book(i, rng)
        (out_dir / f"{book_id}.json").write_text(
            json.dumps(nodes, ensure_ascii=False), encoding="utf-8")
        total_nodes += len(nodes)
        books.append({"book_id": book_id, "isbn": isbn,
                      "title": f"{branch}の研究 第{i % 90 + 1}巻", "author": "（合成）"})

    Path(args.books_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.books_json).write_text(
        json.dumps({"books": books}, ensure_ascii=False), encoding="utf-8")
    print(f"生成: {args.n:,} 冊 / {total_nodes:,} ノード → {out_dir}")
    print(f"      books.json → {args.books_json}")


if __name__ == "__main__":
    main()
