"""CONSUMED.md 派生ビュー — 台帳 (_AUDIT_LEDGER.jsonl) から「消化状態」を描く。

flat スクリプトの consumed-view を package モジュール化したもの。出力 / 入力パスは
旧 monolith の固定パスではなく lane root に紐付ける:

    <root>/_AUDIT_LEDGER.jsonl   … 入力台帳 (jsonl)
    <root>/CONSUMED.md          … 出力 (build) / 比較対象 (check)

build  : 台帳を読み、消化状態別に並べた CONSUMED.md を書き出す。
check  : 再レンダリングして既存 CONSUMED.md と比較する (`generated_at` 行は無視)。
         ドリフトがあれば 1 を返す。
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .ledger import LEDGER_JSONL, now_jst_iso

CONSUMED_NAME = "CONSUMED.md"

# next_action_type -> Owner 向け処分 (disposition) 表記
DISPOSITION = {
    "ratify": "採用",
    "patch": "採用(要修正)",
    "required_materials": "保留(資料補充)",
    "reject": "不採用",
    "none": "採用",
}

# 消化状態の並び順
STATE_ORDER = ["未反映", "ratify待ち", "反映済(後続へ)", "反映済", "closed"]


def default_ledger_path(root: str) -> str:
    return os.path.join(root, LEDGER_JSONL)


def default_consumed_path(root: str) -> str:
    return os.path.join(root, CONSUMED_NAME)


def load_ledger(path: str) -> List[Dict[str, object]]:
    """台帳 jsonl を読む。空行と `_comment` 行はスキップ。request_id 必須。"""
    rows: List[Dict[str, object]] = []
    if not os.path.isfile(path):
        return rows
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            row = json.loads(line)
            if "_comment" in row:
                continue
            if "request_id" not in row:
                raise ValueError(
                    "ledger row {} に request_id がありません: {}".format(lineno, line)
                )
            rows.append(row)
    return rows


def consumption_state(row: Dict[str, object]) -> str:
    """1 レコードの消化状態を導く (flat consumption_state からの移植)。"""
    loop_state = row.get("loop_state")
    if not row.get("reflected"):
        return "ratify待ち" if loop_state == "ratify_wait" else "未反映"
    if loop_state == "requeued":
        return "反映済(後続へ)"
    if loop_state == "closed":
        return "closed"
    return "反映済"


def _latest_per_request(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    latest: Dict[str, Dict[str, object]] = {}
    for r in rows:
        rid = r.get("request_id")
        if not rid:
            continue
        latest[str(rid)] = r
    return list(latest.values())


def _cell(value: object) -> str:
    """セル内の `|` / 改行をエスケープして 1 行にする。"""
    s = "" if value is None else str(value)
    return s.replace("|", "\\|").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


def _digest(row: Dict[str, object]) -> str:
    return str(row.get("owner_digest") or row.get("owner_digest_5line") or "")


def _rethink(row: Dict[str, object]) -> str:
    text = str(row.get("claude_rethink") or row.get("claude_rethink_prompt") or "")
    need = row.get("need_more_type")
    if need:
        text = "[{}] {}".format(need, text)
    return text


def render(rows: List[Dict[str, object]], ledger_src: str,
           generated_at: Optional[str] = None) -> str:
    """消化状態別の CONSUMED.md を組み立てる (flat render からの移植)。"""
    if generated_at is None:
        generated_at = now_jst_iso()
    latest = _latest_per_request(rows)

    by_state: Dict[str, List[Dict[str, object]]] = {s: [] for s in STATE_ORDER}
    for r in latest:
        st = consumption_state(r)
        by_state.setdefault(st, []).append(r)

    consumed_count = sum(
        len(by_state.get(s, [])) for s in ("反映済(後続へ)", "反映済", "closed")
    )
    unreflected_count = len(by_state.get("未反映", []))

    lines: List[str] = [
        "# CONSUMED — 監査結果の消化ビュー",
        "",
        "- generated_at: {}".format(generated_at),
        "- ledger_src: {}".format(ledger_src),
        "- consumed: {} / 未反映: {}".format(consumed_count, unreflected_count),
        "",
        "## disposition マッピング",
        "",
        "| next_action_type | 判断 |",
        "| --- | --- |",
    ]
    for k, v in DISPOSITION.items():
        lines.append("| {} | {} |".format(k, v))
    lines.append("")

    for state in STATE_ORDER:
        bucket = by_state.get(state) or []
        lines.append("## {} ({} 件)".format(state, len(bucket)))
        lines.append("")
        if not bucket:
            lines.append("(なし)")
            lines.append("")
            continue
        lines.append("| request_id | label | 判断 | GPT結論(要旨) | 反映内容/次アクション |")
        lines.append("| --- | --- | --- | --- | --- |")
        for r in sorted(bucket, key=lambda x: str(x.get("request_id") or "")):
            nat = str(r.get("next_action_type") or "")
            lines.append("| {} | {} | {} | {} | {} |".format(
                _cell(r.get("request_id")),
                _cell(r.get("result_label")),
                _cell(DISPOSITION.get(nat, nat)),
                _cell(_digest(r)),
                _cell(_rethink(r)),
            ))
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def _strip_generated_at(text: str) -> str:
    return "\n".join(
        ln for ln in text.splitlines() if not ln.startswith("- generated_at:")
    )


def build(root: str, ledger_path: Optional[str] = None,
          out_path: Optional[str] = None,
          generated_at: Optional[str] = None) -> str:
    """CONSUMED.md を書き出して本文を返す。"""
    ledger_path = ledger_path or default_ledger_path(root)
    out_path = out_path or default_consumed_path(root)
    rows = load_ledger(ledger_path)
    text = render(rows, ledger_path, generated_at)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


def check(root: str, ledger_path: Optional[str] = None,
          out_path: Optional[str] = None,
          generated_at: Optional[str] = None) -> bool:
    """既存 CONSUMED.md と再レンダリング結果を比較する。

    `- generated_at:` 行を無視して一致すれば True (ドリフトなし)。
    """
    ledger_path = ledger_path or default_ledger_path(root)
    out_path = out_path or default_consumed_path(root)
    rows = load_ledger(ledger_path)
    rendered = render(rows, ledger_path, generated_at)
    if not os.path.isfile(out_path):
        return False
    with open(out_path, "r", encoding="utf-8") as fh:
        existing = fh.read()
    return _strip_generated_at(existing) == _strip_generated_at(rendered)
