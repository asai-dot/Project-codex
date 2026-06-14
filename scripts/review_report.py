"""review_report — owner 用 book-level conflict summary (DDLEGALLIBCONCORD v0.3.1 P0-7)。

owner が conflict.jsonl を直読するのは非現実的。book単位サマリ + node単位detail の2層で、
「なぜ安全/危険か」を一目で出す。report-only。本番書き込みなし。
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from concordance import build_concordance  # noqa: E402
from conflict_detector import detect_conflicts, unresolved_count  # noqa: E402
from edition_identity import (  # noqa: E402
    APPLY_OK_STATUS,
    classify_edition_identity,
)


def _risk(edition_status: str, conflicts: list[dict], accounted: bool) -> str:
    if not accounted:
        return "high"
    if any(c["severity"] == "structural" and not c.get("resolved") for c in conflicts):
        return "high"
    if edition_status not in APPLY_OK_STATUS:
        return "high"
    if unresolved_count(conflicts) > 0:
        return "medium"
    return "low"


def book_summary(isbn: str, title: str,
                 sources_nodes: dict[str, list[dict]],
                 source_meta: dict) -> dict:
    """1冊の concordance + conflict から owner 向け summary を作る。"""
    conc = build_concordance(sources_nodes)
    conflicts = detect_conflicts(conc, source_meta)
    bib = [{"source": s, **{k: m.get(k) for k in
            ("isbn", "title", "publisher", "year", "edition", "volume", "page_count")}}
           for s, m in source_meta.items()]
    edition = classify_edition_identity(bib)
    acc = conc["all_nodes_accounted_for"]
    unresolved = unresolved_count(conflicts)
    risk = _risk(edition["status"], conflicts, acc)
    # consensus に数えられない (provenance_origin 未宣言) source 数 (GPT note)。
    consensus_excluded = sum(1 for m in source_meta.values() if not m.get("provenance_origin"))

    if risk == "low":
        rec = "approve candidate (no unresolved conflict, identity resolved)"
    elif risk == "medium":
        rec = f"approve only if {unresolved} unresolved conflicts are stamped"
    else:
        rec = "do not approve; resolve identity / structural conflict first"

    return {
        "isbn": isbn, "title": title,
        "sources": {s: len(ns) for s, ns in sources_nodes.items()},
        "edition_identity_status": edition["status"],
        "all_nodes_accounted_for": acc,
        "conflicts": {
            "unresolved": unresolved,
            "resolved": len(conflicts) - unresolved,
            "total": len(conflicts),
            "by_pattern": dict(Counter(c["pattern"] for c in conflicts)),
        },
        "risk": risk,
        "recommended_action": rec,
        "consensus_excluded_sources": consensus_excluded,
        "_conflicts_detail": conflicts,
    }


def render_book_summary_md(s: dict) -> str:
    src = ", ".join(f"{k} {v} nodes" for k, v in s["sources"].items())
    c = s["conflicts"]
    return "\n".join([
        f"### {s['isbn']}  {s['title']}",
        f"- sources: {src}",
        f"- edition_identity: {s['edition_identity_status']}",
        f"- conflicts: {c['unresolved']} unresolved / {c['resolved']} resolved"
        f"  (patterns: {c['by_pattern'] or '-'})",
        f"- all_nodes_accounted_for: {s['all_nodes_accounted_for']}",
        f"- **risk: {s['risk']}**",
        f"- recommended: {s['recommended_action']}",
        "",
    ])


__all__ = ["book_summary", "render_book_summary_md"]
