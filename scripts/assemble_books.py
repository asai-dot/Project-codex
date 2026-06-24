"""assemble_books — concordance_pipeline 用の複数ソース book 入力を実データから組み立てる。

legallibjoin v0.3.1 Phase B の入力アセンブラ (report-only / stdlib のみ / 決定的)。
concordance_pipeline.py が要求する形:
    各 book = {isbn, title, source_meta:{src:{...bib+page_basis}}, sources:{src:[flat nodes]}}
を、実データ
    - legallib 詳細TOC (~/.../legallib_dl/*.json)   … 唯一の node 源
    - resolver_decisions.normalized.jsonl            … legallib_book_id -> ISBN
    - canonical books.json                           … bib (頁数欄なし・node なし)
から生成する。

【既知の制約 (Phase B 実測 2026-06-15)】
  ローカルに **node を持つ源は legallib 1 つだけ** (canonical は bib のみ・toc array=0)。
  concordance は title が 2 源以上で一致したとき matched になるため、単一 node 源では
  全ノードが orphan になり、cross-source conflict も立たない (= 退化)。
  意味のある evidence ④⑤ には **第2の node 源** (mainline bib_toc / lionbolt / bencom 等、
  DD-TOCADOPT-001 が統合中の corpus) が要る。本アセンブラは `--extra-sources` で
  追加 node 源を受け取れる前方互換設計にしてある (来たら 1 コマンドで合流)。

本番書き込みは一切しない。--out で指定した JSON のみ書く。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase0_inventory import norm_isbn, parse_year  # noqa: E402  (同じ正規化を再利用)

_RESERVED = {"resolver_decisions.json", "resolver_decisions.normalized.json"}


def flatten_toc(toc: list, depth: int = 1) -> list[dict]:
    """legallib のネスト toc を DFS で平坦化 (children は normalize_source_nodes が見ないため必須)。

    各ノードは label/level/pdf_page/print_page を保持。order は原本順。
    """
    out: list[dict] = []
    for n in toc or []:
        if not isinstance(n, dict):
            continue
        out.append({
            "label": n.get("label") or "",
            "level": n.get("level") or depth,
            "pdf_page": n.get("pdf_page"),
            "print_page": n.get("print_page"),
            "kind": n.get("kind"),
        })
        if n.get("children"):
            out.extend(flatten_toc(n["children"], depth + 1))
    return out


def load_resolver(path: Path) -> dict[str, dict]:
    """legallib_book_id -> resolver 判定 (canonical 一致 bucket のみ採用)。"""
    out: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        # canonical に紐づくのは auto_accept / human_review。defer_new は create 候補で接合対象外。
        if r.get("bucket") not in ("auto_accept", "human_review"):
            continue
        bid = str(r.get("legallib_book_id"))
        isbn = norm_isbn(r.get("isbn"))
        if bid and isbn:
            out[bid] = {**r, "isbn": isbn}
    return out


def load_canonical(path: Path) -> dict[str, dict]:
    """ISBN -> canonical bib (頁数欄なし)。"""
    idx: dict[str, dict] = {}
    for b in json.loads(path.read_text(encoding="utf-8")):
        isbn = norm_isbn(b.get("isbn"))
        if isbn:
            idx.setdefault(isbn, {
                "isbn": isbn,
                "title": b.get("title") or "",
                "publisher": b.get("publisher") or "",
                "year": parse_year(b.get("date")),
                "edition": b.get("edition") or "",
                "volume": b.get("volume") or "",
                "page_count": None,
                "page_basis": "print_page",
                "provenance_origin": "canonical_bib",
            })
    return idx


def load_extra_sources(path: Path) -> dict[str, dict[str, list]]:
    """前方互換: 追加 node 源を受け取る。

    期待形 (どちらでも可):
      *.json = {isbn: {"source": <name>, "nodes": [...], "meta": {...}}}  または
               {isbn: {<src>: {"nodes": [...], "meta": {...}}, ...}}
    返り値: isbn -> {src: {"nodes": [...], "meta": {...}}}
    """
    merged: dict[str, dict[str, dict]] = {}
    if not path:
        return merged
    files = [path] if path.is_file() else sorted(path.glob("*.json"))
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        for isbn_raw, payload in data.items():
            isbn = norm_isbn(isbn_raw)
            if not isbn:
                continue
            bucket = merged.setdefault(isbn, {})
            if isinstance(payload, dict) and "nodes" in payload:
                src = payload.get("source") or f.stem
                bucket[src] = {"nodes": payload["nodes"], "meta": payload.get("meta", {})}
            elif isinstance(payload, dict):
                for src, sp in payload.items():
                    if isinstance(sp, dict):
                        bucket[src] = {"nodes": sp.get("nodes", []), "meta": sp.get("meta", {})}
    return merged


def assemble(legallib_dir: Path, resolver: dict[str, dict], canonical: dict[str, dict],
             extra: dict[str, dict], only_isbns: set[str] | None) -> tuple[list[dict], dict]:
    files = sorted(f for f in legallib_dir.glob("*.json") if f.name not in _RESERVED)
    books: dict[str, dict] = {}
    stats = {"legallib_files": len(files), "matched_isbn": 0, "skipped_no_isbn": 0,
             "skipped_filter": 0, "with_2plus_node_sources": 0}

    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        bid = str(d.get("book_id"))
        rdec = resolver.get(bid)
        if not rdec:
            stats["skipped_no_isbn"] += 1
            continue
        isbn = rdec["isbn"]
        if only_isbns is not None and isbn not in only_isbns:
            stats["skipped_filter"] += 1
            continue

        nodes = flatten_toc(d.get("toc") or [])
        ll_meta = {
            "isbn": isbn,
            "title": d.get("title") or "",
            "publisher": d.get("publisher") or "",
            "year": parse_year(d.get("pub_year_raw")),
            "edition": d.get("edition_label") or "",
            "volume": "",
            "page_count": d.get("total_pages"),
            "page_basis": "print_page",  # legallib は pdf/print 両持ち (offset 本単位単一)
            "extraction_method": "llm",
            "extraction_confidence": "medium",
            "coverage": "full_toc" if nodes else "unknown",
            "provenance_origin": "legallib_extraction",
        }
        book = {
            "isbn": isbn,
            "title": d.get("title") or "",
            "resolver_bucket": rdec.get("bucket"),
            "resolver_confidence": rdec.get("confidence"),
            "source_meta": {"legallib": ll_meta},
            "sources": {"legallib": nodes},
        }
        # canonical bib を edition_identity 用に source_meta へ (node は無し)。
        if isbn in canonical:
            book["source_meta"]["canonical"] = canonical[isbn]

        # 前方互換: 追加 node 源を合流。
        for src, sp in (extra.get(isbn) or {}).items():
            book["sources"][src] = sp.get("nodes", [])
            meta = dict(sp.get("meta") or {})
            meta.setdefault("isbn", isbn)
            meta.setdefault("provenance_origin", src)
            book["source_meta"][src] = meta

        node_sources = sum(1 for v in book["sources"].values() if v)
        if node_sources >= 2:
            stats["with_2plus_node_sources"] += 1
        stats["matched_isbn"] += 1
        books[isbn] = book

    return list(books.values()), stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="concordance_pipeline 用の実データ book 入力アセンブラ (report-only)")
    ap.add_argument("--legallib-dir", required=True)
    ap.add_argument("--resolver", required=True)
    ap.add_argument("--canonical", required=True)
    ap.add_argument("--extra-sources", help="追加 node 源 (file or dir of *.json)。前方互換フック。")
    ap.add_argument("--only-isbns", help="ISBN ホワイトリスト (1行1ISBN) で対象を絞る")
    ap.add_argument("--out", required=True, help="出力 books JSON")
    args = ap.parse_args(argv)

    only = None
    if args.only_isbns:
        only = {norm_isbn(x) for x in Path(args.only_isbns).read_text(encoding="utf-8").splitlines() if x.strip()}
        only.discard("")

    resolver = load_resolver(Path(args.resolver))
    canonical = load_canonical(Path(args.canonical))
    extra = load_extra_sources(Path(args.extra_sources)) if args.extra_sources else {}
    books, stats = assemble(Path(args.legallib_dir), resolver, canonical, extra, only)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(books, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"out": str(out), "books": len(books), **stats}, ensure_ascii=False, sort_keys=True))
    if stats["with_2plus_node_sources"] == 0:
        print("WARN: 全 book が単一 node 源 (legallib のみ) → concordance は退化 (matched=0)。"
              " 意味のある evidence には --extra-sources で第2 node 源が必要。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
