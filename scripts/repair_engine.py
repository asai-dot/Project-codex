"""repair_engine — 自己浄化 repair の dry-run オーケストレータ (DDSELFHEAL Phase C0)。

登録 repairer を全 book に当て、**plan (修復案) と repair manifest を出すだけ**。
各 plan は apply_guard 7gate で評価し、phase 書込許可 (C0=実書込なし) と AND を取る。
decision_log に append-only で repair_planned を残し chain hash を返す。

**物理書込は一切しない** (writes_executed は常に 0)。実書込は owner ratify + golden 拡張 +
whitelist + phase 昇格 (C1/C2) を全通過してから別途。stdlib のみ・決定的。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# register 副作用で repairer を登録 (import 順 = registry 順)。
import repair_offset  # noqa: E402,F401
import repair_sha  # noqa: E402,F401
import repair_normalize  # noqa: E402,F401
import repair_quarantine  # noqa: E402,F401
from apply_guard import evaluate_apply_gate  # noqa: E402
from data_health import book_health  # noqa: E402
from decision_log import DecisionLog, verify_chain  # noqa: E402
from regression_taxonomy import regression_diff  # noqa: E402
from repair_base import (  # noqa: E402
    apply_plan, build_manifest, is_write_allowed_in_phase, plan_field, registry, sha256_of,
)
from review_report import book_summary  # noqa: E402
from thresholds import load_thresholds  # noqa: E402

REPAIR_ENGINE_VERSION = "0.3.1"


def _inverse_rollback(plan: dict) -> dict:
    """plan の before/after を入れ替えた rollback bundle (可逆性の明示)。"""
    return {"target": plan.get("target"),
            "changes": [{"locator": c["locator"], "field": c["field"],
                         "before": c["after"], "after": c["before"]}
                        for c in plan.get("changes", [])]}


def _repair_metrics(book: dict, repairer, plan: dict, rollback: dict | None,
                    pre_health: float, thresholds: dict) -> dict:
    """C1 前に必須の証明系メトリクスを dry-run で算出 (本は変更しない)。"""
    applied = apply_plan(book, plan)
    # no-op 二度がけ証明: 適用後は同じ repairer がもう発火しない。
    no_op = repairer.detect(applied) is False
    # health delta + regression: 適用で health が下がらず、新規 P0 defect も作らない。
    pre_defects = book_health(book, thresholds)["defects"]
    post_eval = book_health(applied, thresholds)
    post_health = post_eval["health_score"]
    regression = regression_diff(pre_defects, post_eval["defects"])
    # rollback 検証: plan→rollback で対象 field が原状復帰する。
    rollback_verified = None
    if rollback is not None:
        restored = apply_plan(applied, rollback)
        rollback_verified = all(
            plan_field(book, c["locator"], c["field"]) == plan_field(restored, c["locator"], c["field"])
            for c in plan.get("changes", []))
    return {
        "affected_count": len(plan.get("changes", [])),
        "pre_health": pre_health,
        "post_health": post_health,
        "health_delta": round(post_health - pre_health, 1),
        "idempotency_proof": sha256_of(plan),
        "no_op_second_run": no_op,
        "rollback_verified": rollback_verified,
        "regression": regression,
        "owner_signoff": None,  # C0 は未署名 (C1 で owner が入れる)
    }


def _gate_req(isbn: str, summary: dict, *, rollback_present: bool) -> dict:
    return {
        "isbn": isbn,
        "unresolved_conflict_count": summary["conflicts"]["unresolved"],
        "edition_identity_status": summary["edition_identity_status"],
        "uses_pdf_authority": False,        # repair は PDF authority を主張しない
        "pdf_observation_qualified": False,
        "rollback_bundle_present": rollback_present,
        "decision_log_append_only": True,
        "all_nodes_accounted_for": summary["all_nodes_accounted_for"],
    }


def run_repairs(books: list[dict], *, whitelist: set[str] | None = None,
                rollback_present: bool = False, phase: str = "C0",
                thresholds: dict | None = None,
                decision_log_path: str | Path | None = None) -> dict:
    t = thresholds or load_thresholds()
    dlog = DecisionLog(decision_log_path) if decision_log_path else None
    manifests: list[dict] = []

    for b in books:
        isbn = b["isbn"]
        summary = book_summary(isbn, b.get("title", ""), b.get("sources", {}),
                               b.get("source_meta", {}), t)
        pre_health = book_health(b, t)["health_score"]
        gate = evaluate_apply_gate(_gate_req(isbn, summary, rollback_present=rollback_present),
                                   whitelist=whitelist)
        for r in registry():
            if not r.detect(b):
                continue
            plan = r.plan(b)
            if plan is None:
                continue
            # 冪等の素: plan は決定的 (副作用なしに二度同じ)。
            plan_deterministic = (r.plan(b) == plan)
            rollback = _inverse_rollback(plan) if rollback_present else None
            metrics = _repair_metrics(b, r, plan, rollback, pre_health, t)
            dl_hash = None
            if dlog is not None:
                rec = dlog.append(isbn=isbn, conflict_id=f"repair:{r.name}",
                                  decision="repair_planned", decided_by="repair_engine",
                                  basis=plan["basis"], repair_class=r.repair_class)
                dl_hash = rec["hash"]
            wl_ref = "owner_whitelist" if (whitelist and isbn in whitelist) else None
            m = build_manifest(b, r, plan, gate_result=gate, rollback_bundle=rollback,
                               decision_log_hash=dl_hash, owner_or_whitelist_ref=wl_ref,
                               metrics=metrics)
            # 実書込許可 = phase が許す AND apply_guard 通過 (C0 は phase が常に不許可)。
            m["phase"] = phase
            m["write_allowed"] = bool(
                is_write_allowed_in_phase(r.repair_class, phase) and gate["allowed"])
            m["plan_deterministic"] = plan_deterministic
            manifests.append(m)

    chain = verify_chain(decision_log_path) if decision_log_path else {"ok": True, "count": 0}
    write_allowed = sum(1 for m in manifests if m["write_allowed"])
    return {
        "engine_version": REPAIR_ENGINE_VERSION,
        "phase": phase,
        "report_only": True,
        "writes_executed": 0,                # C0: 物理書込なし
        "manifests": manifests,
        "manifest_count": len(manifests),
        "write_allowed_count": write_allowed,  # C0 では 0 のはず
        "by_repairer": dict(Counter(m["repairer"] for m in manifests)),
        "by_class": dict(Counter(m["repair_class"] for m in manifests)),
        "decision_log_chain": chain,
        "all_plans_deterministic": all(m["plan_deterministic"] for m in manifests),
        # DDSELFHEAL-C0 review: C1 前に全 plan が満たすべき証明系。
        "all_no_op_second_run": all(m["no_op_second_run"] for m in manifests),
        "all_rollback_verified": all(
            m["rollback_verified"] for m in manifests if m["rollback_verified"] is not None),
        "all_health_non_decreasing": all(m["health_delta"] >= 0 for m in manifests),
        # C1 不変条件: 決定的 repair は新規 P0 defect を一切作らない。
        "no_repair_introduces_p0": all(
            not (m.get("regression") or {}).get("introduces_p0") for m in manifests),
        "regression_free": all(
            not (m.get("regression") or {}).get("has_regression") for m in manifests),
    }


def _demo_books() -> list[dict]:
    # 各 book が概ね1 repairer を示す showcase (title_norm 等を入れて他を抑制)。
    return [
        {  # offset_page_convert: 検証済 offset・print_page 未派生
            "isbn": "9784000000010", "title": "国際取引法",
            "page_offset": {"offset": 8, "confidence": 1.0, "validated": True, "anchors": 3},
            "source_meta": {
                "legallib": {"isbn": "9784000000010", "title": "国際取引法", "publisher": "有斐閣",
                             "year": "2018", "page_basis": "pdf_page", "source_sha256": "sha256:x"}},
            "sources": {"legallib": [
                {"title": "第1章 序論", "title_norm": "第1章序論", "depth": 1, "pdf_page": 9},
                {"title": "第2章 当事者", "title_norm": "第2章当事者", "depth": 1, "pdf_page": 58}]},
        },
        {  # body_sha_recompute: source_content あり・sha 欠落
            "isbn": "9784000000020", "title": "民法",
            "source_meta": {"legallib": {"isbn": "9784000000020", "title": "民法",
                                          "page_basis": "print_page", "source_content": "目次本文..."}},
            "sources": {"legallib": [{"title": "第1章 総則", "title_norm": "第1章総則", "depth": 1, "print_page": 1}]},
        },
        {  # normalize_title_regen: title_norm 欠落
            "isbn": "9784000000030", "title": "会社法",
            "source_meta": {"legallib": {"isbn": "9784000000030", "title": "会社法",
                                          "page_basis": "print_page", "source_sha256": "sha256:y"}},
            "sources": {"legallib": [{"title": "第1編 設立", "depth": 1, "print_page": 1}]},
        },
        {  # quarantine_orphan: cross-source 一致なし → orphan
            "isbn": "9784000000040", "title": "刑法",
            "source_meta": {
                "legallib": {"isbn": "9784000000040", "title": "刑法", "page_basis": "print_page", "source_sha256": "sha256:a"},
                "bencom": {"isbn": "9784000000040", "title": "刑法", "page_basis": "print_page", "source_sha256": "sha256:b"}},
            "sources": {
                "legallib": [{"title": "第1章 構成要件", "title_norm": "第1章構成要件", "depth": 1, "print_page": 1}],
                "bencom": [{"title": "第A部 違法性", "title_norm": "第a部違法性", "depth": 1, "print_page": 1}]},
        },
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DDSELFHEAL repair dry-run (C0, report-only)")
    ap.add_argument("--books")
    ap.add_argument("--only-isbns")
    ap.add_argument("--rollback-present", action="store_true")
    ap.add_argument("--phase", default="C0", choices=["C0", "C1", "C2"])
    ap.add_argument("--decision-log")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args(argv)

    books = _demo_books() if args.demo else json.loads(Path(args.books).read_text(encoding="utf-8"))
    wl = None
    if args.only_isbns:
        wl = {ln.strip() for ln in Path(args.only_isbns).read_text(encoding="utf-8").splitlines() if ln.strip()}
    res = run_repairs(books, whitelist=wl, rollback_present=args.rollback_present,
                      phase=args.phase, decision_log_path=args.decision_log)
    print(json.dumps({"phase": res["phase"], "manifests": res["manifest_count"],
                      "write_allowed": res["write_allowed_count"],
                      "writes_executed": res["writes_executed"],
                      "by_repairer": res["by_repairer"]},
                     ensure_ascii=False, sort_keys=True))
    print("repair dry-run (report-only): 物理書込なし。実書込は ratify+golden拡張+whitelist+phase昇格 後。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
