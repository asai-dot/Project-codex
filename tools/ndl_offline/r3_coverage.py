#!/usr/bin/env python3
"""R3: cohort-A の ISBN を R2 索引に当て、被覆と候補を出す（read-only / candidate のみ）。

入力: input/cohortA_isbn.tsv（このリポジトリに同梱・DB由来 read-only）
      out/ndl_isbn_index.tsv（r2 の出力）
出力:
  out/cohortA_isbn_candidates.tsv : 1行=1書。link_status と lineage 付き（全て write_authorization=false）
  out/R3_coverage_report.md       : 被覆率・421解決見込み・freshness 切り分け

重要(監査拘束):
  - dump hit は candidate であって confirmed ではない（版正誤は別途 adjudication）
  - 既存 ndl_bib_id(present) は verified ではない。索引一致は candidate_single 等で表すのみ
  - pub_year >= snapshot_year の no_hit は freshness_miss に分離（matching failure に混ぜない）
"""
import os, csv, json, argparse, datetime
from collections import defaultdict


def load_index(path):
    idx = defaultdict(list)
    with open(path, encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter="\t")
        for row in r:
            idx[row["isbn13"]].append(row)
    return idx


def snapshot_year(out):
    try:
        m = json.load(open(os.path.join(out, "R2_build_manifest.json"), encoding="utf-8"))
        sid = m.get("snapshot_id", "")
        for tok in sid.replace("_", "-").split("-"):
            if tok.isdigit() and len(tok) == 4:
                return int(tok)
    except Exception:
        pass
    return datetime.date.today().year


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="input/cohortA_isbn.tsv")
    ap.add_argument("--index", default="out/ndl_isbn_index.tsv")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    idx = load_index(a.index)
    snap_y = snapshot_year(a.out)

    tot = hit = miss = fresh = present = present_hit = gap421 = gap421_resolved = 0
    multi = 0
    out_rows = []
    with open(a.input, encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter="\t")
        for row in r:
            tot += 1
            isbn = row["isbn13"].strip()
            has_present = bool(row.get("ndl_bib_id_present", "").strip())
            yr = row.get("pub_year", "").strip()
            yr_i = int(yr) if yr.isdigit() else None
            cands = idx.get(isbn, [])
            if has_present:
                present += 1
            else:
                gap421 += 1
            if cands:
                hit += 1
                if has_present:
                    present_hit += 1
                else:
                    gap421_resolved += 1
                if len(cands) > 1:
                    multi += 1
                    status = "multi_bibid"
                else:
                    status = "candidate_single_bibid"
                bibids = "|".join(sorted({c["ndl_bib_id"] for c in cands}))
                lineage = cands[0]
            else:
                if yr_i is not None and yr_i >= snap_y:
                    fresh += 1; status = "freshness_miss"
                else:
                    miss += 1; status = "no_hit_after_valid_isbn"
                bibids = ""; lineage = {}
            out_rows.append({
                "bib_id": row["bib_id"], "isbn13": isbn, "route_cohort": "cohort-A_self_scan",
                "ndl_bib_id_present": row.get("ndl_bib_id_present", ""),
                "ndl_bib_id_candidates": bibids,
                "link_status": status, "ndl_bib_id_verified": "",
                "pub_year": yr,
                "src_file": lineage.get("source_file", ""), "src_row": lineage.get("source_row", ""),
                "snapshot_id": lineage.get("snapshot_id", ""), "build_id": lineage.get("build_id", ""),
                "write_authorization": "false",
            })

    cand_path = os.path.join(a.out, "cohortA_isbn_candidates.tsv")
    with open(cand_path, "w", encoding="utf-8") as f:
        cols = list(out_rows[0].keys())
        f.write("\t".join(cols) + "\n")
        for r0 in out_rows:
            f.write("\t".join(str(r0[c]) for c in cols) + "\n")

    pct = lambda x: f"{100.0*x/tot:.1f}%" if tot else "n/a"
    with open(os.path.join(a.out, "R3_coverage_report.md"), "w", encoding="utf-8") as f:
        f.write("# R3 coverage report (cohort-A self_scan, read-only)\n\n")
        f.write(f"- generated_at: {datetime.datetime.now().isoformat()}\n- dump snapshot year (推定): {snap_y}\n")
        f.write(f"- cohort-A ISBN 総数: {tot}\n\n")
        f.write("## 被覆\n")
        f.write(f"- 索引ヒット: {hit}（{pct(hit)}） / うち multi_bibid: {multi}\n")
        f.write(f"- no_hit_after_valid_isbn（真の欠落候補）: {miss}\n")
        f.write(f"- freshness_miss（pub_year>={snap_y} の新刊・別扱い）: {fresh}\n\n")
        f.write("## 既存値との関係（present≠verified）\n")
        f.write(f"- ndl_bib_id_present あり: {present} / うち索引一致: {present_hit}\n")
        f.write(f"- ISBN有NDL無(=穴421相当): {gap421} / うち索引で新規解決見込み(candidate): {gap421_resolved}\n\n")
        f.write("注: 索引一致は candidate。版の正誤は adjudication(Q1) と独立2証拠で別途確定。confirmed/verified ではない。\n")
    print(f"OK: hit={hit}/{tot} ({pct(hit)}), multi={multi}, no_hit={miss}, freshness_miss={fresh}, gap421_resolvable={gap421_resolved}")
    print(f"→ out/cohortA_isbn_candidates.tsv, out/R3_coverage_report.md を監査/owner へ戻す")


if __name__ == "__main__":
    main()
