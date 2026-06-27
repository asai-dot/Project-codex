#!/usr/bin/env python3
"""load_legallib.py — legal-library カタログ (legallib_toc_full.jsonl) を
Supabase biblio.bib_records / biblio.bib_toc / biblio.library_sources へ投入する
ローダの SCAFFOLD（dry-run 既定・DB非接触）。

設計ポリシー（Phase 1 / NEXT_STEPS_20260626 §Phase1, DD-LIONBOLT-INGEST 派生）:
  - legal-library 行は source='legal-library' として独立に着地。既存行は一切 UPDATE しない。
  - ISBN は基本的に無い（legallib の性質）。bib_id は内部 book_id で mint。
  - dedup（既存 fingerprint との一致）は **レポートのみ**。
    auto-merge / biblio_item mint はしない（DD-LITID HOLD）。
  - 官報・パブコメ系（publisher 空）は form_type で分離タグ → 書籍ユニーク数を水増ししない。
  - 冪等: bib_id = 'legallib:'+book_id, source_hash = sha256(record) で ON CONFLICT 更新。

状態: SCAFFOLD（PR scaffold; 投入は (a)legallib本投入 (b)Phase 2 DDDESIGN 監査PASS の
後）。本ファイルは dry-run のみで apply 経路は確認用スタブ。

使い方:
  # dry-run（既定。DB に触れない。正規化・統計・dedup レポート・TSV を出力）
  python load_legallib.py --input ~/alo-ai/work/legallib_dl/legallib_toc_full.jsonl

  # 既存 fingerprint レポート（既存 33,170冊との title+publisher+year 突合）
  python load_legallib.py --input legallib_toc_full.jsonl \\
      --existing-fingerprints existing_fp.tsv

  # 実投入（owner ratify 後のみ。READ_ONLY 解除済み前提）
  python load_legallib.py --input legallib_toc_full.jsonl --apply \\
      --i-understand-this-writes-prod --dsn "$SUPABASE_DSN"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

SOURCE = "legal-library"
LOADER_VERSION = "legallib_loader/0.1-scaffold"
ISBN13_RE = re.compile(r"^[0-9]{13}$")
PUB_YEAR_RE = re.compile(r"(\d{4})")

LIBRARY_SOURCE_ROW = {
    "id": "legal-library",
    "label": "Legal Library 法律ライブラリ",
    "kind": "commercial_catalog",
    "tier": "subscription",
    "cost": None,
    "page_strategy": "print_page",
    "needs_auth": True,
    "url_template": None,
    "book_url_template": None,
    "note": ("法律ライブラリ由来。書誌+構造化目次のみ、本文不取得。"
             "取得2026-06 (Mac経由)。external_share=false"),
}


def canonical_hash(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def norm_str(s: str | None) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFKC", s).strip()


def norm_key(s: str | None) -> str:
    """fingerprint用：lower + 全角/半角統一 + 空白/句読点除去（FP v1と同じ）"""
    s = norm_str(s).lower()
    return re.sub(r"[\s　・〔〕（）「」『』【】、。，．…ー－‐–—〜～\-_/\\.,:;]", "", s)


def parse_pub_year(rec: dict) -> int | None:
    raw = rec.get("pub_year_raw") or rec.get("pub_year") or rec.get("pub_date") or ""
    m = PUB_YEAR_RE.search(str(raw))
    if m:
        y = int(m.group(1))
        if 1800 <= y <= 2100:
            return y
    return None


def norm_isbn(rec: dict) -> str | None:
    """legallib は基本 ISBN 無し。ある場合のみ拾う。"""
    for k in ("isbn13", "isbn"):
        v = (rec.get(k) or "")
        v = re.sub(r"[-\s]", "", str(v))
        if ISBN13_RE.match(v):
            return v
    return None


def mint_bib_id(rec: dict, isbn: str | None) -> str | None:
    bid = (rec.get("book_id") or "").strip()
    if bid:
        return f"legallib:{bid}"
    if isbn:
        return f"legallib:isbn:{isbn}"
    return None


def detect_form_type(rec: dict) -> str:
    """官報・パブコメ等を分離。書籍ユニーク数を水増ししないため。"""
    title = norm_str(rec.get("title"))
    publisher = norm_str(rec.get("publisher"))
    if not publisher and any(k in title for k in ("官報", "パブリックコメント", "意見公募")):
        if "官報" in title:
            return "gazette"
        return "publiccomment"
    if not publisher:
        return "uncategorized"
    return "monograph"


def to_bib_record(rec: dict) -> dict | None:
    isbn = norm_isbn(rec)
    bib_id = mint_bib_id(rec, isbn)
    title = norm_str(rec.get("title"))
    if not bib_id or not title:
        return None
    return {
        "bib_id": bib_id,
        "title": title,
        "responsibility": norm_str(rec.get("authors_raw") or rec.get("author")) or None,
        "publisher": norm_str(rec.get("publisher")) or None,
        "pub_year": parse_pub_year(rec),
        "physical": None,  # legallib はページ数列を持たないことが多い。実装時に確認
        "isbn": isbn,
        "note": None,
        "source": SOURCE,
        "source_url": None,
        "source_hash": canonical_hash(rec),
        "form_type": detect_form_type(rec),
        "raw": rec,
    }


def to_toc_rows(rec: dict, bib_id: str) -> list[dict]:
    """legallib の目次構造は level ツリー（toc[] / toc_node_count）。

    Phase 2 のシルバー射影は ordinal+level だけで親決定できるよう、ここでは
    深さ優先で flatten して (ordinal, level, page, text) のフラット行を返す。
    """
    items = rec.get("toc") or []
    if not isinstance(items, list):
        return []
    out, ordinal = [], 0

    def walk(node, level):
        nonlocal ordinal
        if not isinstance(node, dict):
            return
        text = norm_str(node.get("text"))
        page = node.get("page") or node.get("startHeadlinePage")
        if text:
            out.append({
                "bib_id": bib_id,
                "ordinal": ordinal,
                "level": level,
                "page": page if isinstance(page, int) else None,
                "text": text,
            })
            ordinal += 1
        children = node.get("children") or []
        if isinstance(children, list):
            for c in children:
                walk(c, level + 1)

    for top in items:
        walk(top, 0)
    return out


def fingerprint_v1(title: str | None, publisher: str | None,
                   pub_year: int | None) -> str:
    """既存FP v1 と同形（title_norm | publisher_norm | year）。"""
    return f"{norm_key(title)}|{norm_key(publisher)}|{pub_year or ''}"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, type=Path,
                   help="legallib_toc_full.jsonl (Mac側)")
    p.add_argument("--out", type=Path, default=Path("artifacts/legallib_ingest_dryrun"),
                   help="dry-run 成果物の出力先")
    p.add_argument("--existing-fingerprints", type=Path,
                   help="既存FP TSV (title_norm\\tpub_norm\\tyear\\tsource\\tbib_id)")
    p.add_argument("--apply", action="store_true",
                   help="DB に投入する（owner ratify 後のみ）")
    p.add_argument("--i-understand-this-writes-prod", action="store_true")
    p.add_argument("--dsn", default=None)
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()

    if args.apply and not args.i_understand_this_writes_prod:
        print("--apply requires --i-understand-this-writes-prod", file=sys.stderr)
        return 2
    if args.apply:
        print("NOTE: --apply path is a SCAFFOLD stub. Phase 1 ratify required before "
              "wiring this to psycopg2.", file=sys.stderr)
        # 実装メモ: lionbolt 同様 \copy で staging → biblio.fn_legallib_upsert() を呼ぶ。
        # マイグレーション migration_legallib.sql は未作成（Phase 1 着手時に追加）。
        return 3

    args.out.mkdir(parents=True, exist_ok=True)
    bib_rows: list[dict] = []
    toc_rows: list[dict] = []
    form_counter: dict[str, int] = {}
    skipped = 0

    with args.input.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if args.limit and i >= args.limit:
                break
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            br = to_bib_record(rec)
            if not br:
                skipped += 1
                continue
            bib_rows.append(br)
            form_counter[br["form_type"]] = form_counter.get(br["form_type"], 0) + 1
            toc_rows.extend(to_toc_rows(rec, br["bib_id"]))

    # サマリ
    summary = {
        "loader_version": LOADER_VERSION,
        "input": str(args.input),
        "bib_rows": len(bib_rows),
        "toc_rows": len(toc_rows),
        "skipped": skipped,
        "form_type_counts": form_counter,
        "isbn_present": sum(1 for r in bib_rows if r["isbn"]),
        "publisher_present": sum(1 for r in bib_rows if r["publisher"]),
        "pub_year_present": sum(1 for r in bib_rows if r["pub_year"]),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (args.out / "SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # FP突合（既存FPファイルがあれば）
    if args.existing_fingerprints and args.existing_fingerprints.exists():
        existing: dict[str, list[tuple[str, str]]] = {}
        for line in args.existing_fingerprints.open(encoding="utf-8"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            tnorm, pnorm, year, src, bid = parts[:5]
            fp = f"{tnorm}|{pnorm}|{year}"
            existing.setdefault(fp, []).append((src, bid))

        hits, uniq = [], 0
        for r in bib_rows:
            if r["form_type"] != "monograph":
                continue  # 官報・パブコメは突合対象外
            fp = fingerprint_v1(r["title"], r["publisher"], r["pub_year"])
            matches = existing.get(fp, [])
            if matches:
                hits.append({"bib_id": r["bib_id"], "fp": fp, "matches": matches})
            else:
                uniq += 1
        dedup_report = {
            "monograph_total": sum(1 for r in bib_rows if r["form_type"] == "monograph"),
            "monograph_unique_against_existing": uniq,
            "monograph_collisions": len(hits),
            "examples": hits[:20],
        }
        (args.out / "DEDUP_REPORT.json").write_text(
            json.dumps(dedup_report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"dry-run done. bib={len(bib_rows)} toc={len(toc_rows)} "
          f"skipped={skipped} forms={form_counter}")
    print(f"artifacts -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
