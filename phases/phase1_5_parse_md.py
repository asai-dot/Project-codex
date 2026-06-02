#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
phase1_5_parse_md.py — 学陽『法令用語辞典 第11次改訂版』 Phase 1.5

決定的（LLM 非依存・再現可能）に final_hourei_jiten.md を見出し語単位へ切り出し、
all_entries.jsonl を生成する。HANDOFF_TO_MAC_20260513_response.md §2.1/§3/§4 準拠。

設計（handoff 準拠）:
  - ## と ### を見出し語候補として抽出
  - 非エントリ heading（あ / カナ1字 / 「1．用語の選定」等の番号付き節）を正規表現で除外
  - 本文 p.815-838 由来セクション（索引）は除外
  - definition は heading 直後〜次 heading 直前のテキスト
  - Phase 2.4 代替: definition_continues フラグが無いため
    「短い定義 + 次見出しが記号始まりでない」ヒューリスティックで打切り候補を flag
  - 生データ非改変: md は読むだけ。結果は別レイヤ（all_entries.jsonl）に出す。

注意（実 md で要確認＝Windows CC が確認・微調整する定数）:
  - PAGE_MARKER_RE: md 内のページ境界マーカ形式。既定は `<!-- page:NNN -->`。
    実 md が別形式（例: 行頭 `[p.123]`、`=== 123 ===`）なら下の定数を差し替える。
    マーカが無い場合 source_page=null となり、index 除外は heading 名ベースに退避。
  - HEADING_RE: ## / ### を見出しとみなす。実 md の heading level に合わせ確認。

入出力:
  python3 phase1_5_parse_md.py INPUT.md OUTPUT.jsonl [--scheme SCHEME_ID]
                               [--expected N] [--index-from-page 815]
  終了コード: 0=正常, 2=想定件数から大きく外れ(±10%超), 3=入出力エラー
  完了基準は rc=0 ではない。件数・空定義率・重複率を stderr に必ず出す。
