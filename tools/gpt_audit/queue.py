#!/usr/bin/env python3
"""GPT お目付け役 監査キュー — v0.2 状態管理プロジェクタ.

QUEUE_EVENTS.jsonl (append-only の状態変更ログ) を唯一の真実とし、
そこから QUEUE_INDEX.md (現在状態の台帳) と CONSUMED.md (Claude 消費記録)
を決定論的に再生成する。RESULT が返っただけでは closed にしない、という
v0.2 の中核ルールを classify() で機械的に強制する。

依存ゼロ (標準ライブラリのみ)。Box 上の v0.3 レーン
(_AUDIT_LEDGER.jsonl / _ACTION_QUEUE.md) との対応は PROTOCOL.md の
crosswalk 表を参照。

使い方:
    python3 queue.py build     # events -> QUEUE_INDEX.md + CONSUMED.md 再生成
    python3 queue.py report    # 件数分類だけ標準出力 (「監査溜まってない?」用)
    python3 queue.py append --event RESULT_RETURNED --request-id ... [...]
    python3 queue.py check     # build 出力が現ファイルと一致するか検証 (CI 用)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
LANE_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "handoffs", "gpt_ometsuke"))
EVENTS_PATH = os.path.join(LANE_DIR, "QUEUE_EVENTS.jsonl")
INDEX_PATH = os.path.join(LANE_DIR, "QUEUE_INDEX.md")
CONSUMED_PATH = os.path.join(LANE_DIR, "CONSUMED.md")

# --- 状態語彙 (v0.2) ----------------------------------------------------------
# 未済 4 分類 + closed。RESULT 返却だけでは closed にならない。
UNAUDITED = "未監査"        # REQUEST はあるが RESULT 未着
UNCONSUMED = "未消費"       # RESULT はあるが Claude が読んで判断していない (CONSUMED 無し)
UNREFLECTED = "未反映"      # CONSUMED 済だが設計本文/再投函/資料補充が未完
AWAITING_OWNER = "浅井判断待ち"  # 反映済だが浅井ratify(または不採用承認)待ち
CLOSED = "closed"

BUCKET_ORDER = [UNAUDITED, UNCONSUMED, UNREFLECTED, AWAITING_OWNER, CLOSED]

# CONSUMED イベントの disposition。reject 以外は反映フェーズを持つ。
REFLECTABLE_DISPOSITIONS = {"adopt", "partial", "defer"}

VALID_EVENTS = {
    "REQUEST_CREATED",   # actor=claude  Claude→GPT 依頼を to_gpt/ に置いた
    "RESULT_RETURNED",   # actor=gpt     GPT が from_gpt/ に RESULT を返した
    "CONSUMED",          # actor=claude  Claude が RESULT を読み採用/不採用を判断
    "REFLECTED",         # actor=claude  設計本文反映 / 資料補充 / 再投函を完了
    "RATIFIED",          # actor=asai    浅井先生が ratify (accepted 化 等)
    "REQUEUED",          # actor=claude  新 version に置換 (supersedes)
    "CLOSED",            # actor=claude  明示クローズ (重複保存 等の事務的閉鎖)
    "REOPENED",          # actor=claude  クローズ取り消し
}


@dataclass
class RequestState:
    request_id: str
    topic: str = ""
    gate: str = ""
    label: str = ""
    result_file_id: str = ""
    disposition: str = ""
    requires_reflection: bool = False
    reflected: bool = False
    ratify_required: bool = False
    ratified: bool = False
    superseded_by: str = ""
    closed_explicit: bool = False
    closed_reason: str = ""
    reopened: bool = False
    summary_owner: str = ""
    summary_claude: str = ""
    need_more_type: str = ""
    first_ts: str = ""
    last_ts: str = ""
    events: list = field(default_factory=list)

    @property
    def label_kind(self) -> str:
        """ラベル末尾の判定種別を返す (例 G0_MODIFY_REQUIRED -> MODIFY_REQUIRED)。"""
        if not self.label:
            return ""
        for kind in (
            "PASS_WITH_NOTES",
            "MODIFY_REQUIRED",
            "NEED_MORE",
            "PASS",
            "FAIL",
        ):
            if self.label.endswith(kind):
                return kind
        return self.label

    @property
    def has_result(self) -> bool:
        return bool(self.label)

    @property
    def has_consumed(self) -> bool:
        return bool(self.disposition)

    def classify(self) -> str:
        """v0.2 の closed 厳格化を機械的に適用して現在状態を返す。

        鉄則: RESULT があるだけでは closed にしない。
        consumed -> (要反映なら反映) -> (要ratifyならratify) まで揃って初めて closed。
        """
        if self.reopened:
            pass  # reopen 後は通常判定に戻す (closed フラグを無視)
        elif self.superseded_by or self.closed_explicit:
            return CLOSED
        if not self.has_result:
            return UNAUDITED
        if not self.has_consumed:
            return UNCONSUMED
        # 不採用 (reject) は理由記録の上、ratify 不要なら closed にできる。
        if self.disposition == "reject" and not self.ratify_required:
            return CLOSED
        if (
            self.disposition in REFLECTABLE_DISPOSITIONS
            and self.requires_reflection
            and not self.reflected
        ):
            return UNREFLECTED
        if self.ratify_required and not self.ratified:
            return AWAITING_OWNER
        reflection_done = (not self.requires_reflection) or self.reflected
        ratify_done = (not self.ratify_required) or self.ratified
        if reflection_done and ratify_done:
            return CLOSED
        return UNREFLECTED


def _apply(state: RequestState, ev: dict) -> None:
    etype = ev.get("event")
    ts = ev.get("ts", "")
    if ts:
        state.last_ts = ts
        if not state.first_ts:
            state.first_ts = ts
    state.events.append(etype)
    if etype == "REQUEST_CREATED":
        state.topic = ev.get("topic", state.topic)
        state.gate = ev.get("gate", state.gate)
    elif etype == "RESULT_RETURNED":
        state.label = ev.get("label", state.label)
        state.result_file_id = str(ev.get("result_file_id", state.result_file_id))
        if ev.get("need_more_type"):
            state.need_more_type = ev["need_more_type"]
        if ev.get("summary_owner"):
            state.summary_owner = ev["summary_owner"]
    elif etype == "CONSUMED":
        state.disposition = ev.get("disposition", state.disposition)
        state.requires_reflection = bool(
            ev.get("requires_reflection", state.requires_reflection)
        )
        state.ratify_required = bool(ev.get("ratify_required", state.ratify_required))
        if ev.get("need_more_type"):
            state.need_more_type = ev["need_more_type"]
        if ev.get("summary_owner"):
            state.summary_owner = ev["summary_owner"]
        if ev.get("summary_claude"):
            state.summary_claude = ev["summary_claude"]
    elif etype == "REFLECTED":
        state.reflected = True
        if ev.get("summary_claude"):
            state.summary_claude = ev["summary_claude"]
    elif etype == "RATIFIED":
        state.ratified = True
    elif etype == "REQUEUED":
        state.superseded_by = ev.get("superseded_by", state.superseded_by)
    elif etype == "CLOSED":
        state.closed_explicit = True
        state.closed_reason = ev.get("reason", state.closed_reason)
    elif etype == "REOPENED":
        state.reopened = True
        state.closed_explicit = False
        state.superseded_by = ""
    else:
        raise ValueError(f"unknown event type: {etype!r}")


def load_events(path: str = EVENTS_PATH) -> list:
    events = []
    if not os.path.exists(path):
        return events
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{lineno}: invalid JSON: {exc}")
            if ev.get("event") not in VALID_EVENTS:
                raise SystemExit(
                    f"{path}:{lineno}: unknown event {ev.get('event')!r}"
                )
            if not ev.get("request_id"):
                raise SystemExit(f"{path}:{lineno}: missing request_id")
            events.append(ev)
    return events


def fold(events: list) -> "dict[str, RequestState]":
    """append-only イベントを request_id ごとに畳み込む。出現順を保持。"""
    states: dict[str, RequestState] = {}
    for ev in events:
        rid = ev["request_id"]
        st = states.get(rid)
        if st is None:
            st = RequestState(request_id=rid)
            states[rid] = st
        _apply(st, ev)
    return states


def bucketize(states: "dict[str, RequestState]") -> "dict[str, list]":
    buckets: dict[str, list] = {b: [] for b in BUCKET_ORDER}
    for st in states.values():
        buckets[st.classify()].append(st)
    return buckets


# --- レンダリング -------------------------------------------------------------

def _md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render_report(states: "dict[str, RequestState]") -> str:
    buckets = bucketize(states)
    total = len(states)
    open_total = sum(len(buckets[b]) for b in (UNAUDITED, UNCONSUMED, UNREFLECTED, AWAITING_OWNER))
    lines = []
    lines.append(f"監査キュー状態報告 (全 {total} 件 / 未済 {open_total} 件 / closed {len(buckets[CLOSED])} 件)")
    for b in (UNAUDITED, UNCONSUMED, UNREFLECTED, AWAITING_OWNER):
        ids = ", ".join(st.request_id for st in buckets[b]) or "—"
        lines.append(f"  {b}: {len(buckets[b])} 件  [{ids}]")
    lines.append(f"  closed: {len(buckets[CLOSED])} 件")
    return "\n".join(lines)


def _table(states: list) -> str:
    if not states:
        return "_(該当なし)_\n"
    rows = [
        "| request_id | topic | label | next_action | 最終更新 |",
        "|---|---|---|---|---|",
    ]
    for st in states:
        nxt = st.summary_claude or st.summary_owner or "—"
        if st.need_more_type:
            nxt = f"[{st.need_more_type}] {nxt}"
        rows.append(
            f"| `{st.request_id}` | {_md_escape(st.topic)} | `{st.label}` "
            f"| {_md_escape(nxt)} | {st.last_ts[:10]} |"
        )
    return "\n".join(rows) + "\n"


def render_index(states: "dict[str, RequestState]", generated_at: str) -> str:
    buckets = bucketize(states)
    total = len(states)
    open_total = sum(len(buckets[b]) for b in (UNAUDITED, UNCONSUMED, UNREFLECTED, AWAITING_OWNER))
    out = []
    out.append("# QUEUE_INDEX — GPT お目付け役 監査キュー 現在状態台帳")
    out.append("")
    out.append("> **自動生成。手で編集しない。** 真実は `QUEUE_EVENTS.jsonl`。")
    out.append("> 再生成: `python3 tools/gpt_audit/queue.py build`")
    out.append("")
    out.append(f"- generated_at: {generated_at}")
    out.append(f"- source: `handoffs/gpt_ometsuke/QUEUE_EVENTS.jsonl`")
    out.append("- protocol: `handoffs/gpt_ometsuke/PROTOCOL.md` (GPT_OMETSUEKE_QUEUE_PROTOCOL v0.2)")
    out.append("- Box 正本との対応: QUEUE_EVENTS.jsonl ⇔ `_AUDIT_LEDGER.jsonl` / QUEUE_INDEX.md ⇔ `_ACTION_QUEUE.md` (PROTOCOL.md §crosswalk)")
    out.append("")
    out.append("## 件数分類 (状態報告)")
    out.append("")
    out.append(f"全 **{total}** 件 / 未済 **{open_total}** 件 / closed **{len(buckets[CLOSED])}** 件")
    out.append("")
    out.append("| 状態 | 件数 | 意味 |")
    out.append("|---|---|---|")
    out.append(f"| 未監査 | {len(buckets[UNAUDITED])} | REQUEST はあるが GPT RESULT 未着 |")
    out.append(f"| 未消費 | {len(buckets[UNCONSUMED])} | RESULT はあるが Claude が読んで判断していない |")
    out.append(f"| 未反映 | {len(buckets[UNREFLECTED])} | 消費済だが設計反映/再投函/資料補充が未完 |")
    out.append(f"| 浅井判断待ち | {len(buckets[AWAITING_OWNER])} | 反映済だが浅井先生の ratify 待ち |")
    out.append(f"| closed | {len(buckets[CLOSED])} | 反映 (+ratify) まで到達し閉じた / 後続に置換 |")
    out.append("")
    titles = {
        UNAUDITED: "## 未監査 — GPT 返答待ち",
        UNCONSUMED: "## 未消費 — Claude 取り込み待ち",
        UNREFLECTED: "## 未反映 — Claude 作業待ち (patch / 資料補充 / 再投函)",
        AWAITING_OWNER: "## 浅井判断待ち — ratify 待ち",
        CLOSED: "## closed — 反映済 / 後続置換",
    }
    for b in BUCKET_ORDER:
        out.append(titles[b])
        out.append("")
        out.append(_table(buckets[b]))
    return "\n".join(out).rstrip() + "\n"


def render_consumed(states: "dict[str, RequestState]", generated_at: str) -> str:
    consumed = [st for st in states.values() if st.has_consumed]
    out = []
    out.append("# CONSUMED — GPT RESULT に対する Claude の採用判断記録")
    out.append("")
    out.append("> **自動生成。手で編集しない。** 真実は `QUEUE_EVENTS.jsonl` の CONSUMED イベント。")
    out.append("> 再生成: `python3 tools/gpt_audit/queue.py build`")
    out.append("")
    out.append(f"- generated_at: {generated_at}")
    out.append("- 目的: GPT RESULT を Claude が **読んだだけでなく、採用/不採用/反映内容まで** 記録し、")
    out.append("  「読んだのに反映していない」「不採用にした理由が残っていない」事故を潰す。")
    out.append("")
    disp_label = {
        "adopt": "採用",
        "partial": "一部採用",
        "defer": "保留 (資料補充)",
        "reject": "不採用",
    }
    out.append(f"記録 **{len(consumed)}** 件。")
    out.append("")
    for st in sorted(consumed, key=lambda s: s.request_id):
        out.append(f"## `{st.request_id}`")
        out.append("")
        out.append(f"- result_label: `{st.label}`")
        out.append(f"- result_file_id (Box): `{st.result_file_id or '—'}`")
        out.append(f"- 判断: **{disp_label.get(st.disposition, st.disposition)}**")
        if st.need_more_type:
            out.append(f"- need_more_type: `{st.need_more_type}`")
        out.append(f"- 反映状態: {'反映済' if st.reflected else '未反映'}"
                   f" / ratify: {'要・済' if (st.ratify_required and st.ratified) else ('要・未' if st.ratify_required else '不要')}")
        out.append(f"- 現在状態: **{st.classify()}**")
        if st.summary_owner:
            out.append(f"- GPT結論(要旨): {_md_escape(st.summary_owner)}")
        if st.summary_claude:
            out.append(f"- 反映内容/次アクション: {_md_escape(st.summary_claude)}")
        if st.superseded_by:
            out.append(f"- 後続: `{st.superseded_by}` に置換")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


# --- コマンド -----------------------------------------------------------------

def _now_jst() -> str:
    jst = _dt.timezone(_dt.timedelta(hours=9))
    return _dt.datetime.now(jst).replace(microsecond=0).isoformat()


def cmd_build(args) -> int:
    states = fold(load_events())
    generated_at = args.generated_at or _now_jst()
    index = render_index(states, generated_at)
    consumed = render_consumed(states, generated_at)
    with open(INDEX_PATH, "w", encoding="utf-8") as fh:
        fh.write(index)
    with open(CONSUMED_PATH, "w", encoding="utf-8") as fh:
        fh.write(consumed)
    print(f"wrote {os.path.relpath(INDEX_PATH)} and {os.path.relpath(CONSUMED_PATH)}")
    print(render_report(states))
    return 0


def cmd_report(args) -> int:
    print(render_report(fold(load_events())))
    return 0


def cmd_append(args) -> int:
    ev = {"ts": args.ts or _now_jst(), "event": args.event, "request_id": args.request_id}
    if args.event not in VALID_EVENTS:
        raise SystemExit(f"invalid event {args.event!r}; one of {sorted(VALID_EVENTS)}")
    for key in (
        "actor", "topic", "gate", "label", "result_file_id", "disposition",
        "need_more_type", "superseded_by", "reason", "summary_owner", "summary_claude",
    ):
        val = getattr(args, key, None)
        if val:
            ev[key] = val
    if args.requires_reflection is not None:
        ev["requires_reflection"] = args.requires_reflection
    if args.ratify_required is not None:
        ev["ratify_required"] = args.ratify_required
    with open(EVENTS_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print("appended:", json.dumps(ev, ensure_ascii=False))
    return 0


def cmd_check(args) -> int:
    """build 出力が現ファイルと一致するか検証 (生成物の手編集/未再生成を検出)。"""
    states = fold(load_events())
    # generated_at 行を無視して比較する。
    def strip_gen(text: str) -> str:
        return "\n".join(
            l for l in text.splitlines() if not l.strip().startswith("- generated_at:")
        )
    ok = True
    for path, render in ((INDEX_PATH, render_index), (CONSUMED_PATH, render_consumed)):
        want = strip_gen(render(states, "X"))
        have = strip_gen(open(path, encoding="utf-8").read()) if os.path.exists(path) else ""
        if want != have:
            ok = False
            print(f"DRIFT: {os.path.relpath(path)} は QUEUE_EVENTS.jsonl と不一致。build を実行してください。")
    if ok:
        print("ok: QUEUE_INDEX.md / CONSUMED.md は QUEUE_EVENTS.jsonl と一致")
    return 0 if ok else 1


def _bool(v):
    return {"true": True, "false": False, "1": True, "0": False}.get(str(v).lower())


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("build", help="events から QUEUE_INDEX.md / CONSUMED.md を再生成")
    sp.add_argument("--generated-at", default=None)
    sp.set_defaults(func=cmd_build)

    sp = sub.add_parser("report", help="件数分類を標準出力")
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("check", help="生成物が events と一致するか検証")
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser("append", help="イベントを 1 件追記")
    sp.add_argument("--event", required=True)
    sp.add_argument("--request-id", required=True, dest="request_id")
    sp.add_argument("--ts", default=None)
    sp.add_argument("--actor", default=None)
    sp.add_argument("--topic", default=None)
    sp.add_argument("--gate", default=None)
    sp.add_argument("--label", default=None)
    sp.add_argument("--result-file-id", default=None, dest="result_file_id")
    sp.add_argument("--disposition", default=None, choices=["adopt", "partial", "defer", "reject", None])
    sp.add_argument("--need-more-type", default=None, dest="need_more_type")
    sp.add_argument("--superseded-by", default=None, dest="superseded_by")
    sp.add_argument("--reason", default=None)
    sp.add_argument("--summary-owner", default=None, dest="summary_owner")
    sp.add_argument("--summary-claude", default=None, dest="summary_claude")
    sp.add_argument("--requires-reflection", default=None, type=_bool, dest="requires_reflection")
    sp.add_argument("--ratify-required", default=None, type=_bool, dest="ratify_required")
    sp.set_defaults(func=cmd_append)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
