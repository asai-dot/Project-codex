"""apply_guard — v0.3.1 本適用の物理ゲート (DDLEGALLIBCONCORD §3 blocking)。

GPT 監査が apply 解禁前の必須 hard gate として挙げた7条件を、ISBN 単位で機械判定する。
**1つでも欠ければ apply 拒否**。owner の人手レビュー前提を「運用」ではなく「コード」で強制する
(v0.2 の危険＝レビュー未強制 を恒久的に塞ぐ)。

report-only / 純関数。本番書き込みはしない (apply 実行器がこの判定を必ず通す前提)。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from edition_identity import is_apply_allowed_identity  # noqa: E402

# 7 gate のコード。
GATES = (
    "whitelist_required",          # owner 承認 ISBN whitelist にあること (create 含む)
    "no_unresolved_conflict",      # unresolved conflict が無いこと
    "edition_identity_resolved",   # edition/manifestation 同一性が解決済み
    "pdf_authority_qualified",     # PDF authority 使用時は qualified_pdf_observation
    "rollback_bundle_present",     # rollback bundle が存在し apply log から参照可能
    "decision_log_append_only",    # decision_log.jsonl が append-only
    "all_nodes_accounted_for",     # 全 node が matched/conflict/orphan/quarantined/dropped に分類
)


def evaluate_apply_gate(req: dict, *, whitelist: set[str] | None) -> dict:
    """1 ISBN の apply 可否を7 gate で判定。

    req の想定キー:
        isbn, unresolved_conflict_count(int), edition_identity_status(str),
        uses_pdf_authority(bool), pdf_observation_qualified(bool),
        rollback_bundle_present(bool), decision_log_append_only(bool),
        all_nodes_accounted_for(bool)

    Returns: {"isbn", "allowed"(bool), "refusals"[gateコード...], "passed"[...]}
    """
    isbn = req.get("isbn")
    refusals: list[str] = []

    # 1 whitelist (None=未承認とみなす)。create 含め全 write に必須。
    if whitelist is None or isbn not in whitelist:
        refusals.append("whitelist_required")
    # 2 unresolved conflict
    if int(req.get("unresolved_conflict_count", 0)) > 0:
        refusals.append("no_unresolved_conflict")
    # 3 edition identity
    if not is_apply_allowed_identity(str(req.get("edition_identity_status", ""))):
        refusals.append("edition_identity_resolved")
    # 4 PDF authority qualification (PDF を typ にしている時のみ要求)
    if req.get("uses_pdf_authority") and not req.get("pdf_observation_qualified"):
        refusals.append("pdf_authority_qualified")
    # 5 rollback bundle
    if not req.get("rollback_bundle_present"):
        refusals.append("rollback_bundle_present")
    # 6 decision log append-only
    if not req.get("decision_log_append_only"):
        refusals.append("decision_log_append_only")
    # 7 all nodes accounted for
    if not req.get("all_nodes_accounted_for"):
        refusals.append("all_nodes_accounted_for")

    return {
        "isbn": isbn,
        "allowed": not refusals,
        "refusals": refusals,
        "passed": [g for g in GATES if g not in refusals],
    }


def filter_appliable(reqs: list[dict], *, whitelist: set[str] | None) -> dict:
    """複数 ISBN を評価し、apply 可能な ISBN と拒否理由集計を返す。"""
    from collections import Counter

    results = [evaluate_apply_gate(r, whitelist=whitelist) for r in reqs]
    allowed = [r["isbn"] for r in results if r["allowed"]]
    refusal_counts: Counter = Counter()
    for r in results:
        for g in r["refusals"]:
            refusal_counts[g] += 1
    return {
        "allowed_isbns": allowed,
        "allowed_count": len(allowed),
        "blocked_count": len(results) - len(allowed),
        "refusal_counts": dict(refusal_counts),
        "results": results,
    }


__all__ = ["GATES", "evaluate_apply_gate", "filter_appliable"]
