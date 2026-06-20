"""edition_identity_v2 — 強化版 manifestation 同定 (DD-EDIDENT-001-IMPL 監査是正版)。

監査 MODIFY_REQUIRED (H1-H8) を反映した evidence-model 版:

  * H1: isbn / 明示 edition / volume の不一致を **読んで** conflict 検出 (fail-closed)。
  * H2: positive-evidence floor。title 一致・substring 単独では apply 許容ラベルに到達しない
        (isbn 一致、または核一致+複数独立信号が必要)。substring は review。
  * H3: edition signature 一致でも year/page/publisher 乖離を必ず評価 (isbn 一致のみが
        reprint として年差を吸収する)。
  * H4: 版文法は `edition_grammar.parse_edition` でトークン化、未知マーカは review。
  * H7: pair ごとに evidence trace (各 rule の pass/fail/unknown・worst pair) を残す。
  * H8: match / mismatch / unknown / parse_error を区別し、unknown は positive evidence に数えない。

返り値 status は既存 4 ラベル互換 (RESOLVED_SAME / SUSPECTED_DIFFERENT / INSUFFICIENT /
MANUAL_RESOLVED)。`APPLY_OK_STATUS = {resolved_same, manual}` 不変。report-only・stdlib のみ・決定的。
"""

from __future__ import annotations

import re
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _toc_text import normalize_title  # noqa: E402
from edition_grammar import parse_edition, title_volume  # noqa: E402
from edition_identity import (  # noqa: E402
    APPLY_OK_STATUS,
    INSUFFICIENT,
    MANUAL_RESOLVED,
    RESOLVED_SAME,
    SUSPECTED_DIFFERENT,
)

EDITION_IDENTITY_V2_VERSION = "0.3.0"
NORMALIZER_REF = "_toc_text.normalize_title"
GRAMMAR_REF = "edition_grammar.parse_edition"

# evidence の状態語彙 (H8)。
MATCH, MISMATCH, WITHIN_TOL, DIVERGENT, CONTAINMENT, UNKNOWN, PARSE_ERROR = (
    "match", "mismatch", "within_tol", "divergent", "containment", "unknown", "parse_error")


def _norm_isbn(v) -> str:
    return re.sub(r"[^0-9Xx]", "", str(v or "")).upper()


def _parse_year(v):
    """(value|None, state)。present-but-unparseable は parse_error (和暦等)。"""
    if v is None or str(v).strip() == "":
        return None, UNKNOWN
    m = re.search(r"(?<!\d)(\d{4})(?!\d)", str(v))
    if not m:
        return None, PARSE_ERROR
    return int(m.group(1)), "parsed"


def _pages(v):
    try:
        n = int(v)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _str_ev(a, b):
    """両方 present → match/mismatch、片方でも欠 → unknown。"""
    na, nb = normalize_title(str(a or "")), normalize_title(str(b or ""))
    if not na or not nb:
        return UNKNOWN
    return MATCH if na == nb else MISMATCH


def _isbn_ev(a, b):
    ia, ib = _norm_isbn(a.get("isbn")), _norm_isbn(b.get("isbn"))
    if not ia or not ib:
        return UNKNOWN
    return MATCH if ia == ib else MISMATCH


def _edition_field_ev(a, b):
    """明示 edition フィールドの版シグネチャ比較 (title とは独立)。"""
    ea, eb = a.get("edition"), b.get("edition")
    if not (ea and str(ea).strip()) or not (eb and str(eb).strip()):
        return UNKNOWN, False
    pa, pb = parse_edition(str(ea)), parse_edition(str(eb))
    if pa.unknown or pb.unknown:
        return UNKNOWN, True            # 未知マーカ → review
    sa = pa.signature or normalize_title(str(ea))
    sb = pb.signature or normalize_title(str(eb))
    return (MATCH if sa == sb else MISMATCH), False


