"""edition_identity_v2 — DD-TOCADOPT-001 Step1 強化版 manifestation 同定 (report-only)。

DDLEGALLIBCONCORD v0.3.1 の `classify_edition_identity` (title 文字列一致 / 年が1つでも
違えば別版) は Phase0 実測で過検知 (生 344件中 偽陽性226) と判明した。本v2は
GPT DDTOCADOPT_PASS_WITH_NOTES の Required note を反映:

  * タイトルから **版番号を抽出**して一次信号にする (第7版 vs 第4版 = 別版)。
  * **核タイトル包含**で副題の有無を吸収 (同一本を分離しない)。
  * **年差±1 は許容**、版番号一致なら年差は重版扱い。
  * Required note 2: **ISBN 一致だけで同一 manifestation 確定にしない**。版番号一致でも
    page_count / publisher / year の不一致が大きければ review(INSUFFICIENT) へ落とす。

返り値の status は既存 4 ラベル (RESOLVED_SAME / SUSPECTED_DIFFERENT / INSUFFICIENT /
MANUAL_RESOLVED) と互換。report-only・stdlib のみ・決定的。
"""

from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _toc_text import normalize_title  # noqa: E402
from edition_identity import (  # noqa: E402
    APPLY_OK_STATUS,
    INSUFFICIENT,
    MANUAL_RESOLVED,
    RESOLVED_SAME,
    SUSPECTED_DIFFERENT,
)
from phase0_inventory import _core_title, edition_signature, title_diff_kind  # noqa: E402


def _year(v):
    try:
        import re
        m = re.search(r"(\d{4})", str(v or ""))
        return int(m.group(1)) if m else None
    except (TypeError, ValueError):
        return None


def _pages(v):
    try:
        n = int(v)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _classify_pair(a: dict, b: dict, *, page_tolerance: float, year_tolerance: int) -> dict:
    """2 source の bib signal から status を返す。"""
    at, bt = a.get("title") or "", b.get("title") or ""
    le, ce = edition_signature(at), edition_signature(bt)

    # 1) 版番号が両方あって相違 → 確実な別版。
    if le and ce and le != ce:
        return {"status": SUSPECTED_DIFFERENT, "reason": f"edition_number_conflict {le} vs {ce}"}

    # 2) タイトル層別 (装飾/副題/版マーカ非対称/核相違)。
    kind = title_diff_kind(at, bt)
    if kind == "edition_number_conflict":
        return {"status": SUSPECTED_DIFFERENT, "reason": "edition_number_conflict"}
    if kind == "genuine_title_diff":
        # 同一 ISBN でも核タイトルが別 = シリーズ別冊の誤マッチ等 → 混ぜない。
        return {"status": SUSPECTED_DIFFERENT, "reason": "genuine_title_diff"}
    if kind == "edition_marker_asymmetry":
        # 片方のみ版表記 = 相手の版が不明 → 確定不可、人手へ。
        return {"status": INSUFFICIENT, "reason": "edition_marker_asymmetry"}
    # ここに来たら kind は cosmetic / subtitle_difference = 本としては同一。

    # 3) 年。版番号一致なら年差は重版/表記ゆれ → 無視。
    ya, yb = _year(a.get("year")), _year(b.get("year"))
    same_version = bool(le) and le == ce
    if ya is not None and yb is not None and ya != yb and not same_version:
        if abs(ya - yb) > year_tolerance:
            return {"status": SUSPECTED_DIFFERENT, "reason": f"year divergence {ya} vs {yb}"}

    # 4) Required note 2: ISBN 一致でも page/publisher が大きく食い違えば確定しない。
    pa, pb = _pages(a.get("page_count")), _pages(b.get("page_count"))
    if pa and pb and abs(pa - pb) / max(pa, pb) > page_tolerance:
        return {"status": INSUFFICIENT, "reason": f"page_count divergence {pa} vs {pb}"}
    na = normalize_title(a.get("publisher") or "")
    nb = normalize_title(b.get("publisher") or "")
    if na and nb and na != nb:
        return {"status": INSUFFICIENT, "reason": "publisher divergence"}

    # 5) 核タイトルが空 (判定材料なし) → 不足。
    if not _core_title(at) or not _core_title(bt):
        return {"status": INSUFFICIENT, "reason": "empty core title"}

    # 積極証拠: 核タイトル一致 + 版整合 + 年/頁/出版社の矛盾なし。
    return {"status": RESOLVED_SAME, "reason": "title core agree + edition consistent"}


# status の悪い順 (worst-case を採る)。
_RANK = {SUSPECTED_DIFFERENT: 3, INSUFFICIENT: 2, RESOLVED_SAME: 1}


def classify_edition_identity_v2(sources: list[dict], *, page_tolerance: float = 0.1,
                                 year_tolerance: int = 1,
                                 manual_override: str | None = None) -> dict:
    """同一書籍と主張された複数 source の bib signal から identity status を返す (強化版)。

    各 source: {title, isbn, publisher, year, edition, page_count}。
    複数 source は総当たりで評価し、最も疑わしいペアの判定を採る (安全側)。
    """
    if manual_override in APPLY_OK_STATUS:
        return {"status": MANUAL_RESOLVED, "reason": "owner manual", "worst_pair": None}

    recs = [s for s in sources if isinstance(s, dict)]
    if len(recs) < 2:
        return {"status": INSUFFICIENT, "reason": "single source", "worst_pair": None}

    worst = {"status": RESOLVED_SAME, "reason": "title core agree + edition consistent"}
    worst_pair = None
    for i, j in combinations(range(len(recs)), 2):
        r = _classify_pair(recs[i], recs[j], page_tolerance=page_tolerance,
                           year_tolerance=year_tolerance)
        if _RANK[r["status"]] > _RANK[worst["status"]]:
            worst = r
            worst_pair = (i, j)
    return {**worst, "worst_pair": worst_pair}


def is_apply_allowed_identity(status: str) -> bool:
    return status in APPLY_OK_STATUS


__all__ = ["classify_edition_identity_v2", "is_apply_allowed_identity"]
