#!/usr/bin/env python3
"""alo-gpt-audit — GPT Pro お目付け役 監査レーン CLI（依存ゼロ）。

設計正本:
  - GPT_PRO_AUDIT_LANE_DESIGN v0.3 (Box:2269736541410)
  - GPT_PRO_AUDIT_LOOP_RULE  v0.1 (Box:2270127270632)
  - ALO_GPT_AUDIT_ROUTE_RULES v0.1 (Box:2269686181805)
  - PROTOCOL.md                     (Box:2266009787864)

中核原則（v0.2 継承・不変）:
  フォルダ位置を状態にする。`to_gpt/` 直下は未回答だけ。
  退避は「GPT 照会 1 回分は回答済み」という pipeline 状態にすぎず、
  artifact lifecycle の accepted 化（Owner ratify 経由）とは別軸である。

レーン構成（root 配下）:
  to_gpt/                未回答 REQUEST だけが直下に残る
  to_gpt/processed/      回答済み REQUEST の物理退避先（名前ではなく場所で状態を表す）
  from_gpt/              GPT Pro が返す RESULT
  _AUDIT_LEDGER.jsonl    派生台帳（SoT はフォルダ位置。台帳は控え）

この CLI は単一書き手（single writer）が退避を実行する前提で、承認不要な
監査事務（RESULT 照合・REQUEST 退避・台帳追記・反映キュー表示）だけを扱う。
accepted/canonical 昇格・backfill・本番/外部送信は owner-gated でここでは触らない。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

# --- 語彙（v0.3 §A/§C）-------------------------------------------------------

RESULT_LABELS = ("PASS", "PASS_WITH_NOTES", "MODIFY_REQUIRED", "FAIL", "NEED_MORE")

# result_label(本体) -> next_action_type（v0.3 §C・route rules v0.1 Rule4）
NEXT_ACTION_BY_LABEL = {
    "PASS": "ratify",
    "PASS_WITH_NOTES": "ratify",
    "MODIFY_REQUIRED": "patch",
    "FAIL": "reject",
    "NEED_MORE": "required_materials",
}

# next_action_type -> 振り分けキュー（route rules v0.1 Rule4）
QUEUE_BY_NEXT_ACTION = {
    "ratify": "approval_queue",
    "patch": "patch_queue",
    "reject": "rejected_queue",
    "required_materials": "material_queue",
    "none": "approval_queue",
}

RATIFY_REQUIRED_LABELS = {"PASS", "PASS_WITH_NOTES"}
REQUEUE_EXPECTED_LABELS = {"MODIFY_REQUIRED", "NEED_MORE"}

# REQUEST / RESULT のファイル名サフィックス。`.processed.md` は v0.2 期の暫定運用で
# 名前に状態を焼いていたもの。v0.3 では場所（processed/）で表すため退避時に剥がす。
_REQ_SUFFIXES = ("_REQUEST.processed.md", "_REQUEST.md")
_RES_SUFFIX = "_RESULT.md"

LEDGER_NAME = "_AUDIT_LEDGER.jsonl"


# --- データモデル ------------------------------------------------------------


@dataclass
class LedgerEntry:
    """反映キュー兼監査台帳の 1 レコード（v0.3 §D + loop-rule v0.1 §8/§11 の和集合）。"""

    request_id: str
    request_filename: str = ""
    request_file_id: str = ""
    result_filename: str = ""
    result_file_id: str = ""
    result_label: str = ""           # 例 DDLAWTIME_MODIFY_REQUIRED（gate prefix 付き）
    gate: str = ""
    next_action_type: str = "none"   # ratify | patch | required_materials | reject | none
    ratify_required: bool = False
    requeue_expected: bool = False
    need_more_type: str = ""         # material_absent | context_insufficient | ...
    missing_materials: list = field(default_factory=list)
    blocking_before_ratify: list = field(default_factory=list)
    reflected: bool = False          # 反映完了で True 化（人手 / 後続ツール）
    owner_digest_5line: str = ""     # Owner 横目確認用 5 行サマリ
    claude_rethink_prompt: str = ""  # Claude が次にやることの指示文
    loop_state: str = "returned"     # returned | reflected | requeued | ratify_wait | closed
    lane_status: str = ""            # active | answered_not_processed | processed_done | ...
    target_queue: str = ""           # 派生: route rules の振り分け先
    updated_at: str = ""

    def enrich_from_label(self) -> "LedgerEntry":
        """result_label から機械的に決まる派生フィールドを埋める。"""
        body = strip_gate(self.result_label)
        if body in NEXT_ACTION_BY_LABEL:
            self.next_action_type = NEXT_ACTION_BY_LABEL[body]
            self.ratify_required = body in RATIFY_REQUIRED_LABELS
            self.requeue_expected = body in REQUEUE_EXPECTED_LABELS
            self.target_queue = QUEUE_BY_NEXT_ACTION[self.next_action_type]
        return self


# --- ファイル名 / ラベル ヘルパ ---------------------------------------------


def stem_of(filename: str) -> Optional[str]:
    """REQUEST/RESULT ファイル名から request_id stem を取り出す。

    `<stem>_REQUEST.md` / `<stem>_REQUEST.processed.md` / `<stem>_RESULT.md`
    のいずれからも同じ stem を返す。一致しなければ None。
    """
    for suf in _REQ_SUFFIXES:
        if filename.endswith(suf):
            return filename[: -len(suf)]
    if filename.endswith(_RES_SUFFIX):
        return filename[: -len(_RES_SUFFIX)]
    return None


def is_request(filename: str) -> bool:
    return any(filename.endswith(s) for s in _REQ_SUFFIXES)


def is_result(filename: str) -> bool:
    return filename.endswith(_RES_SUFFIX)


def canonical_request_name(stem: str) -> str:
    """退避後の正規 REQUEST 名（サフィックスを剥がした素の形）。"""
    return f"{stem}_REQUEST.md"


def gate_of_stem(stem: str) -> str:
    """stem 末尾セグメントを gate とみなす（PROTOCOL.md / v0.3 §G）。

    例: 20260607_lawtime_v0.2_DDLAWTIME -> DDLAWTIME
    """
    return stem.rsplit("_", 1)[-1] if "_" in stem else ""


def strip_gate(label: str) -> str:
    """`<GATE>_<LABEL>` から LABEL 本体を取り出す。

    最長一致でラベル本体を判定する（PASS_WITH_NOTES / MODIFY_REQUIRED 等）。
    """
    if not label:
        return ""
    for body in sorted(RESULT_LABELS, key=len, reverse=True):
        if label == body or label.endswith("_" + body):
            return body
    return ""


def read_result_label(path: Path) -> str:
    """RESULT ファイルの先頭非空行をラベルとして読む（PROTOCOL.md）。"""
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    return line.lstrip("# ").strip()
    except OSError:
        return ""
    return ""


def label_is_valid(label: str, stem: str) -> bool:
    """ラベルが `<gate>_<LABEL>` 形式で、gate が stem の gate と一致するか。

    gate 検査は PROTOCOL.md の「G0_ 固定で読まない」要件に対応。stem から gate を
    取り出し、`<gate>_<body>` を期待集合として照合する。
    """
    body = strip_gate(label)
    if body not in RESULT_LABELS:
        return False
    gate = gate_of_stem(stem)
    if gate and label == f"{gate}_{body}":
        return True
    # gate を stem から一意に取れない／別表記の場合は本体一致のみで許容（緩め）。
    return label == body or label.endswith("_" + body)


# --- レーン走査 --------------------------------------------------------------


@dataclass
class Lane:
    root: Path

    @property
    def to_gpt(self) -> Path:
        return self.root / "to_gpt"

    @property
    def processed(self) -> Path:
        return self.root / "to_gpt" / "processed"

    @property
    def from_gpt(self) -> Path:
        return self.root / "from_gpt"

    @property
    def ledger_path(self) -> Path:
        return self.root / LEDGER_NAME

    def _results_by_stem(self) -> dict:
        out: dict = {}
        if self.from_gpt.is_dir():
            for p in sorted(self.from_gpt.iterdir()):
                if p.is_file() and is_result(p.name):
                    s = stem_of(p.name)
                    if s:
                        out[s] = p
        return out

    def _active_requests(self) -> list:
        """to_gpt/ 直下（processed/ を除く）の REQUEST ファイル一覧。"""
        out = []
        if self.to_gpt.is_dir():
            for p in sorted(self.to_gpt.iterdir()):
                if p.is_file() and is_request(p.name):
                    out.append(p)
        return out

    def _processed_requests(self) -> list:
        out = []
        if self.processed.is_dir():
            for p in sorted(self.processed.iterdir()):
                if p.is_file() and is_request(p.name):
                    out.append(p)
        return out


@dataclass
class StatusRow:
    stem: str
    path: Path
    lane_status: str
    result_path: Optional[Path] = None
    label: str = ""
    note: str = ""


def compute_status(lane: Lane) -> list:
    """三点照合でレーン状態を出す（v0.3 §6 / §H status）。"""
    results = lane._results_by_stem()
    rows: list = []

    for req in lane._active_requests():
        stem = stem_of(req.name) or req.name
        res = results.get(stem)
        if res is None:
            rows.append(StatusRow(stem, req, "active"))
            continue
        label = read_result_label(res)
        if not strip_gate(label):
            rows.append(StatusRow(stem, req, "bad_label", res, label,
                                  "RESULT 先頭行が 5 ラベルに合致しない"))
        elif not label_is_valid(label, stem):
            rows.append(StatusRow(stem, req, "bad_label", res, label,
                                  "gate prefix が REQUEST stem と不一致"))
        else:
            rows.append(StatusRow(stem, req, "answered_not_processed", res, label))

    for req in lane._processed_requests():
        stem = stem_of(req.name) or req.name
        res = results.get(stem)
        if res is None:
            rows.append(StatusRow(stem, req, "processed_without_result", None, "",
                                  "退避済みだが RESULT が無い"))
        else:
            rows.append(StatusRow(stem, req, "processed_done", res,
                                  read_result_label(res)))
    return rows


# --- 台帳（ledger）----------------------------------------------------------


def load_ledger(path: Path) -> "dict[str, LedgerEntry]":
    """jsonl を request_id キーの dict に読み込む。"""
    entries: dict = {}
    if not path.exists():
        return entries
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            rid = obj.get("request_id")
            if not rid:
                continue
            known = {f for f in LedgerEntry.__dataclass_fields__}
            clean = {k: v for k, v in obj.items() if k in known}
            entries[rid] = LedgerEntry(**clean)
    return entries


def save_ledger(path: Path, entries: "dict[str, LedgerEntry]") -> None:
    """request_id 昇順で jsonl を書く（決定的出力でidempotency検証を容易に）。"""
    lines = []
    for rid in sorted(entries):
        lines.append(json.dumps(asdict(entries[rid]), ensure_ascii=False, sort_keys=True))
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def build_ledger(lane: Lane, preserve: bool = True) -> "dict[str, LedgerEntry]":
    """フォルダ状態（SoT）から台帳を再生成する。

    preserve=True のとき、既存台帳の人手エンリッチ項目
    （reflected / owner_digest_5line / claude_rethink_prompt /
      blocking_before_ratify / need_more_type / missing_materials / loop_state）
    を request_id で引き継ぐ（backfill 安全・冪等）。
    """
    existing = load_ledger(lane.ledger_path) if preserve else {}
    results = lane._results_by_stem()
    now = _now_iso()

    rows = {r.stem: r for r in compute_status(lane)}
    merged: dict = {}

    # RESULT を持つ stem すべてを台帳化（退避済みも消化対象として出し続ける、§D）。
    stems = set(results) | set(rows)
    for stem in stems:
        res = results.get(stem)
        label = read_result_label(res) if res else ""
        entry = LedgerEntry(request_id=stem)
        prev = existing.get(stem)
        entry.result_filename = res.name if res else ""
        entry.result_label = label
        entry.gate = gate_of_stem(stem)
        row = rows.get(stem)
        if row is not None:
            entry.lane_status = row.lane_status
            entry.request_filename = row.path.name
        entry.enrich_from_label()

        if prev is not None:
            entry.reflected = prev.reflected
            entry.owner_digest_5line = prev.owner_digest_5line
            entry.claude_rethink_prompt = prev.claude_rethink_prompt
            entry.blocking_before_ratify = prev.blocking_before_ratify
            entry.need_more_type = prev.need_more_type
            entry.missing_materials = prev.missing_materials
            entry.request_file_id = prev.request_file_id or entry.request_file_id
            entry.result_file_id = prev.result_file_id or entry.result_file_id
            if prev.loop_state and prev.loop_state != "returned":
                entry.loop_state = prev.loop_state
        entry.updated_at = now
        merged[stem] = entry
    return merged


def append_ledger_event(lane: Lane, entry: LedgerEntry) -> None:
    """単一 request_id の台帳追記（close 用）。既存があればマージ更新（冪等）。"""
    entries = load_ledger(lane.ledger_path)
    prev = entries.get(entry.request_id)
    if prev is not None:
        # 既存の人手エンリッチを失わない。
        entry.reflected = prev.reflected or entry.reflected
        entry.owner_digest_5line = entry.owner_digest_5line or prev.owner_digest_5line
        entry.claude_rethink_prompt = entry.claude_rethink_prompt or prev.claude_rethink_prompt
        if not entry.blocking_before_ratify:
            entry.blocking_before_ratify = prev.blocking_before_ratify
    entry.updated_at = _now_iso()
    entries[entry.request_id] = entry
    save_ledger(lane.ledger_path, entries)


# --- close / close-all -------------------------------------------------------


@dataclass
class MovePlan:
    stem: str
    src: Path
    dst: Path
    label: str
    skip_reason: str = ""

    @property
    def actionable(self) -> bool:
        return not self.skip_reason


def plan_close(lane: Lane, only_stem: Optional[str] = None) -> list:
    """answered_not_processed な REQUEST の退避計画を立てる。"""
    plans: list = []
    for row in compute_status(lane):
        if row.lane_status not in (
            "active", "answered_not_processed", "bad_label", "processed_without_result"
        ):
            continue
        if only_stem and row.stem != only_stem:
            continue
        if row.lane_status == "active":
            if only_stem:
                plans.append(MovePlan(row.stem, row.path, row.path, "",
                                      "RESULT 未着（未処理）→ 退避しない"))
            continue
        if row.lane_status == "bad_label":
            plans.append(MovePlan(row.stem, row.path, row.path, row.label,
                                  f"bad_label: {row.note}"))
            continue
        if row.lane_status == "processed_without_result":
            continue
        dst = lane.processed / canonical_request_name(row.stem)
        if dst.exists():
            plans.append(MovePlan(row.stem, row.path, dst, row.label,
                                  "退避先に同名既存（既に close 済みとみなす）"))
            continue
        plans.append(MovePlan(row.stem, row.path, dst, row.label))
    return plans


def execute_plan(lane: Lane, plans: Iterable[MovePlan]) -> list:
    """退避計画を適用し、台帳を追記する。actionable のみ動かす（冪等）。"""
    done = []
    lane.processed.mkdir(parents=True, exist_ok=True)
    for plan in plans:
        if not plan.actionable:
            continue
        shutil.move(str(plan.src), str(plan.dst))
        entry = LedgerEntry(
            request_id=plan.stem,
            request_filename=plan.dst.name,
            result_filename=f"{plan.stem}{_RES_SUFFIX}",
            result_label=plan.label,
            gate=gate_of_stem(plan.stem),
            lane_status="processed_done",
            loop_state="returned",
        ).enrich_from_label()
        append_ledger_event(lane, entry)
        done.append(plan)
    return done


# --- action-queue ------------------------------------------------------------


def action_queue(lane: Lane) -> list:
    """reflected:false の台帳エントリ（=未反映 = 監査が閉じていない）を返す。"""
    entries = load_ledger(lane.ledger_path)
    pending = [e for e in entries.values() if not e.reflected]
    # next_action の緊急度順（patch/required_materials を先に）→ request_id。
    order = {"patch": 0, "required_materials": 1, "reject": 2, "ratify": 3, "none": 4}
    pending.sort(key=lambda e: (order.get(e.next_action_type, 9), e.request_id))
    return pending


# --- lint（REQUEST preflight, v0.3 §G）--------------------------------------

_T2_REQUIRED = ("review_scope", "regression_anchors", "decision_requested",
                "target_mode", "source_hash")


def lint_request(path: Path) -> list:
    """T2 REQUEST の front-matter 必須項目を検査して欠落を返す。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    missing = []
    for key in _T2_REQUIRED:
        if not re.search(rf"^\s*{re.escape(key)}\s*:", text, re.MULTILINE):
            missing.append(key)
    if re.search(r"source_hash\s*:\s*(unresolved|TBD|sha1:\s*$)", text):
        missing.append("source_hash(unresolved)")
    return missing


