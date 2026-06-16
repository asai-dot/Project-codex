"""emit_tocadopt_evidence — DD-TOCADOPT-001-IMPL-REAUDIT の機械検証エビデンス生成器。

再監査の PASS 条件が要求する成果物を、合成 golden corpus から決定的に書き出す:
  - baseline_export_sample.json    : export_baseline() 出力サンプル (book-envelope + accepted node 集合)
  - baseline_equivalence_report.json: gate1 (source 入力順を反転した candidate との同値) 結果
  - lane_envelope_summary.json     : 全12冊の 4-lane 分布 + envelope apply 可否

report-only・合成データのみ・stdlib のみ・決定的 (実依頼者データなし)。
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from toc_adopt import adopt_book, adopt_corpus, export_baseline, load_policy  # noqa: E402
from toc_adopt_gates import gate1_reproduces_projection  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "golden" / "tocadopt" / "synthetic_multisource.jsonl"
OUTDIR = ROOT / "docs" / "dd" / "evidence" / "tocadopt_reaudit"


def _books() -> list[dict]:
    return [json.loads(ln)["book"] for ln in FIXTURE.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main() -> int:
    p = load_policy()
    books = _books()
    corpus = adopt_corpus(books, p)
    adoptions = corpus["rows"]
    OUTDIR.mkdir(parents=True, exist_ok=True)

    # 1) baseline export sample (adoptable な consensus3 を含む代表3冊)。
    pick = {"consensus3", "missing_source_hash", "partinfo_volume_structure"}
    sample = export_baseline([a for a in adoptions if any(
        s["scenario"] in pick and s["book"]["isbn"] == a["isbn"]
        for s in (json.loads(ln) for ln in FIXTURE.read_text(encoding="utf-8").splitlines() if ln.strip()))])
    (OUTDIR / "baseline_export_sample.json").write_text(
        json.dumps(sample, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    # 2) baseline equivalence report: source 入力順を反転した candidate と gate1 同値検査。
    baseline = export_baseline(adoptions)
    cand_rows = []
    for b in books:
        rev = copy.deepcopy(b)
        rev["sources"] = dict(reversed(list(rev["sources"].items())))
        rev["source_meta"] = dict(reversed(list(rev["source_meta"].items())))
        cand_rows.append(adopt_book(rev, p))
    candidate = export_baseline(cand_rows)
    g1 = gate1_reproduces_projection(baseline, candidate)
    (OUTDIR / "baseline_equivalence_report.json").write_text(
        json.dumps({"gate1": g1, "books_compared": len(baseline),
                    "method": "source 入力順を反転した candidate を export_baseline 同値比較 "
                              "(node集合・親子・ページ・base分布・projection_sha)"},
                   ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    # 3) lane + envelope summary (全冊)。
    summary = []
    for a in adoptions:
        env = a["envelope"]
        summary.append({
            "isbn": a["isbn"], "title": a["title"], "base_source": a["base_source"],
            "lanes": {"accepted": a["projection_node_count"],
                      "pending_human_review": a["pending_node_count"],
                      "rejected": a["rejected_node_count"],
                      "non_adoptable": a["non_adoptable_node_count"]},
            "envelope": {"edition_identity": env["edition_identity"],
                         "apply_unit": env["apply_unit"], "apply_target": env["apply_target"],
                         "adoptable": env["apply_eligibility"]["adoptable"],
                         "conditions": env["apply_eligibility"]["conditions"],
                         "blockers": env["apply_eligibility"]["blockers"]},
        })
    (OUTDIR / "lane_envelope_summary.json").write_text(
        json.dumps({"policy_version": corpus["policy_version"], "adopt_version": corpus["adopt_version"],
                    "books": corpus["books"], "adoptable_count": corpus["adoptable_count"],
                    "rows": summary}, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    print(f"emitted to {OUTDIR.relative_to(ROOT)}/")
    print(f"  baseline_export_sample.json   ({len(sample)} books)")
    print(f"  baseline_equivalence_report.json  gate1.pass={g1['pass']}")
    print(f"  lane_envelope_summary.json    ({len(summary)} books, adoptable={corpus['adoptable_count']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
