"""監査台帳 (_AUDIT_LEDGER.jsonl / _AUDIT_LEDGER.md) の追記・再生成。

SoT はフォルダ位置とファイル実体。台帳はそこから派生する append-only の控えで、
close が成功したときだけ 1 行追記する。台帳だけ更新してファイルを動かさない運用は禁止。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List

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


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M")


def next_action_for(gate, label: str) -> str:
    suffix = label
    if gate and label.startswith(gate + "_"):
        suffix = label[len(gate) + 1 :]
    return _NEXT_ACTION.get(suffix, "")


def make_entry(close_result) -> Dict[str, object]:
    req = close_result.request
    label = close_result.result_label
    return {
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
