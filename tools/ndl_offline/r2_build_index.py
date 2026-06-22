#!/usr/bin/env python3
"""R2: NDL ダンプ全件をストリームし ISBN13 -> (bibid, edition, ...) の derived 索引を作る。

CONDITIONAL GO（v0.3 §4）の制約を満たす:
  - source file を変更しない（read-only でしか開かない）
  - 出力は再生成可能な isolated artifact（out/ 配下）のみ。DB/canonical へ書かない
  - build manifest と reject report を必ず出す
  - 各 hit に lineage（source_file / row / snapshot / parser_version / build_id）を保持

ローカルちゃん: `python3 r2_build_index.py <DUMP_DIR>` で実行。先に r1_probe.py を回し
out/R1_schema_map.json を目視確認しておくこと（列マッピングをここで再利用する）。
"""
import sys, os, json, csv, glob, argparse, datetime, uuid, hashlib
from isbn_util import normalize_to_isbn13

PARSER_VERSION = "r2_build_index/0.1"


def load_schema(out):
    p = os.path.join(out, "R1_schema_map.json")
    if not os.path.exists(p):
        print("!! out/R1_schema_map.json が無い。先に r1_probe.py を実行してください。"); sys.exit(2)
    return json.load(open(p, encoding="utf-8"))["csv_schema"]


def roles_for(schema, basename, default):
    s = schema.get(basename) or default
    return s["encoding"], s["delimiter"], s["column_roles"], s["has_header"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump_dir")
    ap.add_argument("--out", default="out")
    ap.add_argument("--snapshot-id", default=None, help="ダンプ snapshot 識別子（未指定なら日付）")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    schema = load_schema(a.out)
    default_schema = next(iter(schema.values()))  # 先頭分割のスキーマを全体に流用
    snapshot_id = a.snapshot_id or ("dump_" + datetime.date.today().isoformat())
    build_id = uuid.uuid4().hex[:12]

    csvs = sorted(glob.glob(os.path.join(a.dump_dir, "ndl_all_records_*.csv")))
    if not csvs:
        print("!! csv が見つかりません:", a.dump_dir); sys.exit(2)

    idx_path = os.path.join(a.out, "ndl_isbn_index.tsv")
    rej_path = os.path.join(a.out, "R2_rejects.tsv")
    n_in = n_out = n_rej = n_dup = 0
    seen = {}  # isbn13 -> set(bibid)  （同一ISBNに複数bibid＝multiを検出）

    with open(idx_path, "w", encoding="utf-8") as fo, open(rej_path, "w", encoding="utf-8") as fr:
        fo.write("isbn13\tndl_bib_id\tedition\tpub_year\tpublisher\ttitle\tsource_file\tsource_row\tsnapshot_id\tparser_version\tbuild_id\n")
        fr.write("source_file\tsource_row\treason\traw_isbn\traw_bibid\n")
        for p in csvs:
            base = os.path.basename(p)
            enc, delim, roles, has_hdr = roles_for(schema, base, default_schema)
            ci, cb = roles.get("isbn"), roles.get("ndl_bib_id")
            ce, cy = roles.get("edition"), roles.get("pub_year")
            cp, ct = roles.get("publisher"), roles.get("title")
            with open(p, encoding=enc, errors="replace", newline="") as fi:
                rdr = csv.reader(fi, delimiter=delim)
                for rownum, row in enumerate(rdr):
                    if has_hdr and rownum == 0:
                        continue
                    n_in += 1
                    def g(i):
                        return (row[i].strip() if (i is not None and i < len(row)) else "")
                    raw_isbn, raw_bibid = g(ci), g(cb)
                    norm = normalize_to_isbn13(raw_isbn) if raw_isbn else None
                    if not norm:
                        n_rej += 1; fr.write(f"{base}\t{rownum}\tno_or_bad_isbn\t{raw_isbn}\t{raw_bibid}\n"); continue
                    isbn13, _valid = norm
                    if not raw_bibid:
                        n_rej += 1; fr.write(f"{base}\t{rownum}\tno_bibid\t{raw_isbn}\t{raw_bibid}\n"); continue
                    s = seen.setdefault(isbn13, set())
                    if raw_bibid in s:
                        n_dup += 1; continue
                    s.add(raw_bibid)
                    def cell(i):
                        return g(i).replace("\t", " ").replace("\n", " ")
                    fo.write("\t".join([isbn13, raw_bibid, cell(ce), cell(cy), cell(cp), cell(ct),
                                        base, str(rownum), snapshot_id, PARSER_VERSION, build_id]) + "\n")
                    n_out += 1
            print(f"  scanned {base}: in={n_in} out={n_out} rej={n_rej} dup={n_dup}", flush=True)

    multi = sum(1 for v in seen.values() if len(v) > 1)
    manifest = {"build_id": build_id, "snapshot_id": snapshot_id, "parser_version": PARSER_VERSION,
                "generated_at": datetime.datetime.now().isoformat(), "dump_dir": a.dump_dir,
                "files": [os.path.basename(p) for p in csvs],
                "rows_in": n_in, "rows_indexed": n_out, "rejects": n_rej, "dup_skipped": n_dup,
                "distinct_isbn13": len(seen), "isbn_with_multi_bibid": multi,
                "outputs": {"index": idx_path, "rejects": rej_path},
                "constraints": {"source_mutated": False, "wrote_to_db_or_canonical": False,
                                "isolated_rebuildable_artifact": True, "external_egress": "prohibited"}}
    json.dump(manifest, open(os.path.join(a.out, "R2_build_manifest.json"), "w"), ensure_ascii=False, indent=2)
    print("OK:", json.dumps({k: manifest[k] for k in ("rows_in", "rows_indexed", "rejects", "dup_skipped", "distinct_isbn13", "isbn_with_multi_bibid")}, ensure_ascii=False))
    print("→ 次: r3_coverage.py")


if __name__ == "__main__":
    main()
