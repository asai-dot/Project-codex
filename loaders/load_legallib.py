"""
load_legallib.py — legallib → biblio 取込ローダ（ドラフト v0.5）

Pattern: load_bencom.py 踏襲（asai-biblio-ingest）
Target:  Supabase biblio スキーマ（nixfjmwxmgugiiuqfuym）
Source:  ~/alo-ai/work/legallib_dl/*.json  (2,751 books + 422 journals)

取込順（FK順厳守）: authors → bib_records → bib_authors → bib_toc

フィールド名のゆらぎ対策（v0.5）:
  legallib 生JSON の実キー名が未確定なため、候補キーを優先順で総当たりする
  「多変種エイリアス＋自動検出」方式にした。実物1冊が来たら `--inspect` で
  検出結果を確認するだけでよい（盲目的な編集が不要）。
  下の *_KEYS が候補集合。実物確認後、必要なら候補の先頭を実キーに寄せる。

実行例:
  python load_legallib.py --inspect --limit 3      # 検出されたキー名を表示（DB触らない）
  python load_legallib.py --dry-run --limit 5      # 射影結果の件数だけ確認
  python load_legallib.py --source-dir ~/alo-ai/work/legallib_dl
  python load_legallib.py                          # 全件 upsert (冪等)
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

try:
    from supabase import create_client, Client
except ImportError:  # --inspect / --dry-run は supabase 無しでも動かせるように
    create_client = None  # type: ignore
    Client = Any  # type: ignore

# ─── 設定 ──────────────────────────────────────────────────────────────────────

DEFAULT_SOURCE_DIR = Path.home() / "alo-ai" / "work" / "legallib_dl"
SOURCE_NAME = "legal-library"
BATCH_SIZE = 500

# 候補キー（優先順）。実物JSONのキー名がどれであっても拾えるようにする。
# 生 legallib_dl と 正規化後フォーマットの両系統を許容。
# ※ 先頭は Phase 0（worker 実測 2026-06-08）で確定した実キー。
TITLE_KEYS = ("title", "book_title", "name", "書名")
ISBN_KEYS = ("isbn", "isbn13", "isbn_13", "ISBN")
AUTHOR_KEYS = ("authors_raw", "author", "authors", "creator", "creators", "著者", "responsibility")
PUBLISHER_KEYS = ("publisher", "publisher_name", "出版社", "出版者")
PUB_YEAR_KEYS = ("pub_year_raw", "pub_year", "year", "publication_year")
PUB_DATE_KEYS = ("publication_date", "published_at", "pub_date", "date", "出版年月日")
CONTENT_TYPE_KEYS = ("content_type", "type", "kind", "doc_type")
BOOK_ID_KEYS = ("book_id", "id", "legallib_book_id", "bookId")
SOURCE_URL_KEYS = ("url", "source_url", "book_url", "legallib_url")
TOC_KEYS = ("toc", "toc_nodes", "tableOfContents", "contents")

# TOC ノード内のキー候補
TOC_TEXT_KEYS = ("t", "text", "label", "title", "heading")
TOC_PAGE_KEYS = ("p", "page", "print_page", "pdf_page", "page_start")
TOC_LEVEL_KEYS = ("level", "l", "depth")
# 階層TOCの子ノード配列キー候補（詳細TOCを取りこぼさないため再帰する）
# Phase 0.1 worker 実測で実キー = "children" 確定（候補先頭）。
TOC_CHILD_KEYS = ("children", "child", "items", "nodes", "sub", "subnodes",
                  "subitems", "sections", "subsections", "childs")

# content_type → biblio.form_type マッピング（Phase 0.1 実測の4種）
CONTENT_TYPE_TO_FORM = {
    "book": "BOOK",
    "journal": "PERIODICAL",
    "periodical": "PERIODICAL",
    "magazine": "PERIODICAL",
    "pubcom": "PUBCOM",      # 出版社系コンテンツ（要 authority 層での性質確定）
    "material": "MATERIAL",  # 資料/書式系
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ─── キー解決ヘルパー ───────────────────────────────────────────────────────────

def pick(d: dict, keys: tuple[str, ...], default: Any = None) -> Any:
    """候補キーを優先順に探し、最初に非None/非空で見つかった値を返す。"""
    for k in keys:
        if k in d and d[k] not in (None, "", []):
            return d[k]
    return default


def pick_key(d: dict, keys: tuple[str, ...]) -> str | None:
    """どの候補キーが実際にヒットしたか（キー名）を返す。--inspect 用。"""
    for k in keys:
        if k in d and d[k] not in (None, "", []):
            return k
    return None



# ─── Supabase 接続 ─────────────────────────────────────────────────────────────

def get_client() -> Client:
    if create_client is None:
        raise SystemExit("supabase パッケージが無い。pip install supabase（--inspect/--dry-run は不要）")
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


def make_author_id(name: str, book_id: str, ordinal: int, mode: str = "per-occurrence") -> str:
    """著者IDを生成。
    mode='per-occurrence'（既定・GPT監査 INGEST_RESULT Finding 2 推奨）:
        出現ごとに一意 = biblio 内で別人を絶対に統合しない（誤統合0を構造保証）。
        normalized_key は別カラムに保持し、横断同定は authority 層で candidate→reviewed→promoted。
    mode='dedup'（オプトイン）:
        md5(normalized) で source-local 名寄せ。同姓同名を統合し得るので誤統合0 gate を要確認。
    """
    key = normalize_author_key(name)
    digest = hashlib.md5(key.encode()).hexdigest()
    if mode == "dedup":
        return f"LEGALLIB-AUTH:{digest}"
    return f"LEGALLIB-AUTH:{book_id}:{ordinal}:{digest[:8]}"


def make_source_hash(raw: dict) -> str:
    """raw JSON の sha256 ハッシュ（変更検知用）。"""
    serialized = json.dumps(raw, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


# ─── 著者名抽出 ──────────────────────────────────────────────────────────────────

def extract_authors(raw: dict) -> list[str]:
    """
    著者名のリストを返す。
    bencom 方針: 複合著者は分割しない（1著者エンティティとして保持）。
    str / list / [{name:...}] のいずれの形でも拾えるようにする。
    """
    author_val = pick(raw, AUTHOR_KEYS)
    if not author_val:
        return []
    if isinstance(author_val, list):
        out = []
        for a in author_val:
            if isinstance(a, dict):
                name = pick(a, ("name", "foaf:name", "full_name", "氏名"))
                if name:
                    out.append(str(name).strip())
            elif str(a).strip():
                out.append(str(a).strip())
        return out
    # 文字列形式: 単一著者として扱う（bencom 方針 = 分割しない）
    return [str(author_val).strip()] if str(author_val).strip() else []


# ─── pub_year 抽出 ─────────────────────────────────────────────────────────────

def extract_pub_year(raw: dict) -> int | None:
    """出版年を int で返す。pub_year 系 → publication_date 系（先頭4桁）の順で解決。"""
    val = pick(raw, PUB_YEAR_KEYS)
    if val is None:
        pub_date = pick(raw, PUB_DATE_KEYS)
        if pub_date:
            m = re.search(r"\d{4}", str(pub_date))
            if m:
                return int(m.group())
        return None
    try:
        return int(str(val)[:4])
    except (ValueError, TypeError):
        return None


# ─── TOC 抽出 ─────────────────────────────────────────────────────────────────

def _child_list(node: dict) -> list | None:
    """ノード配下の子ノード配列を返す（最初に見つかった候補キー）。無ければ None。"""
    for ck in TOC_CHILD_KEYS:
        v = node.get(ck)
        if isinstance(v, list) and v:
            return v
    return None


def _walk_toc(nodes: list, depth: int, out: list[dict]) -> None:
    """階層TOCを pre-order DFS でフラット化。
    詳細TOC（ネストした子見出し）を取りこぼさず全ノードを ordinal 連番で展開する。
    level は node の明示 level/depth を優先、無ければ再帰深さ（root直下=1）。"""
    for node in nodes:
        if not isinstance(node, dict):
            continue
        text = pick(node, TOC_TEXT_KEYS)

        explicit = pick(node, TOC_LEVEL_KEYS)
        try:
            level = int(explicit) if explicit is not None else depth
        except (ValueError, TypeError):
            level = depth

        if text:  # 見出しテキストを持つノードのみ行化（ordinal は行に対して連番）
            page = pick(node, TOC_PAGE_KEYS)
            try:
                page = int(page) if page is not None else None
            except (ValueError, TypeError):
                page = None
            out.append({
                "ordinal": len(out),  # 0始まり連番（locator。anchorではない＝v0.5 §B）
                "level": level,
                "page": page,
                "text": str(text),
            })

        children = _child_list(node)
        if children:
            _walk_toc(children, level + 1, out)


def extract_toc_nodes(raw: dict) -> list[dict]:
    """
    legallib raw JSON から bib_toc 行リストを生成。
    bib_toc はフラット: (bib_id, ordinal[0始まり], level, page, text)。親/toc_node_id は持たない。
    **階層TOCは再帰展開**（詳細TOCを取りこぼさない）。フラットTOCもそのまま動く。
    生 legallib_dl と正規化後フォーマットの両系統のキー名を許容する。
    """
    toc = pick(raw, TOC_KEYS, default=[])
    if not isinstance(toc, list) or not toc:
        return []
    out: list[dict] = []
    _walk_toc(toc, 1, out)
    return out


# ─── bib_record 構築 ───────────────────────────────────────────────────────────

def resolve_book_id(path: Path, raw: dict) -> str:
    """book_id を解決。raw 内の id 系キー優先、無ければファイル名 stem。"""
    return str(pick(raw, BOOK_ID_KEYS, default=path.stem))


def build_bib_record(book_id: str, raw: dict, path: Path) -> dict:
    isbn = pick(raw, ISBN_KEYS)
    title = pick(raw, TITLE_KEYS, default="")
    responsibility = pick(raw, AUTHOR_KEYS)
    if isinstance(responsibility, (list, dict)):
        responsibility = "; ".join(extract_authors(raw)) or None

    # form_type: legallib content_type を忠実にマップ（Phase 0.1 実測で4種を確認）
    #   book→BOOK / journal→PERIODICAL / pubcom→PUBCOM / material→MATERIAL
    #   未知の content_type は大文字化して保全（raw にも content_type を保持）。
    content_type = str(pick(raw, CONTENT_TYPE_KEYS, default="book")).lower()
    form_type = CONTENT_TYPE_TO_FORM.get(content_type, content_type.upper() or "BOOK")

    source_url = pick(raw, SOURCE_URL_KEYS, default=f"https://legal-library.jp/books/{book_id}")

    return {
        "bib_id": make_bib_id(book_id),
        "title": str(title),
        "publisher": pick(raw, PUBLISHER_KEYS),
        "pub_year": extract_pub_year(raw),
        "isbn": isbn,
        "responsibility": responsibility,
        "source": SOURCE_NAME,
        "form_type": form_type,
        "raw": raw,
        "source_hash": make_source_hash(raw),
        "source_url": source_url,
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


# ─── inspect（実物JSONのキー名を検出して表示・DB不要） ────────────────────────────

def inspect(source_dir: Path, limit: int | None) -> None:
    """実物JSON数件から、どの候補キーが実際にヒットするかを表示する。
    実物が来たらまずこれを流し、検出が期待どおりか確認する（盲目編集を回避）。"""
    json_files = sorted(source_dir.glob("*.json"))[: (limit or 3)]
    if not json_files:
        raise SystemExit(f"JSON が無い: {source_dir}")

    for path in json_files:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
        print(f"\n=== {path.name} ===")
        print(f"  top-level keys: {sorted(raw.keys()) if isinstance(raw, dict) else type(raw)}")
        if not isinstance(raw, dict):
            print("  (配列ルート＝TOCのみのファイルの可能性。生 legallib_dl ではないかも)")
            continue
        print(f"  title       <- {pick_key(raw, TITLE_KEYS)!r}  = {str(pick(raw, TITLE_KEYS))[:60]!r}")
        print(f"  book_id     <- {pick_key(raw, BOOK_ID_KEYS)!r} (無ければ stem={path.stem!r})")
        print(f"  isbn        <- {pick_key(raw, ISBN_KEYS)!r}  = {pick(raw, ISBN_KEYS)!r}")
        print(f"  author      <- {pick_key(raw, AUTHOR_KEYS)!r} -> {extract_authors(raw)[:3]}")
        print(f"  publisher   <- {pick_key(raw, PUBLISHER_KEYS)!r}  = {pick(raw, PUBLISHER_KEYS)!r}")
        print(f"  pub_year    <- year:{pick_key(raw, PUB_YEAR_KEYS)!r} date:{pick_key(raw, PUB_DATE_KEYS)!r} -> {extract_pub_year(raw)}")
        print(f"  content_type<- {pick_key(raw, CONTENT_TYPE_KEYS)!r}  = {pick(raw, CONTENT_TYPE_KEYS)!r}")
        toc = pick(raw, TOC_KEYS, default=[])
        print(f"  toc key     <- {pick_key(raw, TOC_KEYS)!r}  len={len(toc) if isinstance(toc, list) else 'N/A'}")
        if isinstance(toc, list) and toc and isinstance(toc[0], dict):
            n = toc[0]
            print(f"    node keys : {sorted(n.keys())}")
            print(f"    text <- {pick_key(n, TOC_TEXT_KEYS)!r} / page <- {pick_key(n, TOC_PAGE_KEYS)!r} / level <- {pick_key(n, TOC_LEVEL_KEYS)!r}")
            # 階層TOCの暴露: どのキーが list 値（=子ノード配列候補）か、既知候補に当たるか
            list_keys = [k for k, v in n.items() if isinstance(v, list) and v and isinstance(v[0], dict)]
            print(f"    child(list of dict) keys on node0 : {list_keys}  / 既知候補ヒット: {pick_key(n, TOC_CHILD_KEYS)!r}")
        nodes = extract_toc_nodes(raw)
        levels = sorted({r['level'] for r in nodes})
        top_len = len(toc) if isinstance(toc, list) else 0
        print(f"  -> extract_toc_nodes: {len(nodes)} 行 (top-level配列={top_len}) / levels={levels}")
        print(f"     例[0]: {nodes[0] if nodes else None}")
        if len(nodes) > 1:
            print(f"     例[深]: {next((r for r in nodes if r['level'] > 1), '（level>1 が出ていない＝ネスト未捕捉の疑い。上の child keys を確認）')}")


# ─── メイン処理 ───────────────────────────────────────────────────────────────

def load(source_dir: Path, dry_run: bool, limit: int | None, book_only: bool,
         author_id_mode: str = "per-occurrence") -> None:
    client = None if dry_run else get_client()

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

        if not isinstance(raw, dict):
            log.warning(f"skip {path.name}: ルートが dict でない（TOCのみファイル?）")
            skipped += 1
            continue

        content_type = str(pick(raw, CONTENT_TYPE_KEYS, default="book")).lower()
        if book_only and content_type not in ("book", ""):
            continue

        book_id = resolve_book_id(path, raw)

        # bib_record
        bib_rec = build_bib_record(book_id, raw, path)
        all_bib_records.append(bib_rec)

        # authors + bib_authors（ordinal は著者順を反映＝旧来 0 固定のバグを修正）
        for idx, author_name in enumerate(extract_authors(raw)):
            author_id = make_author_id(author_name, book_id, idx, mode=author_id_mode)
            if author_id not in all_authors:
                all_authors[author_id] = {
                    "author_id": author_id,
                    "name": author_name,
                    "source": SOURCE_NAME,
                    "normalized_key": normalize_author_key(author_name),
                }
            all_bib_authors.append({
                "bib_id": bib_rec["bib_id"],
                "author_id": author_id,
                "role": "creator",
                "ordinal": idx,
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
    parser.add_argument("--inspect", action="store_true", help="実物JSONのキー名検出を表示（DB不要）")
    parser.add_argument("--dry-run", action="store_true", help="DB 書き込みなし")
    parser.add_argument("--limit", type=int, default=None, help="処理ファイル数上限")
    parser.add_argument(
        "--book-only", action="store_true", help="content_type==book のみ処理（雑誌除外）"
    )
    parser.add_argument(
        "--author-id-mode", choices=("per-occurrence", "dedup"), default="per-occurrence",
        help="著者ID戦略。per-occurrence=誤統合0を構造保証（既定）/ dedup=md5名寄せ（要誤統合確認）",
    )
    args = parser.parse_args()

    if not args.source_dir.exists():
        raise SystemExit(f"source-dir が存在しません: {args.source_dir}")

    if args.inspect:
        inspect(source_dir=args.source_dir, limit=args.limit)
        return

    load(
        source_dir=args.source_dir,
        dry_run=args.dry_run,
        limit=args.limit,
        book_only=args.book_only,
        author_id_mode=args.author_id_mode,
    )


if __name__ == "__main__":
    main()
