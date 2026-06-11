"""authority_resolver — どのソースを採否の権威とするか (v0.3.1 P0-1 Rule 1/1b / §2)。

絶対視を避ける:
  * pdf_primary は「qualified PDF observation かつ edition解決済 かつ page_basis整合」のみ。
  * 低信頼/未整合 PDF は pdf_observed_not_ground_truth → consensus か human_review。
  * PDF なしは 3 独立ソース consensus。独立でなければ human_review。
report-only。本番書き込みなし。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from edition_identity import APPLY_OK_STATUS  # noqa: E402
from page_basis import PDF_OBSERVED, page_basis_consistent, qualify_pdf_observation  # noqa: E402

AUTH_PDF_PRIMARY = "pdf_primary"
AUTH_CONSENSUS = "consensus"
AUTH_HUMAN_REVIEW = "human_review"


def _independent_sources(source_meta: dict) -> int:
    """独立な (二次由来が重複でない) ソース数。independence 未宣言は独立扱いしない。"""
    groups = set()
    indep = 0
    for s, m in source_meta.items():
        origin = m.get("provenance_origin")  # 例: ndl / publisher / scan / openbd_secondary
        if origin is None:
            # 独立性が宣言されていない → consensus には数えない (安全側)。
            continue
        if origin in groups:
            continue
        groups.add(origin)
        indep += 1
    return indep


def resolve_authority(source_meta: dict, *, edition_status: str) -> dict:
    """採否の権威を決める。

    Returns: {"authority", "reason", "pdf": {...} | None}
    """
    edition_ok = edition_status in APPLY_OK_STATUS

    pdf_meta = source_meta.get("pdf")
    if pdf_meta is not None:
        q = qualify_pdf_observation(pdf_meta)
        if q["qualified"] and edition_ok and page_basis_consistent(source_meta):
            return {"authority": AUTH_PDF_PRIMARY,
                    "reason": "qualified PDF + edition resolved + page_basis consistent",
                    "pdf": q}
        # PDF はあるが資格を満たさない → 二次扱い、合議/人手へ。
        reason = "pdf present but not ground truth: " + (
            "; ".join(q["reasons"]) or
            ("edition unresolved" if not edition_ok else "page_basis inconsistent"))
        # PDF を除いた残りで consensus が成り立つか。
        rest = {s: m for s, m in source_meta.items() if s != "pdf"}
        if edition_ok and _independent_sources(rest) >= 3:
            return {"authority": AUTH_CONSENSUS, "reason": reason + " → fallback consensus",
                    "pdf": q}
        return {"authority": AUTH_HUMAN_REVIEW, "reason": reason, "pdf": q}

    # PDF なし: 3 独立ソース consensus。
    if edition_ok and _independent_sources(source_meta) >= 3:
        return {"authority": AUTH_CONSENSUS, "reason": "3 independent sources agree", "pdf": None}
    why = "edition unresolved" if not edition_ok else "insufficient independent sources (<3)"
    return {"authority": AUTH_HUMAN_REVIEW, "reason": why, "pdf": None}


__all__ = ["AUTH_PDF_PRIMARY", "AUTH_CONSENSUS", "AUTH_HUMAN_REVIEW", "resolve_authority"]
