"""alo-gpt-audit CLI — status / close / close-all。

  alo-gpt-audit status            … レーン状態の一覧 (読み取りのみ)
  alo-gpt-audit close <id>        … 1件を検証して processed/ へ退避 + 台帳追記
  alo-gpt-audit close-all         … answered_not_processed を一括退避 (既定 dry-run)

root の解決順:  --root  >  $ALO_GPT_OMETSUKE_ROOT
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from . import __version__, ledger
from .lane import (
    ANSWERED_NOT_PROCESSED,
    BLOCKED_ACTIVE,
    DUPLICATE,
    PROCESSED_WITHOUT_RESULT,
    CloseError,
    close_request,
    scan,
)

ENV_ROOT = "ALO_GPT_OMETSUKE_ROOT"

_STATUS_ORDER = [
    ANSWERED_NOT_PROCESSED,
    DUPLICATE,
    PROCESSED_WITHOUT_RESULT,
    BLOCKED_ACTIVE,
    "active",
]


def _resolve_root(arg_root: Optional[str]) -> str:
    root = arg_root or os.environ.get(ENV_ROOT)
    if not root:
        raise SystemExit(
            "error: レーンの root を指定してください (--root <gpt_ometsuke パス> または "
            "環境変数 {})".format(ENV_ROOT)
        )
    root = os.path.abspath(os.path.expanduser(root))
    if not os.path.isdir(root):
        raise SystemExit("error: root が存在しません: {}".format(root))
    return root


# --- status ----------------------------------------------------------------
def cmd_status(args) -> int:
    root = _resolve_root(args.root)
    lane = scan(root)
    counts = lane.counts()

    if args.json:
        payload = {
            "root": root,
            "counts": counts,
            "requests": [
                {
                    "request_id": r.request_id,
                    "filename": r.filename,
                    "gate": r.gate,
                    "status": r.status,
                    "lane_status": r.lane_status,
                    "result_label": r.result_label,
                }
                for r in lane.requests
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("root: {}".format(root))
    print(
        "active_requests: {active_requests}  |  answered_not_processed: "
        "{answered_not_processed}  |  active(awaiting GPT): {active}  |  "
        "blocked: {blocked_active}  |  duplicate: {duplicate_in_processed}  |  "
        "accident(processed_without_result): {processed_without_result}".format(**counts)
    )
    print("results(from_gpt): {results}  |  processed: {processed}".format(**counts))
    print("")

    shown = False
    for status in _STATUS_ORDER:
        items = lane.by_status(status)
        if not items:
            continue
        shown = True
        print("[{}]".format(status))
        for r in items:
            label = r.result_label or "-"
            print("  - {}  (gate={}, label={})".format(r.filename, r.gate or "-", label))
        print("")
    if not shown:
        print("(to_gpt/ 直下に REQUEST はありません — active queue はゼロ)")
    return 0


# --- close -----------------------------------------------------------------
def _do_close(lane, ident: str, force: bool) -> int:
    try:
        result = close_request(lane, ident, force=force)
    except CloseError as exc:
        print("REFUSED [{}] {}".format(exc.code, exc.message), file=sys.stderr)
        return 2
    entry = ledger.make_entry(result)
    ledger.append(lane.root, entry)
    ledger.render_md(lane.root)
    print(
        "CLOSED  {}  [{}]  label={}  -> to_gpt/processed/".format(
            result.request.request_id, result.action, result.result_label
        )
    )
    for w in result.warnings:
        print("  warn: {}".format(w))
    return 0


def cmd_close(args) -> int:
    root = _resolve_root(args.root)
    lane = scan(root)
    return _do_close(lane, args.request_id, args.force)


# --- close-all -------------------------------------------------------------
def cmd_close_all(args) -> int:
    root = _resolve_root(args.root)
    lane = scan(root)
    targets = lane.by_status(ANSWERED_NOT_PROCESSED)

    if not targets:
        print("answered_not_processed: 0 件。退避するものはありません。")
        return 0

    if not args.apply:
        print("DRY-RUN: 以下 {} 件を to_gpt/processed/ へ退避します (--apply で実行):".format(len(targets)))
        for r in targets:
            print("  - {}  (label={})".format(r.filename, r.result_label or "-"))
        print("")
        print("実行するには: alo-gpt-audit close-all --root <root> --apply")
        return 0

    rc = 0
    for r in targets:
        # 退避で lane が変わるため都度再走査して安全に処理
        lane = scan(root)
        if _do_close(lane, r.request_id or r.filename, args.force) != 0:
            rc = 2
    return rc


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="alo-gpt-audit",
        description="GPT 目付け役 監査レーン (gpt_ometsuke) の close/status ツール",
    )
    p.add_argument("--version", action="version", version="alo-gpt-audit {}".format(__version__))
    p.add_argument(
        "--root",
        help="レーン root (Box folder gpt_ometsuke を Box Drive 同期した実パス)。"
        "未指定時は環境変数 {} を使用。".format(ENV_ROOT),
    )
    sub = p.add_subparsers(dest="command")

    ps = sub.add_parser("status", help="レーン状態の一覧 (読み取りのみ)")
    ps.add_argument("--json", action="store_true", help="JSON で出力")
    ps.set_defaults(func=cmd_status)

    pc = sub.add_parser("close", help="1件を検証して processed/ へ退避")
    pc.add_argument("request_id", help="request_id または REQUEST ファイル名")
    pc.add_argument("--force", action="store_true", help="ラベル不正/重複衝突でも強制実行")
    pc.set_defaults(func=cmd_close)

    pa = sub.add_parser("close-all", help="answered_not_processed を一括退避 (既定 dry-run)")
    pa.add_argument("--apply", action="store_true", help="実際に退避を実行 (未指定は dry-run)")
    pa.add_argument("--force", action="store_true", help="ラベル不正/重複衝突でも強制実行")
    pa.set_defaults(func=cmd_close_all)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
