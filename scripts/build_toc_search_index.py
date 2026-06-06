#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_toc_search_index.py  (Fork2 / 検索・RAG 版)

既存 app/scripts/build_toc_search_index.py は {t, d} しか持たず、検索結果を
「書名・章節・ページ」に着地させられなかった。本版は各ノードに
  - p     : 印刷ページ（page_start / p）
  - path  : 親をたどった章節パス（例「第3章 消滅時効 > 第2節 時効の起算点」）
  - src   : 出典（toc_source）
  - id    : 正規ノードID（toc_node_id）
を持たせ、book_id/isbn + page_start + path をメタに保持する（＝RAGのチャンク単位）。
同時に books_or_jp の JS/HTML 断片・ナビ語彙・文字化け（既存 server.js の防衛ロジック）を
ビルド時に除去し、インデックスを最初からクリーンにする。

入出力（環境変数で上書き可）:
  TOC_DIR    入力 toc/ ディレクトリ      default: <repo>/data/toc
  BOOKS_JSON 蔵書マスタ                  default: <repo>/data/books.json
  OUT        出力インデックス            default: <repo>/data/toc_search_index.json

本番（Box app）で回す場合:
  TOC_DIR=~/Box/.../app/data/toc BOOKS_JSON=~/Box/.../app/data/books.json \
  OUT=~/Box/.../app/data/toc_search_index_v2.json python3 build_toc_search_index.py
