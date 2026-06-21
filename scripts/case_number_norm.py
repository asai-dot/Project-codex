#!/usr/bin/env python3
"""case_number_norm.py — 事件番号 正規化の参照実装 v0.2 (DD-CASEID-002 §1.1 N1〜N5)。

v0.2 変更 (DDCASEID_MODIFY_REQUIRED 2026-06-21 の MUST FIX 反映):
  MF-1 西暦→元号の自動逆引きを禁止。元号が観測できる入力のみ R/H/S/T/M へ。
       西暦のみ/元号不明は era_resolution_status='unresolved' → norm=None (provisional)。
       決定日から推測しない。
  MF-4 併合事件を 1:N の docket 観測へ。先頭だけ採らない。
       全 docket を正規化し is_primary/ordinal/source_span を保持。

正準形 {ERA}{year}-{符号}-{number}[-{枝}]。かな/漢字保持・ローマ字化しない。
未解析は None (= provisional 採番へ。捨てない・推測しない)。

注意: 本実装は N1〜N5 規則の *参照* (fixture 回帰用)。production は 31c。
N規則↔fixture 対応は test_case_number_norm.py 冒頭の MAPPING を参照。
"""
from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass, asdict

ERA = {"令和": "R", "平成": "H", "昭和": "S", "大正": "T", "明治": "M"}
_K = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
      "六": 6, "七": 7, "八": 8, "九": 9}


def _kanji_to_int(s: str) -> int | None:
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


# 完全な docket (元号+年+符号+番号[+枝]) を *先頭から* 1件取り出すパターン
_HEAD = re.compile(
    r"(?P<era>令和|平成|昭和|大正|明治)"
    r"(?P<year>元|[0-9一二三四五六七八九十百千]+)年?"
    r"[(（](?P<sym>[^)）]+)[)）]"
    r"第?(?P<num>[0-9]+)号?"
    r"(?:の(?P<branch>[0-9]+))?"
)
# 後続 docket: 「(符号)番号」or「第N号」or 裸番号。era/year を先頭から継承。
_TAIL = re.compile(
    r"(?:[(（](?P<sym>[^)）]+)[)）])?"
    r"第?(?P<num>[0-9]+)号?"
    r"(?:の(?P<branch>[0-9]+))?"
)
# 西暦のみ (元号不明) の検出: 先頭に4桁西暦 + (符号)
_SEIREKI = re.compile(r"^(19|20)[0-9]{2}\s*[(（]")


@dataclass
class Docket:
    norm: str | None
    era: str | None
    year: int | None
    symbol: str | None
    number: int | None
    branch: int | None
    is_primary: bool
    ordinal: int
    source_span: str
    era_resolution_status: str  # resolved / unresolved


def _mk(era, year, sym, num, branch, primary, ordinal, span) -> Docket:
    sym = unicodedata.normalize("NFC", sym).strip() if sym else None
    if era and year and sym and num is not None:
        core = f"{era}{year}-{sym}-{num}"
        norm = f"{core}-{branch}" if branch is not None else core
        status = "resolved"
    else:
        norm = None
        status = "unresolved"
    return Docket(norm, era, year, sym, num, branch, primary, ordinal, span, status)


def normalize_dockets(raw: str) -> list[Docket]:
    """併合事件を含む文字列 → docket 観測のリスト (1:N, MF-4)。

    解析できない/元号不明は norm=None・era_resolution_status='unresolved' で返す
    (捨てない・推測しない・最近傍丸めしない)。
    """
    if not raw:
        return []
    s = unicodedata.normalize("NFKC", raw)
    s = re.sub(r"\s+", "", s)

    # MF-1: 西暦のみ (元号観測なし) は逆引きせず unresolved
    if _SEIREKI.match(s) and not any(e in s for e in ERA):
        return [Docket(None, None, None, None, None, None, True, 0, s, "unresolved")]

    head = _HEAD.match(s)
    if not head:
        return [Docket(None, None, None, None, None, None, True, 0, s, "unresolved")]

    era = ERA[head.group("era")]
    yraw = head.group("year")
    year = 1 if yraw == "元" else _kanji_to_int(yraw)
    if year is None or year <= 0:
        return [Docket(None, None, None, None, None, None, True, 0, s, "unresolved")]

    dockets: list[Docket] = []
    h_branch = head.group("branch")
    dockets.append(_mk(era, year, head.group("sym"),
                       int(head.group("num")),
                       int(h_branch) if h_branch else None,
                       True, 0, head.group(0)))

    # 先頭以降を区切り (、・,) で分割し後続 docket を回収 (era/year 継承)
    rest = s[head.end():]
    cur_sym = dockets[0].symbol
    ordinal = 1
    for seg in re.split(r"[、,・]+", rest):
        seg = seg.strip("。.　 ")
        if not seg:
            continue
        m = _TAIL.fullmatch(seg)
        if not m:
            dockets.append(Docket(None, era, year, None, None, None, False, ordinal, seg, "unresolved"))
            ordinal += 1
            continue
        sym = m.group("sym") or cur_sym
        cur_sym = sym
        b = m.group("branch")
        dockets.append(_mk(era, year, sym, int(m.group("num")),
                           int(b) if b else None, False, ordinal, seg))
        ordinal += 1
    return dockets


def normalize(raw: str) -> str | None:
    """後方互換: 代表(primary) docket の norm を返す。解析不能なら None。"""
    ds = normalize_dockets(raw)
    return ds[0].norm if ds else None


if __name__ == "__main__":
    import sys, json
    for line in sys.argv[1:]:
        print(json.dumps([asdict(d) for d in normalize_dockets(line)], ensure_ascii=False))
