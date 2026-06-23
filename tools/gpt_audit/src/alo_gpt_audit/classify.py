"""RESULT 消化のための分類器 — 「反映キュー (action queue)」を台帳から派生で作る。

監査の出口を閉じるための層。processed への退避は「GPT 照会 1 回分は回答済み」を
意味するだけで、「設計に反映済み」ではない (§8 注記)。本モジュールは各 RESULT を
読んで次アクションを導出し、Box フォルダを増やさずに反映キューを提供する。

導出元:
- RESULT 先頭行ラベル -> next_action_type / ratify_required / requeue_expected
- RESULT 本文 (任意項目) -> need_more_type / missing_materials / blocking_before_ratify
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

from .lane import (
    LABEL_SUFFIXES,
    RESULT_SUFFIX,
    REQUEST_SUFFIX,
    Lane,
    Request,
    first_label,
    lane_dirs,
    parse_request,
)

# label 接尾辞 -> (next_action_type, ratify_required, requeue_expected)
_LABEL_ACTION = {
    "PASS": ("ratify", True, False),
    "PASS_WITH_NOTES": ("ratify", True, False),   # ただし blocking notes は ratify 前に反映必須
    "MODIFY_REQUIRED": ("patch", False, True),
    "FAIL": ("reject", False, False),
    "NEED_MORE": ("required_materials", False, True),
}

# action-queue の表示順
ACTION_ORDER = ["patch", "required_materials", "ratify", "reject", "none"]


@dataclass
class ActionItem:
    request_id: Optional[str]
    gate: Optional[str]
    topic: Optional[str]
    result_filename: str
    result_label: str
    next_action_type: str
    ratify_required: bool
    requeue_expected: bool
    lane_status: str
    need_more_type: Optional[str] = None
    missing_materials: List[str] = field(default_factory=list)
    blocking_notes: List[str] = field(default_factory=list)


def label_suffix(gate: Optional[str], label: str) -> str:
    if gate and label.startswith(gate + "_"):
        return label[len(gate) + 1 :]
    for s in sorted(LABEL_SUFFIXES, key=len, reverse=True):
        if label.endswith(s):
            return s
    return label


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def extract_scalar(text: str, key: str) -> Optional[str]:
    m = re.search(r"^[ \t]*{}:[ \t]*(\S.*?)\s*$".format(re.escape(key)), text, re.MULTILINE)
    if not m:
        return None
    val = m.group(1).strip()
    # インラインコメント除去
    idx = val.find(" #")
    if idx != -1:
        val = val[:idx].strip()
    return val or None


def extract_list(text: str, key: str) -> List[str]:
    """``key:`` の直後に続く ``- item`` 行を集める (contiguous block)。"""
    lines = text.splitlines()
    out: List[str] = []
    capturing = False
    for line in lines:
        if not capturing:
            if re.match(r"^[ \t]*{}:[ \t]*$".format(re.escape(key)), line):
                capturing = True
            continue
        m = re.match(r"^[ \t]*-\s+(.*\S)\s*$", line)
        if m:
            out.append(m.group(1).strip())
        else:
            break
    return out


def _gate_from_result_name(name: str) -> Optional[str]:
    stem = name[: -len(RESULT_SUFFIX)] if name.endswith(RESULT_SUFFIX) else name
    parts = stem.split("_")
    return parts[-1] if parts else None


def derive_action(gate: Optional[str], result_path: str, request: Optional[Request],
                  lane_status: str) -> ActionItem:
    label = first_label(result_path)
    suffix = label_suffix(gate, label)
    nat, ratify, requeue = _LABEL_ACTION.get(suffix, ("none", False, False))
    text = _read(result_path)
    return ActionItem(
        request_id=extract_scalar(text, "request_id") or (request.request_id if request else None),
        gate=gate,
        topic=request.topic if request else None,
        result_filename=os.path.basename(result_path),
        result_label=label,
        next_action_type=nat,
        ratify_required=ratify,
        requeue_expected=requeue,
        lane_status=lane_status,
        need_more_type=extract_scalar(text, "need_more_type"),
        missing_materials=extract_list(text, "missing_materials"),
        blocking_notes=extract_list(text, "blocking_before_ratify"),
    )


def build_action_queue(lane: Lane) -> List[ActionItem]:
    """from_gpt の全 RESULT を消化対象として ActionItem 化する。

    退避済み (processed_done) でも反映が終わったとは限らないので、
    lane_status に関わらず全 RESULT を出す — ここが「赤入れで止まる」事故を防ぐ。
    """
    dirs = lane_dirs(lane.root)
    to_gpt_by_result = {r.expected_result: r for r in lane.requests}
    items: List[ActionItem] = []
    for name in sorted(lane.result_names):
        result_path = os.path.join(dirs["from_gpt"], name)
        req = to_gpt_by_result.get(name)
        if req is not None:
            lane_status = req.lane_status
        else:
            # to_gpt に無ければ processed (退避済み=回答済み) を引く
            req_filename = (name[: -len(RESULT_SUFFIX)] + REQUEST_SUFFIX
                            if name.endswith(RESULT_SUFFIX) else name)
            p = lane.processed_by_name.get(req_filename)
            if p is not None:
                req = parse_request(p)
                lane_status = "processed_done"
            else:
                lane_status = "orphan_result"
        gate = req.gate if req else _gate_from_result_name(name)
        items.append(derive_action(gate, result_path, req, lane_status))
    return items