def _volume_ev(a, b):
    """明示 volume フィールド優先、無ければ title から巻表示を補完。"""
    va = str(a.get("volume") or "").strip() or title_volume(a.get("title") or "")
    vb = str(b.get("volume") or "").strip() or title_volume(b.get("title") or "")
    na, nb = normalize_title(va), normalize_title(vb)
    if not na or not nb:
        return UNKNOWN
    return MATCH if na == nb else MISMATCH


def _year_ev(a, b, tol):
    ya, sa = _parse_year(a.get("year"))
    yb, sb = _parse_year(b.get("year"))
    if PARSE_ERROR in (sa, sb):
        return PARSE_ERROR, (ya, yb)
    if ya is None or yb is None:
        return UNKNOWN, (ya, yb)
    if ya == yb:
        return MATCH, (ya, yb)
    return (WITHIN_TOL if abs(ya - yb) <= tol else DIVERGENT), (ya, yb)


def _page_ev(a, b, tol):
    pa, pb = _pages(a.get("page_count")), _pages(b.get("page_count"))
    if not pa or not pb:
        return UNKNOWN
    return MATCH if abs(pa - pb) / max(pa, pb) <= tol else DIVERGENT


def _title_ev(a, b):
    """title core の match / containment / different と版 signature 比較。"""
    pa, pb = parse_edition(a.get("title") or ""), parse_edition(b.get("title") or "")
    if pa.unknown or pb.unknown:
        title_sig = UNKNOWN
    elif pa.signature and pb.signature:
        title_sig = MATCH if pa.signature == pb.signature else MISMATCH
    elif pa.has_marker != pb.has_marker:
        title_sig = "asymmetry"
    else:
        title_sig = UNKNOWN
    if not pa.core or not pb.core:
        core = UNKNOWN
    elif pa.core == pb.core:
        core = MATCH
    elif pa.core in pb.core or pb.core in pa.core:
        core = CONTAINMENT
    else:
        core = DIVERGENT
    return {"title_core": core, "title_edition_sig": title_sig,
            "core_a": pa.core, "core_b": pb.core,
            "sig_a": pa.signature, "sig_b": pb.signature}


def _classify_pair(a: dict, b: dict, *, page_tolerance: float, year_tolerance: int) -> dict:
    """1 ペアを evidence model で判定し、status/reason/evidence(trace) を返す。"""
    isbn = _isbn_ev(a, b)
    ed_field, ed_field_unknown = _edition_field_ev(a, b)
    volume = _volume_ev(a, b)
    year, years = _year_ev(a, b, year_tolerance)
    page = _page_ev(a, b, page_tolerance)
    publisher = _str_ev(a.get("publisher"), b.get("publisher"))
    author = _str_ev(a.get("author"), b.get("author"))
    tev = _title_ev(a, b)

    ev = {"isbn": isbn, "edition_field": ed_field, "volume": volume, "year": year,
          "years": years, "page": page, "publisher": publisher, "author": author,
          **tev, "edition_field_unknown_marker": ed_field_unknown}

    def out(status, reason):
        return {"status": status, "reason": reason, "evidence": ev}

    # --- HARD CONFLICT → suspected_different (異 manifestation) -------------
    if isbn == MISMATCH:
        return out(SUSPECTED_DIFFERENT, "isbn_mismatch")
    if ed_field == MISMATCH:
        return out(SUSPECTED_DIFFERENT, "edition_field_conflict")
    if volume == MISMATCH:
        return out(SUSPECTED_DIFFERENT, "volume_conflict")
    if tev["title_edition_sig"] == MISMATCH:
        return out(SUSPECTED_DIFFERENT, "edition_number_conflict")
    if tev["title_core"] == DIVERGENT:
        return out(SUSPECTED_DIFFERENT, "genuine_title_diff")
    # 版 signature が無く isbn も一致しないのに年が大きく乖離 → 別版疑い。
    if year == DIVERGENT and isbn != MATCH:
        return out(SUSPECTED_DIFFERENT, "year_divergence")

    # --- REVIEW → insufficient (異常乖離は isbn 一致でも免除しない: Required note 2) ----
    if tev["title_edition_sig"] == UNKNOWN and (
            parse_edition(a.get("title") or "").unknown or parse_edition(b.get("title") or "").unknown):
        return out(INSUFFICIENT, "unknown_edition_marker")
    if ed_field_unknown:
        return out(INSUFFICIENT, "unknown_edition_marker")
    if year == PARSE_ERROR:
        return out(INSUFFICIENT, "year_parse_error")
    if year == DIVERGENT:                       # ここに来るのは isbn 一致時。年大差は anomaly → review。
        return out(INSUFFICIENT, "year_divergence_anomaly")
    if tev["title_edition_sig"] == "asymmetry":  # 版マーカ非対称は isbn 一致でも review (OQ-1)。
        return out(INSUFFICIENT, "edition_marker_asymmetry")
    if tev["title_core"] == CONTAINMENT and isbn != MATCH:
        return out(INSUFFICIENT, "title_containment_only")     # H2: substring は positive 不可
    if page == DIVERGENT:
        return out(INSUFFICIENT, "page_divergence")
    if publisher == MISMATCH:
        return out(INSUFFICIENT, "publisher_divergence")

    # --- POSITIVE FLOOR → resolved_same (H2) -------------------------------
    if isbn == MATCH:
        return out(RESOLVED_SAME, "isbn_match")
    corrob = sum(1 for s in (ed_field, publisher, author, page) if s == MATCH)
    corrob += 1 if year in (MATCH, WITHIN_TOL) else 0
    corrob += 1 if tev["title_edition_sig"] == MATCH else 0
    if tev["title_core"] == MATCH and corrob >= 2:
        return out(RESOLVED_SAME, f"title_core_agree+{corrob}_signals")

    # 積極証拠が足りない → 確定不可。
    return out(INSUFFICIENT, "insufficient_positive_evidence")


