"""legallib 接合 本適用器 (Fork 1 / ロールアウト §7 step 3).

ドライラン (`legallib_join_dryrun.py`) で承認された接合を実ファイル
(`app/data/toc/isbn_*.json`) へ反映する。**dry-run が既定** — `--commit` を
明示しない限り 1 バイトも書かない。

安全設計 (defense in depth):
  * 既定は dry-run。`--commit` を付けて初めて書き込む。
  * `--only-isbns FILE`: レビューで承認された ISBN ホワイトリスト。指定時は
    それ以外を `needs_approval` で skip。
  * **書き込み直前に、ライブの既存ファイルへ `decide_join_action` を再適用** し、
    書き込み系 action でなければ `refused_protected` で拒否する。これにより
    入力が壊れていても保護対象 (人手/NDL/出版社/PDF目次・非simple) を
    物理的に上書きできない (検収「非simple 劣化0」を二重に担保)。
  * 書き込みは temp ファイル + `os.replace` の atomic write。
  * 既に legallib のファイルは `skip_idempotent` で触らない (再実行で diff 0)。

books.json の `hasToc` 反映は既存パイプライン (`merge_toc_updates.py` の
`books_write_lock`/`atomic_write_json`) に委譲する。本ツールは TOC ファイルの
書き込みと、hasToc を立てるべき ISBN の manifest 出力までを担う。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from legallib_join_dryrun import (  # noqa: E402
    decide_for_isbn,
    load_books_isbn_set,
    load_resolver,
    run_dryrun,
)
from legallib_join_policy import (  # noqa: E402
    PROTECTED_SOURCES,
    WRITE_ACTIONS,
    load_policy,
)


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)  # atomic on POSIX


def _load_whitelist(path: str | None) -> set[str] | None:
    if not path:
        return None
    text = Path(path).read_text(encoding="utf-8")
    return {ln.strip() for ln in text.splitlines() if ln.strip()}


def apply_join(
    resolver_rows: list[dict],
    legallib_dir: Path,
    toc_dir: Path,
    known_isbns: set[str],
    policy: dict[str, Any],
    *,
    commit: bool,
    whitelist: set[str] | None,
    log_path: Path | None = None,
    backup_dir: Path | None = None,
) -> dict[str, Any]:
    protected = frozenset(policy.get("protected_sources", PROTECTED_SOURCES))
    result = run_dryrun(resolver_rows, legallib_dir, toc_dir, known_isbns, policy)
    proposed = result["proposed_files"]

    # DDJOINAUDIT P0-1: 破壊的 overwrite_simple は承認済み whitelist 必須。
    # whitelist 無しで overwrite を含む commit は **拒否** (人手レビューを CLI で強制)。
    overwrite_targets = {
        e["isbn"] for e in result["actions"]
        if e.get("action") == "overwrite_simple" and e.get("isbn") in proposed
    }
    if commit and overwrite_targets and whitelist is None:
        return {
            "commit": False,
            "refused": "overwrite_requires_whitelist",
            "overwrite_count": len(overwrite_targets),
            "applied": [],
            "status_counts": {"refused_overwrite_needs_whitelist": len(overwrite_targets)},
            "hastoc_isbns": [],
            "dryrun_counts": result["counts"],
            "blocked": result["blocked"],
            "invariant_violations": result["invariant_violations"],
        }

    applied: list[dict] = []
    hastoc_isbns: list[str] = []
    log_f = log_path.open("a", encoding="utf-8") if (log_path and commit) else None

    try:
        for entry in result["actions"]:
            action = entry.get("action")
            isbn = entry.get("isbn")
            if action not in WRITE_ACTIONS or isbn not in proposed:
                continue

            if whitelist is not None and isbn not in whitelist:
                applied.append({"isbn": isbn, "status": "needs_approval", "action": action})
                continue

            # defense in depth: ライブの既存へゲートを再適用 (unreadable も保護)。
            live_action, _, live_existing = decide_for_isbn(toc_dir, isbn, protected)
            if live_action not in WRITE_ACTIONS:
                applied.append({"isbn": isbn, "status": "refused_protected",
                                "live_action": live_action})
                continue

            nodes = proposed[isbn]
            out_path = toc_dir / f"isbn_{isbn}.json"
            if commit:
                # P1 rollback: overwrite 前に旧ファイルを backup (新規 create は対象外)。
                if live_action == "overwrite_simple" and live_existing and backup_dir:
                    _atomic_write_json(backup_dir / f"isbn_{isbn}.json", live_existing)
                _atomic_write_json(out_path, nodes)
                status = "written"
            else:
                status = "would_write"
            hastoc_isbns.append(isbn)
            rec = {"isbn": isbn, "status": status, "action": live_action,
                   "node_count": len(nodes), "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
            applied.append(rec)
            if log_f:
                log_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    finally:
        if log_f:
            log_f.close()

    from collections import Counter

    return {
        "commit": commit,
        "applied": applied,
        "status_counts": dict(Counter(a["status"] for a in applied)),
        "hastoc_isbns": hastoc_isbns,
        "dryrun_counts": result["counts"],
        "blocked": result["blocked"],
        "invariant_violations": result["invariant_violations"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="legallib 接合 本適用 (既定 dry-run)")
    ap.add_argument("--resolver", required=True)
    ap.add_argument("--legallib-dir", required=True)
    ap.add_argument("--toc-dir", required=True)
    ap.add_argument("--books", required=True)
    ap.add_argument("--policy")
    ap.add_argument("--only-isbns",
                    help="承認済み ISBN のホワイトリスト (1行1ISBN)。overwrite を含む --commit には必須")
    ap.add_argument("--backup-dir", help="overwrite 前の旧ファイル退避先 (rollback 用)")
    ap.add_argument("--log", help="適用ログ jsonl の追記先 (--commit 時のみ)")
    ap.add_argument("--commit", action="store_true",
                    help="実書き込み。付けなければ would_write のみ")
    args = ap.parse_args(argv)

    policy = load_policy(args.policy)
    result = apply_join(
        load_resolver(Path(args.resolver)),
        Path(args.legallib_dir),
        Path(args.toc_dir),
        load_books_isbn_set(Path(args.books)),
        policy,
        commit=args.commit,
        whitelist=_load_whitelist(args.only_isbns),
        log_path=Path(args.log) if args.log else None,
        backup_dir=Path(args.backup_dir) if args.backup_dir else None,
    )

    print(json.dumps(result["status_counts"], ensure_ascii=False, sort_keys=True))
    print(f"commit={result['commit']} hastoc_to_set={len(result['hastoc_isbns'])}")
    # P0-1: overwrite を whitelist 無しで commit しようとした → 拒否 (exit 1)。
    if result.get("refused") == "overwrite_requires_whitelist":
        print(f"REFUSED: overwrite_simple {result['overwrite_count']} 件は "
              f"--only-isbns (承認済み ISBN) が必須。create のみ自動可。", file=sys.stderr)
        return 1
    # 保護対象への書き込み拒否は正常系だが、invariant 違反があれば失敗扱い。
    if result["invariant_violations"]:
        print(f"INVARIANT VIOLATION: {result['invariant_violations']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