"""
import json
import os
import re
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOC_DIR = Path(os.environ.get("TOC_DIR", REPO / "data" / "toc"))
BOOKS_JSON = Path(os.environ.get("BOOKS_JSON", REPO / "data" / "books.json"))
OUT = Path(os.environ.get("OUT", REPO / "data" / "toc_search_index.json"))

# --- データ品質防衛（server.js の isCleanTocEntry を移植） -------------------
TOC_GARBAGE_PATTERNS = [
    re.compile(r"\$\s*\("),
    re.compile(r"</?(?:h[1-6]|div|span|p|a|li|ul|ol|br|strong|em|b|i|table|tr|td)\b", re.I),
    re.compile(r"\.append\s*\("),
    re.compile(r"\.html\s*\("),
    re.compile(r"text-heading|text-color|accessiblebook", re.I),
]
TOC_NAV_TERMS = {
    "雑誌", "書籍", "新刊", "既刊", "近刊", "新刊・既刊", "別冊商事法務", "別冊NBL",
    "資料版商事法務", "NBL", "訂正・サポート情報", "常備店一覧", "常備店", "セミナー",
    "申込受付中", "今月の開催・配信開始", "注目のテーマ", "デジタル", "電子書籍",
    "商事法務データベース", "メルマガ", "商事法務ポータル", "研究会", "商事法務について",
    "個人情報保護方針", "TOP", "処理中です…", "処理中です...", "このままお待ちください。",
    "ホーム", "メニュー", "検索", "ログイン", "ログアウト", "カート", "会社概要",
    "利用規約", "プライバシーポリシー", "サイトマップ", "お問い合わせ", "問い合わせ",
    "よくある質問", "FAQ", "もくじ", "目次", "その他",
}
TOC_NAV_REGEXES = [
    re.compile(r"^Copyright\s*[©Ⓒ]", re.I),
    re.compile(r"All rights reserved", re.I),
    re.compile(r"^©\s*\d{4}"),
    re.compile(r"^\(c\)\s*\d{4}", re.I),
]
CJK = re.compile(r"[　-鿿぀-ヿ]")


def looks_mojibake(t: str) -> bool:
    head = t[:16]
    if CJK.search(head):
        return False
    bad = sum(1 for ch in head if 0x80 <= ord(ch) <= 0xFF)
    return bad >= 8


def norm_ws(s: str) -> str:
    return re.sub(r"[　\s]+", " ", s).strip()


def is_clean(node: dict) -> bool:
    t = (node.get("t") or "").strip()
    if len(t) < 2:
        return False
    tn = norm_ws(t)
    if t in TOC_NAV_TERMS or tn in TOC_NAV_TERMS:
        return False
    for pat in TOC_NAV_REGEXES:
        if pat.search(t):
            return False
    for pat in TOC_GARBAGE_PATTERNS:
        if pat.search(t):
            return False
    if looks_mojibake(t):
        return False
    return True


# --- パス構築 ---------------------------------------------------------------
def build_paths(nodes):
    """parent_toc_node_id をたどって各ノードの章節パス文字列を作る。"""
    by_id = {n.get("toc_node_id"): n for n in nodes if n.get("toc_node_id")}
    cache = {}

    def path_of(node, seen=None):
        nid = node.get("toc_node_id")
        if nid in cache:
            return cache[nid]
        seen = seen or set()
        title = norm_ws(node.get("t") or "")
        parent_id = node.get("parent_toc_node_id") or ""
        if parent_id and parent_id in by_id and parent_id not in seen:
            seen.add(parent_id)
            parent_path = path_of(by_id[parent_id], seen)
            result = f"{parent_path} > {title}" if parent_path else title
        else:
            result = title
        if nid:
            cache[nid] = result
        return result

    return {n.get("toc_node_id"): path_of(n) for n in nodes if n.get("toc_node_id")}


def load_titles():
    try:
        data = json.loads(BOOKS_JSON.read_text(encoding="utf-8"))
        books = data.get("books", data) if isinstance(data, dict) else data
        out = {}
        for b in books:
            bid = b.get("book_id") or (f"isbn_{b['isbn']}" if b.get("isbn") else None)
            if bid:
                out[bid] = {"title": b.get("title", ""), "isbn": b.get("isbn", "")}
        return out
    except Exception as e:
        print(f"  books.json 読込失敗（タイトル無しで継続）: {e}", flush=True)
        return {}


def main():
    titles = load_titles()
    files = sorted(f for f in os.listdir(TOC_DIR) if f.endswith(".json"))
    total = len(files)
    print(f"toc/ファイル数: {total}", flush=True)

    index = {"built_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "books": {}}
    n_nodes = n_dropped = n_empty = n_error = 0
    t0 = time.time()

    for i, fn in enumerate(files):
        try:
            nodes = json.loads((TOC_DIR / fn).read_text(encoding="utf-8"))
        except Exception:
            n_error += 1
            continue
        if not isinstance(nodes, list) or not nodes:
            n_empty += 1
            continue

        book_id = fn[:-5]  # strip .json
        paths = build_paths(nodes)
        compact = []
        for nd in nodes:
            if not is_clean(nd):
                n_dropped += 1
                continue
            t = norm_ws(nd.get("t") or "")
            p = nd.get("page_start", nd.get("p"))
            compact.append({
                "t": t,
                "d": nd.get("depth", nd.get("l", 1)),
                "p": p if isinstance(p, int) else None,
                "path": paths.get(nd.get("toc_node_id"), t),
                "path_id": nd.get("toc_path_id", ""),
                "src": nd.get("toc_source", "unknown"),
                "id": nd.get("toc_node_id", ""),
            })
        if not compact:
            n_empty += 1
            continue
        meta = titles.get(book_id, {})
        index["books"][book_id] = {
            "title": meta.get("title", ""),
            "isbn": meta.get("isbn", book_id.replace("isbn_", "")),
            "nodes": compact,
        }
        n_nodes += len(compact)
        if (i + 1) % 500 == 0:
            print(f"  {i+1}/{total} ({time.time()-t0:.0f}s)...", flush=True)

    elapsed = time.time() - t0
    print(f"インデックス構築: {len(index['books'])} 冊 / {n_nodes:,} ノード "
          f"(除去 {n_dropped:,} / 空 {n_empty} / エラー {n_error}) {elapsed:.1f}s", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_mb = OUT.stat().st_size / 1024 / 1024
    print(f"→ {OUT} ({size_mb:.2f} MB)", flush=True)


if __name__ == "__main__":
    main()
