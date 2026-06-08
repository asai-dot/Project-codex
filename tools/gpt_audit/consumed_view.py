#!/usr/bin/env python3
"""CONSUMED ビュー生成 — Box v0.3 監査レーンへの小さな追加.

既存 v0.3 レーンの正本台帳 `_AUDIT_LEDGER.jsonl` から、
「GPT RESULT を Claude が読んだか / 採用・不採用 / 反映内容」を 1 ファイルで
追える CONSUMED.md を生成する。新しい状態システムは作らない。台帳の
next_action_type / loop_state / reflected を読み替えて表示するだけの派生ビュー。

背景: v0.3 では消費判断が ledger の owner_digest_5line / claude_rethink_prompt /
reflected / loop_state に散在し、「読んだのに反映していない」を人が一目で追い
にくい。それを 1 ビューに集約する (GPT v0.2 提案で唯一 v0.3 に無かった発想)。

使い方:
    python3 consumed_view.py build            # 既定スナップショットから生成
    python3 consumed_view.py build --ledger <path>   # Box 同期の _AUDIT_LEDGER.jsonl
    python3 consumed_view.py check            # 生成物と台帳が一致するか検証 (CI)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEDGER = os.path.join(HERE, "_AUDIT_LEDGER.snapshot.jsonl")
OUT_PATH = os.path.normpath(
    os.path.join(HERE, "..", "..", "handoffs", "gpt_ometsuke", "CONSUMED.md")
)

# next_action_type -> Claude の採用判断 (採用/不採用/保留)
DISPOSITION = {
    "ratify": "採用",
    "patch": "採用(要修正)",
    "required_materials": "保留(資料補充)",
    "reject": "不採用",
    "none": "採用",
}

# CONSUMED.md の表示順 (未反映を最上段に出して「読んだのに未反映」を可視化)
STATE_ORDER = ["未反映", "ratify待ち", "反映済(後続へ)", "反映済", "closed"]


def load_ledger(path: str) -> list:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{lineno}: invalid JSON: {exc}")
            if obj.get("_comment"):
                continue  # ヘッダ行
            if not obj.get("request_id"):
                raise SystemExit(f"{path}:{lineno}: missing request_id")
            rows.append(obj)
    return rows


def consumption_state(row: dict) -> str:
    """消費の現在地。`reflected:false` が残る限り「反映済」にはしない (v0.3 §J)。"""
    loop_state = row.get("loop_state", "")
    if not row.get("reflected", False):
        # 未閉。ratify 待ちか、それ以外 (returned / 未反映のまま requeued) か。
        return "ratify待ち" if loop_state == "ratify_wait" else "未反映"
    if loop_state == "requeued":
        return "反映済(後続へ)"
    if loop_state == "closed":
        return "closed"
    return "反映済"


def _esc(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def render(rows: list, ledger_src: str, generated_at: str) -> str:
    by_state: dict[str, list] = {s: [] for s in STATE_ORDER}
    for r in rows:
        by_state.setdefault(consumption_state(r), []).append(r)

    consumed = len(rows)
    unreflected = len(by_state.get("未反映", []))
    out = []
    out.append("# CONSUMED — GPT RESULT に対する Claude の採用判断ビュー")
    out.append("")
    out.append("> **自動生成。手で編集しない。** 出典は v0.3 監査レーン台帳 `_AUDIT_LEDGER.jsonl`。")
    out.append("> 再生成: `python3 tools/gpt_audit/consumed_view.py build`")
    out.append("> これは v0.3 レーンへの **派生ビュー追加** であり、別の状態システムではない。")
    out.append("")
    out.append(f"- generated_at: {generated_at}")
    out.append(f"- source_ledger: `{ledger_src}` (正本は Box `_AUDIT_LEDGER.jsonl` file_id 2271040382325)")
    out.append("")
    out.append("## 要約")
    out.append("")
    out.append(f"消費済 RESULT **{consumed}** 件 / うち **未反映 {unreflected}** 件 "
               "(= 読んだが設計反映・再投函・資料補充が未完。`reflected:false`)。")
    out.append("")
    out.append("| 判断の読み替え | next_action_type |")
    out.append("|---|---|")
    out.append("| 採用 | ratify / none |")
    out.append("| 採用(要修正) | patch (MODIFY_REQUIRED) |")
    out.append("| 保留(資料補充) | required_materials (NEED_MORE) |")
    out.append("| 不採用 | reject (FAIL) |")
    out.append("")

    titles = {
        "未反映": "## 未反映 — 読んだが反映/再投函/資料補充が未完",
        "ratify待ち": "## ratify待ち — 反映済・浅井判断待ち",
        "反映済(後続へ)": "## 反映済(後続へ) — 反映の上で新 version に置換",
        "反映済": "## 反映済",
        "closed": "## closed",
    }
    for state in STATE_ORDER:
        rows_s = by_state.get(state, [])
        if not rows_s:
            continue
        out.append(titles.get(state, f"## {state}"))
        out.append("")
        out.append("| request_id | label | 判断 | GPT結論(要旨) | 反映内容 / 次アクション |")
        out.append("|---|---|---|---|---|")
        for r in sorted(rows_s, key=lambda x: x["request_id"]):
            disp = DISPOSITION.get(r.get("next_action_type", ""), r.get("next_action_type", "—"))
            nm = r.get("need_more_type")
            owner = r.get("owner_digest", "")
            claude = r.get("claude_rethink", "")
            if nm:
                claude = f"[{nm}] {claude}"
            out.append(
                f"| `{r['request_id']}` | `{r.get('result_label','')}` | {disp} "
                f"| {_esc(owner)} | {_esc(claude)} |"
            )
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _now_jst() -> str:
    jst = _dt.timezone(_dt.timedelta(hours=9))
    return _dt.datetime.now(jst).replace(microsecond=0).isoformat()


def cmd_build(args) -> int:
    rows = load_ledger(args.ledger)
    src = os.path.relpath(args.ledger, os.path.join(HERE, "..", ".."))
    md = render(rows, src, args.generated_at or _now_jst())
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(md)
    unreflected = sum(1 for r in rows if consumption_state(r) == "未反映")
    print(f"wrote {os.path.relpath(OUT_PATH)} ({len(rows)} consumed, {unreflected} 未反映)")
    return 0


def cmd_check(args) -> int:
    rows = load_ledger(args.ledger)
    src = os.path.relpath(args.ledger, os.path.join(HERE, "..", ".."))

    def strip_gen(text: str) -> str:
        return "\n".join(
            l for l in text.splitlines() if not l.strip().startswith("- generated_at:")
        )

    want = strip_gen(render(rows, src, "X"))
    have = strip_gen(open(OUT_PATH, encoding="utf-8").read()) if os.path.exists(OUT_PATH) else ""
    if want != have:
        print("DRIFT: CONSUMED.md は台帳と不一致。build を実行してください。")
        return 1
    print("ok: CONSUMED.md は台帳と一致")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, func in (("build", cmd_build), ("check", cmd_check)):
        sp = sub.add_parser(name)
        sp.add_argument("--ledger", default=DEFAULT_LEDGER, help="v0.3 _AUDIT_LEDGER.jsonl のパス")
        if name == "build":
            sp.add_argument("--generated-at", default=None)
        sp.set_defaults(func=func)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
