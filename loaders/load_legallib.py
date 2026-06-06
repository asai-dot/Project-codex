"""
load_legallib.py — legallib → biblio 取込ローダ（ドラフト）

Pattern: load_bencom.py 踏襲（asai-biblio-ingest）
Target:  Supabase biblio スキーマ（nixfjmwxmgugiiuqfuym）
Source:  ~/alo-ai/work/legallib_dl/*.json  (2,751 books + 422 journals)

取込順（FK順厳守）: authors → bib_records → bib_authors → bib_toc

TODO (フィールド名確認 — 実物 1 冊の JSON で確認後に修正):
  FIELD_TITLE       = "title"         # ← article parser instruction で確認済
  FIELD_ISBN        = "isbn"          # ← 要確認
  FIELD_AUTHOR      = "author"        # ← 要確認 (単数/複数/リスト?)
  FIELD_PUBLISHER   = "publisher"     # ← 要確認
  FIELD_PUB_YEAR    = "pub_year"      # ← 要確認 (int? or "publication_date"?)
  FIELD_CONTENT_TYPE = "content_type" # ← article parser instruction で確認済
  TOC_TEXT          = "t"             # ← v0.4 plan 記載。要確認 ("t" or "label"?)
  TOC_PAGE          = "p"             # ← 要確認 ("p" or "print_page"?)
  TOC_LEVEL         = "level"         # ← article parser instruction で確認済

実行例:
  python load_legallib.py --dry-run --limit 5
  python load_legallib.py --source-dir ~/alo-ai/work/legallib_dl
  python load_legallib.py  # 全件 upsert (冪等)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

from supabase import create_client, Client

# ─── 設定 ──────────────────────────────────────────────────────────────────────

DEFAULT_SOURCE_DIR = Path.home() / "alo-ai" / "work" / "legallib_dl"
SOURCE_NAME = "legal-library"
BATCH_SIZE = 500

# TODO: 実物 JSON で確認後に修正
FIELD_TITLE = "title"
FIELD_ISBN = "isbn"
FIELD_AUTHOR = "author"        # 複数著者の場合リスト or "/"区切り文字列の可能性あり
FIELD_PUBLISHER = "publisher"
FIELD_PUB_YEAR = "pub_year"    # int or "publication_date" "YYYY-MM-DD" 形式の可能性あり
FIELD_CONTENT_TYPE = "content_type"  # "book" or "journal"
TOC_TEXT = "t"       # toc node のテキストフィールド
TOC_PAGE = "p"       # toc node のページ番号フィールド (int or null)
TOC_LEVEL = "level"  # toc node の階層レベル (int)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ─── Supabase 接続 ─────────────────────────────────────────────────────────────

def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    schema = os.environ.get("SUPABASE_SCHEMA", "biblio")
    client = create_client(url, key)
    client.schema = schema
    return client


# ─── ID 生成（決定論的・再実行で同一） ─────────────────────────────────────────

def make_bib_id(book_id: str) -> str:
    return f"LEGALLIB:{book_id}"


def normalize_author_key(name: str) -> str:
    """著者名を正規化してdedup キーを生成。"""
    normalized = unicodedata.normalize("NFKC", name).strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def make_author_id(name: str) -> str:
    key = normalize_author_key(name)
    digest = hashlib.md5(key.encode()).hexdigest()
    return f"LEGALLIB-AUTH:{digest}"


def make_source_hash(raw: dict) -> str:
    """raw JSON の sha256 ハッシュ（変更検知用）。"""
    serialized = json.dumps(raw, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


# ─── 著者名抽出 ──────────────────────────────────────────────────────────────────

def extract_authors(raw: dict) -> list[str]:
    """
    著者名のリストを返す。
    bencom 方針: 複合著者は分割しない（1著者エンティティとして保持）。
    TODO: legallib の author フィールドが文字列か配列かによって調整が必要。
    """
    author_val = raw.get(FIELD_AUTHOR, "")
    if not author_val:
        return []
    if isinstance(author_val, list):
        # リスト形式の場合: そのまま使用
        return [str(a).strip() for a in author_val if str(a).strip()]
    # 文字列形式: 単一著者として扱う（bencom 方針 = 分割しない）
    return [str(author_val).strip()] if str(author_val).strip() else []


# ─── pub_year 抽出 ─────────────────────────────────────────────────────────────

def extract_pub_year(raw: dict) -> int | None:
    """出版年を int で返す。"""
    val = raw.get(FIELD_PUB_YEAR)
    if val is None:
        # TODO: "publication_date" フィールドがある場合はこちらを使う
        pub_date = raw.get("publication_date", "")
        if pub_date:
            try:
                return int(str(pub_date)[:4])
            except (ValueError, TypeError):
                pass
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


# ─── TOC 抽出 ─────────────────────────────────────────────────────────────────

def extract_toc_nodes(raw: dict) -> list[dict]:
    """
    legallib raw JSON から bib_toc 行リストを生成。
    bib_toc はフラット: (bib_id, ordinal[0始まり], level, page, text)
    親/toc_node_id は持たない。
    """
    toc = raw.get("toc", [])
    if not toc:
        return []

    rows = []
    for i, node in enumerate(toc):
        text = node.get(TOC_TEXT, "")
        if not text:
            continue
        level = node.get(TOC_LEVEL)
        # TODO: "l" フィールドとの優先順位確認。現在は level を優先。
        if level is None:
            level = node.get("l")
        if level is None:
            level = 1

        page = node.get(TOC_PAGE)
        # TODO: "print_page" or "pdf_page" フィールドの確認
        if page is None:
            page = node.get("print_page") or node.get("pdf_page")

        rows.append({
            "ordinal": i,       # 0始まり・配列位置
            "level": int(level),
            "page": int(page) if page is not None else None,
            "text": str(text),
        })
    return rows


# ─── bib_record 構築 ───────────────────────────────────────────────────────────

def build_bib_record(book_id: str, raw: dict) -> dict:
    isbn = raw.get(FIELD_ISBN) or None
    title = raw.get(FIELD_TITLE, "")
    pub_year = extract_pub_year(raw)

    # form_type: 書籍は BOOK 統一（PERIODICAL は次スコープ）
    content_type = raw.get(FIELD_CONTENT_TYPE, "book")
    form_type = "PERIODICAL" if content_type == "journal" else "BOOK"

    return {
        "bib_id": make_bib_id(book_id),
        "title": title,
        "publisher": raw.get(FIELD_PUBLISHER) or None,
        "pub_year": pub_year,
        "isbn": isbn,
        "responsibility": raw.get(FIELD_AUTHOR) or None,
        "source": SOURCE_NAME,
        "form_type": form_type,
        "raw": raw,
        "source_hash": make_source_hash(raw),
        # TODO: legallib の書籍 URL フォーマット確認
        "source_url": f"https://legal-library.jp/books/{book_id}",
    }


# ─── upsert ヘルパー ───────────────────────────────────────────────────────────

def batch_upsert(client: Client, table: str, rows: list[dict], on_conflict: str, dry_run: bool) -> int:
    if not rows:
        return 0
    if dry_run:
        log.info(f"[dry-run] {table}: {len(rows)} rows (skipped)")
        return len(rows)
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        client.table(table).upsert(batch, on_conflict=on_conflict).execute()
    return len(rows)


# ─── メイン処理 ───────────────────────────────────────────────────────────────

def load(source_dir: Path, dry_run: bool, limit: int | None, book_only: bool) -> None:
    client = get_client()

    json_files = sorted(source_dir.glob("*.json"))
    if limit:
        json_files = json_files[:limit]

    all_authors: dict[str, dict] = {}    # author_id → row
    all_bib_records: list[dict] = []
    all_bib_authors: list[dict] = []
    all_bib_toc: list[dict] = []

    skipped = 0
    for path in json_files:
        try:
            with path.open(encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            log.warning(f"skip {path.name}: {e}")
            skipped += 1
            continue

        content_type = raw.get(FIELD_CONTENT_TYPE, "book")
        if book_only and content_type != "book":
            continue

        book_id = path.stem  # ファイル名（拡張子除く）= legallib 内部 book_id

        # bib_record
        bib_rec = build_bib_record(book_id, raw)
        all_bib_records.append(bib_rec)

        # authors + bib_authors
        for author_name in extract_authors(raw):
            author_id = make_author_id(author_name)
            if author_id not in all_authors:
                norm_key = normalize_author_key(author_name)
                all_authors[author_id] = {
                    "author_id": author_id,
                    "name": author_name,
                    "source": SOURCE_NAME,
                    "normalized_key": norm_key,
                }
            all_bib_authors.append({
                "bib_id": bib_rec["bib_id"],
                "author_id": author_id,
                "role": "creator",
                "ordinal": 0,
            })

        # bib_toc
        bib_id = bib_rec["bib_id"]
        for node in extract_toc_nodes(raw):
            all_bib_toc.append({
                "bib_id": bib_id,
                "ordinal": node["ordinal"],
                "level": node["level"],
                "page": node["page"],
                "text": node["text"],
            })

    log.info(f"Loaded {len(json_files) - skipped} files ({skipped} skipped)")
    log.info(f"  authors:     {len(all_authors)}")
    log.info(f"  bib_records: {len(all_bib_records)}")
    log.info(f"  bib_authors: {len(all_bib_authors)}")
    log.info(f"  bib_toc:     {len(all_bib_toc)}")

    # FK 順で upsert
    batch_upsert(client, "authors", list(all_authors.values()), "author_id", dry_run)
    batch_upsert(client, "bib_records", all_bib_records, "bib_id", dry_run)
    batch_upsert(client, "bib_authors", all_bib_authors, "bib_id,author_id,role,ordinal", dry_run)
    batch_upsert(client, "bib_toc", all_bib_toc, "bib_id,ordinal", dry_run)

    log.info("Done.")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="legallib → biblio loader")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help=f"legallib JSON フォルダ (default: {DEFAULT_SOURCE_DIR})",
    )
    parser.add_argument("--dry-run", action="store_true", help="DB 書き込みなし")
    parser.add_argument("--limit", type=int, default=None, help="処理ファイル数上限")
    parser.add_argument(
        "--book-only", action="store_true", help="content_type==book のみ処理（雑誌除外）"
    )
    args = parser.parse_args()

    if not args.source_dir.exists():
        raise SystemExit(f"source-dir が存在しません: {args.source_dir}")

    load(
        source_dir=args.source_dir,
        dry_run=args.dry_run,
        limit=args.limit,
        book_only=args.book_only,
    )


if __name__ == "__main__":
    main()