# --- 雑用 --------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- CLI ---------------------------------------------------------------------


def _fmt_rows(rows: list) -> str:
    if not rows:
        return "(なし)"
    width = max(len(r.lane_status) for r in rows)
    out = []
    for r in sorted(rows, key=lambda x: (x.lane_status, x.stem)):
        line = f"  {r.lane_status:<{width}}  {r.stem}"
        if r.label:
            line += f"  [{r.label}]"
        if r.note:
            line += f"  -- {r.note}"
        out.append(line)
    return "\n".join(out)


def cmd_status(lane: Lane, args) -> int:
    rows = compute_status(lane)
    counts: dict = {}
    for r in rows:
        counts[r.lane_status] = counts.get(r.lane_status, 0) + 1
    if args.json:
        print(json.dumps({
            "counts": counts,
            "rows": [
                {"stem": r.stem, "lane_status": r.lane_status,
                 "label": r.label, "note": r.note}
                for r in rows
            ],
        }, ensure_ascii=False, indent=2))
        return 0
    print("# alo-gpt-audit status")
    print(f"root: {lane.root}")
    print(f"to_gpt 直下 active(未回答): {counts.get('active', 0)}")
    print(f"answered_not_processed   : {counts.get('answered_not_processed', 0)}")
    print(f"bad_label                : {counts.get('bad_label', 0)}")
    print(f"processed_done           : {counts.get('processed_done', 0)}")
    print(f"processed_without_result : {counts.get('processed_without_result', 0)}")
    print("\n" + _fmt_rows(rows))
    return 0


