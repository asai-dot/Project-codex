"""Worker Queue 台帳 (_registry.jsonl / _registry.md) の追記・再生成。

SoT はフォルダ位置と RESULT ラベル。台帳はそこから派生する append-only の控えで、
terminal 遷移 (complete / block) が成功したときだけ 1 行追記する。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from .queue import TransitionResult

JST = timezone(timedelta(hours=9))
REGISTRY_JSONL = "_registry.jsonl"
REGISTRY_MD = "_registry.md"

# RESULT ラベル -> Owner/GPT 側の次アクション (§7 検査官レーンへ橋渡し)
_NEXT_ACTION = {
    "WORKER_PASS": "GPT 再監査 → ratify",
    "WORKER_PASS_WITH_NOTES": "notes 確認 → GPT 再監査",
    "WORKER_BLOCKED": "blocker 解消 → 再 inbox 化",
    "WORKER_FAIL": "原因切り分け → task 再設計",
}


def now_jst_iso() -> str:
    return datetime.now(JST).replace(microsecond=0).isoformat()


def next_action_for(label: Optional[str]) -> str:
    return _NEXT_ACTION.get(label or "", "")


def make_entry(result: TransitionResult, ts: Optional[str] = None) -> Dict[str, object]:
    """台帳 1 行を作る。``ts`` を渡せば決定的 (テスト用)、省略時は now(JST)。"""
    task = result.task
    return {
        "worker_task_id": task.worker_task_id,
        "priority": task.priority,
        "goal": task.goal,
        "op": result.op,                       # complete | block
        "src_lane": result.src_lane,
        "dest_lane": result.dest_lane,          # done | blocked
        "action": result.action,                # moved | consolidated | already
        "result_filename": task.expected_result,
        "result_label": result.result_label,
        "next_action": next_action_for(result.result_label),
        "test_command": task.test_command,
        "ts": ts or now_jst_iso(),
        "notes": "; ".join(result.warnings),
    }


def append(root: str, entry: Dict[str, object]) -> None:
    with open(os.path.join(root, REGISTRY_JSONL), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load(root: str) -> List[Dict[str, object]]:
    path = os.path.join(root, REGISTRY_JSONL)
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def latest_per_task(root: str) -> Dict[str, Dict[str, object]]:
    """worker_task_id ごとに最新行を返す (後勝ち)。"""
    latest: Dict[str, Dict[str, object]] = {}
    for e in load(root):
        tid = e.get("worker_task_id")
        if tid:
            latest[tid] = e
    return latest


_MD_COLUMNS = [
    ("ts", "ts"),
    ("worker_task_id", "task_id"),
    ("priority", "pri"),
    ("dest_lane", "lane"),
    ("result_label", "label"),
    ("next_action", "next_action"),
]


def render_md(root: str) -> str:
    rows = load(root)
    header = "| " + " | ".join(c[1] for c in _MD_COLUMNS) + " |"
    sep = "| " + " | ".join("---" for _ in _MD_COLUMNS) + " |"
    lines = [
        "# Claude Code Worker Queue 台帳 (_registry)",
        "",
        "append-only。SoT はフォルダ位置と RESULT ラベル。本表は派生控え。",
        "`alo-worker registry build` で再生成する。",
        "",
        header,
        sep,
    ]
    for r in rows:
        cells = [str(r.get(k, "") or "") for k, _ in _MD_COLUMNS]
        lines.append("| " + " | ".join(cells) + " |")
    text = "\n".join(lines) + "\n"
    with open(os.path.join(root, REGISTRY_MD), "w", encoding="utf-8") as fh:
        fh.write(text)
    return text
