#!/usr/bin/env python3
"""alo-gpt-audit — GPT Pro 監査ループ運用ツール (dependency-zero).

正本 (canonical references):
  - GPT_PRO_AUDIT_LOOP_RULE_v0.1_20260607.md
  - GPT_PRO_AUDIT_LANE_DESIGN_v0.3_20260607.md
  - GPT_PRO_AUDIT_LANE_APPROVAL_RULE_v0.1_20260606.md

設計原則 (v0.2 から不変):
  「フォルダ位置を状態にする。to_gpt/ 直下は未回答だけ。」

このツールは GPT Pro 監査の「行き・帰り・反映」を回す。Owner が「監査を回して」
「回しといて」「監査溜まってない？」と言ったら、

  1. to_gpt/ 直下を未回答 REQUEST だけにする (answered は to_gpt/processed/ へ退避)
  2. from_gpt/ の RESULT を読み、_AUDIT_LEDGER.jsonl に追記する
  3. result_label から next_action_type を分類する
  4. action-queue (reflected:false の一覧 = Claude が次にやること) を出す
  5. Owner 向け 5 行サマリを出す
  6. 承認不要処理 (退避・台帳・ルーティング) と承認必要処理 (accepted化等) を分ける

このツールが行うのは「承認不要な監査事務」だけ。accepted/canonical 化、
Generated Index backfill、本番 DB 投入、SF 書戻し、外部送信は OWNER_GATED であり、
このツールは絶対に実行しない (refuse する)。

root は Box Drive 同期パス (例: ~/Library/CloudStorage/Box-Box/.../gpt_ometsuke)
を --root か環境変数 ALO_GPT_AUDIT_ROOT で渡す。**単一書き手**で実行すること。
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Iterable

# --------------------------------------------------------------------------- #
# 語彙 (vocabulary) — DESIGN v0.3 §A/§C, LOOP_RULE §4/§8, APPROVAL_RULE §1/§2
# --------------------------------------------------------------------------- #

# RESULT 先頭ラベルの verdict 接尾辞。長いものから順に照合する (PASS_WITH_NOTES を
# PASS より先に判定するため)。REJECT/ESCALATE_OWNER は現場で観測される別名。
VERDICTS = [
    "PASS_WITH_NOTES",
    "MODIFY_REQUIRED",
    "ESCALATE_OWNER",
    "NEED_MORE",
    "REJECT",
    "FAIL",
    "PASS",
]

# 正規化: 観測される別名を正本 5 区分へ寄せる。
VERDICT_CANON = {
    "PASS": "PASS",
    "PASS_WITH_NOTES": "PASS_WITH_NOTES",
    "MODIFY_REQUIRED": "MODIFY_REQUIRED",
    "NEED_MORE": "NEED_MORE",
    "FAIL": "FAIL",
    "REJECT": "FAIL",            # REJECT は FAIL 系として reject 処理
    "ESCALATE_OWNER": "NEED_MORE",  # owner 判断必要 = NEED_MORE(ambiguity_owner)
}

# result_label(正規化後) -> next_action_type  (LOOP_RULE §3, DESIGN v0.3 §C)
NEXT_ACTION = {
    "PASS": "ratify",
    "PASS_WITH_NOTES": "ratify",        # blocking notes があれば patch へ降格 (§F)
    "MODIFY_REQUIRED": "patch",
    "NEED_MORE": "required_materials",
    "FAIL": "reject",
}

# next_action_type -> route カードを置くキュー (ROUTE_RULES Rule 4)
QUEUE_FOR_ACTION = {
    "ratify": "approval_queue",
    "patch": "patch_queue",
    "required_materials": "material_queue",
    "reject": "rejected_queue",
    "none": None,
}

# ratify が必要か / 再投函が想定されるか (DESIGN v0.3 §C 表)
RATIFY_REQUIRED = {"PASS": True, "PASS_WITH_NOTES": True}
REQUEUE_EXPECTED = {"MODIFY_REQUIRED": True, "NEED_MORE": True}

# loop_state (LOOP_RULE §11): returned | reflected | requeued | ratify_wait | closed
LOOP_STATES = {"returned", "reflected", "requeued", "ratify_wait", "closed"}

# 承認不要 / 承認必要 (APPROVAL_RULE §1, §2 / ROUTE_RULES Rule 2,3)
APPROVAL_FREE_OPS = {
    "result_save",          # RESULT ファイル保存
    "request_retreat",      # REQUEST を processed/ へ退避
    "ledger_append",        # 監査台帳追記
    "action_queue_update",  # action queue 更新 / route カード作成
    "status",               # 読取・検査
    "dry_run",
}
OWNER_GATED_OPS = {
    "accepted_promotion",   # DD を accepted/canonical 化
    "canonical_designation",
    "index_backfill",       # Generated Index / design_decisions backfill
    "production_db",        # 本番 DB 投入・DDL 適用
    "sf_writeback",         # Salesforce 書戻し
    "external_send",        # 外部送信・公開
}

LEDGER_NAME = "_AUDIT_LEDGER.jsonl"
PROCESSED_DIRNAME = "processed"
QUEUE_DIRS = ["approval_queue", "patch_queue", "material_queue", "rejected_queue"]

REQUEST_SUFFIX = "_REQUEST.md"          # active REQUEST (top-level)
RESULT_SUFFIX = "_RESULT.md"
PROCESSED_INPLACE_SUFFIX = "_REQUEST.processed.md"  # 旧式: その場リネーム退避

LABEL_RE = re.compile(r"^([A-Z][A-Z0-9]*)_(" + "|".join(VERDICTS) + r")\s*$")


# --------------------------------------------------------------------------- #
# handoff lane (operational; non_mutating only; feature-flagged, default off)
# Design: HANDOFF_OPERATIONAL_IMPL_DESIGN v0.1 (RATIFIED 2026-06-23).
# Audit: 20260623_handoff_operational_impl_v0.1 GPTPRO PASS_WITH_NOTES.
# must_fix: blocked -> no route card (#1); blocked reason append-only (#2);
#   single validator source (#3); feature flag default off (#4).
# --------------------------------------------------------------------------- #

# (#4) default off; owner ratify turns it on via env.
HANDOFF_LANE_ENABLED = os.environ.get("ALO_HANDOFF_LANE", "0") == "1"
HANDOFF_QUEUE = "handoff_queue"

# (#3) single validator implementation: import the prototype validator as the
# one source of truth instead of redefining the rules here.
import sys as _sys  # noqa: E402
_PROTO_DIR = Path(__file__).resolve().parent / "handoff_proto"
if str(_PROTO_DIR) not in _sys.path:
    _sys.path.insert(0, str(_PROTO_DIR))
try:
    from validator import Env as HandoffEnv  # noqa: E402
    from validator import validate_dispatch as handoff_validate_dispatch  # noqa: E402
    HANDOFF_VALIDATOR_AVAILABLE = True
except Exception:  # pragma: no cover - import guard
    HANDOFF_VALIDATOR_AVAILABLE = False


def now_jst_iso() -> str:
    """JST の ISO8601 タイムスタンプ。"""
    jst = datetime.timezone(datetime.timedelta(hours=9))
    return datetime.datetime.now(jst).replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------- #
# front-matter パーサ (依存ゼロ。PyYAML を使わない最小 YAML サブセット)
# --------------------------------------------------------------------------- #


def parse_front_matter(text: str) -> dict:
    """`---` で囲まれた front-matter を読む。

    対応: top-level スカラー (key: value)、リスト (key: のあと `- item`)、
    1 段ネストのマッピング (key: のあと indented `subkey: value`)。
    lint で「キーの有無」を見れば足りるので完全 YAML は不要。
    """
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    # 最初の '---' の次から、次の '---' までを front-matter とする
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}
    fm: dict = {}
    current_list_key: str | None = None
    current_map_key: str | None = None
    for raw in lines[1:end]:
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip())
        stripped = raw.strip()
        if stripped.startswith("- "):
            # リスト要素
            if current_list_key is not None:
                fm.setdefault(current_list_key, [])
                if isinstance(fm[current_list_key], list):
                    fm[current_list_key].append(stripped[2:].strip())
            continue
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if indent > 0 and current_map_key is not None:
                # ネストしたマッピングの子。親キーに「存在」を記録。
                fm.setdefault(current_map_key, {})
                if isinstance(fm[current_map_key], dict):
                    fm[current_map_key][key] = val
                continue
            # top-level キー
            if val == "":
                # 値が無い -> 次行がリスト or ネストマップ
                fm[key] = ""
                current_list_key = key
                current_map_key = key
            else:
                fm[key] = val
                current_list_key = None
                current_map_key = None
    return fm


def _strip_bom(text: str) -> str:
    return text.lstrip("﻿")


# --------------------------------------------------------------------------- #
# データモデル
# --------------------------------------------------------------------------- #


@dataclasses.dataclass
class Result:
    path: Path
    filename: str
    raw_label: str | None          # 先頭行そのまま (bad label 検出用)
    label: str | None              # 正規化された <GATE>_<VERDICT> or None
    gate: str | None
    verdict: str | None            # 正規化後 (PASS/PASS_WITH_NOTES/...)
    request_id_in_body: str | None
    text: str

    @property
    def is_valid_label(self) -> bool:
        return self.label is not None


@dataclasses.dataclass
class Request:
    path: Path
    filename: str
    request_id: str | None
    gate: str | None
    status: str                    # request_status: queued/blocked/superseded/cancelled
    result_expected_filename: str | None
    front_matter: dict
    in_processed: bool             # processed/ 配下にあるか


@dataclasses.dataclass
class Match:
    request: Request
    result: Result | None
    lane_status: str               # active / answered_not_processed / missing_result / bad_label / skipped
    reason: str


# --------------------------------------------------------------------------- #
# 読み込み
# --------------------------------------------------------------------------- #


def parse_result(path: Path) -> Result:
    text = _strip_bom(path.read_text(encoding="utf-8", errors="replace"))
    first = ""
    for line in text.splitlines():
        if line.strip():
            first = line.strip()
            break
    m = LABEL_RE.match(first)
    label = gate = verdict = None
    if m:
        gate = m.group(1)
        raw_verdict = m.group(2)
        verdict = VERDICT_CANON.get(raw_verdict, raw_verdict)
        label = first
    # body 内の request_id を拾う (`request_id:` / `request:` 行)
    rid = None
    mm = re.search(r"^\s*request_id:\s*(\S+)", text, re.MULTILINE)
    if mm:
        rid = mm.group(1)
    else:
        mm = re.search(r"^\s*request:\s*(\S+)", text, re.MULTILINE)
        if mm:
            rid = mm.group(1)
    return Result(
        path=path,
        filename=path.name,
        raw_label=first or None,
        label=label,
        gate=gate,
        verdict=verdict,
        request_id_in_body=rid,
        text=text,
    )


def parse_request(path: Path, in_processed: bool) -> Request:
    text = _strip_bom(path.read_text(encoding="utf-8", errors="replace"))
    fm = parse_front_matter(text)
    return Request(
        path=path,
        filename=path.name,
        request_id=fm.get("request_id") or None,
        gate=fm.get("gate") or None,
        status=(fm.get("status") or "queued").strip() or "queued",
        result_expected_filename=fm.get("result_expected_filename") or None,
        front_matter=fm,
        in_processed=in_processed,
    )


class Lane:
    """gpt_ometsuke レーンの read 層。"""

    def __init__(self, root: Path):
        self.root = root
        self.to_gpt = root / "to_gpt"
        self.processed = self.to_gpt / PROCESSED_DIRNAME
        self.from_gpt = root / "from_gpt"
        self.ledger_path = root / LEDGER_NAME

    # ----- discovery ----- #
    def active_requests(self) -> list[Request]:
        """to_gpt/ 直下 (processed/ を除く) の active REQUEST。

        `*_REQUEST.md` だけ。`*_REQUEST.processed.md` (旧式その場退避) は active で
        ない。
        """
        out = []
        if not self.to_gpt.is_dir():
            return out
        for p in sorted(self.to_gpt.iterdir()):
            if p.is_dir():
                continue
            if p.name.endswith(PROCESSED_INPLACE_SUFFIX):
                continue
            if p.name.endswith(REQUEST_SUFFIX):
                out.append(parse_request(p, in_processed=False))
        return out

    def inplace_processed_requests(self) -> list[Request]:
        """to_gpt/ 直下に残る旧式 `*_REQUEST.processed.md` (要 relocate)。"""
        out = []
        if not self.to_gpt.is_dir():
            return out
        for p in sorted(self.to_gpt.iterdir()):
            if p.is_file() and p.name.endswith(PROCESSED_INPLACE_SUFFIX):
                out.append(parse_request(p, in_processed=True))
        return out

    def processed_requests(self) -> list[Request]:
        out = []
        if not self.processed.is_dir():
            return out
        for p in sorted(self.processed.iterdir()):
            if p.is_file() and p.name.endswith(".md"):
                out.append(parse_request(p, in_processed=True))
        return out

    def results(self) -> list[Result]:
        out = []
        if not self.from_gpt.is_dir():
            return out
        for p in sorted(self.from_gpt.iterdir()):
            if p.is_file() and p.name.endswith(RESULT_SUFFIX):
                out.append(parse_result(p))
        return out

    # ----- matching (DESIGN v0.3 §I 三点照合) ----- #
    def match_request(self, req: Request, results: list[Result]) -> Match:
        """REQUEST に対応する RESULT を三点照合で探す。

        優先順:
          1) result_expected_filename と一致するファイルがある (最強・言語非依存)
          2) result ファイル名が REQUEST ファイル名の _REQUEST->_RESULT 置換と一致
          3) request_id が result 本文 / ファイル名に含まれ、かつ gate 一致
        """
        if req.status in ("superseded", "cancelled"):
            return Match(req, None, "skipped", f"request_status={req.status}")

        cand: Result | None = None
        reason = ""

        # 1) result_expected_filename
        if req.result_expected_filename:
            for r in results:
                if r.filename == req.result_expected_filename:
                    cand, reason = r, "result_expected_filename"
                    break

        # 2) ファイル名規約 (_REQUEST.md -> _RESULT.md)
        if cand is None and req.filename.endswith(REQUEST_SUFFIX):
            guess = req.filename[: -len(REQUEST_SUFFIX)] + RESULT_SUFFIX
            for r in results:
                if r.filename == guess:
                    cand, reason = r, "filename_convention"
                    break

        # 3) request_id 照合 + gate 一致
        if cand is None and req.request_id:
            for r in results:
                rid_hit = (
                    (r.request_id_in_body and req.request_id in r.request_id_in_body)
                    or (req.request_id in r.text)
                    or r.filename.startswith(req.request_id)
                )
                gate_ok = (req.gate is None) or (r.gate == req.gate)
                if rid_hit and gate_ok:
                    cand, reason = r, "request_id+gate"
                    break

        if cand is None:
            return Match(req, None, "missing_result", "no RESULT found")
        if not cand.is_valid_label:
            return Match(req, cand, "bad_label",
                         f"first line not a valid label: {cand.raw_label!r}")
        return Match(req, cand, "answered_not_processed", reason)

    def matches(self) -> list[Match]:
        results = self.results()
        return [self.match_request(r, results) for r in self.active_requests()]

    # ----- ledger ----- #
    def read_ledger(self) -> list[dict]:
        if not self.ledger_path.is_file():
            return []
        out = []
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                # 壊れた行はスキップ (台帳は派生控え。SoT はフォルダ位置)
                continue
        return out

    def append_ledger(self, entry: dict) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- #
# RESULT 本文からの best-effort 抽出
# --------------------------------------------------------------------------- #


def extract_list_block(text: str, key: str) -> list[str]:
    """`key:` の下にぶら下がる `- ...` 行 (or `key: [a, b]`) を拾う。"""
    items: list[str] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(rf"^\s*{re.escape(key)}\s*:\s*(.*)$", line)
        if not m:
            continue
        inline = m.group(1).strip()
        if inline.startswith("[") and inline.endswith("]"):
            body = inline[1:-1].strip()
            if body:
                items += [x.strip().strip("'\"") for x in body.split(",") if x.strip()]
            return items
        base_indent = len(line) - len(line.lstrip())
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                continue
            ind = len(nxt) - len(nxt.lstrip())
            s = nxt.strip()
            if s.startswith("- ") and ind > base_indent:
                items.append(s[2:].strip())
            elif ind <= base_indent:
                break
        return items
    return items


def extract_scalar(text: str, key: str) -> str | None:
    m = re.search(rf"^\s*{re.escape(key)}\s*:\s*(\S.*)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def derive_next_action(verdict: str, blocking: list[str]) -> str:
    if verdict == "PASS_WITH_NOTES" and blocking:
        return "patch"  # blocking notes があるなら ratify でなく patch (§F)
    return NEXT_ACTION.get(verdict, "none")


def derive_loop_state(verdict: str, next_action: str, blocking: list[str]) -> str:
    if verdict in ("PASS", "PASS_WITH_NOTES") and not blocking:
        return "ratify_wait"
    return "returned"


def make_owner_digest(topic: str, request_id: str, verdict: str,
                      reasons: list[str], next_action: str,
                      ratify_required: bool, blocking: list[str]) -> str:
    """Owner 向け 5 行サマリ (LOOP_RULE §5)。"""
    if next_action == "patch":
        next_line = "Claude が patch 作成"
    elif next_action == "required_materials":
        next_line = "Claude が資料補充して再投函"
    elif next_action == "ratify":
        next_line = "ratify 待ち" if not blocking else "blocking 反映後 ratify"
    elif next_action == "reject":
        next_line = "別案起票 (reject)"
    else:
        next_line = "なし"

    if verdict in ("PASS", "PASS_WITH_NOTES"):
        owner_line = "ratify必要" if ratify_required else "不要"
        if blocking:
            owner_line = "判断必要 (blocking あり)"
    elif verdict == "NEED_MORE":
        owner_line = "判断必要" if any("owner" in r.lower() for r in reasons) else "不要"
    elif verdict == "FAIL":
        owner_line = "判断必要"
    else:
        owner_line = "不要"

    reason_str = " / ".join(reasons[:2]) if reasons else "(RESULT本文参照)"
    return (
        f"監査: {topic} / {request_id}\n"
        f"結論: {verdict}\n"
        f"理由: {reason_str}\n"
        f"次アクション: {next_line}\n"
        f"Owner確認: {owner_line}"
    )


def make_claude_rethink_prompt(verdict: str, next_action: str, gate: str,
                               blocking: list[str], missing: list[str]) -> str:
    """Claude が次に再思考すべき内容 (LOOP_RULE §7/§8)。"""
    if next_action == "patch":
        head = f"[{gate}] MODIFY: GPT 指摘を patch に反映し新 version で再投函する。"
        if blocking:
            head += " blocking: " + "; ".join(blocking[:3])
        return head
    if next_action == "required_materials":
        head = f"[{gate}] NEED_MORE: 資料を補充して再投函する。"
        if missing:
            head += " 不足: " + "; ".join(missing[:5])
        return head
    if next_action == "ratify":
        if blocking:
            return (f"[{gate}] PASS_WITH_NOTES: blocking notes を反映してから "
                    "Owner ratify を依頼する。blocking: " + "; ".join(blocking[:3]))
        return f"[{gate}] PASS: accepted 候補。Owner ratify を依頼する (昇格は要承認)。"
    if next_action == "reject":
        return f"[{gate}] FAIL: 別案を起票する。元案は昇格しない。"
    return f"[{gate}] 次アクションなし。"


def build_record(match: Match, *, event: str) -> dict:
    """RESULT から台帳 1 レコードを組み立てる (LOOP_RULE §2/§8/§11 の全項目)。"""
    req = match.request
    res = match.result
    assert res is not None and res.verdict is not None

    verdict = res.verdict
    topic = req.front_matter.get("topic") or (req.request_id or req.filename)
    blocking = extract_list_block(res.text, "blocking_before_ratify")
    missing = extract_list_block(res.text, "missing_materials")
    if not missing:
        missing = extract_list_block(res.text, "required_materials")
    need_more_type = extract_scalar(res.text, "need_more_type")

    next_action = derive_next_action(verdict, blocking)
    ratify_required = bool(RATIFY_REQUIRED.get(verdict, False))
    requeue_expected = bool(REQUEUE_EXPECTED.get(verdict, False))
    loop_state = derive_loop_state(verdict, next_action, blocking)

    # 理由 (best-effort): verdict 行直後の見出し or required_patches 先頭
    reasons: list[str] = []
    rp = extract_list_block(res.text, "required_patches")
    if rp:
        reasons = rp[:2]

    owner_digest = make_owner_digest(
        topic, req.request_id or req.filename, verdict, reasons,
        next_action, ratify_required, blocking)
    rethink = make_claude_rethink_prompt(
        verdict, next_action, res.gate or "?", blocking, missing)

    return {
        "ts": now_jst_iso(),
        "event": event,                       # close / route / reflect
        "request_id": req.request_id,
        "request_filename": req.filename,
        "result_filename": res.filename,
        "result_label": res.label,
        "verdict": verdict,
        "gate": res.gate,
        "next_action_type": next_action,
        "ratify_required": ratify_required,
        "requeue_expected": requeue_expected,
        "need_more_type": need_more_type,
        "reflected": False,
        "blocking_before_ratify": blocking,
        "missing_materials": missing,
        "owner_digest_5line": owner_digest,
        "claude_rethink_prompt": rethink,
        "loop_state": loop_state,
        "queue": QUEUE_FOR_ACTION.get(next_action),
        "approval_required_to_act": next_action in ("ratify",),  # 昇格は要承認
    }


# --------------------------------------------------------------------------- #
# 操作 (commands)
# --------------------------------------------------------------------------- #


def ledger_has(lane: Lane, request_id: str, result_filename: str,
               event: str) -> bool:
    """同じ (request_id, result_filename, event) が既に台帳にあるか (idempotency)。"""
    for e in lane.read_ledger():
        if (e.get("request_id") == request_id
                and e.get("result_filename") == result_filename
                and e.get("event") == event):
            return True
    return False


def write_route_card(lane: Lane, record: dict, apply: bool) -> str | None:
    """next_action に応じたキューへ route カードを置く。冪等。"""
    queue = record.get("queue")
    if not queue:
        return None
    qdir = lane.root / queue
    card_name = f"{record['request_id']}_CARD.md"
    card_path = qdir / card_name
    if card_path.exists():
        return f"card exists (skip): {queue}/{card_name}"
    if not apply:
        return f"would create card: {queue}/{card_name}"
    qdir.mkdir(parents=True, exist_ok=True)
    body = (
        f"# action card: {record['request_id']}\n\n"
        f"- result_label: {record['result_label']}\n"
        f"- next_action_type: {record['next_action_type']}\n"
        f"- ratify_required: {record['ratify_required']}\n"
        f"- requeue_expected: {record['requeue_expected']}\n"
        f"- reflected: {record['reflected']}\n"
        f"- loop_state: {record['loop_state']}\n"
        f"- result_filename: {record['result_filename']}\n\n"
        f"## owner digest\n```\n{record['owner_digest_5line']}\n```\n\n"
        f"## claude rethink\n{record['claude_rethink_prompt']}\n"
    )
    card_path.write_text(body, encoding="utf-8")
    return f"created card: {queue}/{card_name}"


def close_match(lane: Lane, match: Match, apply: bool, log) -> bool:
    """1 件を close: processed 退避 + 台帳追記 + route カード。

    APPROVAL_RULE §3 の機械チェック必須:
      1) RESULT が from_gpt に存在
      2) RESULT 先頭行が allowed label
      3) RESULT 本文に request_id (best-effort)
      4) REQUEST と RESULT の request_id 一致 (best-effort)
      5) 退避先に既にあれば idempotent
      6) RESULT 不在 / bad label は移動しない
    """
    req = match.request
    res = match.result
    if match.lane_status != "answered_not_processed":
        log(f"  SKIP {req.filename}: lane_status={match.lane_status} ({match.reason})")
        return False
    assert res is not None

    dest = lane.processed / req.filename
    record = build_record(match, event="close")

    # idempotency: 既に processed にあり、台帳にも close 済みなら何もしない
    already_moved = dest.exists() or not req.path.exists()
    already_ledgered = ledger_has(lane, req.request_id or "", res.filename, "close")

    if already_moved and already_ledgered:
        log(f"  IDEMPOTENT {req.filename}: already processed + ledgered")
        # route カードだけ未作成なら冪等に作る
        msg = write_route_card(lane, record, apply)
        if msg:
            log(f"    {msg}")
        return False

    if not apply:
        log(f"  WOULD CLOSE {req.filename}")
        log(f"    result : {res.filename}  [{res.label}] -> {record['next_action_type']}")
        log(f"    move   : to_gpt/{req.filename} -> to_gpt/processed/{req.filename}")
        log(f"    ledger : append close ({record['loop_state']})")
        msg = write_route_card(lane, record, apply=False)
        if msg:
            log(f"    {msg}")
        return True

    # --- apply --- #
    lane.processed.mkdir(parents=True, exist_ok=True)
    if req.path.exists() and not dest.exists():
        shutil.move(str(req.path), str(dest))
        log(f"  MOVED {req.filename} -> processed/")
    elif req.path.exists() and dest.exists():
        # 退避先に既存 -> 元を消さず残す (単一書き手前提だが安全側)
        log(f"  CONFLICT {req.filename}: dest exists, left source in place")
    else:
        log(f"  ALREADY-MOVED {req.filename}")

    if not already_ledgered:
        lane.append_ledger(record)
        log(f"  LEDGER append: {req.request_id} [{res.label}] {record['loop_state']}")
    msg = write_route_card(lane, record, apply=True)
    if msg:
        log(f"    {msg}")
    return True


# --------------------------------------------------------------------------- #
# action-queue: ledger 派生ビュー (DESIGN v0.3 §D)
# --------------------------------------------------------------------------- #


def latest_state_per_request(lane: Lane) -> dict[str, dict]:
    """request_id ごとに最新の台帳レコードを返す (後勝ち)。"""
    latest: dict[str, dict] = {}
    for e in lane.read_ledger():
        rid = e.get("request_id")
        if not rid:
            continue
        latest[rid] = e  # 行は時系列なので後勝ちで最新が残る
    return latest


def action_queue(lane: Lane) -> list[dict]:
    """reflected:false (= 未反映) のレコードを next_action 付きで返す。"""
    out = []
    for rid, e in latest_state_per_request(lane).items():
        if e.get("reflected"):
            continue
        if e.get("loop_state") == "closed":
            continue
        out.append(e)
    # next_action の緊急度でソート: patch/material 先、ratify 後
    order = {"patch": 0, "required_materials": 1, "reject": 2, "ratify": 3, "none": 4}
    out.sort(key=lambda e: (order.get(e.get("next_action_type"), 9),
                            e.get("request_id") or ""))
    return out


# --------------------------------------------------------------------------- #
# lint: REQUEST preflight (DESIGN v0.3 §G)
# --------------------------------------------------------------------------- #

T2_REQUIRED_KEYS = [
    "review_scope", "regression_anchors", "decision_requested",
    "target_mode", "source_hash",
]


def lint_request(req: Request) -> list[str]:
    problems = []
    if not req.request_id:
        problems.append("request_id 欠落")
    if not req.gate:
        problems.append("gate 欠落")
    if not req.result_expected_filename:
        problems.append("result_expected_filename 欠落 (照合が弱くなる)")
    if req.status not in ("queued", "blocked", "superseded", "cancelled"):
        problems.append(f"status が runtime 語彙でない: {req.status!r}")
    # T2 推奨キー
    for k in T2_REQUIRED_KEYS:
        if k not in req.front_matter:
            problems.append(f"T2必須キー欠落(推奨): {k}")
    return problems


# --------------------------------------------------------------------------- #
# CLI コマンド本体
# --------------------------------------------------------------------------- #


def resolve_root(args) -> Path:
    root = args.root or os.environ.get("ALO_GPT_AUDIT_ROOT")
    if not root:
        sys.exit("error: --root か環境変数 ALO_GPT_AUDIT_ROOT で gpt_ometsuke を指定してください")
    p = Path(root).expanduser()
    if not p.is_dir():
        sys.exit(f"error: root が存在しません: {p}")
    return p


def cmd_status(lane: Lane, args) -> int:
    matches = lane.matches()
    counts: dict[str, int] = {}
    for m in matches:
        counts[m.lane_status] = counts.get(m.lane_status, 0) + 1
    inplace = lane.inplace_processed_requests()

    print(f"# audit lane status — {lane.root}")
    print(f"to_gpt 直下 active REQUEST 総数 : {len(matches)}")
    print(f"  answered_not_processed (要 close): {counts.get('answered_not_processed', 0)}")
    print(f"  missing_result (未回答 / GPT待ち) : {counts.get('missing_result', 0)}")
    print(f"  bad_label (移動しない)            : {counts.get('bad_label', 0)}")
    print(f"  skipped (superseded/cancelled)    : {counts.get('skipped', 0)}")
    print(f"旧式 *_REQUEST.processed.md (要 relocate): {len(inplace)}")
    print()
    for m in matches:
        rid = m.request.request_id or m.request.filename
        extra = ""
        if m.result:
            extra = f"  <- {m.result.filename} [{m.result.label or m.result.raw_label}]"
        print(f"  [{m.lane_status}] {rid}{extra}")
    if args.verbose and inplace:
        print("\n旧式その場退避 (processed/ へ relocate 推奨):")
        for r in inplace:
            print(f"  {r.filename}")
    return 0


def cmd_close(lane: Lane, args) -> int:
    target = args.request_id
    matches = lane.matches()
    found = [m for m in matches
             if (m.request.request_id == target) or (m.request.filename == target)
             or (m.request.filename.startswith(target))]
    if not found:
        print(f"error: REQUEST が見つかりません: {target}")
        return 1
    apply = args.apply
    print(f"# close {'(APPLY)' if apply else '(dry-run)'} — {target}")
    changed = False
    for m in found:
        changed |= close_match(lane, m, apply, log=print)
    if not apply:
        print("\n(dry-run。実行するには --apply)")
    return 0 if changed or apply else 0


def cmd_close_all(lane: Lane, args) -> int:
    apply = args.apply
    print(f"# close-all {'(APPLY)' if apply else '(dry-run, 既定)'} — {lane.root}")
    matches = lane.matches()
    answered = [m for m in matches if m.lane_status == "answered_not_processed"]
    skipped = [m for m in matches if m.lane_status in ("bad_label", "missing_result")]
    if not answered:
        print("answered_not_processed なし。退避対象は 0 件。")
    for m in answered:
        close_match(lane, m, apply, log=print)
    if skipped:
        print("\n移動しない (理由付き):")
        for m in skipped:
            rid = m.request.request_id or m.request.filename
            print(f"  [{m.lane_status}] {rid}: {m.reason}")
    if not apply:
        print("\n(dry-run。承認不要処理だが既定は安全側。実行は --apply)")
    return 0


def cmd_action_queue(lane: Lane, args) -> int:
    q = action_queue(lane)
    print(f"# action-queue (reflected:false) — {len(q)} 件")
    print("Claude が次に何をすべきか:\n")
    if not q:
        print("  (未反映の監査結果なし。すべて reflected または closed)")
        return 0
    for e in q:
        print(f"● {e.get('request_id')}  [{e.get('result_label')}]")
        print(f"    next_action : {e.get('next_action_type')}  "
              f"(loop_state={e.get('loop_state')})")
        if e.get("blocking_before_ratify"):
            print(f"    blocking    : {e['blocking_before_ratify']}")
        if e.get("missing_materials"):
            print(f"    missing     : {e['missing_materials']}")
        print(f"    do          : {e.get('claude_rethink_prompt')}")
        print()
    return 0


def cmd_owner_digest(lane: Lane, args) -> int:
    q = action_queue(lane) if not args.all else list(
        latest_state_per_request(lane).values())
    print(f"# Owner 5行サマリ — {len(q)} 件\n")
    for e in q:
        print(e.get("owner_digest_5line", "(no digest)"))
        print("---")
    return 0


def cmd_lint(lane: Lane, args) -> int:
    reqs = lane.active_requests()
    print(f"# lint — active REQUEST {len(reqs)} 件")
    bad = 0
    for r in reqs:
        problems = lint_request(r)
        if problems:
            bad += 1
            print(f"\n✗ {r.filename} (request_id={r.request_id})")
            for p in problems:
                print(f"    - {p}")
        else:
            print(f"✓ {r.filename}")
    print(f"\n{bad}/{len(reqs)} 件に指摘あり")
    return 1 if bad else 0


def cmd_reflect(lane: Lane, args) -> int:
    """RESULT を反映済みにする (reflected:true)。承認不要処理。

    台帳は append-only。最新状態に reflect イベントを追記する。
    """
    rid = args.request_id
    latest = latest_state_per_request(lane).get(rid)
    if not latest:
        print(f"error: 台帳に request_id={rid} がありません")
        return 1
    if latest.get("reflected"):
        print(f"既に reflected: {rid}")
        return 0
    entry = dict(latest)
    entry["ts"] = now_jst_iso()
    entry["event"] = "reflect"
    entry["reflected"] = True
    entry["loop_state"] = "closed" if entry.get("next_action_type") in (
        "none", "reject") else "reflected"
    if args.apply:
        lane.append_ledger(entry)
        print(f"REFLECTED {rid} -> loop_state={entry['loop_state']}")
    else:
        print(f"WOULD REFLECT {rid} -> loop_state={entry['loop_state']} (--apply で実行)")
    return 0


def cmd_gate_check(lane: Lane, args) -> int:
    """承認要否の判定表を出す (APPROVAL_RULE §1/§2)。"""
    op = args.operation
    if op in APPROVAL_FREE_OPS:
        print(f"{op}: 承認不要 (監査レーン内の事務処理)")
        return 0
    if op in OWNER_GATED_OPS:
        print(f"{op}: 承認必要 (Owner ratify / 所定 T2 ゲート)。このツールは実行しません。")
        return 2
    print(f"{op}: 未知の操作。安全側で承認必要とみなします。")
    return 2


def cmd_health(lane: Lane, args) -> int:
    report = health_report(lane)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_health_md(report))
    return 0


def health_report(lane: Lane) -> dict:
    matches = lane.matches()
    counts: dict[str, int] = {}
    for m in matches:
        counts[m.lane_status] = counts.get(m.lane_status, 0) + 1
    q = action_queue(lane)
    by_action: dict[str, int] = {}
    for e in q:
        a = e.get("next_action_type", "none")
        by_action[a] = by_action.get(a, 0) + 1
    queue_sizes = {}
    for d in QUEUE_DIRS:
        p = lane.root / d
        queue_sizes[d] = sum(1 for _ in p.glob("*.md")) if p.is_dir() else 0
    ledger = lane.read_ledger()
    return {
        "generated_at_jst": now_jst_iso(),
        "root": str(lane.root),
        "active_requests": len(matches),
        "lane_status_counts": counts,
        "inplace_processed_pending_relocate": len(lane.inplace_processed_requests()),
        "results_total": len(lane.results()),
        "processed_requests": len(lane.processed_requests()),
        "ledger_events": len(ledger),
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
        f"- generated_at_jst: {r['generated_at_jst']}",
        f"- root: {r['root']}",
        "",
        "## サマリ",
        f"- to_gpt 直下 active REQUEST: {r['active_requests']}",
        f"- 未反映 action item (reflected:false): {r['unreflected_action_items']}",
        f"- from_gpt RESULT 総数: {r['results_total']}",
        f"- processed REQUEST: {r['processed_requests']}",
        f"- 台帳イベント数: {r['ledger_events']}",
        f"- 旧式 *_REQUEST.processed.md (要 relocate): "
        f"{r['inplace_processed_pending_relocate']}",
        "",
        "## lane_status 内訳",
    ]
    for k, v in sorted(r["lane_status_counts"].items()):
        lines.append(f"- {k}: {v}")
    lines += ["", "## next_action 内訳"]
    if r["action_queue_by_type"]:
        for k, v in sorted(r["action_queue_by_type"].items()):
            lines.append(f"- {k}: {v}")
    else:
        lines.append("- (未反映なし)")
    lines += ["", "## route queue サイズ"]
    for k, v in r["route_queue_sizes"].items():
        lines.append(f"- {k}: {v}")
    if r["action_items"]:
        lines += ["", "## 未反映 action item"]
        for it in r["action_items"]:
            lines.append(
                f"- {it['request_id']} [{it['result_label']}] "
                f"-> {it['next_action_type']} ({it['loop_state']})")
    health = "GREEN"
    if r["lane_status_counts"].get("bad_label"):
        health = "RED (bad_label あり)"
    elif r["unreflected_action_items"] > 0:
        health = "YELLOW (未反映 action item あり)"
    lines += ["", f"## health: {health}"]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# handoff lane commands (non_mutating only; fail-closed; flag-gated writes)
# --------------------------------------------------------------------------- #


def write_handoff_card(lane: Lane, packet: dict, verdict, apply: bool) -> str:
    """Dispatchable non_mutating packet -> route card in handoff_queue. Idempotent.

    Writes only when apply AND HANDOFF_LANE_ENABLED. Never called for blocked
    packets (must_fix #1)."""
    pid = packet.get("packet_id", "UNKNOWN")
    qdir = lane.root / HANDOFF_QUEUE
    card_path = qdir / f"{pid}_DISPATCH_CARD.md"
    if card_path.exists():
        return f"card exists (skip): {HANDOFF_QUEUE}/{card_path.name}"
    if not (apply and HANDOFF_LANE_ENABLED):
        return f"would create card: {HANDOFF_QUEUE}/{card_path.name} (flag off / dry-run)"
    qdir.mkdir(parents=True, exist_ok=True)
    body = (
        f"# handoff dispatch card: {pid}\n\n"
        f"- assignee: {packet.get('assignee')}\n"
        f"- execution_role: {packet.get('execution_role')}\n"
        f"- next_action_type: {packet.get('next_action_type')}\n"
        f"- mutation_class: {verdict.mutation_class}\n"
        f"- egress_decision: {verdict.egress_decision}\n"
        f"- resource_effect_class: {verdict.resource_effect_class}\n"
        f"- objective: {packet.get('objective', '')}\n"
    )
    card_path.write_text(body, encoding="utf-8")
    return f"created card: {HANDOFF_QUEUE}/{card_path.name}"


def handoff_validate_packet(lane: Lane, packet: dict, *, apply: bool, log) -> int:
    """Validate one DISPATCH packet through the single-source validator.

    fail-closed Env (lease/permit/audit subsystems unavailable). Blocked packets
    get NO route card (#1) and an append-only ledger entry (#2). Only the
    non_mutating lane is operational; everything else stays blocked/hold."""
    if not HANDOFF_VALIDATOR_AVAILABLE:
        log("  handoff validator unavailable (import failed)")
        return 3
    env = HandoffEnv()  # all subsystems unavailable -> fail-closed (design §3)
    v = handoff_validate_dispatch(dict(packet), env)
    pid = packet.get("packet_id", "UNKNOWN")
    log(f"  packet={pid} dispatchable={v.dispatchable} "
        f"block_reason={v.block_reason} mutation={v.mutation_class} "
        f"egress={v.egress_decision} resource={v.resource_effect_class}")

    if not v.dispatchable:
        entry = {
            "ts": now_jst_iso(),
            "event": "handoff_blocked",
            "packet_id": pid,
            "source_queue_item_id": packet.get("source_queue_item_id"),
            "block_reason": v.block_reason,
            "mutation_class": v.mutation_class,
            "egress_decision": v.egress_decision,
            "resource_effect_class": v.resource_effect_class,
        }
        if apply and HANDOFF_LANE_ENABLED:
            lane.append_ledger(entry)  # (#2) append-only blocked record
            log(f"  BLOCKED -> no card; ledger appended ({v.block_reason})")
        else:
            log(f"  BLOCKED -> no card; would append ledger ({v.block_reason}) "
                f"[flag off / dry-run]")
        return 0

    log(write_handoff_card(lane, packet, v, apply))
    return 0


def cmd_handoff_validate(lane: Lane, args) -> int:
    log = print
    if not HANDOFF_LANE_ENABLED:
        log("handoff lane: DISABLED (default). set ALO_HANDOFF_LANE=1 to enable "
            "writes after owner ratify. running read-only.")
    try:
        packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - arg error
        log(f"cannot read packet json: {exc}")
        return 2
    packets = packet if isinstance(packet, list) else [packet]
    rc = 0
    for p in packets:
        rc = handoff_validate_packet(lane, p, apply=args.apply, log=log) or rc
    return rc


# --------------------------------------------------------------------------- #
# argparse
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="alo-gpt-audit",
        description="GPT Pro 監査ループ運用ツール (承認不要な監査事務のみ)。")
    p.add_argument("--root", help="gpt_ometsuke ルート (既定: $ALO_GPT_AUDIT_ROOT)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="三点照合でレーン状態 (読取)")
    s.add_argument("-v", "--verbose", action="store_true")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("close", help="1件 close (退避+台帳+route)")
    s.add_argument("request_id")
    s.add_argument("--apply", action="store_true", help="実行 (既定 dry-run)")
    s.set_defaults(func=cmd_close)

    s = sub.add_parser("close-all", help="answered を一括 close (既定 dry-run)")
    s.add_argument("--apply", action="store_true")
    s.set_defaults(func=cmd_close_all)

    s = sub.add_parser("action-queue", help="reflected:false の一覧 (Claudeの次手)")
    s.set_defaults(func=cmd_action_queue)

    s = sub.add_parser("owner-digest", help="Owner 5行サマリ")
    s.add_argument("--all", action="store_true", help="reflected 済みも含む")
    s.set_defaults(func=cmd_owner_digest)

    s = sub.add_parser("lint", help="REQUEST preflight (T2 必須キー)")
    s.set_defaults(func=cmd_lint)

    s = sub.add_parser("reflect", help="RESULT を反映済みにする (reflected:true)")
    s.add_argument("request_id")
    s.add_argument("--apply", action="store_true")
    s.set_defaults(func=cmd_reflect)

    s = sub.add_parser("gate-check", help="操作の承認要否を判定")
    s.add_argument("operation")
    s.set_defaults(func=cmd_gate_check)

    s = sub.add_parser("health", help="監査レーン health report")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_health)

    s = sub.add_parser(
        "handoff-validate",
        help="DISPATCH packet を検証 (non_mutating レーンのみ運用・flag 既定 off)")
    s.add_argument("packet", help="dispatch packet JSON ファイル")
    s.add_argument("--apply", action="store_true",
                   help="ALO_HANDOFF_LANE=1 時のみ card/ledger を書く")
    s.set_defaults(func=cmd_handoff_validate)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    lane = Lane(resolve_root(args))
    return args.func(lane, args)


if __name__ == "__main__":
    raise SystemExit(main())
