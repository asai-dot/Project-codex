"""data_health — 1冊の「3層チェーン健全度」スコアラ (report-only)。

ゴール (owner 定義): 総合メタ(L1 NDL書誌) → 個別メタ(L2 詳細TOC) → 本文(L3 PDF/物理) が
一貫して連なり AI 可読である状態。data_health はその達成度を 0–100 で可視化し、
自己浄化ループ (検知→修復→再スキャン) が「綺麗になっていく」ことを測れるようにする。

スコアは判定の可視化のみ。**本番書き込みは一切しない**。apply は別途 apply_guard が制御する。
stdlib のみ・決定的。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from edition_identity import APPLY_OK_STATUS  # noqa: E402
from page_basis import normalize_page_basis, page_basis_consistent  # noqa: E402
from review_report import book_summary  # noqa: E402
from thresholds import load_thresholds  # noqa: E402

DATA_HEALTH_VERSION = "0.3.1"

# L1: NDL 書誌で「連結に必須」とみなす最小フィールド。
_L1_FIELDS = ("isbn", "title", "publisher", "year")


def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def _l1_bib_score(source_meta: dict) -> tuple[float, list[str]]:
    """総合メタ完全性: 必須書誌フィールドが揃っているか (どれか1ソースにあれば可)。"""
    present = {f for m in source_meta.values() for f in _L1_FIELDS
               if str(m.get(f) or "").strip()}
    missing = [f for f in _L1_FIELDS if f not in present]
    return len(present) / len(_L1_FIELDS), missing


def _l2_toc_score(sources_nodes: dict, *, min_depth: int, min_nodes: int) -> tuple[float, list[str]]:
    """個別メタ豊富さ: simple ではなく階層/件数のある詳細TOC があるか。"""
    defects: list[str] = []
    total_nodes = sum(len(ns) for ns in sources_nodes.values())
    if total_nodes == 0:
        return 0.0, ["toc_absent"]
    max_depth = max((int(n.get("depth") or n.get("l") or 1)
                     for ns in sources_nodes.values() for n in ns), default=1)
    richest = max((len(ns) for ns in sources_nodes.values()), default=0)
    has_depth = max_depth >= min_depth
    has_volume = richest >= min_nodes
    if not has_depth:
        defects.append("toc_flat_only")  # 階層なし (simple の兆候)
    if not has_volume:
        defects.append("toc_too_sparse")
    return (0.5 * has_depth + 0.5 * has_volume), defects


def _l3_body_score(source_meta: dict, edition_status: str) -> tuple[float, list[str]]:
    """本文連結性: page_basis が判明し整合、PDF実体(sha)があり、版同一性が解決済みか。"""
    defects: list[str] = []
    bases = {normalize_page_basis(m.get("page_basis")) for m in source_meta.values()}
    bases.discard("unknown")
    has_basis = bool(bases)
    consistent = page_basis_consistent(source_meta)
    has_sha = any(str(m.get("source_sha256") or "").strip() for m in source_meta.values())
    edition_ok = edition_status in APPLY_OK_STATUS
    if not has_basis:
        defects.append("page_basis_unknown")
    if not consistent:
        defects.append("page_basis_inconsistent")
    if not has_sha:
        defects.append("body_sha_absent")
    if not edition_ok:
        defects.append("edition_unresolved")
    score = (0.3 * has_basis + 0.2 * consistent + 0.2 * has_sha + 0.3 * edition_ok)
    return _clamp01(score), defects


def book_health(book: dict, thresholds: dict | None = None) -> dict:
    """1冊の health (0–100) + 層別内訳 + defect 一覧 + 修復ヒントを返す。

    book = {isbn, title, source_meta:{src:{bib...}}, sources:{src:[nodes]}}。
    """
    t = thresholds or load_thresholds()
    h = t.get("health", {})
    w1 = h.get("weight_l1_bib", 30)
    w2 = h.get("weight_l2_toc", 40)
    w3 = h.get("weight_l3_body", 30)
    min_depth = h.get("l2_rich_min_depth", 2)
    min_nodes = h.get("l2_rich_min_nodes", 5)

    isbn = book.get("isbn", "")
    title = book.get("title", "")
    source_meta = book.get("source_meta", {})
    sources = book.get("sources", {})

    summary = book_summary(isbn, title, sources, source_meta, t)

    l1, m1 = _l1_bib_score(source_meta)
    l2, m2 = _l2_toc_score(sources, min_depth=min_depth, min_nodes=min_nodes)
    l3, m3 = _l3_body_score(source_meta, summary["edition_identity_status"])

    chain_ok = summary["all_nodes_accounted_for"]
    unresolved = summary["conflicts"]["unresolved"]
    chain_defects: list[str] = []
    if not chain_ok:
        chain_defects.append("nodes_unaccounted")
    if unresolved:
        chain_defects.append(f"unresolved_conflicts:{unresolved}")

    raw = w1 * l1 + w2 * l2 + w3 * l3
    # chain が壊れている (orphan / 未解決 conflict) 間は満点を出さない。
    chain_factor = 1.0 if (chain_ok and unresolved == 0) else 0.85
    score = round(raw * chain_factor, 1)

    defects = ([f"L1:{d}" for d in m1] + [f"L2:{d}" for d in m2]
               + [f"L3:{d}" for d in m3] + [f"chain:{d}" for d in chain_defects])

    # DDSELFHEAL must_fix #4: health_score と apply_eligibility を分離する。
    # health が高くても、以下の P0 ブロッカーが1つでもあれば apply 適格は 0。
    # (これは可視化であり、本番書込の物理ゲートは apply_guard が別途強制する。)
    apply_blockers: list[str] = []
    if summary["edition_identity_status"] not in APPLY_OK_STATUS:
        apply_blockers.append("edition_unresolved")
    if not chain_ok:
        apply_blockers.append("nodes_unaccounted")
    if unresolved:
        apply_blockers.append("unresolved_conflicts")
    apply_eligible = not apply_blockers

    clean = not defects
    clean_reason = ("no defects across L1/L2/L3/chain" if clean
                    else f"{len(defects)} defect(s): " + ",".join(defects[:4]))
    return {
        "isbn": isbn, "title": title,
        "health_score": score,
        "layers": {
            "l1_bib": round(l1, 3),
            "l2_toc": round(l2, 3),
            "l3_body": round(l3, 3),
        },
        "chain_ok": chain_ok,
        "unresolved_conflicts": unresolved,
        "risk": summary["risk"],
        # health とは独立した apply 適格 (P0 cap)。本番ゲートは apply_guard。
        "apply_eligible": apply_eligible,
        "apply_blockers": apply_blockers,
        "clean": clean,
        "clean_reason": clean_reason,
        "quarantined": not chain_ok,  # nodes_unaccounted は quarantine 対象
        "defects": defects,
        "repair_hints": _repair_hints(defects),
    }


# defect → 自己浄化ループでの想定ルート (auto / refetch / human)。実装は後続フェーズ。
_REPAIR_ROUTE = {
    "L1:isbn": "human", "L1:title": "refetch_ndl", "L1:publisher": "refetch_ndl",
    "L1:year": "refetch_ndl",
    "L2:toc_absent": "refetch_legallib", "L2:toc_flat_only": "refetch_legallib",
    "L2:toc_too_sparse": "refetch_legallib",
    "L3:page_basis_unknown": "auto_reprofile", "L3:page_basis_inconsistent": "auto_convert",
    "L3:body_sha_absent": "auto_hash", "L3:edition_unresolved": "human",
    "chain:nodes_unaccounted": "quarantine",
}


def _repair_hints(defects: list[str]) -> dict:
    routes: dict[str, list[str]] = {}
    for d in defects:
        key = d.split(":unresolved", 1)[0] if d.startswith("chain:unresolved") else d
        route = _REPAIR_ROUTE.get(key, "human")
        routes.setdefault(route, []).append(d)
    return routes


def corpus_health(books: list[dict], thresholds: dict | None = None) -> dict:
    """corpus 全体の health 分布 + apply 適格 + quarantine KPI。report-only。

    DDSELFHEAL must_fix #4/#5: health と apply_eligibility を分離し、quarantine を
    「成功」でなく管理対象の負債として KPI 化する。age/escape_rate/recurrence は
    スナップショット単体では算出不可 → 永続 ledger 必須 (needs_ledger に明示)。
    """
    t = thresholds or load_thresholds()
    rows = [book_health(b, t) for b in books]
    scores = [r["health_score"] for r in rows]
    n = len(rows) or 1
    buckets = {"0-49": 0, "50-79": 0, "80-99": 0, "100": 0}
    for s in scores:
        if s >= 100:
            buckets["100"] += 1
        elif s >= 80:
            buckets["80-99"] += 1
        elif s >= 50:
            buckets["50-79"] += 1
        else:
            buckets["0-49"] += 1

    # defect reason_code 分布 (should_fix: regression taxonomy の土台)。
    defect_counts: dict[str, int] = {}
    for r in rows:
        for d in r["defects"]:
            defect_counts[d] = defect_counts.get(d, 0) + 1

    quarantine_count = sum(1 for r in rows if r["quarantined"])
    apply_eligible_count = sum(1 for r in rows if r["apply_eligible"])
    return {
        "books": len(rows),
        "mean_health": round(sum(scores) / n, 1),
        "min_health": min(scores, default=0.0),
        "buckets": buckets,
        "clean_count": sum(1 for r in rows if r["clean"]),
        # health とは別軸: apply 適格 (P0 cap 通過) と quarantine 負債。
        "apply_eligible_count": apply_eligible_count,
        "quarantine": {
            "count": quarantine_count,
            "rate": round(quarantine_count / n, 3),
            # 以下はスナップショット単体では出せない (履歴 ledger が要る)。
            "needs_ledger": ["age", "escape_rate", "recurrence_rate"],
        },
        "defect_counts": dict(sorted(defect_counts.items())),
        "rows": rows,
        "report_only": True,
    }


__all__ = ["DATA_HEALTH_VERSION", "book_health", "corpus_health"]
