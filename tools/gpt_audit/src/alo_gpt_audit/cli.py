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

from . import __version__, consumed, ledger
from .classify import ACTION_ORDER, build_action_queue, derive_action
from .lane import (
    ANSWERED_NOT_PROCESSED,
    BLOCKED_ACTIVE,
    DUPLICATE,
    PROCESSED_WITHOUT_RESULT,
    CloseError,
    close_request,
    lane_dirs,
    scan,
)

ENV_ROOT = "ALO_GPT_OMETSUKE_ROOT"

# 承認不要 / 承認必要 (APPROVAL_RULE §1, §2 — flat からの移植)
APPROVAL_FREE_OPS = {
    "result_save",
    "request_retreat",
    "ledger_append",
    "action_queue_update",
    "status",
    "dry_run",
}
OWNER_GATED_OPS = {
    "accepted_promotion",
    "canonical_designation",
    "index_backfill",
    "production_db",
    "sf_writeback",
    "external_send",
}

# health: route カードを置くキューのディレクトリ
QUEUE_DIRS = ["approval_queue", "patch_queue", "material_queue", "rejected_queue"]

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
    result_path = os.path.join(lane_dirs(lane.root)["from_gpt"], result.result_filename)
    action = derive_action(result.request.gate, result_path, result.request, ANSWERED_NOT_PROCESSED)
    entry = ledger.make_entry(result, action)
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


# --- action-queue (反映キュー) --------------------------------------------
def cmd_action_queue(args) -> int:
    root = _resolve_root(args.root)
    lane = scan(root)
    items = build_action_queue(lane)

    if args.json:
        print(json.dumps([vars(i) for i in items], ensure_ascii=False, indent=2))
        return 0

    print("root: {}".format(root))
    print("反映キュー (RESULT を消化するための next_action。退避済でも反映は別)\n")
    by_type = {t: [] for t in ACTION_ORDER}
    for i in items:
        by_type.setdefault(i.next_action_type, []).append(i)
    for atype in ACTION_ORDER:
        bucket = by_type.get(atype) or []
        if not bucket:
            continue
        print("[{}]  ({} 件)".format(atype, len(bucket)))
        for i in bucket:
            flags = []
            if i.ratify_required:
                flags.append("ratify_required")
            if i.requeue_expected:
                flags.append("requeue")
            if i.need_more_type:
                flags.append("need_more={}".format(i.need_more_type))
            if i.lane_status != "processed_done":
                flags.append(i.lane_status)
            suffix = "  <{}>".format(", ".join(flags)) if flags else ""
            print("  - {}  [{}]{}".format(i.request_id or i.result_filename, i.result_label, suffix))
            for m in i.missing_materials:
                print("      missing: {}".format(m))
            for b in i.blocking_notes:
                print("      blocking-before-ratify: {}".format(b))
        print("")
    if not items:
        print("(from_gpt に RESULT がありません)")
    return 0


# --- lint (REQUEST preflight 検査) -----------------------------------------
# T2 監査 (accepted化/規範新設/本番投入前) で揃っているべき front-matter キー
_SCOPE_KEYS = ("review_scope", "regression_anchors", "decision_requested")


def cmd_lint(args) -> int:
    root = _resolve_root(args.root)
    lane = scan(root)
    total_warnings = 0
    for req in lane.requests:
        warns = []
        for key in _SCOPE_KEYS:
            if key not in req.meta:
                warns.append("missing {} (監査スコープ境界 §4)".format(key))
        if "target_mode" not in req.meta:
            warns.append("missing target_mode (inline_embedded|box_hash_locked|box_pointer_only §6)")
        sh = req.meta.get("source_hash")
        if not sh or sh.lower() in ("unresolved", "none", ""):
            warns.append("source_hash 未固定 (T2 は box_hash_locked 推奨 §6)")
        if warns:
            total_warnings += len(warns)
            print("{}  (status={})".format(req.filename, req.status))
            for w in warns:
                print("  - {}".format(w))
    if total_warnings == 0:
        print("lint: 警告なし ({} REQUEST 検査)".format(len(lane.requests)))
        return 0
    print("\nlint: {} 件の警告".format(total_warnings))
    return 1 if args.strict else 0


