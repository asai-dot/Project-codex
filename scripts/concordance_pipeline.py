"""concordance_pipeline — v0.3.1 統合ドライバ兼 Phase0 evidence ハーネス (report-only)。

9モジュール (concordance / conflict_detector / edition_identity / page_basis /
authority_resolver / review_report / apply_guard / decision_log) を束ね、複数ソース
book 入力から **GPT 指定の最小 dry-run evidence 5点** を生成する:

  1. source inventory table          -> evidence/source_inventory.csv
  2. parser success histogram         -> evidence/parser_histogram.csv
  3. (既知 conflict 10冊 seed は入力側) -> conflicts.jsonl (review_report 経由)
  4. all_nodes_accounted_for 照合      -> evidence/accounting_reconciliation.csv
  5. apply_guard 物理拒否ログ           -> evidence/apply_guard_log.jsonl
  + decision_log chain hash サンプル検証 -> evidence/decision_log.jsonl + verify

**apply_guard は評価のみ。final_toc / app/data/toc への書き込みは一切しない (report-only)。**
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_guard import evaluate_apply_gate  # noqa: E402
from authority_resolver import AUTH_PDF_PRIMARY, resolve_authority  # noqa: E402
from concordance import CONCORDANCE_VERSION, build_concordance  # noqa: E402
from decision_log import DecisionLog, verify_chain  # noqa: E402
from page_basis import qualify_pdf_observation  # noqa: E402
from review_report import book_summary  # noqa: E402
from thresholds import load_thresholds  # noqa: E402

PIPELINE_VERSION = "0.3.1"


def _bucket(n: int) -> str:
    if n == 0:
        return "empty"
    if n <= 10:
        return "1-10"
    if n <= 50:
        return "11-50"
    return "51+"


def run_pipeline(books: list[dict], *, whitelist: set[str] | None,
                 rollback_present: bool = False,
                 thresholds: dict | None = None) -> dict:
    """全 book を評価し evidence 行を組み立てる (書き込みはしない)。

    thresholds=None なら config/thresholds.json (既定 edition v1) をロード。
    edition_classifier_version="v2" にすれば edition 判定が強化版へ切替わる。
    """
    t = thresholds if thresholds is not None else load_thresholds()
    inventory_rows: list[dict] = []
    histogram = Counter()
    accounting_rows: list[dict] = []
    guard_rows: list[dict] = []
    summaries: list[dict] = []
    conflicts_rows: list[dict] = []

    for b in books:
        isbn = b["isbn"]
        title = b.get("title", "")
        source_meta = b.get("source_meta", {})
        sources = b["sources"]

        s = book_summary(isbn, title, sources, source_meta, t)
        summaries.append({k: v for k, v in s.items() if k != "_conflicts_detail"})
        for c in s.get("_conflicts_detail", []):
            conflicts_rows.append({"isbn": isbn, **c})

        # 1) inventory + 2) histogram
        for src, nodes in sources.items():
            inventory_rows.append({"isbn": isbn, "title": title, "source": src,
                                   "node_count": len(nodes),
                                   "provenance_origin": source_meta.get(src, {}).get("provenance_origin", "")})
            histogram[(src, _bucket(len(nodes)))] += 1

        # 4) accounting reconciliation
        conc = build_concordance(sources)
        a = conc["accounting"]
        accounting_rows.append({"isbn": isbn, "total_nodes": a["total_nodes"],
                                "matched": a["matched"], "orphan": a["orphan"],
                                "accounted": a["accounted"],
                                "all_nodes_accounted_for": conc["all_nodes_accounted_for"]})

        # 5) apply_guard 評価 (物理拒否ログ)
        auth = resolve_authority(source_meta, edition_status=s["edition_identity_status"])
        uses_pdf = auth["authority"] == AUTH_PDF_PRIMARY
        pdf_meta = source_meta.get("pdf")
        pdf_qualified = bool(pdf_meta and qualify_pdf_observation(pdf_meta)["qualified"])
        req = {
            "isbn": isbn,
            "unresolved_conflict_count": s["conflicts"]["unresolved"],
            "edition_identity_status": s["edition_identity_status"],
            "uses_pdf_authority": uses_pdf,
            "pdf_observation_qualified": pdf_qualified,
            "rollback_bundle_present": rollback_present,
            "decision_log_append_only": True,
            "all_nodes_accounted_for": conc["all_nodes_accounted_for"],
        }
        g = evaluate_apply_gate(req, whitelist=whitelist)
        guard_rows.append({"isbn": isbn, "authority": auth["authority"],
                           "allowed": g["allowed"], "refusals": g["refusals"]})

    return {
        "pipeline_version": PIPELINE_VERSION,
        "concordance_version": CONCORDANCE_VERSION,
        "report_only": True, "final_toc_written": False, "toc_dir_written": False,
        "inventory": inventory_rows,
        "histogram": {f"{s}/{b}": c for (s, b), c in sorted(histogram.items())},
        "accounting": accounting_rows,
        "apply_guard": guard_rows,
        "summaries": summaries,
        "conflicts": conflicts_rows,
        "apply_allowed_isbns": [r["isbn"] for r in guard_rows if r["allowed"]],
        "risk_counts": dict(Counter(s["risk"] for s in summaries)),
    }


def write_evidence(result: dict, out_dir: Path) -> dict:
    ev = out_dir / "evidence"
    ev.mkdir(parents=True, exist_ok=True)

    def wcsv(name, rows):
        if not rows:
            (ev / name).write_text("", encoding="utf-8")
            return
        with (ev / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)

    wcsv("source_inventory.csv", result["inventory"])
    wcsv("accounting_reconciliation.csv", result["accounting"])
    (ev / "parser_histogram.csv").write_text(
        "key,count\n" + "".join(f"{k},{v}\n" for k, v in result["histogram"].items()),
        encoding="utf-8")
    (ev / "apply_guard_log.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in result["apply_guard"]),
        encoding="utf-8")
    (out_dir / "conflicts.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in result["conflicts"]),
        encoding="utf-8")

    # decision_log サンプル + chain 検証 (evidence の改竄耐性確認)。
    dlog = DecisionLog(ev / "decision_log.jsonl")
    for r in result["apply_guard"]:
        if not r["allowed"]:
            dlog.append(isbn=r["isbn"], conflict_id="gate", decision="hold",
                        decided_by="pipeline", basis="apply_guard refusals: " + ",".join(r["refusals"]))
    chain = verify_chain(ev / "decision_log.jsonl")

    readme = [
        "# Phase0 dry-run evidence (report-only / 本番未書込)",
        f"- pipeline v{result['pipeline_version']} / concordance v{result['concordance_version']}",
        f"- books: {len(result['accounting'])} / risk: {result['risk_counts']}",
        f"- apply 可 (全7 gate 通過) ISBN: {len(result['apply_allowed_isbns'])}",
        f"- decision_log chain: ok={chain['ok']} count={chain['count']}",
        "",
        "## GPT 指定 evidence 5点 対応",
        "1. source_inventory.csv  (source × node_count)",
        "2. parser_histogram.csv  (source × node数バケット)",
        "3. conflicts.jsonl       (既知 conflict; 入力 seed に対応)",
        "4. accounting_reconciliation.csv (all_nodes_accounted_for 照合)",
        "5. apply_guard_log.jsonl (未whitelist/未解決conflict 等を物理拒否したログ)",
        "+ decision_log.jsonl (append-only, chain hash 検証済)",
        "",
        "> toc_dir_written=false / final_toc_written=false。apply_guard は評価のみ。",
    ]
    (out_dir / "EVIDENCE_README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    return {"chain": chain}


def _demo_books():
    from concordance_report import _demo_books as base
    books = base()
    # provenance_origin を付与して consensus / pdf 経路も踏ませる
    books[0]["source_meta"]["legallib"]["provenance_origin"] = "legallib"
    books[0]["source_meta"]["bencom"]["provenance_origin"] = "bencom"
    return books


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="v0.3.1 統合 pipeline + Phase0 evidence (report-only)")
    ap.add_argument("--books")
    ap.add_argument("--only-isbns", help="承認 whitelist (1行1ISBN)")
    ap.add_argument("--rollback-present", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--edition-version", choices=["v1", "v2"], default=None,
                    help="edition classifier 上書き (既定は config の v1)")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args(argv)

    books = _demo_books() if args.demo else json.loads(Path(args.books).read_text(encoding="utf-8"))
    wl = None
    if args.only_isbns:
        wl = {ln.strip() for ln in Path(args.only_isbns).read_text(encoding="utf-8").splitlines() if ln.strip()}
    elif args.demo:
        wl = {"9784000000010"}  # demo: 低リスク本だけ承認
    override = {"edition_classifier_version": args.edition_version} if args.edition_version else None
    thresholds = load_thresholds(override=override)
    result = run_pipeline(books, whitelist=wl,
                          rollback_present=args.demo or args.rollback_present,
                          thresholds=thresholds)
    write_evidence(result, Path(args.out))
    print(json.dumps({"risk": result["risk_counts"],
                      "apply_allowed": len(result["apply_allowed_isbns"])},
                     ensure_ascii=False, sort_keys=True))
    print(f"evidence: {Path(args.out) / 'evidence'} (report-only, toc 未書込)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
