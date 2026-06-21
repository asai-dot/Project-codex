#!/usr/bin/env python3
"""case_number_norm.py — 事件番号 正規化の参照実装 (DD-CASEID-002 §1.1 N1〜N5)。

正準形 {ERA}{year}-{符号}-{number}[-{枝}] を決定的に生成する。
識別はかな/漢字保持・ローマ字化しない (DD-CASEID-001 §1.3 確定)。

注意: 本実装は N1〜N5 規則の *参照* であり、31c_case_number_norm_spec.md の
production 実装そのものではない。fixture 回帰用。未解析は None を返す
(= provisional 採番へ。捨てない・推測しない)。
"""
from __future__ import annotations
import re
import unicodedata

ERA = {"令和": "R", "平成": "H", "昭和": "S", "大正": "T", "明治": "M"}
_K = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
      "六": 6, "七": 7, "八": 8, "九": 9}


def _kanji_to_int(s: str) -> int | None:
    """漢数字 (0-9999) → int。算用数字混在も許容。元 は呼び出し側で 1 に変換済前提。"""
    if s.isdigit():
        return int(s)
    total, section, current = 0, 0, 0
    units = {"十": 10, "百": 100, "千": 1000}
    for ch in s:
        if ch in _K:
            current = _K[ch]
        elif ch in units:
            section += (current or 1) * units[ch]
            current = 0
        elif ch.isdigit():
            current = current * 10 + int(ch)
        else:
            return None
    return total + section + current


# NFKC 後 (全角→半角・全角カッコ→半角) を前提に組むパターン
_PAT = re.compile(
    r"^\s*(?P<era>令和|平成|昭和|大正|明治)"
    r"(?P<year>元|[0-9一二三四五六七八九十百千]+)年"
    r"[(（](?P<sym>[^)）]+)[)）]"
    r"第?(?P<num>[0-9]+)号?"
    r"(?:の(?P<branch>[0-9]+))?\s*$"
)


def normalize(raw: str) -> str | None:
    """事件番号文字列 → case_number_norm。解析不能なら None。"""
    if not raw:
        return None
    # N2(前段): NFKC で全角数字・全角カッコを半角へ。符号のかな/漢字は保持。
    s = unicodedata.normalize("NFKC", raw)
    # N4(前段): 空白(全角含む)を除去。中黒は番号構造に出ないため温存しない。
    s = re.sub(r"\s+", "", s).strip()
    m = _PAT.match(s)
    if not m:
        return None
    # N1 元号
    era = ERA[m.group("era")]
    # N2 年 (元=1, 漢数字→算用, 先頭ゼロ除去)
    yraw = m.group("year")
    year = 1 if yraw == "元" else _kanji_to_int(yraw)
    if year is None or year <= 0:
        return None
    # N3 符号: NFC 正準字形のまま保持 (ローマ字化しない)
    sym = unicodedata.normalize("NFC", m.group("sym")).strip()
    if not sym:
        return None
    # N2 番号: 先頭ゼロ除去
    num = str(int(m.group("num")))
    # N5 枝番: -{枝} で保持
    branch = m.group("branch")
    core = f"{era}{year}-{sym}-{num}"
    return f"{core}-{branch}" if branch else core