# --- owner-digest (Owner 5行サマリ) ----------------------------------------
def cmd_owner_digest(args) -> int:
    root = _resolve_root(args.root)
    if args.all:
        items = list(ledger.latest_state_per_request(root).values())
    else:
        items = ledger.action_queue(root)
    print("# Owner 5行サマリ — {} 件\n".format(len(items)))
    for e in items:
        print(e.get("owner_digest_5line", "(no digest)"))
        print("---")
    return 0


# --- reflect (RESULT を反映済みにする) -------------------------------------
def cmd_reflect(args) -> int:
    root = _resolve_root(args.root)
    rid = args.request_id
    latest = ledger.latest_state_per_request(root).get(rid)
    if not latest:
        print("error: 台帳に request_id={} がありません".format(rid))
        return 1
    if latest.get("reflected"):
        print("既に reflected: {}".format(rid))
        return 0
    entry = dict(latest)
    entry["ts"] = ledger.now_jst_iso()
    entry["event"] = "reflect"
    entry["reflected"] = True
    entry["loop_state"] = (
        "closed"
        if entry.get("next_action_type") in ("none", "reject")
        else "reflected"
    )
    if args.apply:
        ledger.append(root, entry)
        print("REFLECTED {} -> loop_state={}".format(rid, entry["loop_state"]))
    else:
        print("WOULD REFLECT {} -> loop_state={} (--apply で実行)".format(
            rid, entry["loop_state"]))
    return 0


# --- gate-check (承認要否) --------------------------------------------------
def cmd_gate_check(args) -> int:
    op = args.operation
    if op in APPROVAL_FREE_OPS:
        print("{}: 承認不要 (監査レーン内の事務処理)".format(op))
        return 0
    if op in OWNER_GATED_OPS:
        print("{}: 承認必要 (Owner ratify / 所定 T2 ゲート)。このツールは実行しません。".format(op))
        return 2
    print("{}: 未知の操作。安全側で承認必要とみなします。".format(op))
    return 2


# --- health (レーン health report) -----------------------------------------
def _count_inplace_processed(root: str) -> int:
    """旧式 *_REQUEST.processed.md を to_gpt/ 配下から数える (なければ 0)。"""
    to_gpt = lane_dirs(root)["to_gpt"]
    if not os.path.isdir(to_gpt):
        return 0
    return sum(
        1
        for n in os.listdir(to_gpt)
        if n.endswith("_REQUEST.processed.md")
        and os.path.isfile(os.path.join(to_gpt, n))
    )


def health_report(root: str) -> dict:
    lane = scan(root)
    counts = lane.counts()
    q = ledger.action_queue(root)
    by_action: dict = {}
    for e in q:
        a = e.get("next_action_type", "none")
        by_action[a] = by_action.get(a, 0) + 1
    queue_sizes = {}
    for d in QUEUE_DIRS:
        p = os.path.join(root, d)
        queue_sizes[d] = (
            sum(1 for n in os.listdir(p) if n.endswith(".md"))
            if os.path.isdir(p)
            else 0
        )
    rows = ledger.load(root)
    return {
        "generated_at_jst": ledger.now_jst_iso(),
        "root": root,
        "active_requests": len(lane.requests),
        "lane_status_counts": {
            k: v
            for k, v in counts.items()
            if k not in ("active_requests", "processed", "results")
        },
        "inplace_processed_pending_relocate": _count_inplace_processed(root),
        "results_total": len(lane.result_names),
        "processed_requests": len(lane.processed_by_name),
        "ledger_events": len(rows),
        "unreflected_action_items": len(q),
        "action_queue_by_type": by_action,
        "route_queue_sizes": queue_sizes,
        "action_items": [
            {
                "request_id": e.get("request_id"),
                "result_label": e.get("result_label"),
                "next_action_type": e.get("next_action_type"),
                "loop_state": e.get("loop_state"),
            }
            for e in q
        ],
    }


