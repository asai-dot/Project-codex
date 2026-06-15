"""resolver_resend_candidates — resolver bucket の human_review 差し戻し候補を抽出 (report-only)。

Phase 0 所見3/4 の確定:
  * auto_accept 偽陽性 12 件: bucket=auto_accept だが is_real_suspect (版衝突/版非対称/核相違/
    年差≧2) = 実質要レビュー → human_review へ差し戻し (apply 時 edition gate が物理拒否すべき対象)。
  * defer_new 取りこぼし 58 件: bucket=defer_new (canonical 不在として create 予定) だが
    その isbn が canonical に**存在** = resolver の recall 取りこぼし → human_review へ差し戻し。

入力は Phase 0 の **certified 成果物** (edition_identity_sample.jsonl, sha256 固定) を一次ソースにする。
原本 resolver_decisions は**上書きしない**。差し戻し適用版は別ファイル (derived) として書く。
stdlib のみ・決定的・--out 配下のみ書込。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase0_inventory import is_real_suspect, norm_isbn  # noqa: E402

AA_REASON = "auto_accept_false_positive"          # 所見3
DN_REASON = "defer_new_recall_isbn_in_canonical"  # 所見4
RESEND_TO = "human_review"


def load_jsonl(p: Path) -> list[dict]:
    # NOTE: str.splitlines() は   等の Unicode 行区切りでも割れ、日本語タイトル内の
    # 当該文字で JSON レコードを途中分断する。file 反復 (\n のみ) を使う。
    with p.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def build_candidates(ident_rows: list[dict]) -> list[dict]:
    cands: list[dict] = []
    for r in ident_rows:
        bucket = r.get("resolver_bucket")
        if bucket == "auto_accept" and is_real_suspect(r):
            reason = AA_REASON
        elif bucket == "defer_new":
            reason = DN_REASON
        else:
            continue
        cands.append({
            "legallib_book_id": str(r.get("legallib_book_id")),
            "isbn": norm_isbn(r.get("isbn")),
            "from_bucket": bucket,
            "to_bucket": RESEND_TO,
            "resend_reason": reason,
            "edition_status": r.get("status"),
            "edition_reason": r.get("reason"),
            "title_diff_kind": r.get("title_diff_kind"),
            "year_gap": r.get("year_gap"),
            "legallib_edition_sig": r.get("legallib_edition_sig"),
            "canonical_edition_sig": r.get("canonical_edition_sig"),
            "resolver_confidence": r.get("resolver_confidence"),
            "legallib_title": (r.get("legallib") or {}).get("title"),
            "canonical_title": (r.get("canonical") or {}).get("title"),
        })
    # 決定的順序: 理由 → book_id。
    cands.sort(key=lambda c: (c["resend_reason"], c["legallib_book_id"]))
    return cands


def write_outputs(out: Path, cands: list[dict], resolver_path: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    cols = ["legallib_book_id", "isbn", "from_bucket", "to_bucket", "resend_reason",
            "edition_status", "edition_reason", "title_diff_kind", "year_gap",
            "legallib_edition_sig", "canonical_edition_sig", "resolver_confidence",
            "legallib_title", "canonical_title"]
    with (out / "resolver_resend_candidates.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(cands)
    (out / "resolver_resend_candidates.jsonl").write_text(
        "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cands), encoding="utf-8")

    # derived: 原本を読み、候補のみ bucket を human_review へ (原本は上書きしない)。
    by_bid = {c["legallib_book_id"]: c for c in cands}
    applied = []
    matched = 0
    for r in load_jsonl(resolver_path):
        rr = dict(r)
        bid = str(r.get("legallib_book_id"))
        c = by_bid.get(bid)
        # isbn 整合を guard にして取り違えを防ぐ。
        if c and norm_isbn(r.get("isbn")) == c["isbn"]:
            rr["original_bucket"] = r.get("bucket")
            rr["bucket"] = RESEND_TO
            rr["resend_reason"] = c["resend_reason"]
            matched += 1
        applied.append(rr)
    (out / "resolver_decisions.resend_applied.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in applied), encoding="utf-8")

    from collections import Counter
    by_reason = dict(Counter(c["resend_reason"] for c in cands))
    return {"candidates": len(cands), "by_reason": by_reason,
            "rebucketed_in_derived": matched, "resolver_records": len(applied)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="resolver human_review 差し戻し候補抽出 (report-only)")
    ap.add_argument("--edition-sample", required=True, help="Phase0 edition_identity_sample.jsonl")
    ap.add_argument("--resolver", required=True, help="resolver_decisions.normalized.jsonl (原本・読むだけ)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    ident_rows = load_jsonl(Path(args.edition_sample))
    cands = build_candidates(ident_rows)
    stats = write_outputs(Path(args.out), cands, Path(args.resolver))
    # 整合性 guard: derived の再バケット数 = 候補数 であること。
    stats["consistent"] = stats["rebucketed_in_derived"] == stats["candidates"]
    print(json.dumps({"out": args.out, **stats}, ensure_ascii=False, sort_keys=True))
    if not stats["consistent"]:
        print("WARN: derived 再バケット数 != 候補数 (book_id/isbn 取り違えの疑い)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
