"""TOC 見出し・論文タイトルから条文/判例参照を抽出し e-gov 法令へリンクする.

Fork 4 ステップ③「引用グラフの芽」。出力は 2 系統の link record:

  scheme = "jp_statute_ref"     … 法令(+条) 参照。e-gov law_id / uri を解決
  scheme = "jp_case_citation"   … 判例参照。引用グラフのノード (法令には繋がない)

法令参照は egov_index の法令名辞書を貪欲マッチし、直後に続く「第○条」を
解析して条 URI を組み立てる。条が取れない場合も法令レベルのリンクを残す。
"""

from __future__ import annotations

import re

from .egov_index import EgovIndex, egov_article_uri
from .jp_numerals import KANJI_NUM_CHARS, normalize_article_number

# 「第709条」「709条」「第七百九条」「四二三条」「第34条の2」等
_ARTICLE_RE = re.compile(
    r"第?\s*([0-9０-９" + KANJI_NUM_CHARS + r"]+(?:[のノ][0-9０-９" + KANJI_NUM_CHARS + r"]+)*)\s*条"
    r"(?:[のノ]([0-9０-９" + KANJI_NUM_CHARS + r"]+))?"
)

# 判例引用: 最高裁/高裁/地裁 + 元号 + 年月日 + 判決/決定
# 例: 最判平成元年6月20日 / 最大判昭和60年3月27日 / 最決令和2年9月30日 / 東京地判平成…
# 下級審の地名 prefix は漢字に限定する (ひらがなを巻き込まないため)。
_KANJI = r"一-龥々〇"
_COURT_RE = (
    r"(?:最大判|最大決|最判|最決|大判|大決"
    r"|[" + _KANJI + r"]{1,5}高判|[" + _KANJI + r"]{1,5}高決"
    r"|[" + _KANJI + r"]{1,5}地判|[" + _KANJI + r"]{1,5}地決"
    r"|[" + _KANJI + r"]{1,5}家審)"
)
_ERA = r"(?:明治|大正|昭和|平成|令和)"
_CASE_RE = re.compile(
    r"(" + _COURT_RE + _ERA
    + r"(?:元|[0-9０-９一二三四五六七八九十]+)年"
    + r"(?:[0-9０-９一二三四五六七八九十]+月)?"
    + r"(?:[0-9０-９一二三四五六七八九十]+日)?"
    + r")"
)
_ERA_RE = re.compile(_ERA)
_COURT_HEAD_RE = re.compile(
    r"^(最大判|最大決|最判|最決|大判|大決|[" + _KANJI + r"]{1,5}(?:高判|高決|地判|地決|家審))"
)


_KANJI_CHAR_RE = re.compile(r"[一-龥々]")


def _ref_confidence(law_name: str, prev_char: str, article: str | None) -> str:
    """法令参照の確からしさ。

    - high  : 条番号を伴う (例: 民法709条) → ほぼ確実に引用
    - low   : 短い法令名 (<=3字) が漢字に直接後続する位置で素抽出された
              (例: 「特別刑法」中の「刑法」のような複合語誤検出のリスク)
    - medium: それ以外の素抽出 (語境界が立っている)
    """
    if article:
        return "high"
    if len(law_name) <= 3 and _KANJI_CHAR_RE.match(prev_char or ""):
        return "low"
    return "medium"


def extract_statute_refs(text: str, index: EgovIndex) -> list[dict]:
    """text から法令(+条)参照を抽出。重複 span は最長一致を優先。"""
    s = text or ""
    refs: list[dict] = []
    occupied: list[tuple[int, int]] = []

    # 法令名は長い順 (index.law_names) に貪欲マッチ。同一 span の二重採用を防ぐ。
    for name in index.law_names:
        start = 0
        while True:
            i = s.find(name, start)
            if i < 0:
                break
            j = i + len(name)
            start = j
            # 既により長い法令名でカバー済みなら飛ばす
            if any(a <= i and j <= b for (a, b) in occupied):
                continue
            law_id = index.name_to_law[name]
            prev_char = s[i - 1] if i > 0 else ""
            ref = {
                "scheme": "jp_statute_ref",
                "law_name": name,
                "law_id": law_id,
                "match_text": name,
                "char_start": i,
                "ambiguous_law_name": name in index.ambiguous_names,
                "article": None,
                "article_raw": None,
                "uri": f"egov:{law_id}",
                "article_in_egov": None,
                "confidence": None,
            }
            # 直後に続く条番号を解析 (法令名の直後 ~ 数文字以内)
            m = _ARTICLE_RE.match(s, j)
            if m:
                art_norm = normalize_article_number(m.group(1))
                if art_norm and m.group(2):
                    branch = normalize_article_number(m.group(2))
                    if branch:
                        art_norm = f"{art_norm}_{branch}"
                if art_norm:
                    ref["article"] = art_norm
                    ref["article_raw"] = m.group(0)
                    ref["uri"] = egov_article_uri(law_id, art_norm)
                    ref["article_in_egov"] = index.has_definition(law_id, art_norm)
                    j = m.end()
            ref["confidence"] = _ref_confidence(name, prev_char, ref["article"])
            occupied.append((i, j))
            refs.append(ref)

    refs.sort(key=lambda r: r["char_start"])
    return refs


def _normalize_case_citation(raw: str) -> dict:
    """判例引用文字列から court / era を抽出 (正規化キー生成)。"""
    court = None
    m = _COURT_HEAD_RE.match(raw)
    if m:
        court = m.group(1)
    era_m = _ERA_RE.search(raw)
    era = era_m.group(0) if era_m else None
    key = re.sub(r"\s+", "", raw)
    return {"court": court, "era": era, "cite_key": key}


def extract_case_citations(text: str) -> list[dict]:
    """text から判例引用を抽出 (引用グラフのノード候補)。"""
    s = text or ""
    out: list[dict] = []
    for m in _CASE_RE.finditer(s):
        raw = m.group(1)
        info = _normalize_case_citation(raw)
        out.append({
            "scheme": "jp_case_citation",
            "match_text": raw,
            "char_start": m.start(),
            **info,
        })
    return out


def extract_links(text: str, index: EgovIndex) -> list[dict]:
    """法令参照 + 判例参照をまとめて抽出し char_start 昇順で返す。"""
    links = extract_statute_refs(text, index) + extract_case_citations(text)
    links.sort(key=lambda r: r["char_start"])
    return links


def link_article_row(row: dict, index: EgovIndex) -> list[dict]:
    """articles_extracted.jsonl の 1 行から link record 群を生成。

    title と section と raw_label を対象テキストにする (重複は span+scheme で排除)。
    返り値の各 record に source 情報 (journal_book_id, ordinal, field) を付与。
    """
    out: list[dict] = []
    seen: set[tuple] = set()
    fields = []
    if row.get("title"):
        fields.append(("title", row["title"]))
    if row.get("section") and row.get("kind") == "section_header":
        fields.append(("section", row["section"]))
    # raw_label は title を含むことが多いが、section_header 行などのために拾う
    if not fields and row.get("raw_label"):
        fields.append(("raw_label", row["raw_label"]))

    for field_name, text in fields:
        for link in extract_links(text, index):
            dedup = (link["scheme"], link.get("uri") or link.get("cite_key"), link["match_text"])
            if dedup in seen:
                continue
            seen.add(dedup)
            out.append({
                "journal_book_id": row.get("journal_book_id"),
                "ordinal": row.get("ordinal"),
                "source_field": field_name,
                **link,
            })
    return out
