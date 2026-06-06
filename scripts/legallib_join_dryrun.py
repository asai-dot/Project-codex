"""legallib auto_accept 新規分のドライラン diff (Fork 1 / 最初の一歩 ③).

resolver の 3 層 (auto_accept / human_review / defer_new) を本番にどう落とすかを
**書き込みゼロ** で検証する。実ファイル (``app/data/toc/``) は一切変更せず、
「もし接合したら何が起きるか」の diff レポートと提案ファイルを ``--out`` に出す。

resolver 出力の想定 (本番では ``~/alo-ai/`` 側の成果物。1 行 1 件)::

    {"legallib_book_id": "305760", "isbn": "9784...", "bucket": "auto_accept",
     "confidence": 0.98}

bucket は ``auto_accept`` / ``human_review`` / ``defer_new`` のいずれか。

3 層の本番マッピング:
  * ``auto_accept`` : ISBN 突合 OK → 変換し、policy ゲートに従って
    create / overwrite_simple / route_human_review / skip_idempotent。
  * ``human_review``: 機械では確定しない → レビューキューへ (書き込みなし)。
  * ``defer_new``   : canonical に対応書籍なし → legallib_book_id 名前空間の
    staging へ退避 (ISBN 名前空間には**絶対に書かない** = 誤マージ0)。

誤マージ0ガード (book_id ↔ ISBN):
  * ISBN が books.json に存在しないものは ``blocked_missing_isbn``。
  * 1 ISBN に複数 legallib_book_id、または 1 book_id に複数 ISBN が
    auto_accept で割り当たっているものは ``blocked_ambiguous`` (両方除外)。
  これらは書き込み候補から完全に外れる。

使い方:
    python scripts/legallib_join_dryrun.py \\
        --resolver  ~/alo-ai/work/legallib_dl/resolver_decisions.jsonl \\
        --legallib-dir ~/alo-ai/work/legallib_dl \\
        --toc-dir   app/data/toc \\
        --books     app/data/books.json \\
        --out       build/legallib_dryrun

    # リポジトリ同梱の合成フィクスチャで素振り (実データ不要):
    python scripts/legallib_join_dryrun.py --demo --out build/legallib_dryrun_demo
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from legallib_join_policy import (  # noqa: E402
    PROTECTED_SOURCES,
    WRITE_ACTIONS,
    decide_join_action,
    existing_primary_source,
    load_policy,
)
from legallib_to_canonical import convert_legallib_nodes  # noqa: E402

VALID_BUCKETS = {"auto_accept", "human_review", "defer_new"}
_ISBN13 = __import__("re").compile(r"^97[89]\d{10}$")


# --- 入出力ヘルパ -----------------------------------------------------------

def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _load_csv(path: Path) -> list[dict]:
    import csv

    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_resolver(path: Path) -> list[dict]:
    rows = _load_csv(path) if path.suffix.lower() == ".csv" else _load_jsonl(path)
    norm = []
    for r in rows:
        norm.append(
            {
                "legallib_book_id": str(
                    r.get("legallib_book_id") or r.get("book_id") or ""
                ).strip(),
                "isbn": str(r.get("isbn") or "").strip(),
                "bucket": str(r.get("bucket") or r.get("decision") or "").strip(),
                "confidence": r.get("confidence"),
            }
        )
    return norm


def load_legallib_nodes(legallib_dir: Path, book_id: str) -> list[dict]:
    """legallib_dl/{book_id}.json から toc ノード列を取り出す。"""
    path = legallib_dir / f"{book_id}.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("toc", "nodes", "toc_nodes", "items"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def load_existing_toc(toc_dir: Path, isbn: str) -> list[dict] | None:
    path = toc_dir / f"isbn_{isbn}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def load_books_isbn_set(books_path: Path) -> set[str]:
    books = json.loads(books_path.read_text(encoding="utf-8"))
    out = set()
    for b in books:
        isbn = str(b.get("isbn") or "").strip()
        if isbn:
            out.add(isbn)
    return out


# --- 誤マージ0ガード ---------------------------------------------------------

def detect_mismerge(resolver_rows: list[dict], known_isbns: set[str]) -> dict[str, str]:
    """auto_accept 行のうち書き込んではいけないものを理由付きで返す。

    Returns: ``{legallib_book_id: reason}`` (blocked 対象のみ)。
    """
    auto = [r for r in resolver_rows if r["bucket"] == "auto_accept"]
    blocked: dict[str, str] = {}

    by_isbn: dict[str, set[str]] = defaultdict(set)
    by_book: dict[str, set[str]] = defaultdict(set)
    for r in auto:
        bid, isbn = r["legallib_book_id"], r["isbn"]
        if bid and isbn:
            by_isbn[isbn].add(bid)
            by_book[bid].add(isbn)

    for r in auto:
        bid, isbn = r["legallib_book_id"], r["isbn"]
        if not bid:
            blocked[bid] = "blocked_no_book_id"
        elif not isbn or not _ISBN13.match(isbn):
            blocked[bid] = "blocked_bad_isbn"
        elif isbn not in known_isbns:
            blocked[bid] = "blocked_missing_isbn"  # books.json に無い ISBN
        elif len(by_isbn[isbn]) > 1:
            blocked[bid] = "blocked_ambiguous_isbn"  # 同 ISBN に複数 book_id
        elif len(by_book[bid]) > 1:
            blocked[bid] = "blocked_ambiguous_book"  # 同 book_id に複数 ISBN
    return blocked


# --- ドライラン本体 ---------------------------------------------------------

def run_dryrun(
    resolver_rows: list[dict],
    legallib_dir: Path,
    toc_dir: Path,
    known_isbns: set[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    priority = policy.get("priority", [])
    protected = frozenset(policy.get("protected_sources", PROTECTED_SOURCES))

    blocked = detect_mismerge(resolver_rows, known_isbns)
    actions: list[dict] = []
    proposed_files: dict[str, list[dict]] = {}
    review_queue: list[dict] = []
    defer_staging: list[dict] = []
    all_warnings: list[str] = []

    for r in resolver_rows:
        bucket = r["bucket"]
        bid = r["legallib_book_id"]
        isbn = r["isbn"]

        if bucket not in VALID_BUCKETS:
            actions.append({"book_id": bid, "isbn": isbn, "action": "skip_unknown_bucket"})
            continue

        if bucket == "defer_new":
            # ISBN 名前空間には書かない。book_id 名前空間へ退避。
            defer_staging.append({"book_id": bid, "reason": "no_canonical_match"})
            actions.append({"book_id": bid, "isbn": isbn, "action": "defer_staging"})
            continue

        if bucket == "human_review":
            review_queue.append({"book_id": bid, "isbn": isbn, "reason": "resolver_human_review"})
            actions.append({"book_id": bid, "isbn": isbn, "action": "route_human_review"})
            continue

        # --- auto_accept ---
        if bid in blocked:
            actions.append({"book_id": bid, "isbn": isbn, "action": blocked[bid]})
            continue

        raw_nodes = load_legallib_nodes(legallib_dir, bid)
        if not raw_nodes:
            actions.append({"book_id": bid, "isbn": isbn, "action": "skip_empty_source"})
            continue

        warnings: list[str] = []
        new_nodes = convert_legallib_nodes(raw_nodes, isbn, warnings=warnings)
        all_warnings.extend(warnings)
        if not new_nodes:
            actions.append({"book_id": bid, "isbn": isbn, "action": "skip_empty_after_convert"})
            continue

        existing = load_existing_toc(toc_dir, isbn)
        action = decide_join_action(existing, protected_sources=protected)

        entry: dict[str, Any] = {
            "book_id": bid,
            "isbn": isbn,
            "action": action,
            "new_node_count": len(new_nodes),
            "existing_node_count": len(existing) if existing else 0,
            "existing_primary_source": (
                existing_primary_source(existing, priority) if existing else None
            ),
        }

        if action in WRITE_ACTIONS:
            proposed_files[isbn] = new_nodes
            entry["node_delta"] = len(new_nodes) - (len(existing) if existing else 0)
        elif action == "route_human_review":
            review_queue.append(
                {
                    "book_id": bid,
                    "isbn": isbn,
                    "reason": "existing_protected",
                    "existing_primary_source": entry["existing_primary_source"],
                }
            )
        actions.append(entry)

    # --- 検収アサーション (バグ検出): 保護対象が書き込み候補に入っていないこと ---
    invariant_violations = []
    for e in actions:
        if e.get("action") in WRITE_ACTIONS and e["isbn"] in proposed_files:
            existing = load_existing_toc(toc_dir, e["isbn"])
            if existing and decide_join_action(existing, protected_sources=protected) not in WRITE_ACTIONS:
                invariant_violations.append(e["isbn"])

    counts = Counter(e["action"] for e in actions)
    return {
        "counts": dict(counts),
        "actions": actions,
        "proposed_files": proposed_files,
        "review_queue": review_queue,
        "defer_staging": defer_staging,
        "blocked": blocked,
        "warnings": all_warnings,
        "invariant_violations": invariant_violations,
    }


def write_report(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    proposed_dir = out_dir / "proposed"
    proposed_dir.mkdir(exist_ok=True)

    # 提案ファイル (本番 toc-dir には触れない)。
    for isbn, nodes in result["proposed_files"].items():
        (proposed_dir / f"isbn_{isbn}.json").write_text(
            json.dumps(nodes, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    (out_dir / "review_queue.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in result["review_queue"]),
        encoding="utf-8",
    )
    (out_dir / "defer_staging.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in result["defer_staging"]),
        encoding="utf-8",
    )
    (out_dir / "actions.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in result["actions"]),
        encoding="utf-8",
    )

    counts = result["counts"]
    write_count = sum(counts.get(a, 0) for a in WRITE_ACTIONS)
    lines = [
        "# legallib 接合 ドライラン diff レポート",
        "",
        f"- 判定総数: {len(result['actions'])}",
        f"- 書き込み候補 (create + overwrite_simple): {write_count}",
        "",
        "## action 内訳",
        "",
        *[f"- {action}: {n}" for action, n in sorted(counts.items())],
        "",
        "## 検収ガード",
        "",
        f"- 誤マージ blocked: {len(result['blocked'])} 件",
        f"- human_review 退避: {len(result['review_queue'])} 件",
        f"- defer_new staging: {len(result['defer_staging'])} 件",
        f"- 変換 warning: {len(result['warnings'])} 件",
        f"- 不変条件違反 (保護対象への書き込み): {len(result['invariant_violations'])} 件"
        + ("  ✅ OK" if not result["invariant_violations"] else "  ❌ NG"),
        "",
        "> 非simple (人手/NDL/出版社/PDF目次) は overwrite 候補に入らない = diff 0。",
        "> 上の「不変条件違反」が 0 件であることが検収の機械的証明。",
    ]
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- demo (合成フィクスチャ) -------------------------------------------------

def _demo_inputs(tmp: Path) -> tuple[list[dict], Path, Path, set[str]]:
    legallib_dir = tmp / "legallib_dl"
    toc_dir = tmp / "toc"
    legallib_dir.mkdir(parents=True, exist_ok=True)
    toc_dir.mkdir(parents=True, exist_ok=True)

    # legallib 1冊: level 入れ子あり (1->2->2->1)。
    (legallib_dir / "L100.json").write_text(json.dumps({
        "title": "会社法コンメンタール 1",
        "toc": [
            {"level": 1, "t": "第1編 総則", "p": 1},
            {"level": 2, "t": "第1章 通則", "p": 3},
            {"level": 2, "t": "第2章 会社の商号", "p": 20},
            {"level": 1, "t": "第2編 株式会社", "p": 50},
        ],
    }, ensure_ascii=False), encoding="utf-8")
    (legallib_dir / "L200.json").write_text(json.dumps({
        "title": "新規本", "toc": [{"level": 1, "t": "序章"}, {"level": 1, "t": "第1章"}],
    }, ensure_ascii=False), encoding="utf-8")
    (legallib_dir / "L300.json").write_text(json.dumps({
        "title": "人手既存本", "toc": [{"level": 1, "t": "上書きされたくない"}],
    }, ensure_ascii=False), encoding="utf-8")

    # 既存 toc: 9784000000010 は simple のみ (上書き可), 9784000000027 は人手 (保護)。
    (toc_dir / "isbn_9784000000010.json").write_text(json.dumps([
        {"l": 1, "p": None, "t": "古いフラット目次", "toc_node_id": "alo:book:isbn:9784000000010:toc:001",
         "depth": 1, "parent_toc_node_id": "", "toc_path_id": "c01", "page_start": None,
         "toc_source": "openbd", "toc_status": "simple"},
    ], ensure_ascii=False), encoding="utf-8")
    (toc_dir / "isbn_9784000000027.json").write_text(json.dumps([
        {"l": 1, "p": 5, "t": "人手で作った章", "toc_node_id": "alo:book:isbn:9784000000027:toc:001",
         "depth": 1, "parent_toc_node_id": "", "toc_path_id": "c01", "page_start": 5,
         "toc_source": "manual", "toc_status": "curated"},
    ], ensure_ascii=False), encoding="utf-8")

    resolver = [
        {"legallib_book_id": "L100", "isbn": "9784000000010", "bucket": "auto_accept", "confidence": 0.98},
        {"legallib_book_id": "L200", "isbn": "9784000000034", "bucket": "auto_accept", "confidence": 0.97},
        {"legallib_book_id": "L300", "isbn": "9784000000027", "bucket": "auto_accept", "confidence": 0.96},
        {"legallib_book_id": "L900", "isbn": "9784000099999", "bucket": "auto_accept", "confidence": 0.95},
        {"legallib_book_id": "L777", "isbn": "", "bucket": "human_review", "confidence": 0.7},
        {"legallib_book_id": "L888", "isbn": "", "bucket": "defer_new", "confidence": 0.4},
    ]
    known = {"9784000000010", "9784000000027", "9784000000034"}  # L900 の ISBN は未登録
    return resolver, legallib_dir, toc_dir, known


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="legallib 接合ドライラン diff")
    ap.add_argument("--resolver")
    ap.add_argument("--legallib-dir")
    ap.add_argument("--toc-dir")
    ap.add_argument("--books")
    ap.add_argument("--policy")
    ap.add_argument("--out", required=True)
    ap.add_argument("--demo", action="store_true", help="同梱フィクスチャで素振り")
    args = ap.parse_args(argv)

    policy = load_policy(args.policy)
    out_dir = Path(args.out)

    if args.demo:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            resolver_rows, legallib_dir, toc_dir, known = _demo_inputs(Path(td))
            result = run_dryrun(resolver_rows, legallib_dir, toc_dir, known, policy)
            write_report(result, out_dir)
    else:
        missing = [n for n in ("resolver", "legallib_dir", "toc_dir", "books")
                   if getattr(args, n.replace("-", "_")) is None]
        if missing:
            ap.error(f"--demo 以外では必須: {', '.join('--' + m for m in missing)}")
        resolver_rows = load_resolver(Path(args.resolver))
        known = load_books_isbn_set(Path(args.books))
        result = run_dryrun(
            resolver_rows, Path(args.legallib_dir), Path(args.toc_dir), known, policy
        )
        write_report(result, out_dir)

    print(json.dumps(result["counts"], ensure_ascii=False, sort_keys=True))
    print(f"report: {out_dir / 'report.md'}")
    if result["invariant_violations"]:
        print(f"INVARIANT VIOLATION: {result['invariant_violations']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