def cmd_close(lane: Lane, args) -> int:
    plans = plan_close(lane, only_stem=args.request_id)
    if not plans:
        print(f"対象 REQUEST が見つかりません: {args.request_id}")
        return 1
    for p in plans:
        if not p.actionable:
            print(f"SKIP {p.stem}: {p.skip_reason}")
            return 1 if "RESULT 未着" in p.skip_reason or "bad_label" in p.skip_reason else 0
    if args.dry_run:
        for p in plans:
            print(f"DRY-RUN move {p.src.name} -> processed/{p.dst.name}  [{p.label}]")
        return 0
    done = execute_plan(lane, plans)
    for p in done:
        print(f"CLOSED {p.stem}: -> processed/{p.dst.name}  [{p.label}]")
    return 0


def cmd_close_all(lane: Lane, args) -> int:
    plans = plan_close(lane)
    movable = [p for p in plans if p.actionable]
    skipped = [p for p in plans if not p.actionable]
    if not args.apply:
        print("# close-all (dry-run; 実行は --apply)")
        for p in movable:
            print(f"DRY-RUN move {p.src.name} -> processed/{p.dst.name}  [{p.label}]")
        for p in skipped:
            print(f"SKIP {p.stem}: {p.skip_reason}")
        print(f"\n退避予定 {len(movable)} 件 / スキップ {len(skipped)} 件")
        return 0
    done = execute_plan(lane, movable)
    for p in done:
        print(f"CLOSED {p.stem}: -> processed/{p.dst.name}  [{p.label}]")
    for p in skipped:
        print(f"SKIP {p.stem}: {p.skip_reason}")
    print(f"\n退避 {len(done)} 件 / スキップ {len(skipped)} 件")
    return 0


