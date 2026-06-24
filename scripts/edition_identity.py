"""edition / manifestation identity 判定 (DDLEGALLIBCONCORD v0.3.1 P0-2).

「答えは一つ」は**同一 edition/manifestation が確認された範囲でのみ**成立する。
接合前にこの gate を通し、未解決(同一性が確認できない)なら apply をブロックする
(page差/階層差は conflict ではなく『別版の兆候』かもしれないため)。

report-only。本番書き込みは一切しない。stdlib のみ・決定的。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _toc_text import normalize_title  # noqa: E402

# GPT 指定の4ラベル (Q2)。
RESOLVED_SAME = "resolved_same_manifestation"
SUSPECTED_DIFFERENT = "suspected_different_manifestation"
INSUFFICIENT = "insufficient_evidence"
MANUAL_RESOLVED = "manual_resolved"

EDITION_IDENTITY_STATUS = frozenset(
    {RESOLVED_SAME, SUSPECTED_DIFFERENT, INSUFFICIENT, MANUAL_RESOLVED}
)

# apply を許すのは「同一性が解決済み」のときだけ。
APPLY_OK_STATUS = frozenset({RESOLVED_SAME, MANUAL_RESOLVED})

_SIGNAL_KEYS = ("isbn", "title", "publisher", "year", "edition", "volume", "page_count")


def _norm(v) -> str:
    return normalize_title(str(v)) if v not in (None, "") else ""


def _page_count(v) -> int | None:
    try:
        n = int(v)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def classify_edition_identity(
    sources: list[dict],
    *,
    page_tolerance: float = 0.1,
    manual_override: str | None = None,
) -> dict:
    """同一書籍と主張された複数 source の bib signal から identity status を返す。

    Args:
        sources: 各 source の bib signal dict
            ({source, isbn, title, publisher, year, edition, volume, page_count})。
        page_tolerance: page_count のズレ許容比率 (これ超で別版の兆候)。
        manual_override: owner が手動解決した場合に MANUAL_RESOLVED を強制。

    Returns:
        {"status", "reason", "evidence"}。status は EDITION_IDENTITY_STATUS。
    """
    if manual_override in APPLY_OK_STATUS:
        return {"status": MANUAL_RESOLVED, "reason": "owner manual", "evidence": {}}

    recs = [s for s in sources if isinstance(s, dict)]
    if len(recs) < 2:
        # 単一 source だけでは「複数資料で同一」を確認できない。
        return {"status": INSUFFICIENT, "reason": "single source", "evidence": {}}

    isbns = {str(s["isbn"]).strip() for s in recs if s.get("isbn")}
    titles = {_norm(s.get("title")) for s in recs if _norm(s.get("title"))}
    pubs = {_norm(s.get("publisher")) for s in recs if _norm(s.get("publisher"))}
    years = {str(s.get("year")).strip() for s in recs if s.get("year")}
    editions = {_norm(s.get("edition")) for s in recs if _norm(s.get("edition"))}
    volumes = {_norm(s.get("volume")) for s in recs if _norm(s.get("volume"))}
    pages = [p for p in (_page_count(s.get("page_count")) for s in recs) if p is not None]

    ev = {"isbns": sorted(isbns), "titles": len(titles), "years": sorted(years),
          "editions": sorted(editions), "pages": pages}

    # 1) 複数の異なる ISBN → 別 manifestation の強い兆候。
    if len(isbns) > 1:
        return {"status": SUSPECTED_DIFFERENT, "reason": "multiple distinct ISBN", "evidence": ev}
    # 2) title が割れている → 別物の疑い。
    if len(titles) > 1:
        return {"status": SUSPECTED_DIFFERENT, "reason": "title divergence", "evidence": ev}
    # 3) edition / volume ラベルが割れている → 別版。
    if len(editions) > 1 or len(volumes) > 1:
        return {"status": SUSPECTED_DIFFERENT, "reason": "edition/volume divergence", "evidence": ev}
    # 4) 刊行年が割れている → 別版の疑い。
    if len(years) > 1:
        return {"status": SUSPECTED_DIFFERENT, "reason": "year divergence", "evidence": ev}
    # 5) page_count が大きくズレる → 別版の疑い。
    if len(pages) >= 2 and min(pages) > 0:
        if (max(pages) - min(pages)) / max(pages) > page_tolerance:
            return {"status": SUSPECTED_DIFFERENT, "reason": "page_count divergence", "evidence": ev}

    # 6) 同一性の積極証拠 (ISBN一致 か title+publisher一致) があるか。
    has_isbn = len(isbns) == 1
    has_title_pub = len(titles) == 1 and len(pubs) == 1
    if has_isbn or has_title_pub:
        return {"status": RESOLVED_SAME, "reason": "isbn or title+publisher agree", "evidence": ev}

    # それ以外は判断材料不足。
    return {"status": INSUFFICIENT, "reason": "weak signals", "evidence": ev}


def is_apply_allowed_identity(status: str) -> bool:
    """edition identity の観点で apply 可か (P0-2)。"""
    return status in APPLY_OK_STATUS


__all__ = [
    "RESOLVED_SAME", "SUSPECTED_DIFFERENT", "INSUFFICIENT", "MANUAL_RESOLVED",
    "EDITION_IDENTITY_STATUS", "APPLY_OK_STATUS",
    "classify_edition_identity", "is_apply_allowed_identity",
]
