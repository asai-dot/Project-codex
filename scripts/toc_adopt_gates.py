"""toc_adopt_gates — DD-TOCADOPT-001 §4 の本番反映 required gates (report-only 検査)。

owner ratify 済み ACCEPTED §4 が「production 反映の前提」とした 7 gate を、採用 projection に
対する **機械検査**として実装する。全 gate green + owner 最終 ratify まで policy 本番切替/apply
はしない (本モジュールは検査するだけで何も書かない)。stdlib のみ・決定的。

gate 1 (既存 projection 完全再現) は ALOBookDX 本流の baseline projection export を要する。
本 repo に baseline 実データが無い間は `gate1_reproduces_projection(baseline, candidate)` の
**比較器**を提供し、合成 baseline で比較器の正当性を固定する (実 baseline 到着で即実行可)。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from edition_identity import APPLY_OK_STATUS, SUSPECTED_DIFFERENT  # noqa: E402
from edition_identity_v2 import classify_edition_identity_v2  # noqa: E402

_PROVENANCE_FIELDS = ("source_system", "provenance_origin", "locator", "page_basis", "source_hash")


def _node_set(rec: dict) -> set:
    """baseline export の1冊から (toc_node_id, parent_id, title_norm, page_start, origin) 集合。"""
    return {(n.get("toc_node_id"), n.get("parent_id"), n.get("title_norm"),
             n.get("page_start"), n.get("provenance_origin")) for n in rec.get("nodes", [])}


def gate1_reproduces_projection(baseline: dict, candidate: dict) -> dict:
    """gate_policy_unification_reproduces_existing_projection の比較器 (F2 強化版)。

    baseline/candidate = export_baseline() 形式 (nodes 付き)。sha 一致だけでなく
    **ノード集合・親子・ページ・base 分布**の同値を検査する (sha 衝突や粒度の取りこぼしを防ぐ)。
    """
    isbns = sorted(set(baseline) | set(candidate))
    sha_mismatch, base_mismatch, missing = [], [], []
    nodeset_mismatch, dist_mismatch = [], []
    for isbn in isbns:
        b, c = baseline.get(isbn), candidate.get(isbn)
        if b is None or c is None:
            missing.append(isbn)
            continue
        if b.get("projection_sha") != c.get("projection_sha"):
            sha_mismatch.append(isbn)
        if b.get("base_source") != c.get("base_source"):
            base_mismatch.append(isbn)
        if _node_set(b) != _node_set(c):
            nodeset_mismatch.append(isbn)
        if b.get("base_source_distribution") != c.get("base_source_distribution"):
            dist_mismatch.append(isbn)
    ok = not (sha_mismatch or base_mismatch or missing or nodeset_mismatch or dist_mismatch)
    return {"gate": "gate_policy_unification_reproduces_existing_projection", "pass": ok,
            "sha_mismatch": sha_mismatch, "base_source_mismatch": base_mismatch,
            "node_set_mismatch": nodeset_mismatch, "base_distribution_mismatch": dist_mismatch,
            "missing": missing,
            "note": ("baseline export は export_baseline() 形式 (toc_node_id/parent_id/title_norm/"
                     "page_start/page_end/provenance_origin/source_snapshot_hash/projection_sha)。"
                     "ALOBookDX 実 631クラスタ baseline 到着でそのまま本実行。")}


def gate2_edition_regression(gold_rows: list[dict]) -> dict:
    """gate_edition_identity_phase0_regression: 独立 adversarial gold に対する双方向検証。

    DD-EDIDENT-001-IMPL H5 是正: classifier 派生の known_conflict golden (false positive を含む)
    でなく、人手 truth の adversarial gold (`a`/`b`/`expected`) で双方向に固定する:
      * 真の別版/要レビュー (expected ∉ APPLY_OK) が合議参加 (APPLY_OK) へ昇格しない。
      * 真の同一 (expected ∈ APPLY_OK) が誤って弾かれない。
    旧形式 (legallib/canonical/v1_status) も後方互換で受ける (この場合は escape 検査のみ)。
    """
    escaped, false_block = [], []
    for r in gold_rows:
        if "a" in r and "b" in r:                      # 新 adversarial gold 形式
            res = classify_edition_identity_v2([r["a"], r["b"]])
            exp_apply = r.get("expected") in APPLY_OK_STATUS
            got_apply = res["status"] in APPLY_OK_STATUS
            if exp_apply and not got_apply:
                false_block.append({"case_id": r.get("case_id"), "got": res["status"]})
            if not exp_apply and got_apply:
                escaped.append({"case_id": r.get("case_id"), "got": res["status"]})
        else:                                          # 旧 known_conflict 形式 (escape のみ)
            res = classify_edition_identity_v2([r.get("legallib", {}), r.get("canonical", {})])
            if res["status"] in APPLY_OK_STATUS:
                escaped.append({"isbn": r.get("isbn"), "status": res["status"]})
    return {"gate": "gate_edition_identity_phase0_regression",
            "pass": not escaped and not false_block,
            "escaped_to_cluster": escaped, "false_blocked_true_same": false_block,
            "checked": len(gold_rows)}


def gate3_no_rich_to_shallow(adoptions: list[dict], policy: dict | None = None) -> dict:
    """gate_no_rich_to_shallow_degradation: guard 未満の源が base になっていない。

    F1: engine と同じ per-source override / default を policy から読む (閾値の二重定義を排除)。
    """
    guard = (policy or {}).get("step2_base_selection", {}).get("granularity_guard", {})
    default_ratio = guard.get("min_node_ratio_vs_richest_default", 0.2)
    per_source = guard.get("min_node_ratio_vs_richest_per_source", {})
    violations = []
    for a in adoptions:
        s2 = a.get("step2", {})
        base = s2.get("base")
        blocked = {b["source"] for b in s2.get("guard_blocked", [])}
        if base in blocked:
            violations.append({"isbn": a.get("isbn"), "base": base, "reason": "base is guard_blocked"})
        rc, rd = s2.get("richest_count"), s2.get("richest_depth")
        if base and rc:
            ratio = per_source.get(base, default_ratio)
            base_nodes = s2.get("candidates", {}).get(base, 0)
            base_depth = (s2.get("granularity", {}).get(base) or [0])[0]
            if base_nodes < ratio * rc:
                violations.append({"isbn": a.get("isbn"), "base": base,
                                   "node_ratio": round(base_nodes / rc, 3), "min_ratio": ratio})
            if rd and base_depth < rd:
                violations.append({"isbn": a.get("isbn"), "base": base,
                                   "base_depth": base_depth, "richest_depth": rd})
    return {"gate": "gate_no_rich_to_shallow_degradation",
            "pass": not violations, "violations": violations}


def gate4_node_provenance_complete(adoptions: list[dict]) -> dict:
    """gate_node_provenance_complete: 全採用/補完ノードに 5 provenance フィールド。"""
    missing = []
    for a in adoptions:
        for n in a.get("projection", []):
            absent = [f for f in _PROVENANCE_FIELDS if not n.get(f)]
            if absent:
                missing.append({"isbn": a.get("isbn"), "node": n.get("title_norm"),
                                "missing": absent})
    return {"gate": "gate_node_provenance_complete",
            "pass": not missing, "missing": missing[:20], "missing_count": len(missing)}


def gate5_no_node_invention(adoptions: list[dict], books_by_isbn: dict[str, dict]) -> dict:
    """gate_append_missing_no_node_invention: 採用ノードは必ず source snapshot に実在。"""
    invented = []
    for a in adoptions:
        book = books_by_isbn.get(a.get("isbn"), {})
        sources = book.get("sources", {})
        for n in a.get("projection", []):
            loc = n.get("locator", "")
            if "#" not in loc:
                invented.append({"isbn": a.get("isbn"), "locator": loc})
                continue
            src, idx = loc.split("#", 1)
            try:
                _ = sources[src][int(idx)]
            except (KeyError, IndexError, ValueError):
                invented.append({"isbn": a.get("isbn"), "locator": loc})
    return {"gate": "gate_append_missing_no_node_invention",
            "pass": not invented, "invented": invented}


def gate6_votes_by_provenance_origin(adoptions: list[dict], books_by_isbn: dict[str, dict]) -> dict:
    """gate_votes_by_provenance_origin: votes は provenance_origin 単位・同一 origin 二重計上禁止。"""
    violations = []
    for a in adoptions:
        book = books_by_isbn.get(a.get("isbn"), {})
        meta = book.get("source_meta", {})
        clustered = a.get("step1", {}).get("clustered_with_nodes", [])
        distinct_origins = len({meta.get(s, {}).get("provenance_origin", s) for s in clustered})
        for n in a.get("projection", []):
            v = n.get("votes_by_provenance_origin")
            if v is None:
                continue
            # 票数は distinct provenance_origin 数を超えてはならない (二重計上の検出)。
            if v > distinct_origins:
                violations.append({"isbn": a.get("isbn"), "node": n.get("title_norm"),
                                   "votes": v, "distinct_origins": distinct_origins})
    return {"gate": "gate_votes_by_provenance_origin",
            "pass": not violations, "violations": violations}


def gate7_report_only(adoptions: list[dict], corpus_result: dict | None = None) -> dict:
    """gate_report_only_no_write: 採用結果は投影のみ・書込フラグなし。"""
    bad = [a.get("isbn") for a in adoptions if a.get("report_only") is not True]
    corpus_ok = corpus_result is None or corpus_result.get("report_only") is True
    return {"gate": "gate_report_only_no_write",
            "pass": not bad and corpus_ok, "non_report_only": bad}


def gate8_lane_separation(adoptions: list[dict]) -> dict:
    """gate_node_lane_structural_separation (REAUDIT N1)。

    accepted / pending_human_review / rejected / non_adoptable が **構造上分離**され、
    projection==accepted で、accepted には保留・拒否・非採用要因が混ざらないことを保証する。
    """
    v = []
    for a in adoptions:
        isbn = a.get("isbn")
        lanes = a.get("lanes", {})
        acc = lanes.get("accepted", [])
        pend = lanes.get("pending_human_review", [])
        rej = lanes.get("rejected", [])
        nad = lanes.get("non_adoptable", [])

        # (1) projection は accepted と同一実体。
        if a.get("projection") is not acc:
            v.append({"isbn": isbn, "why": "projection is not accepted lane"})

        # (2) 各 node はちょうど1レーン (toc_node_id が複数レーンに跨らない)。
        ids = [n.get("toc_node_id") for n in acc + pend + nad]
        if len(ids) != len(set(ids)):
            v.append({"isbn": isbn, "why": "node appears in multiple lanes"})

        # (3) accepted は consensus かつ provenance 健全かつ lane タグが accepted。
        for n in acc:
            if not n.get("consensus"):
                v.append({"isbn": isbn, "node": n.get("title_norm"), "why": "accepted but non_consensus"})
            if not n.get("source_hash"):
                v.append({"isbn": isbn, "node": n.get("title_norm"), "why": "accepted but no source_hash"})
            if n.get("snapshot_missing"):
                v.append({"isbn": isbn, "node": n.get("title_norm"), "why": "accepted but snapshot_missing"})
            if n.get("needs_offset"):
                v.append({"isbn": isbn, "node": n.get("title_norm"), "why": "accepted but needs_offset"})
            if n.get("lane") != "accepted":
                v.append({"isbn": isbn, "node": n.get("title_norm"), "why": f"lane tag={n.get('lane')}"})

        # (4) non_adoptable は全て provenance 欠落要因。
        for n in nad:
            if not n.get("snapshot_missing"):
                v.append({"isbn": isbn, "node": n.get("title_norm"), "why": "non_adoptable without snapshot_missing"})

        # (5) rejected は採用/保留に出てこない (構造拒否)。
        rej_ids = {n.get("title_norm") for n in rej}
        if rej_ids & {n.get("title_norm") for n in acc + pend}:
            v.append({"isbn": isbn, "why": "rejected node leaks into accepted/pending"})

        # (6) envelope の apply_target は accepted_node_set。
        env = a.get("envelope", {})
        if env.get("apply_target") != "accepted_node_set":
            v.append({"isbn": isbn, "why": f"apply_target={env.get('apply_target')}"})
    return {"gate": "gate_node_lane_structural_separation", "pass": not v, "violations": v}


def run_gates(books: list[dict], adoptions: list[dict], *,
              policy: dict | None = None,
              corpus_result: dict | None = None,
              baseline_projection: dict | None = None,
              candidate_projection: dict | None = None,
              known_conflict_rows: list[dict] | None = None) -> dict:
    """全 gate を走らせて要約を返す。baseline/known_conflict 未供給の gate は skipped。"""
    by_isbn = {b.get("isbn"): b for b in books}
    results = []
    if baseline_projection is not None and candidate_projection is not None:
        results.append(gate1_reproduces_projection(baseline_projection, candidate_projection))
    else:
        results.append({"gate": "gate_policy_unification_reproduces_existing_projection",
                        "pass": None, "skipped": "ALOBookDX baseline projection 未供給"})
    if known_conflict_rows is not None:
        results.append(gate2_edition_regression(known_conflict_rows))
    else:
        results.append({"gate": "gate_edition_identity_phase0_regression",
                        "pass": None, "skipped": "known_conflict fixture 未供給"})
    results.append(gate3_no_rich_to_shallow(adoptions, policy))
    results.append(gate4_node_provenance_complete(adoptions))
    results.append(gate5_no_node_invention(adoptions, by_isbn))
    results.append(gate6_votes_by_provenance_origin(adoptions, by_isbn))
    results.append(gate7_report_only(adoptions, corpus_result))
    results.append(gate8_lane_separation(adoptions))

    checked = [g for g in results if g["pass"] is not None]
    return {
        "gates": results,
        "all_checked_pass": all(g["pass"] for g in checked),
        "passed": sum(1 for g in checked if g["pass"]),
        "checked": len(checked),
        "skipped": [g["gate"] for g in results if g["pass"] is None],
        "report_only": True,
    }


__all__ = ["gate1_reproduces_projection", "gate2_edition_regression",
           "gate3_no_rich_to_shallow", "gate4_node_provenance_complete",
           "gate5_no_node_invention", "gate6_votes_by_provenance_origin",
           "gate7_report_only", "run_gates", "SUSPECTED_DIFFERENT"]
