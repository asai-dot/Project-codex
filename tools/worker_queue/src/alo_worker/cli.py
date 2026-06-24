"""alo-worker CLI — Claude Code Worker Queue の単一書き手。

  alo-worker status                  … レーン状態の一覧 (読み取りのみ)
  alo-worker next                    … 次に着手すべき 1 件 (P0>P1>P2) を出す
  alo-worker lint [--strict]         … inbox task の front-matter preflight
  alo-worker claim <id>              … inbox → doing (着手宣言)
  alo-worker complete <id>           … doing → done (WORKER_PASS 系 RESULT 必須) + 台帳
  alo-worker block <id>              … doing → blocked (WORKER_BLOCKED/FAIL RESULT 必須) + 台帳
  alo-worker recover                 … doing に残った中断 task を監査して畳み方を提示
  alo-worker registry build          … _registry.md を jsonl から再生成

root の解決順:  --root  >  $ALO_WORKER_QUEUE_ROOT  >  ./docs/worker_queue
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from . import __version__, registry
from .queue import (
    BLOCKED,
    DONE,
    HELD,
    IN_PROGRESS,
    QUEUED,
    TERMINAL_BAD_LABEL,
    TERMINAL_NO_RESULT,
    TransitionError,
    block,
    claim,
    complete,
    scan,
)
from .task import lint_task

ENV_ROOT = "ALO_WORKER_QUEUE_ROOT"
DEFAULT_ROOT = os.path.join("docs", "worker_queue")

_PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2}

_STATUS_ORDER = [
    IN_PROGRESS,
    TERMINAL_NO_RESULT,
    TERMINAL_BAD_LABEL,
    QUEUED,
    HELD,
    DONE,
    BLOCKED,
]


def _resolve_root(arg_root: Optional[str]) -> str:
    root = arg_root or os.environ.get(ENV_ROOT) or DEFAULT_ROOT
    root = os.path.abspath(os.path.expanduser(root))
    if not os.path.isdir(root):
        raise SystemExit(
            "error: queue root が存在しません: {}\n"
            "  --root <docs/worker_queue パス> か 環境変数 {} を指定してください".format(
                root, ENV_ROOT))
    return root


def _priority_key(task) -> tuple:
    return (_PRIORITY_RANK.get(task.priority, 9), task.filename)


# --- status ----------------------------------------------------------------
def cmd_status(args) -> int:
    root = _resolve_root(args.root)
    queue = scan(root)
    counts = queue.counts()

    if args.json:
        payload = {
            "root": root,
            "counts": counts,
            "tasks": [
                {
                    "worker_task_id": t.worker_task_id,
                    "filename": t.filename,
                    "lane": t.lane,
                    "lane_status": t.lane_status,
                    "priority": t.priority,
                    "result_label": t.result_label,
                }
                for t in queue.tasks
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("root: {}".format(root))
    print(
        "in_progress: {in_progress}  |  queued: {queued}  |  held: {held}  |  "
        "done: {done}  |  blocked: {blocked}".format(**counts))
    accidents = counts[TERMINAL_NO_RESULT] + counts[TERMINAL_BAD_LABEL]
    if accidents:
        print("⚠ accidents: terminal_without_result={}  terminal_bad_label={}".format(
            counts[TERMINAL_NO_RESULT], counts[TERMINAL_BAD_LABEL]))
    print("")

    for status in _STATUS_ORDER:
        items = queue.by_lane_status(status)
        if not items:
            continue
        print("[{}]".format(status))
        for t in sorted(items, key=_priority_key):
            label = t.result_label or "-"
            print("  - {}  (pri={}, label={})".format(
                t.filename, t.priority or "-", label))
        print("")
    return 0


# --- next ------------------------------------------------------------------
def cmd_next(args) -> int:
    root = _resolve_root(args.root)
    queue = scan(root)

    in_prog = queue.by_lane_status(IN_PROGRESS)
    if in_prog and not args.allow_wip:
        t = sorted(in_prog, key=_priority_key)[0]
        print("doing に着手中 task があります。先に畳んでください: {}".format(t.filename))
        print("  -> complete/block するか、`alo-worker recover` で監査")
        return 2

    queued = sorted(queue.by_lane_status(QUEUED), key=_priority_key)
    if not queued:
        print("inbox に着手可能な task はありません (queued=0)")
        return 0
    t = queued[0]
    if args.json:
        print(json.dumps({
            "worker_task_id": t.worker_task_id, "filename": t.filename,
            "priority": t.priority, "goal": t.goal,
            "allowed_paths": t.allowed_paths, "test_command": t.test_command,
        }, ensure_ascii=False, indent=2))
        return 0
    print("次の 1 件: {}".format(t.filename))
    print("  task_id : {}".format(t.worker_task_id or "-"))
    print("  priority: {}".format(t.priority or "-"))
    print("  goal    : {}".format(t.goal or "-"))
    print("  test    : {}".format(t.test_command or "(exit_criteria 参照)"))
    print("\n  着手: alo-worker claim {}".format(t.worker_task_id or t.filename))
    return 0


# --- lint ------------------------------------------------------------------
def cmd_lint(args) -> int:
    root = _resolve_root(args.root)
    queue = scan(root)
    targets = queue.by_lane("inbox") if not args.all else queue.tasks
    if not targets:
        print("lint 対象 task なし")
        return 0

    errors = 0
    warns = 0
    findings_json = []
    for t in sorted(targets, key=_priority_key):
        findings = lint_task(t, root=root)
        for f in findings:
            findings_json.append({
                "task": f.task_filename, "level": f.level,
                "code": f.code, "message": f.message})
            if f.level == "error":
                errors += 1
            else:
                warns += 1
            if not args.json:
                mark = "ERROR" if f.level == "error" else "warn "
                print("  [{}] {}: {} ({})".format(mark, f.task_filename, f.message, f.code))

    if args.json:
        print(json.dumps({"errors": errors, "warns": warns,
                          "findings": findings_json}, ensure_ascii=False, indent=2))
    else:
        print("\nlint: {} error / {} warn  ({} task)".format(errors, warns, len(targets)))
    if errors:
        return 1
    if warns and args.strict:
        return 1
    return 0


# --- transitions -----------------------------------------------------------
def _run_transition(args, fn, op: str, write_ledger: bool) -> int:
    root = _resolve_root(args.root)
    queue = scan(root)
    try:
        if args.dry_run:
            # dry-run: 検証だけ走らせ、移動はしない。fn を呼ぶと移動するので
            # ここでは scan の分類から畳めるかだけ確かめる。
            print("[dry-run] {} {} を検証します (移動しません)".format(op, args.id))
            result = _dry_check(queue, args.id, op)
        elif hasattr(args, "force"):
            result = fn(queue, args.id, force=args.force)
        else:
            result = fn(queue, args.id)
    except TransitionError as e:
        print("error[{}]: {}".format(e.code, e.message), file=sys.stderr)
        return 2

    if args.dry_run:
        return 0

    if result.action == "already":
        print("{}: {} ({})".format(op, result.task.filename, "; ".join(result.warnings)))
        return 0

    print("{}: {} -> {}/  (label={}, action={})".format(
        op, result.task.filename, result.dest_lane,
        result.result_label or "-", result.action))
    for w in result.warnings:
        print("  warn: {}".format(w))

    if write_ledger:
        entry = registry.make_entry(result)
        registry.append(root, entry)
        registry.render_md(root)
        print("  台帳追記: {} (next_action={})".format(
            entry["worker_task_id"], entry["next_action"]))
    return 0


def _dry_check(queue, ident, op):
    from .queue import find_task
    t = find_task(queue, ident)
    if t is None:
        raise TransitionError("not_found", "task '{}' が見つかりません".format(ident))
    print("  現在: lane={} lane_status={}".format(t.lane, t.lane_status))
    return None


def cmd_claim(args) -> int:
    return _run_transition(args, claim, "claim", write_ledger=False)


def cmd_complete(args) -> int:
    return _run_transition(args, complete, "complete", write_ledger=True)


def cmd_block(args) -> int:
    return _run_transition(args, block, "block", write_ledger=True)


# --- recover ---------------------------------------------------------------
def cmd_recover(args) -> int:
    """doing に残った中断 task を監査し、畳み方を提示する (§6 復旧手順)。"""
    root = _resolve_root(args.root)
    queue = scan(root)
    wip = sorted(queue.by_lane_status(IN_PROGRESS), key=_priority_key)
    accidents = (queue.by_lane_status(TERMINAL_NO_RESULT)
                 + queue.by_lane_status(TERMINAL_BAD_LABEL))

    if not wip and not accidents:
        print("doing は空、accident なし。クリーンです。inbox から next を取れます。")
        return 0

    if wip:
        print("doing に残る中断 task ({} 件) — 状態を確定してください:".format(len(wip)))
        for t in wip:
            done_r = os.path.join(root, "done", t.expected_result)
            blocked_r = os.path.join(root, "blocked", t.expected_result)
            if os.path.isfile(done_r):
                hint = "done/{} あり -> `alo-worker complete {}`".format(
                    t.expected_result, t.worker_task_id or t.filename)
            elif os.path.isfile(blocked_r):
                hint = "blocked/{} あり -> `alo-worker block {}`".format(
                    t.expected_result, t.worker_task_id or t.filename)
            else:
                hint = ("RESULT 未作成 -> 作業実体を確認。完了済なら done/ に RESULT を書いて "
                        "complete、未完なら blocked/ に BLOCKED RESULT を書いて block。"
                        "推測で続きを実装しないこと。")
            print("  - {}  [{}]".format(t.filename, hint))
        print("")
    if accidents:
        print("⚠ accident ({} 件) — 自動処理せず人間/GPT 確認:".format(len(accidents)))
        for t in accidents:
            print("  - {}/{}  ({})".format(t.lane, t.filename, t.lane_status))
    return 1 if accidents else 0


# --- registry --------------------------------------------------------------
def cmd_registry(args) -> int:
    root = _resolve_root(args.root)
    if args.action == "build":
        registry.render_md(root)
        rows = registry.load(root)
        print("台帳再生成: {} 行 -> {}".format(len(rows), registry.REGISTRY_MD))
        return 0
    print("unknown registry action: {}".format(args.action), file=sys.stderr)
    return 2


# --- parser ----------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="alo-worker", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version="alo-worker {}".format(__version__))
    p.add_argument("--root", help="queue root (既定: $%s か ./%s)" % (ENV_ROOT, DEFAULT_ROOT))
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("status", help="レーン状態一覧 (読み取りのみ)")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("next", help="次に着手すべき 1 件を出す")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--allow-wip", action="store_true",
                    help="doing に着手中があっても次を出す")
    sp.set_defaults(func=cmd_next)

    sp = sub.add_parser("lint", help="inbox task の front-matter preflight")
    sp.add_argument("--strict", action="store_true", help="warn があっても exit 1")
    sp.add_argument("--all", action="store_true", help="全レーンを対象にする")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_lint)

    for name, fn, helptext in [
        ("claim", cmd_claim, "inbox -> doing (着手宣言)"),
        ("complete", cmd_complete, "doing -> done (WORKER_PASS 系 RESULT 必須)"),
        ("block", cmd_block, "doing -> blocked (WORKER_BLOCKED/FAIL RESULT 必須)"),
    ]:
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("id", help="worker_task_id か task ファイル名")
        sp.add_argument("--dry-run", action="store_true", help="検証のみ・移動しない")
        if name != "claim":
            sp.add_argument("--force", action="store_true",
                            help="RESULT ラベル不整合を強制的に通す")
        sp.set_defaults(func=fn)

    sp = sub.add_parser("recover", help="doing の中断 task を監査し畳み方を提示")
    sp.set_defaults(func=cmd_recover)

    sp = sub.add_parser("registry", help="台帳 (_registry.md) 操作")
    sp.add_argument("action", choices=["build"], help="build: jsonl から md 再生成")
    sp.set_defaults(func=cmd_registry)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