# status の悪い順 (worst-case を採る)。
_RANK = {SUSPECTED_DIFFERENT: 3, INSUFFICIENT: 2, RESOLVED_SAME: 1}


def classify_edition_identity_v2(sources: list[dict], *, page_tolerance: float = 0.1,
                                 year_tolerance: int = 1,
                                 manual_override: str | None = None) -> dict:
    """同一書籍と主張された複数 source の bib signal から identity status を返す。

    各 source: {title, isbn, publisher, year, edition, volume, author, page_count}。
    全ペア worst-case を採る (安全側)。返り値に pair-level evidence trace を含む (H7)。
    """
    meta = {"classifier_version": EDITION_IDENTITY_V2_VERSION,
            "normalizer": NORMALIZER_REF, "grammar": GRAMMAR_REF,
            "policy": {"page_tolerance": page_tolerance, "year_tolerance": year_tolerance}}
    if manual_override in APPLY_OK_STATUS:
        return {"status": MANUAL_RESOLVED, "reason": "owner manual",
                "worst_pair": None, "evidence": None, **meta}

    recs = [s for s in sources if isinstance(s, dict)]
    if len(recs) < 2:
        return {"status": INSUFFICIENT, "reason": "single source",
                "worst_pair": None, "evidence": None, **meta}

    worst = None
    worst_pair = None
    pair_traces = []
    for i, j in combinations(range(len(recs)), 2):
        r = _classify_pair(recs[i], recs[j], page_tolerance=page_tolerance,
                           year_tolerance=year_tolerance)
        pair_traces.append({"pair": (i, j), "status": r["status"], "reason": r["reason"],
                            "evidence": r["evidence"]})
        if worst is None or _RANK[r["status"]] > _RANK[worst["status"]]:
            worst, worst_pair = r, (i, j)
    return {"status": worst["status"], "reason": worst["reason"],
            "worst_pair": worst_pair, "evidence": worst["evidence"],
            "pair_traces": pair_traces, **meta}


def is_apply_allowed_identity(status: str) -> bool:
    return status in APPLY_OK_STATUS


__all__ = ["classify_edition_identity_v2", "is_apply_allowed_identity",
           "EDITION_IDENTITY_V2_VERSION"]
