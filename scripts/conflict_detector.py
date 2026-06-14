"""conflict_detector — concordance 上の矛盾/隔離を検出 (DDLEGALLIBCONCORD v0.3.1)。

GPT 指定の追加7パターン + base を report-only で検出する。各 conflict は既定 unresolved。
unresolved が残る ISBN は apply_guard が apply を拒否する (P0-4)。本番書き込みなし。
"""


from __future__ import annotations

CONFLICT_DETECTOR_VERSION = "0.3.1"

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from edition_identity import RESOLVED_SAME, MANUAL_RESOLVED, classify_edition_identity  # noqa: E402

# 別表/索引/凡例/書式 等 (appendix_or_table_misclassified 用)。
_APPENDIX_RX = re.compile(r"(索引|別表|凡例|書式|資料編?|付録|附録|参考文献|奥付)")


def _coverage_mismatch(normalized: dict, *, ratio: float = 3.0) -> list[dict]:
    counts = {s: len(ns) for s, ns in normalized.items() if ns}
    if len(counts) < 2:
        return []
    hi, lo = max(counts.values()), min(counts.values())
    if lo > 0 and hi / lo >= ratio:
        return [{"pattern": "coverage_mismatch", "severity": "major", "resolved": False,
                 "detail": {"counts": counts, "ratio": round(hi / lo, 2)}}]
    return []


def _page_basis_mismatch(source_meta: dict) -> list[dict]:
    bases = {s: m.get("page_basis") for s, m in source_meta.items() if m.get("page_basis")}
    distinct = {b for b in bases.values() if b and b != "unknown"}
    if len(distinct) >= 2:
        return [{"pattern": "page_basis_mismatch", "severity": "moderate", "resolved": False,
                 "detail": {"page_basis": bases}}]
    return []


def _edition_mismatch(source_meta: dict) -> list[dict]:
    bib = [{"source": s, **{k: m.get(k) for k in
            ("isbn", "title", "publisher", "year", "edition", "volume", "page_count")}}
           for s, m in source_meta.items()]
    res = classify_edition_identity(bib)
    if res["status"] not in (RESOLVED_SAME, MANUAL_RESOLVED):
        sev = "structural" if res["status"] == "suspected_different_manifestation" else "moderate"
        return [{"pattern": "edition_mismatch_suspected", "severity": sev, "resolved": False,
                 "detail": res}]
    return []


def _partial_toc(normalized: dict) -> list[dict]:
    out = []
    for s, ns in normalized.items():
        if not ns:
            continue
        min_depth = min(n["depth"] for n in ns)
        if min_depth > 1:  # 冒頭階層が欠落 = 途中から
            out.append({"pattern": "partial_toc_source", "severity": "moderate",
                        "resolved": False, "detail": {"source": s, "min_depth": min_depth}})
    return out


def _appendix_misclassified(normalized: dict) -> list[dict]:
    out = []
    for s, ns in normalized.items():
        bad = [n["title"] for n in ns if n["depth"] == 1 and _APPENDIX_RX.search(n["title"])]
        # depth1 に索引/別表等が「混在」かつ本体章もある場合に疑い。
        has_body = any(n["depth"] >= 2 for n in ns)
        if bad and has_body and len(bad) >= 2:
            out.append({"pattern": "appendix_or_table_misclassified", "severity": "minor",
                        "resolved": False, "detail": {"source": s, "examples": bad[:5]}})
    return out


def _repeated_heading(repeated: dict) -> list[dict]:
    # 正当な反復 (総論/小括 等) を duplicate と誤検出しないための明示分類。
    out = []
    for s, m in repeated.items():
        out.append({"pattern": "same_heading_repeated_legitimately", "severity": "info",
                    "resolved": True,  # 正当反復は解決済み扱い (apply ブロックしない)
                    "detail": {"source": s, "headings": m}})
    return out


def _numbering_scheme_changed(normalized: dict) -> list[dict]:
    schemes = {}
    for s, ns in normalized.items():
        sset = {n["scheme"] for n in ns if n["scheme"]}
        if sset:
            schemes[s] = sorted(sset)
    allschemes = {sc for v in schemes.values() for sc in v}
    if len(allschemes) >= 2 and len(schemes) >= 2:
        return [{"pattern": "numbering_scheme_changed", "severity": "minor", "resolved": False,
                 "detail": {"by_source": schemes}}]
    return []


def detect_conflicts(concordance: dict, source_meta: dict) -> list[dict]:
    """concordance + ソース別メタから conflict/quarantine を列挙。"""
    normalized = concordance["normalized"]
    conflicts: list[dict] = []
    conflicts += _coverage_mismatch(normalized)
    conflicts += _page_basis_mismatch(source_meta)
    conflicts += _edition_mismatch(source_meta)
    conflicts += _partial_toc(normalized)
    conflicts += _appendix_misclassified(normalized)
    conflicts += _repeated_heading(concordance.get("repeated_headings", {}))
    conflicts += _numbering_scheme_changed(normalized)
    # orphan は削除せず quarantine (P0-6)。
    orphan_clusters = [c for c in concordance["clusters"] if c["kind"] == "orphan"]
    if orphan_clusters:
        conflicts.append({"pattern": "orphan_quarantined", "severity": "info", "resolved": False,
                          "detail": {"orphan_clusters": len(orphan_clusters)}})
    return conflicts


def unresolved_count(conflicts: list[dict]) -> int:
    return sum(1 for c in conflicts if not c.get("resolved"))


__all__ = ["detect_conflicts", "unresolved_count"]