"""

import argparse
import json
import re
import sys
import unicodedata

# --- 実 md で要確認の定数 ---------------------------------------------------
HEADING_RE = re.compile(r"^(#{2,3})\s+(.*\S)\s*$")
# ページ境界マーカ（既定）。実 md 形式に合わせて Windows CC が調整。
PAGE_MARKER_RE = re.compile(r"<!--\s*page[:=]\s*0*(\d+)\s*-->", re.I)

# --- 非エントリ heading 除外パターン ---------------------------------------
# 1) 五十音見出し（1〜2文字の かな/カナ のみ）: あ, い, ア行, カ 等
_KANA_ONLY_RE = re.compile(r"^[ぁ-んァ-ヴー]{1,2}$")
# 2) 番号付き節: 「1．用語の選定」「1.」「(1)」「第1 ...」「Ⅰ ...」等
_NUMBERED_SECTION_RE = re.compile(
    r"^\s*(?:第?\s*\d+\s*[．.、　 ]"      # 1． / 第1 .
    r"|[(（]\s*\d+\s*[)）]"               # (1) （1）
    r"|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+[．.、　 ]?"      # ローマ数字節
    r"|[０-９]+\s*[．.、])"                # 全角数字節
)
# 3) 既知の構造見出し（目次・凡例・索引・奥付など）
_STRUCTURAL_RE = re.compile(
    r"(目次|凡例|索引|奥付|まえがき|はしがき|改訂版について|執筆者|凡\s*例|"
    r"用語の選定|本書の|利用の手引|使い方|^法令用語辞典$)"
)
# 4) 辞書内サブセクション見出し（エントリではない: 類語/用例/番号付き定義点 等）
_SUBSECTION_LABEL_RE = re.compile(r"^(類語|用例|参考|備考|参照|例|注|注記|表)$")
# 5) リストマーカで始まる見出し（定義内の番号点が誤って見出し化されたもの）。
#    例: "1)", "例2)", "1) 事業要件", "2)1)の意味の…"。先頭一致で除外。
#    ※ 後続テキストの有無に関わらず、先頭が番号+括弧なら定義点とみなす。
_LIST_MARKER_RE = re.compile(r"^(?:例)?[（(]?[0-9０-９]+[)）]")


def is_non_entry_heading(title: str) -> bool:
    t = title.strip()
    if not t:
        return True
    if _KANA_ONLY_RE.match(t):
        return True
    if _NUMBERED_SECTION_RE.match(t):
        return True
    if _STRUCTURAL_RE.search(t):
        return True
    if _SUBSECTION_LABEL_RE.match(t):
        return True
    if _LIST_MARKER_RE.match(t):
        return True
    return False


def normalize_headword(title: str):
    """見出し語と読みを分離。例: '勘案（かんあん）' -> ('勘案', 'かんあん')。
    読み表記が無ければ reading=None。生データは別途保持するため非破壊的整形のみ。"""
    t = unicodedata.normalize("NFKC", title).strip()
    m = re.match(r"^(.*?)[（(]([ぁ-んァ-ヴー・\s]+)[)）]\s*$", t)
    if m and m.group(1).strip():
        return m.group(1).strip(), m.group(2).strip()
    return t, None


def make_entry_id(scheme_id: str, seq: int) -> str:
    return f"{scheme_id}__{seq:05d}"


def parse(md_lines, scheme_id, index_from_page):
    """md 行イテレータ -> エントリ list。ページ追跡しつつ heading で区切る。"""
    entries = []
    cur_page = None
    cur = None  # 現在構築中のエントリ
    seq = 0

    def flush():
        nonlocal cur
        if cur is not None:
            cur["definition"] = cur["definition"].strip()
            entries.append(cur)
            cur = None

    for raw in md_lines:
        line = raw.rstrip("\n")

        pm = PAGE_MARKER_RE.search(line)
        if pm:
            cur_page = int(pm.group(1))
            if cur is not None and cur.get("source_page") is None:
                cur["source_page"] = cur_page
            continue

        hm = HEADING_RE.match(line)
        if hm:
            level = len(hm.group(1))
            title = hm.group(2)
            flush()
            if is_non_entry_heading(title):
                cur = None  # 非エントリ heading 配下は本文に取り込まない
                continue
            headword, reading = normalize_headword(title)
            seq += 1
            cur = {
                "scheme_id": scheme_id,
                "entry_id": make_entry_id(scheme_id, seq),
                "headword": headword,
                "reading": reading,
                "raw_heading": title,
                "heading_level": level,
                "source_page": cur_page,
                "definition": "",
                "flags": [],
            }
            continue

        if cur is not None:
            cur["definition"] += line + "\n"

    flush()

    # index ページ由来を除外（source_page が分かる場合のみ）
    kept = []
    dropped_index = 0
    for e in entries:
        if e["source_page"] is not None and e["source_page"] >= index_from_page:
            dropped_index += 1
            continue
        kept.append(e)
    return kept, dropped_index


# Phase 2.4 代替ヒューリスティック: 末尾切れ候補の flag 付け
_SYMBOL_START_RE = re.compile(r"^[、。，．）)」』】〕〉》\]]")


def flag_truncation(entries, short_len=12):
    for i, e in enumerate(entries):
        d = e["definition"]
        if len(d) < short_len:
            nxt = entries[i + 1]["headword"] if i + 1 < len(entries) else ""
            if nxt and not _SYMBOL_START_RE.match(nxt):
                e["flags"].append("definition_maybe_truncated")
        if not d:
            e["flags"].append("empty_definition")
    return entries


def report(entries, dropped_index, expected):
    n = len(entries)
    empty = sum(1 for e in entries if not e["definition"])
    seen, dups = set(), 0
    for e in entries:
        key = (e["headword"], e["reading"])
        if key in seen:
            dups += 1
        seen.add(key)
    trunc = sum(1 for e in entries if "definition_maybe_truncated" in e["flags"])
    pages_known = sum(1 for e in entries if e["source_page"] is not None)

    def pct(x):
        return f"{(100.0 * x / n):.1f}%" if n else "n/a"

    lines = [
        "=== Phase 1.5 parse report ===",
        f"entries(kept)         : {n}",
        f"dropped(index>=p)     : {dropped_index}",
        f"empty_definition      : {empty} ({pct(empty)})",
        f"duplicate(headword)   : {dups} ({pct(dups)})",
        f"maybe_truncated       : {trunc} ({pct(trunc)})",
        f"source_page resolved  : {pages_known} ({pct(pages_known)})",
    ]
    rc = 0
    if expected:
        lo, hi = expected * 0.9, expected * 1.1
        verdict = "OK" if lo <= n <= hi else "OUT-OF-RANGE"
        lines.append(f"expected~{expected} (±10%: {lo:.0f}-{hi:.0f}) -> {verdict}")
        if not (lo <= n <= hi):
            rc = 2
    for ln in lines:
        print(ln, file=sys.stderr)
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser(description="学陽 Phase 1.5 md->all_entries.jsonl")
    ap.add_argument("input_md")
    ap.add_argument("output_jsonl")
    ap.add_argument("--scheme", default="hourei_yougo_jiten_11")
    ap.add_argument("--expected", type=int, default=2603)
    ap.add_argument("--index-from-page", type=int, default=815)
    ap.add_argument("--short-len", type=int, default=12)
    args = ap.parse_args(argv)

    try:
        with open(args.input_md, encoding="utf-8") as fh:
            entries, dropped = parse(fh, args.scheme, args.index_from_page)
    except OSError as e:
        print(f"input error: {e}", file=sys.stderr)
        return 3

    entries = flag_truncation(entries, args.short_len)

    try:
        with open(args.output_jsonl, "w", encoding="utf-8") as out:
            for e in entries:
                out.write(json.dumps(e, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"output error: {e}", file=sys.stderr)
        return 3

    return report(entries, dropped, args.expected)


if __name__ == "__main__":
    sys.exit(main())
