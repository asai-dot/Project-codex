#!/usr/bin/env python3
"""selftest: 小さな偽ダンプを作り r1→r2→r3 を通しで実行する。

ローカルちゃん: 本番16GBの前にこれを1回流して「緑」を確認する。
  python3 selftest.py
最後に "SELFTEST PASS" が出れば配管はOK。out_selftest/ は消してよい。
"""
import os, subprocess, sys, csv, tempfile, shutil, json

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    print("$", " ".join(cmd))
    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    print(r.stdout[-2000:]);  print(r.stderr[-1000:])
    if r.returncode != 0:
        print("!! failed:", cmd); sys.exit(1)


def main():
    dump = os.path.join(HERE, "_selftest_dump")
    out = os.path.join(HERE, "out_selftest")
    inp = os.path.join(HERE, "_selftest_input.tsv")
    shutil.rmtree(dump, ignore_errors=True); shutil.rmtree(out, ignore_errors=True)
    os.makedirs(dump)
    # 偽 NDL CSV（ヘッダ付き・CP932）
    rows = [
        ["書誌ID", "ISBN", "タイトル", "出版者", "出版年", "版"],
        ["111111111", "978-4-535-52384-5", "法律文書作成の基本", "日本評論社", "2019", "第2版"],
        ["222222222", "9784535523845", "法律文書作成の基本", "日本評論社", "2016", "初版"],  # 同ISBN別bibid=multi
        ["333333333", "4-535-00207-X", "旧ISBN10の本", "日本評論社", "2001", ""],            # ISBN10
        ["444444444", "", "ISBN無し本", "X社", "2020", ""],                                    # reject
    ]
    with open(os.path.join(dump, "ndl_all_records_001.csv"), "w", encoding="cp932", newline="") as f:
        csv.writer(f).writerows(rows)
    # 偽 cohort-A 入力
    with open(inp, "w", encoding="utf-8") as f:
        f.write("bib_id\tisbn13\tndl_bib_id_present\tpub_year\tedition\tpublisher\ttitle\n")
        f.write("alo:book:isbn:9784535523845\t9784535523845\t029854077\t2019\t第2版\t日本評論社\t法律文書作成の基本\n")  # present + hit(multi)
        f.write("alo:book:isbn:9784535002074\t9784535002074\t\t2016\t\t日本評論社\tコンメンタール\n")                  # gap421, no_hit(old)
        f.write("alo:book:isbn:9784999999999\t9784999999999\t\t2099\t\tX社\t未来の新刊\n")                            # gap421, freshness_miss

    run([sys.executable, "r1_probe.py", dump, "--out", out, "--full-hash"])
    run([sys.executable, "r2_build_index.py", dump, "--out", out, "--snapshot-id", "dump_2025"])
    run([sys.executable, "r3_coverage.py", "--input", inp, "--index", os.path.join(out, "ndl_isbn_index.tsv"), "--out", out])

    man = json.load(open(os.path.join(out, "R2_build_manifest.json"), encoding="utf-8"))
    assert man["rows_indexed"] == 3, man            # 2 same-isbn + 1 isbn10 = 3 indexed
    assert man["rejects"] == 1, man                 # ISBN無し1
    assert man["isbn_with_multi_bibid"] == 1, man   # 同ISBN別bibid
    rep = open(os.path.join(out, "R3_coverage_report.md"), encoding="utf-8").read()
    assert "freshness_miss（pub_year>=2025" in rep, "freshness 切り分け不成立"
    print("\nSELFTEST PASS")
    shutil.rmtree(dump, ignore_errors=True); os.remove(inp)


if __name__ == "__main__":
    main()