def render_health_md(r: dict) -> str:
    lines = [
        "# 監査レーン health report",
        "",
        "- generated_at_jst: {}".format(r["generated_at_jst"]),
        "- root: {}".format(r["root"]),
        "",
        "## サマリ",
        "- to_gpt 直下 active REQUEST: {}".format(r["active_requests"]),
        "- 未反映 action item (reflected:false): {}".format(r["unreflected_action_items"]),
        "- from_gpt RESULT 総数: {}".format(r["results_total"]),
        "- processed REQUEST: {}".format(r["processed_requests"]),
        "- 台帳イベント数: {}".format(r["ledger_events"]),
        "- 旧式 *_REQUEST.processed.md (要 relocate): {}".format(
            r["inplace_processed_pending_relocate"]),
        "",
        "## lane_status 内訳",
    ]
    for k, v in sorted(r["lane_status_counts"].items()):
        lines.append("- {}: {}".format(k, v))
    lines += ["", "## next_action 内訳"]
    if r["action_queue_by_type"]:
        for k, v in sorted(r["action_queue_by_type"].items()):
            lines.append("- {}: {}".format(k, v))
    else:
        lines.append("- (未反映なし)")
    lines += ["", "## route queue サイズ"]
    for k, v in r["route_queue_sizes"].items():
        lines.append("- {}: {}".format(k, v))
    if r["action_items"]:
        lines += ["", "## 未反映 action item"]
        for it in r["action_items"]:
            lines.append(
                "- {} [{}] -> {} ({})".format(
                    it["request_id"], it["result_label"],
                    it["next_action_type"], it["loop_state"]))
    health = "GREEN"
    if r["lane_status_counts"].get("processed_without_result"):
        health = "RED (processed_without_result あり)"
    elif r["unreflected_action_items"] > 0:
        health = "YELLOW (未反映 action item あり)"
    lines += ["", "## health: {}".format(health)]
    return "\n".join(lines)


def cmd_health(args) -> int:
    root = _resolve_root(args.root)
    report = health_report(root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_health_md(report))
    return 0


# --- consumed (CONSUMED.md 派生ビュー) -------------------------------------
def cmd_consumed(args) -> int:
    root = _resolve_root(args.root)
    ledger_path = args.ledger or consumed.default_ledger_path(root)
    out_path = consumed.default_consumed_path(root)
    if args.mode == "build":
        consumed.build(root, ledger_path=ledger_path, out_path=out_path,
                       generated_at=args.generated_at)
        print("CONSUMED 書き出し: {} (台帳: {})".format(out_path, ledger_path))
        return 0
    # check
    ok = consumed.check(root, ledger_path=ledger_path, out_path=out_path,
                        generated_at=args.generated_at)
    if ok:
        print("CONSUMED は最新です (ドリフトなし): {}".format(out_path))
        return 0
    print("CONSUMED にドリフトがあります (build で再生成してください): {}".format(out_path))
    return 1


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

    pq = sub.add_parser("action-queue", help="RESULT の next_action を反映キューとして表示")
    pq.add_argument("--json", action="store_true", help="JSON で出力")
    pq.set_defaults(func=cmd_action_queue)

    pl = sub.add_parser("lint", help="REQUEST の preflight 検査 (scope/target_mode/hash)")
    pl.add_argument("--strict", action="store_true", help="警告があれば exit 1")
    pl.set_defaults(func=cmd_lint)

    pod = sub.add_parser("owner-digest", help="Owner 向け 5 行サマリ (台帳派生)")
    pod.add_argument("--all", action="store_true",
                     help="reflected 済みも含む (既定は action_queue のみ)")
    pod.set_defaults(func=cmd_owner_digest)

    pr = sub.add_parser("reflect", help="RESULT を反映済みにする (reflected:true)")
    pr.add_argument("request_id", help="台帳上の request_id")
    pr.add_argument("--apply", action="store_true", help="実際に追記 (未指定は dry-run)")
    pr.set_defaults(func=cmd_reflect)

    pg = sub.add_parser("gate-check", help="操作の承認要否を判定")
    pg.add_argument("operation", help="判定する操作名")
    pg.set_defaults(func=cmd_gate_check)

    ph = sub.add_parser("health", help="監査レーン health report")
    ph.add_argument("--json", action="store_true", help="JSON で出力")
    ph.set_defaults(func=cmd_health)

    pco = sub.add_parser("consumed", help="CONSUMED.md 派生ビュー (build / check)")
    pco.add_argument("mode", choices=["build", "check"], help="build=書き出し / check=ドリフト検査")
    pco.add_argument("--ledger", help="入力台帳 jsonl (既定 <root>/_AUDIT_LEDGER.jsonl)")
    pco.add_argument("--generated-at", dest="generated_at",
                     help="generated_at の固定値 (既定 JST 現在時刻)")
    pco.set_defaults(func=cmd_consumed)

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
