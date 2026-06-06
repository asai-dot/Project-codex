"""雑誌目次ノード「論文タイトル　著者名」を構造化する parser.

指示書 cc_instruction_legallib_journal_article_parser_20260605.md (v1.1) §3 の
確定ロジックを実装する。kind は article / section_header / other / unknown の
4 種に排他的に振り分ける。

判定優先順 (指示書 §3.1):
  1. section_header  …「【…】」始まり or SECTION_HEADER_KEYWORDS or SECTION_LIKE_PATTERN
  2. other           … BOILERPLATE_KEYWORDS に完全一致
  3. article         … 末尾「全角空白 + 著者部」を持つ (最後の全角空白で分割)
  4. unknown         … 上記いずれにも該当しない
"""

from __future__ import annotations

import re

ZSP = "　"  # 全角空白 (U+3000)

SECTION_HEADER_KEYWORDS = (
    "第", "序", "プロローグ", "エピローグ", "巻頭",
    "Part ", "Chapter ", "CHAPTER ", "Vol ", "VOL ",
)

SECTION_LIKE_PATTERN = re.compile(
    r"^(第[0-9０-９一二三四五六七八九十百千]+[部編章節]"
    r"|序章|序論|序説|総論|各論|資料編|参考資料)"
)

BOILERPLATE_KEYWORDS = {
    "編集後記", "奥付", "目次", "もくじ", "次号予告",
    "刊行のお知らせ", "投稿のお願い", "executive summary",
}

SERIES_TAG_RE = re.compile(
    r"[（(]("
    r"(?:第[\d０-９]+(?:回|号|巻))"   # 第3回、第10巻
    r"|連載(?:第[\d０-９]+回)?"        # 連載、連載第3回
    r"|完|前編|中編|後編"             # 完結マーカー
    r"|その[\d０-９]+"                # その2
    r")[）)]\s*$"
)

AUTHOR_SPLIT_RE = re.compile(r"[・／、,]")

VALID_KINDS = {"article", "section_header", "other", "unknown"}


def parse_article(label: str, level: int, ordinal: int) -> dict:
    """1 ノードを kind 別に正規化して dict を返す.

    raw_label と level は呼び出し元から transit。返り値は最低限
    {ordinal, level, raw_label, kind} を持ち、article の場合は
    {title, authors_raw, authors, series_tag} を追加する。
    """
    s = (label or "").strip()
    base = {"ordinal": ordinal, "level": level, "raw_label": s}
    if not s:
        return {**base, "kind": "unknown"}

    # 1) section_header (先判定)
    if s.startswith("【") and "】" in s:
        return {**base, "kind": "section_header", "section": s}
    if any(s.startswith(k) for k in SECTION_HEADER_KEYWORDS):
        if SECTION_LIKE_PATTERN.match(s):
            return {**base, "kind": "section_header", "section": s}
    # refinement (§9 self-decide): SECTION_LIKE_PATTERN は資料編/総論/各論/参考資料 等の
    # 見出し語を含むが、指示書 reference では keyword prefix gating により到達不能。
    # 著者部 (全角空白) を持たない bare 見出しに限り section_header と判定する
    # (著者付きタイトルは ZSP を持つので誤分類しない)。
    if ZSP not in s and SECTION_LIKE_PATTERN.match(s):
        return {**base, "kind": "section_header", "section": s}

    # 2) boilerplate / other
    if s in BOILERPLATE_KEYWORDS:
        return {**base, "kind": "other", "title": s}

    # 3) article: 末尾の全角空白で author 候補を抜く
    if ZSP not in s:
        return {**base, "kind": "unknown"}
    last = s.rfind(ZSP)
    title_part = s[:last].strip()
    authors_raw = s[last + 1:].strip()
    if not title_part or not authors_raw:
        return {**base, "kind": "unknown"}

    # title 末尾の連載タグを optional 抽出 (失敗しても kind は変えない)
    series_tag = None
    m = SERIES_TAG_RE.search(title_part)
    if m:
        series_tag = m.group(1)
        title_part = title_part[:m.start()].strip()

    authors = [a.strip() for a in AUTHOR_SPLIT_RE.split(authors_raw) if a.strip()]
    return {
        **base,
        "kind": "article",
        "title": title_part,
        "authors_raw": authors_raw,
        "authors": authors,
        "series_tag": series_tag,
    }


# ---------------------------------------------------------------------------
# TOC flattening — 元 JSON の構造ゆれを吸収する
# ---------------------------------------------------------------------------

# label として扱いうるキー (優先順)
_LABEL_KEYS = ("label", "title", "text", "name", "heading")
# 子ノードとして扱いうるキー
_CHILDREN_KEYS = ("children", "nodes", "items", "child", "toc")
# ページ番号として扱いうるキー (指示書 §4.2)
_PAGE_KEYS = ("print_page", "pdf_page", "page", "page_start")


def _coerce_page(node: dict) -> int | None:
    for k in _PAGE_KEYS:
        if k in node and node[k] not in (None, ""):
            try:
                return int(str(node[k]).strip())
            except (TypeError, ValueError):
                continue
    return None


def _node_label(node: dict) -> str:
    for k in _LABEL_KEYS:
        v = node.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def iter_toc_nodes(toc, level: int = 1):
    """toc を pre-order で平坦化し (label, level, page_start) を yield する.

    toc がリスト/dict のどちらでも、また children がネストしていても扱える。
    label を持たない純粋なコンテナノードはスキップするが、子は辿る。
    """
    if toc is None:
        return
    if isinstance(toc, dict):
        # node 自身が level を持つならそれを優先
        node_level = toc.get("level", level)
        try:
            node_level = int(node_level)
        except (TypeError, ValueError):
            node_level = level
        label = _node_label(toc)
        if label.strip():
            yield label, node_level, _coerce_page(toc)
        for ck in _CHILDREN_KEYS:
            if ck in toc and isinstance(toc[ck], (list, dict)):
                yield from iter_toc_nodes(toc[ck], node_level + 1)
    elif isinstance(toc, list):
        for item in toc:
            if isinstance(item, str):
                if item.strip():
                    yield item, level, None
            else:
                yield from iter_toc_nodes(item, level)


def parse_journal(journal: dict, journal_book_id: str) -> list[dict]:
    """1 雑誌 (元 JSON dict) を articles_extracted.jsonl 行のリストへ.

    指示書 §4 の出力 schema に従う。section は直近 1 つの section_header を
    単段で保持 (stack ではない)。ordinal は 1 origin。
    """
    journal_title = journal.get("title") or journal.get("name") or ""
    toc = None
    for k in ("toc", "nodes", "children", "items", "contents"):
        if k in journal:
            toc = journal[k]
            break

    rows: list[dict] = []
    current_section: str | None = None
    ordinal = 0
    for label, level, page in iter_toc_nodes(toc):
        ordinal += 1
        parsed = parse_article(label, level, ordinal)
        if parsed["kind"] == "section_header":
            current_section = parsed.get("section")
        row = {
            "journal_book_id": journal_book_id,
            "journal_title": journal_title,
            "ordinal": parsed["ordinal"],
            "level": parsed["level"],
            "kind": parsed["kind"],
            "section": parsed.get("section") if parsed["kind"] == "section_header" else current_section,
            "title": parsed.get("title"),
            "authors_raw": parsed.get("authors_raw"),
            "authors": parsed.get("authors"),
            "series_tag": parsed.get("series_tag"),
            "page_start": page,
            "raw_label": parsed["raw_label"],
        }
        rows.append(row)
    return rows
