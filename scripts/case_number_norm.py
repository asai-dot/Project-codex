#!/usr/bin/env python3
"""case_number_norm.py — 事件番号 正規化の参照実装 v0.3 (DD-CASEID-002)。

v0.3 変更 (DDCASEID_MODIFY_REQUIRED 2026-06-22 再監査の MF-4/P0-1/P1-1 反映):
  MF-4-1 後続 docket も *まず full parser* を適用。era/year/symbol が省略された時のみ
         直前 resolved から継承。明示値は継承で上書きしない。
  MF-4-2 component_basis(era/year/symbol/number/branch = observed|inherited|unresolved|absent)、
         parse_status(parsed|partial|unresolved)、review_status を各 docket に付与。
  MF-4-3 raw span 保存: raw_segment + raw_start/raw_end(原文オフセット)、normalized_segment 別持ち。
  MF-4-4 delimiter registry(、,，・;；／/改行/及び/並びに)。未知連結は fail-closed(unresolved)。
  P0-1   NFKC は segment 全体に適用し *符号にも及ぶ*(半角カタカナ畳み込み等 identity-safe)と
         明示。DD の「符号は NFC 保持」表記を「符号も NFKC」へ統一(仕様↔コード一致)。
  P0-2   漢数字→算用は *元号年のみ*。事件番号/枝番は算用前提、漢数字番号は unresolved(fail-closed)。
  P1-1   is_primary → is_display_primary(文字列先頭の表示上の代表。法的主事件性ではない)。

正準形 {ERA}{year}-{符号}-{number}[-{枝}]。かな/漢字保持・ローマ字化しない。
未解析は norm=None(provisional。捨てない・推測しない・最近傍丸めしない)。
"""
from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass, field, asdict

ERA = {"令和": "R", "平成": "H", "昭和": "S", "大正": "T", "明治": "M"}
_K = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
      "六": 6, "七": 7, "八": 8, "九": 9}

# MF-4-4 delimiter registry (事件番号連結子)。未知連結はここに無い→segment内で解析できず unresolved。
_DELIM = re.compile(r"[、,，・;；／/\n]+|及び|並びに")

# full docket: 元号+年+符号+番号[+枝]
_FULL = re.compile(
    r"^(?P<era>令和|平成|昭和|大正|明治)"
    r"(?P<year>元|[0-9一二三四五六七八九十百千]+)年?"
    r"[(](?P<sym>[^)]+)[)]"
    r"第?(?P<num>[0-9]+)号?"
    r"(?:の(?P<branch>[0-9]+))?$"
)
# tail docket: [(符号)]番号[の枝]。era/year は継承。
_TAIL = re.compile(
    r"^(?:[(](?P<sym>[^)]+)[)])?"
    r"第?(?P<num>[0-9]+)号?"
    r"(?:の(?P<branch>[0-9]+))?$"
)
_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


def _kanji_year_to_int(s: str) -> int | None:
    """元号年のみ: 漢数字/算用→int (P0-2: 事件番号には使わない)。"""
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


@dataclass
class Docket:
    norm: str | None
    era: str | None
    year: int | None
    symbol: str | None
    number: int | None
    branch: int | None
    component_basis: dict           # field -> observed|inherited|unresolved|absent
    parse_status: str               # parsed|partial|unresolved
    review_status: str              # not_required|review_required
    era_resolution_status: str      # resolved|unresolved
    is_display_primary: bool        # P1-1: 表示上の先頭(法的主事件性ではない)
    ordinal: int
    raw_segment: str                # 原文 substring
    raw_start: int
    raw_end: int
    normalized_segment: str


def _norm_seg(seg: str) -> str:
    """segment 正規化: NFKC(符号含む・半角畳み込み)→全角数字半角化→空白除去。"""
    s = unicodedata.normalize("NFKC", seg).translate(_DIGITS)
    return re.sub(r"\s+", "", s)


def _build(era, year, sym, num, branch, basis, primary, ordinal, seg, s, e, nseg) -> Docket:
    sym = unicodedata.normalize("NFC", sym).strip() if sym else None
    resolved = bool(era and year and sym and num is not None)
    norm = None
    if resolved:
        core = f"{era}{year}-{sym}-{num}"
        norm = f"{core}-{branch}" if branch is not None else core
    inherited = any(v == "inherited" for v in basis.values())
    parse_status = "parsed" if (resolved and not inherited) else ("partial" if resolved else "unresolved")
    review_status = "not_required" if parse_status == "parsed" else "review_required"
    return Docket(norm, era, year, sym, num, branch, basis, parse_status, review_status,
                  "resolved" if (era and year) else "unresolved",
                  primary, ordinal, seg, s, e, nseg)


def _split_with_offsets(raw: str):
    out, pos = [], 0
    for m in _DELIM.finditer(raw):
        if m.start() > pos:
            out.append((raw[pos:m.start()], pos, m.start()))
        pos = m.end()
    if pos < len(raw):
        out.append((raw[pos:], pos, len(raw)))
    return out


def normalize_dockets(raw: str) -> list[Docket]:
    if not raw:
        return []
    segments = _split_with_offsets(raw)
    if not segments:
        return []
    dockets: list[Docket] = []
    ctx = {"era": None, "year": None, "symbol": None}
    for ordinal, (seg, s, e) in enumerate(segments):
        nseg = _norm_seg(seg)
        primary = (ordinal == 0)
        full = _FULL.match(nseg)
        if full:
            yr = 1 if full.group("year") == "元" else _kanji_year_to_int(full.group("year"))
            b = full.group("branch")
            basis = {"era": "observed", "year": "observed" if yr else "unresolved",
                     "symbol": "observed", "number": "observed",
                     "branch": "observed" if b else "absent"}
            d = _build(ERA[full.group("era")], yr, full.group("sym"),
                       int(full.group("num")), int(b) if b else None,
                       basis, primary, ordinal, seg, s, e, nseg)
        else:
            tail = _TAIL.match(nseg)
            if tail:
                sym_obs = tail.group("sym")
                era = ctx["era"]; year = ctx["year"]
                sym = sym_obs or ctx["symbol"]
                b = tail.group("branch")
                basis = {
                    "era": "inherited" if era else "unresolved",
                    "year": "inherited" if year else "unresolved",
                    "symbol": "observed" if sym_obs else ("inherited" if ctx["symbol"] else "unresolved"),
                    "number": "observed",
                    "branch": "observed" if b else "absent",
                }
                d = _build(era, year, sym, int(tail.group("num")),
                           int(b) if b else None, basis, primary, ordinal, seg, s, e, nseg)
            else:
                # MF-4-4 fail-closed: 未知連結/解析不能
                basis = {k: "unresolved" for k in ("era", "year", "symbol", "number", "branch")}
                d = _build(None, None, None, None, None, basis, primary, ordinal, seg, s, e, nseg)
        if d.norm is not None:
            ctx = {"era": d.era, "year": d.year, "symbol": d.symbol}
        dockets.append(d)
    return dockets


def normalize(raw: str) -> str | None:
    """後方互換: 代表(display primary) docket の norm。解析不能なら None。"""
    ds = normalize_dockets(raw)
    return ds[0].norm if ds else None


if __name__ == "__main__":
    import sys, json
    for line in sys.argv[1:]:
        print(json.dumps([asdict(d) for d in normalize_dockets(line)], ensure_ascii=False))