def cmd_action_queue(lane: Lane, args) -> int:
    pending = action_queue(lane)
    if args.json:
        print(json.dumps([asdict(e) for e in pending], ensure_ascii=False, indent=2))
        return 0
    print("# alo-gpt-audit action-queue (reflected:false = 未反映 = 監査未クローズ)")
    if not pending:
        print("(反映待ちなし)")
        return 0
    for e in pending:
        print(f"\n- request_id: {e.request_id}")
        print(f"  result_label: {e.result_label}")
        print(f"  next_action_type: {e.next_action_type}  (queue: {e.target_queue})")
        print(f"  ratify_required: {e.ratify_required}  requeue_expected: {e.requeue_expected}")
        if e.blocking_before_ratify:
            print(f"  blocking_before_ratify: {e.blocking_before_ratify}")
        if e.missing_materials:
            print(f"  missing_materials: {e.missing_materials}")
        print(f"  loop_state: {e.loop_state}")
        if e.claude_rethink_prompt:
            print(f"  claude_rethink_prompt: {e.claude_rethink_prompt.splitlines()[0]} ...")
    print(f"\n反映待ち {len(pending)} 件")
    return 0


def cmd_build_ledger(lane: Lane, args) -> int:
    merged = build_ledger(lane, preserve=not args.no_preserve)
    if args.dry_run:
        print(json.dumps([asdict(merged[k]) for k in sorted(merged)],
                         ensure_ascii=False, indent=2))
        return 0
    save_ledger(lane.ledger_path, merged)
    print(f"台帳を再生成: {lane.ledger_path}  ({len(merged)} 件)")
    return 0


