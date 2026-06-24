"""page_basis — ページ基準の正規化と PDF observation qualification (v0.3.1 P0-1)。

PDF は ground truth ではなく「抽出された TOC observation」。authority=pdf_primary を
許すのは high_confidence かつ edition一致 かつ page_basis整合 のときのみ。ここでは
PDF observation の品質ゲートと print/pdf ページ変換を担う。report-only・stdlib のみ。
"""


from __future__ import annotations

PAGE_BASIS_VERSION = "0.3.1"

PAGE_BASIS = frozenset({"print_page", "pdf_page", "unknown"})
EXTRACTION_METHODS = frozenset({"manual", "ocr", "llm", "publisher_pdf_toc"})
CONFIDENCE = frozenset({"high", "medium", "low"})
COVERAGE = frozenset({"full_toc", "partial_toc", "unknown"})

PDF_PRIMARY = "pdf_primary"
PDF_OBSERVED = "pdf_observed_not_ground_truth"


def normalize_page_basis(v) -> str:
    s = str(v or "").strip().lower()
    if s in PAGE_BASIS:
        return s
    if s in ("print", "paper", "本文ページ", "印刷ページ"):
        return "print_page"
    if s in ("pdf", "image", "通しページ"):
        return "pdf_page"
    return "unknown"


def qualify_pdf_observation(meta: dict) -> dict:
    """PDF observation が pdf_primary 足りうるか (P0-1 Rule 1/1b)。

    Returns: {"qualified": bool, "authority_label": pdf_primary|pdf_observed..., "reasons": [...]}
    """
    reasons = []
    if meta.get("extraction_method") not in EXTRACTION_METHODS:
        reasons.append("extraction_method 不明/不正")
    if meta.get("extraction_confidence") != "high":
        reasons.append("extraction_confidence != high")
    if normalize_page_basis(meta.get("page_basis")) == "unknown":
        reasons.append("page_basis unknown")
    if meta.get("coverage") != "full_toc":
        reasons.append("coverage != full_toc")
    if not meta.get("source_sha256"):
        reasons.append("source_sha256 欠如")
    qualified = not reasons
    return {
        "qualified": qualified,
        "authority_label": PDF_PRIMARY if qualified else PDF_OBSERVED,
        "reasons": reasons,
    }


def to_print_page(pdf_page: int, offset: int) -> int:
    """pdf_page → print_page (offset = pdf_page - print_page)。"""
    return int(pdf_page) - int(offset)


def to_pdf_page(print_page: int, offset: int) -> int:
    return int(print_page) + int(offset)


def page_basis_consistent(source_meta: dict) -> bool:
    """全ソースの page_basis が unknown を除いて単一か (混在は P0-1 で要注意)。"""
    bases = {normalize_page_basis(m.get("page_basis")) for m in source_meta.values()}
    bases.discard("unknown")
    return len(bases) <= 1


__all__ = [
    "PAGE_BASIS", "EXTRACTION_METHODS", "PDF_PRIMARY", "PDF_OBSERVED",
    "normalize_page_basis", "qualify_pdf_observation",
    "to_print_page", "to_pdf_page", "page_basis_consistent",
]
