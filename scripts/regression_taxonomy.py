"""regression_taxonomy — defect コードの安定分類と修復前後の回帰検出 (DDSELFHEAL C1 前提)。

GPT 監査 (DDSELFHEAL-C0) が C1 write 解禁の **必須前提** に指定: 「regression taxonomy が
C1 前に必須」。data_health が出す defect コード (L1/L2/L3/chain) を安定した family に
正規化し、修復 plan の前後で defect 集合を比較して『直った / 変わらない / 新規回帰 / 悪化』を
機械判定する。これにより repair が health を上げても別の層を壊していないかを監視できる。

**分類と差分を返すだけ。本番書き込みは一切しない。** stdlib のみ・決定的。
"""

from __future__ import annotations

# defect code → (family, severity, expected_route, c1_relevant)
# severity: P0 (apply ブロッカー) / P1 (連結を損なう) / P2 (品質低下)。
# c1_relevant: C1 で決定的 repair が触れる可能性のある defect か (= 回帰監視対象)。
_TAXONOMY: dict[str, tuple[str, str, str, bool]] = {
    # L1 書誌
    "L1:isbn": ("bib_identity", "P0", "human", False),
    "L1:title": ("bib_completeness", "P1", "refetch_ndl", False),
    "L1:publisher": ("bib_completeness", "P2", "refetch_ndl", False),
    "L1:year": ("bib_completeness", "P2", "refetch_ndl", False),
    # L2 TOC
    "L2:toc_absent": ("toc_presence", "P1", "refetch_legallib", False),
    "L2:toc_flat_only": ("toc_richness", "P2", "refetch_legallib", False),
    "L2:toc_too_sparse": ("toc_richness", "P2", "refetch_legallib", False),
    # L3 本文
    "L3:page_basis_unknown": ("page_basis", "P1", "auto_reprofile", True),
    "L3:page_basis_inconsistent": ("page_basis", "P1", "auto_convert", True),
    "L3:body_sha_absent": ("body_integrity", "P1", "auto_hash", True),
    "L3:edition_unresolved": ("edition_identity", "P0", "human", False),
    # chain 連結
    "chain:nodes_unaccounted": ("chain_coverage", "P0", "quarantine", True),
    "chain:unresolved_conflicts": ("chain_conflict", "P0", "human", False),
}

_UNKNOWN = ("unclassified", "P1", "human", False)


def _norm_code(code: str) -> str:
    """`chain:unresolved_conflicts:3` の様な可変サフィックスを安定 key に畳む。"""
    if code.startswith("chain:unresolved_conflicts"):
        return "chain:unresolved_conflicts"
    return code


def classify(code: str) -> dict:
    fam, sev, route, c1 = _TAXONOMY.get(_norm_code(code), _UNKNOWN)
    return {"code": _norm_code(code), "family": fam, "severity": sev,
            "expected_route": route, "c1_relevant": c1,
            "known": _norm_code(code) in _TAXONOMY}


def classify_defects(defects: list[str]) -> dict:
    """defect 一覧を family/severity 別に集計 (regression dashboard の土台)。"""
    rows = [classify(d) for d in defects]
    by_family: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    unknown: list[str] = []
    for r in rows:
        by_family[r["family"]] = by_family.get(r["family"], 0) + 1
        by_severity[r["severity"]] = by_severity.get(r["severity"], 0) + 1
        if not r["known"]:
            unknown.append(r["code"])
    return {
        "total": len(rows),
        "by_family": dict(sorted(by_family.items())),
        "by_severity": dict(sorted(by_severity.items())),
        "p0_count": by_severity.get("P0", 0),
        # 未知 defect コード = taxonomy 更新が要るシグナル (黙って捨てない)。
        "unknown_codes": sorted(set(unknown)),
        "rows": rows,
    }


def regression_diff(before: list[str], after: list[str]) -> dict:
    """修復前後の defect 集合を比較し回帰を機械判定する。

    fixed         … before にあり after で消えた (修復成功)。
    persisted     … 両方に残る (未修復・正常な未着手)。
    new           … after で新たに出た defect (= 回帰の疑い)。
    new_p0        … new のうち P0 (apply ブロッカーを新設 = 重大回帰)。
    has_regression … new が空でなければ True (repair が別所を壊した可能性)。
    """
    b, a = set(before), set(after)
    fixed = sorted(b - a)
    persisted = sorted(b & a)
    new = sorted(a - b)
    new_rows = [classify(c) for c in new]
    new_p0 = sorted(r["code"] for r in new_rows if r["severity"] == "P0")
    return {
        "fixed": fixed,
        "persisted": persisted,
        "new": new,
        "new_p0": new_p0,
        "fixed_count": len(fixed),
        "new_count": len(new),
        "has_regression": bool(new),
        # C1 不変条件: 決定的 repair は新規 P0 を作ってはならない。
        "introduces_p0": bool(new_p0),
        "net_defect_delta": len(a) - len(b),
    }


__all__ = ["classify", "classify_defects", "regression_diff",
           "_TAXONOMY", "_UNKNOWN"]