def cmd_lint(lane: Lane, args) -> int:
    targets = []
    if args.request_id:
        for p in lane._active_requests():
            if (stem_of(p.name) or "") == args.request_id:
                targets.append(p)
    else:
        targets = lane._active_requests()
    if not targets:
        print("lint 対象 REQUEST なし")
        return 0
    rc = 0
    for p in targets:
        missing = lint_request(p)
        if missing:
            rc = 1
            print(f"LINT-FAIL {p.name}: 欠落 {missing}")
        else:
            print(f"LINT-OK   {p.name}")
    return rc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alo-gpt-audit",
        description="GPT Pro お目付け役 監査レーン CLI（依存ゼロ）",
    )
    parser.add_argument(
        "--root", default=os.environ.get("ALO_GPT_AUDIT_ROOT", "."),
        help="gpt_ometsuke レーンの root（to_gpt/ from_gpt/ を含む）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("status", help="三点照合でレーン状態を表示")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("close", help="単一 REQUEST を照合して退避・台帳追記")
    p.add_argument("request_id")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_close)

    p = sub.add_parser("close-all", help="answered_not_processed を一括退避（既定 dry-run）")
    p.add_argument("--apply", action="store_true", help="実際に移動する")
    p.set_defaults(func=cmd_close_all)

    p = sub.add_parser("action-queue", help="reflected:false の反映キューを表示")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_action_queue)

    p = sub.add_parser("build-ledger", help="フォルダ状態から台帳を再生成（人手項目は引継ぎ）")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-preserve", action="store_true",
                   help="既存台帳の人手エンリッチを引き継がない")
    p.set_defaults(func=cmd_build_ledger)

    p = sub.add_parser("lint", help="REQUEST preflight（T2 必須メタ）")
    p.add_argument("request_id", nargs="?")
    p.set_defaults(func=cmd_lint)

    return parser


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    lane = Lane(Path(args.root).expanduser().resolve())
    return args.func(lane, args)


if __name__ == "__main__":
    sys.exit(main())
