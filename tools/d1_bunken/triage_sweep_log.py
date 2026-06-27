#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D1文献編 全雑誌スイープのログ (~/d1_full_sweep.log) を読み、
`総件数=0` で返った誌を「本当に検討すべきもの」だけに絞り込むトリアージ。

スイープの 0件 行は性質が3種類に混ざる:
  ① 括弧別名で 0 だがベース名で取れている  → 無視可（実体は取得済み）
     例: 法と政治〔関西学院大学〕=0 の直後に 法と政治=578
  ② 取得済も 0 の真ゼロ                      → 要・表記当て直し / D1非収録判定（本命）
     例: 法学研究〔慶応義塾大学〕、商事法務研究
  ③ Timeout / 切替失敗 由来の 0              → フレーキー。再試行候補（非収録ではない）
     例: 法と政治〔関西学院大学〕 (Page.select_option Timeout)
  + データ安全: 総件数=0 だが取得済>0           → 再検索の揺れ。既存データは無事（消えていない）
     例: 法学=0 (取得済1165)、民事研修=0 (取得済42)

使い方:
  python3 tools/d1_bunken/triage_sweep_log.py ~/d1_full_sweep.log
  python3 tools/d1_bunken/triage_sweep_log.py ~/d1_full_sweep.log --tsv /tmp/d1_triage.tsv

出力: 標準出力にサマリ + バケツ別一覧。--tsv 指定で機械可読TSVも書く。
追加のみ・read-only（ログを読むだけ。元データには触れない）。
"""
import sys
import re
import argparse
import unicodedata

# 掲載誌=<名> 総件数=<N> 50件/頁 → <P>ページ処理 (取得済 <A>)
RE_RESULT = re.compile(
    r"掲載誌=(?P<name>.+?)\s+総件数=(?P<total>\d+)\s+.*?(?:→\s*(?P<pages>\d+)ページ)?.*?\(取得済\s*(?P<acq>\d+)\)"
)
RE_HEAD = re.compile(r"^###\s")
RE_ERR = re.compile(r"(失敗|Timeout|timeout|Error|エラー|例外|Traceback)")

# 角括弧・丸括弧・墨付き括弧などでベース名を切り出す
RE_BRACKET = re.compile(r"[〔「『（(【\[].*$")


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "")


def base_name(s: str) -> str:
    """〔大学名〕など括弧以降を落としたベース名（前後空白除去）。"""
    return RE_BRACKET.split(nfkc(s), 1)[0].strip()


def parse(path):
    """ログを誌ブロック単位で読み、結果レコードの配列を返す。

    各ブロックは `### …` 見出しで始まり、途中に Timeout 等のエラー行を含みうる。
    1ブロック内に複数の `掲載誌=…` 行が出ることがある（別名=0 → ベース名=N の再試行）。
    """
    records = []
    block_has_err = False
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if RE_HEAD.match(line):
                block_has_err = False
                continue
            if RE_ERR.search(line):
                block_has_err = True
            m = RE_RESULT.search(line)
            if m:
                records.append({
                    "name": m.group("name").strip(),
                    "total": int(m.group("total")),
                    "pages": int(m.group("pages") or 0),
                    "acq": int(m.group("acq")),
                    "had_error": block_has_err,
                })
    return records


def triage(records):
    # ベース名で 総件数>0 で取れている集合（①判定に使う）
    base_have = set()
    for r in records:
        if r["total"] > 0:
            base_have.add(base_name(r["name"]))
    base_have.discard("")

    buckets = {"ok": [], "covered_by_base": [], "data_safe": [], "flaky": [], "true_zero": []}
    for r in records:
        if r["total"] > 0:
            buckets["ok"].append(r)
            continue
        # ここから 総件数=0
        if r["had_error"]:
            buckets["flaky"].append(r)
        elif base_name(r["name"]) in base_have:
            buckets["covered_by_base"].append(r)
        elif r["acq"] > 0:
            buckets["data_safe"].append(r)
        else:
            buckets["true_zero"].append(r)
    return buckets


def main():
    ap = argparse.ArgumentParser(description="D1 sweep log triage")
    ap.add_argument("logfile", help="~/d1_full_sweep.log")
    ap.add_argument("--tsv", help="機械可読TSVの出力先（任意）")
    args = ap.parse_args()

    records = parse(args.logfile)
    b = triage(records)

    n_journals = len(records)
    print(f"=== D1 sweep triage: {args.logfile} ===")
    print(f"結果行(誌・別名込み): {n_journals}")
    print(f"  取得OK (総件数>0)            : {len(b['ok'])}")
    print(f"  ① 括弧別名→ベースで取得済    : {len(b['covered_by_base'])}  （無視可）")
    print(f"  + データ安全 (0だが取得済>0) : {len(b['data_safe'])}  （既存データ無事）")
    print(f"  ③ Timeout/失敗 由来の0       : {len(b['flaky'])}  （再試行候補）")
    print(f"  ② 真ゼロ＝要・表記当て直し    : {len(b['true_zero'])}  ★本命")
    print()

    if b["flaky"]:
        print("--- ③ 再試行候補（Timeout/切替失敗で0。非収録ではない）---")
        for r in b["flaky"]:
            print(f"  {r['name']}")
        print()

    if b["true_zero"]:
        print("--- ② 真ゼロ（D1非収録 or 表記差。要・別表記トライ）★本命 ---")
        for r in b["true_zero"]:
            print(f"  {r['name']}")
        print()

    if b["data_safe"]:
        print("--- データ安全（再検索0だが取得済あり。確認のみ）---")
        for r in b["data_safe"]:
            print(f"  {r['name']}  (取得済 {r['acq']})")
        print()

    if args.tsv:
        with open(args.tsv, "w", encoding="utf-8") as out:
            out.write("bucket\tname\ttotal\tpages\tacquired\thad_error\n")
            for bucket, rows in b.items():
                for r in rows:
                    out.write(f"{bucket}\t{r['name']}\t{r['total']}\t{r['pages']}\t{r['acq']}\t{int(r['had_error'])}\n")
        print(f"TSV → {args.tsv}")


if __name__ == "__main__":
    main()
