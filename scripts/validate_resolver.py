"""resolver 出力の preflight 契約検証 (Mac セッションが接合前に最初に実行).

接合を回す前に resolver 出力が想定スキーマ・想定件数か検証し、
深部で失敗する前に**即座に弾く**。ハードエラーがあれば exit 1。

期待スキーマ (1 行 1 件 JSONL、または CSV):
    legallib_book_id, isbn, bucket(auto_accept|human_review|defer_new), confidence

検査:
  * bucket が 3 値のいずれか (未知値はハードエラー)。
  * legallib_book_id 重複 (ハードエラー: 1 book を二重に処理する事故の元)。
  * auto_accept の isbn が ISBN-13 形式か / 空でないか。
  * auto_accept 内の isbn 衝突 (同 isbn に複数 book_id) / book_id→複数 isbn
    (誤マージ予備軍 → 警告として件数報告。接合側で blocked になる)。
  * --expect "1839,305,616" を渡すと bucket 件数を期待値と突合。
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from legallib_join_dryrun import VALID_BUCKETS, load_resolver  # noqa: E402

_ISBN13 = re.compile(r"^97[89]\d{10}$")


def validate(rows: list[dict], expect: tuple[int, int, int] | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    buckets = Counter(r["bucket"] for r in rows)
    unknown = sorted(set(buckets) - VALID_BUCKETS)
    if unknown:
        errors.append(f"未知の bucket: {unknown}")

    book_counts = Counter(r["legallib_book_id"] for r in rows if r["legallib_book_id"])
    dup_books = [b for b, c in book_counts.items() if c > 1]
    if dup_books:
        errors.append(f"legallib_book_id 重複 {len(dup_books)} 件 (例: {dup_books[:5]})")
    blank_book = sum(1 for r in rows if not r["legallib_book_id"])
    if blank_book:
        errors.append(f"legallib_book_id 空 {blank_book} 件")

    auto = [r for r in rows if r["bucket"] == "auto_accept"]
    bad_isbn = [r["legallib_book_id"] for r in auto
                if not r["isbn"] or not _ISBN13.match(r["isbn"])]
    if bad_isbn:
        warnings.append(
            f"auto_accept で isbn 不正/空 {len(bad_isbn)} 件 (接合側で blocked)"
        )

    by_isbn: dict[str, set[str]] = defaultdict(set)
    by_book: dict[str, set[str]] = defaultdict(set)
    for r in auto:
        if r["legallib_book_id"] and r["isbn"]:
            by_isbn[r["isbn"]].add(r["legallib_book_id"])
            by_book[r["legallib_book_id"]].add(r["isbn"])
    isbn_collision = [i for i, s in by_isbn.items() if len(s) > 1]
    book_multi_isbn = [b for b, s in by_book.items() if len(s) > 1]
    if isbn_collision:
        warnings.append(f"同 isbn に複数 book_id {len(isbn_collision)} 件 (blocked 予備軍)")
    if book_multi_isbn:
        warnings.append(f"同 book_id に複数 isbn {len(book_multi_isbn)} 件 (blocked 予備軍)")

    if expect is not None:
        got = (buckets.get("auto_accept", 0), buckets.get("human_review", 0),
               buckets.get("defer_new", 0))
        if got != expect:
            warnings.append(f"件数が期待と不一致: got={got} expect={expect}")

    return {
        "total": len(rows),
        "buckets": dict(buckets),
        "dup_book_ids": len(dup_books),
        "auto_bad_isbn": len(bad_isbn),
        "isbn_collisions": len(isbn_collision),
        "book_multi_isbn": len(book_multi_isbn),
        "errors": errors,
        "warnings": warnings,
        "ok": not errors,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="resolver 出力 preflight 検証")
    ap.add_argument("--resolver", required=True)
    ap.add_argument("--expect", help='"auto,human,defer" 例: "1839,305,616"')
    args = ap.parse_args(argv)

    expect = None
    if args.expect:
        try:
            a, h, d = (int(x) for x in args.expect.split(","))
        except ValueError:
            ap.error('--expect は "auto,human,defer" の整数3つ 例: "1839,305,616"')
        expect = (a, h, d)

    res = validate(load_resolver(Path(args.resolver)), expect)
    print(f"total={res['total']} buckets={res['buckets']}")
    for w in res["warnings"]:
        print(f"  ⚠ {w}")
    for e in res["errors"]:
        print(f"  ❌ {e}", file=sys.stderr)
    print("OK" if res["ok"] else "FAILED")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
