"""監査台帳 (_AUDIT_LEDGER.jsonl / _AUDIT_LEDGER.md) の追記・再生成。

SoT はフォルダ位置とファイル実体。台帳はそこから派生する append-only の控えで、
close が成功したときだけ 1 行追記する。台帳だけ更新してファイルを動かさない運用は禁止。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from .classify import label_suffix

JST = timezone(timedelta(hours=9))
LEDGER_JSONL = "_AUDIT_LEDGER.jsonl"
LEDGER_MD = "_AUDIT_LEDGER.md"

# RESULT ラベル接尾辞 -> 次アクション (§8)
_NEXT_ACTION = {
    "PASS": "Owner ratify / accepted化",
    "PASS_WITH_NOTES": "notes反映 → Owner ratify",
    "MODIFY_REQUIRED": "v0.x hotfix / 再投函",
    "FAIL": "別案起票",
    "NEED_MORE": "資料補充 → 再投函",
}

# next_action_type -> route カードを置くキュー (ROUTE_RULES Rule 4 / flat QUEUE_FOR_ACTION)
QUEUE_FOR_ACTION = {
    "ratify": "approval_queue",
    "patch": "patch_queue",
    "required_materials": "material_queue",
    "reject": "rejected_queue",
    "none": None,
}

# action_queue の緊急度ソート順 (flat 由来)
_URGENCY_ORDER = {"patch": 0, "required_materials": 1, "reject": 2, "ratify": 3, "none": 4}


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M")


def now_jst_iso() -> str:
    """JST の ISO8601 タイムスタンプ (flat now_jst_iso からの移植)。"""
    return datetime.now(JST).replace(microsecond=0).isoformat()


def next_action_for(gate, label: str) -> str:
    suffix = label
    if gate and label.startswith(gate + "_"):
        suffix = label[len(gate) + 1 :]
    return _NEXT_ACTION.get(suffix, "")


def derive_loop_state(verdict: str, next_action: str, blocking: List[str]) -> str:
    """loop_state 導出 (flat derive_loop_state からの移植)。

    PASS / PASS_WITH_NOTES で blocking が無ければ ratify_wait、それ以外は returned。
    """
    if verdict in ("PASS", "PASS_WITH_NOTES") and not blocking:
        return "ratify_wait"
    return "returned"


def make_owner_digest(topic: str, request_id: str, verdict: str,
                      reasons: List[str], next_action: str,
                      ratify_required: bool, blocking: List[str]) -> str:
    """Owner 向け 5 行サマリ (flat make_owner_digest からの移植, LOOP_RULE §5)。"""
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
                               blocking: List[str], missing: List[str]) -> str:
    """Claude が次に再思考すべき内容 (flat make_claude_rethink_prompt からの移植)。"""
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


def make_entry(close_result, action=None) -> Dict[str, object]:
    """台帳 1 行を作る。``action`` (classify.ActionItem) があれば反映キュー項目も載せる。"""
    req = close_result.request
    label = close_result.result_label
    entry = {
        "request_id": req.request_id,
        "topic": req.topic,
        "gate": req.gate,
        "request_filename": req.filename,
        "request_status": req.status,
        "result_filename": close_result.result_filename,
        "result_label": label,
        "processed_request_folder": "to_gpt/processed",
        "processed_at_jst": now_jst(),
        "action": close_result.action,
        "next_action": next_action_for(req.gate, label),
        "supersedes_request_id": req.supersedes,
        "notes": "; ".join(close_result.warnings),
    }
    if action is not None:
        # 反映キュー項目 (§1): 退避だけで終わらせないための next_action 構造化
        verdict = label_suffix(req.gate, label) if label else ""
        blocking = list(action.blocking_notes or [])
        missing = list(action.missing_materials or [])
        next_action = action.next_action_type
        topic = req.topic or req.request_id or req.filename
        loop_state = derive_loop_state(verdict, next_action, blocking)
        owner_digest = make_owner_digest(
            topic, req.request_id or req.filename, verdict, [],
            next_action, bool(action.ratify_required), blocking,
        )
        rethink = make_claude_rethink_prompt(
            verdict, next_action, req.gate or "?", blocking, missing,
        )
        entry.update(
            {
                "next_action_type": next_action,
                "ratify_required": action.ratify_required,
                "requeue_expected": action.requeue_expected,
                "need_more_type": action.need_more_type,
                "missing_materials": action.missing_materials,
                "blocking_before_ratify": action.blocking_notes,
                "reflected": False,  # 反映済みフラグ (人手 / 後続ツールで true 化)
                # --- flat build_record からの enrichment ---
                "event": "close",
                "ts": now_jst_iso(),
                "verdict": verdict,
                "loop_state": loop_state,
                "owner_digest_5line": owner_digest,
                "claude_rethink_prompt": rethink,
                "queue": QUEUE_FOR_ACTION.get(next_action),
                "approval_required_to_act": next_action in ("ratify",),
            }
        )
    return entry


def append(root: str, entry: Dict[str, object]) -> None:
    with open(os.path.join(root, LEDGER_JSONL), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load(root: str) -> List[Dict[str, object]]:
    path = os.path.join(root, LEDGER_JSONL)
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def latest_state_per_request(root: str) -> Dict[str, Dict[str, object]]:
    """request_id ごとに最新の台帳レコードを返す (後勝ち)。

    台帳行は時系列なので、後に出てくる行 (reflect 等) が最新状態として残る。
    flat latest_state_per_request からの移植 (引数を Lane から root へ変更)。
    """
    latest: Dict[str, Dict[str, object]] = {}
    for e in load(root):
        rid = e.get("request_id")
        if not rid:
            continue
        latest[rid] = e
    return latest


def action_queue(root: str) -> List[Dict[str, object]]:
    """未反映 (reflected:false かつ loop_state != closed) のレコード一覧。

    flat action_queue からの移植。owner-digest / reflect / health が使う
    台帳派生ビュー。緊急度 (patch > required_materials > reject > ratify > none)
    で並べ、同順位は request_id 昇順。
    """
    out: List[Dict[str, object]] = []
    for _rid, e in latest_state_per_request(root).items():
        if e.get("reflected"):
            continue
        if e.get("loop_state") == "closed":
            continue
        out.append(e)
    out.sort(key=lambda e: (_URGENCY_ORDER.get(e.get("next_action_type"), 9),
                            e.get("request_id") or ""))
    return out


_MD_COLUMNS = [
    ("processed_at_jst", "processed_at"),
    ("request_id", "request_id"),
    ("gate", "gate"),
    ("result_label", "result_label"),
    ("action", "action"),
    ("next_action", "next_action"),
]


def render_md(root: str) -> str:
    rows = load(root)
    header = "| " + " | ".join(c[1] for c in _MD_COLUMNS) + " |"
    sep = "| " + " | ".join("---" for _ in _MD_COLUMNS) + " |"
    lines = [
        "# GPT 目付け役 監査台帳 (_AUDIT_LEDGER)",
        "",
        "append-only。SoT はフォルダ位置とファイル実体。本表は派生控え。",
        "",
        header,
        sep,
    ]
    for r in rows:
        cells = [str(r.get(k, "") or "") for k, _ in _MD_COLUMNS]
        lines.append("| " + " | ".join(cells) + " |")
    text = "\n".join(lines) + "\n"
    with open(os.path.join(root, LEDGER_MD), "w", encoding="utf-8") as fh:
        fh.write(text)
    return text
