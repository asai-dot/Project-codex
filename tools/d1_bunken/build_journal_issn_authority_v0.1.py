#!/usr/bin/env python3
"""D1文献編 931誌 → ISSN/NCID 権威マップ 自動ビルダ v0.1

目的:
  label_journals_v0.2.1.py が出した canonical 931誌(article_meta_labeled.jsonl)の
  **全誌**に、ISSN/NCID を自動付与する。手作業のWeb検索ではなく NDL書誌バルク
  (雑誌レイヤ仕様§2.2 / §5: ISSN+巻号突合の権威ソース, ~240万レコード) との
  誌名突合で全件処理する。

  検証済みの頭部46誌(artifacts/periodical/d1_journal_issn_authority_head_20260623.csv)を
  **override seed** として内蔵し、NDL自動突合より優先する。特に内部DB由来ISSNの誤りを
  是正済みの4誌(税経通信=他誌ISSN混入→NCID 等)はここで上書きして汚染を源流停止する。

入力:
  --labeled  : article_meta_labeled.jsonl（journal_canonical を持つ。Mac build/labeled_v0.2.1/）
  --ndl      : NDL書誌 (jsonl or tsv)。title と issn(必要なら ncid) を持つ行。ndl_download.py 出力。
  --seed     : 検証済み頭部 authority CSV（このリポジトリ同梱。journal_canonical,key_type,key_value,status,note）
  --out      : 出力 CSV（全931誌 + key + status + source + 候補）

出力 status:
  seed_verified / seed_correction / seed_ncid_fallback : 頭部seedの確定値（最優先）
  ndl_unique     : NDLで誌名→ISSNが一意に確定
  ndl_ambiguous  : NDLに複数ISSN候補（隣接誌/改題の疑い。要レビュー）
  unresolved     : NDLに該当なし（ISSN未付番 or 表記差。NCID/手当て候補へ）

注意（誌名突合の罠。コメントで固定）:
  - 旧字/新字: 警察學論集↔警察学論集, 法學協會雜誌↔法学協会雑誌 → NFKC+旧字マップで吸収。
  - 隣接誌の誤マージ厳禁: 戸籍≠戸籍時報, 登記研究≠月刊登記情報≠登記インターネット,
    銀行法務≠銀行法務21, 金融法務事情≠旬刊金融法務事情。exact一致のみ採用、部分一致は ambiguous。
  - 接尾ノイズ「雑誌記事メタデータ」等を除去（フォルダ名由来）。
"""
import argparse, csv, json, re, sys, unicodedata, collections

_SUFFIX_NOISE = ["雑誌記事メタデータ", "雑誌記事メタ"]
# 最小限の旧字→新字（誌名で実在するもののみ。過剰変換しない）
_KYUJI = str.maketrans({"學": "学", "會": "会", "雜": "雑", "藝": "芸", "區": "区",
                        "勞": "労", "經": "経", "證": "証", "廳": "庁", "讀": "読"})

def norm_title(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(_KYUJI)
    for suf in _SUFFIX_NOISE:
        s = s.replace(suf, "")
    s = re.split(r"[(（]", s, 1)[0]          # 括弧修飾(出版者・大学名)を落として誌名核に
    s = re.sub(r"\s+", "", s).strip(" 　・,，、。.")
    return s

def load_seed(path):
    """検証済み頭部 authority。journal_canonical -> dict。status を seed_* へ写像。"""
    seed = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            st = (r.get("status") or "").strip()
            if st in ("verified",):       mapped = "seed_verified"
            elif st == "correction":      mapped = "seed_correction"
            elif st == "ncid_fallback":   mapped = "seed_ncid_fallback"
            else:                          mapped = None    # pending 等は seed 採用しない
            if mapped and (r.get("key_value") or r.get("key_type") == "isbn_per_issue"):
                seed[norm_title(r["journal_canonical"])] = {
                    "key_type": r.get("key_type", ""), "key_value": r.get("key_value", ""),
                    "status": mapped, "source": "seed:" + (r.get("source") or "head_csv"),
                    "note": r.get("note", ""),
                }
    return seed

def load_ndl_index(path):
    """NDL書誌から 正規化誌名 -> set(ISSN)。jsonl(title,issn) か tsv(列名 title/issn) を許容。"""
    idx = collections.defaultdict(set)
    with open(path, encoding="utf-8") as f:
        head = f.readline()
        f.seek(0)
        if head.lstrip().startswith("{"):           # jsonl
            for line in f:
                line = line.strip()
                if not line: continue
                r = json.loads(line)
                t, issn = r.get("title"), r.get("issn")
                if t and issn:
                    idx[norm_title(t)].add(issn.strip())
        else:                                         # tsv
            rdr = csv.DictReader(f, delimiter="\t")
            for r in rdr:
                t = r.get("title") or r.get("誌名") or r.get("タイトル")
                issn = r.get("issn") or r.get("ISSN")
                if t and issn:
                    idx[norm_title(t)].add(issn.strip())
    return idx

def journal_counts(labeled_path):
    c = collections.Counter()
    with open(labeled_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            j = json.loads(line).get("journal_canonical")
            if j:
                c[j] += 1
    return c

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--ndl", default=None, help="NDL書誌バルク(jsonl/tsv)。無指定ならNDL突合をスキップ")
    ap.add_argument("--seed", default=None, help="検証済み頭部authority CSV。無指定ならseed override無し")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    counts = journal_counts(a.labeled)
    seed = load_seed(a.seed) if a.seed else {}
    ndl = load_ndl_index(a.ndl) if a.ndl else {}
    if not a.ndl:
        print("[info] --ndl 未指定: NDL突合スキップ。seed以外は unresolved として全誌を出力します。", file=sys.stderr)

    rows, agg = [], collections.Counter()
    for journal, n in counts.most_common():
        key = norm_title(journal)
        if key in seed:
            s = seed[key]
            rows.append([journal, n, s["key_type"], s["key_value"], s["status"], s["source"], s["note"]])
            agg[s["status"]] += 1
            continue
        issns = ndl.get(key, set())
        if len(issns) == 1:
            rows.append([journal, n, "issn", next(iter(issns)), "ndl_unique", "ndl_bulk", ""])
            agg["ndl_unique"] += 1
        elif len(issns) >= 2:
            rows.append([journal, n, "issn", "|".join(sorted(issns)), "ndl_ambiguous", "ndl_bulk",
                         "複数ISSN候補=改題/隣接誌の疑い・要レビュー"])
            agg["ndl_ambiguous"] += 1
        else:
            rows.append([journal, n, "", "", "unresolved", "", "NDL該当なし→NCID/ISBN/手当て候補"])
            agg["unresolved"] += 1

    with open(a.out, "w", encoding="utf-8", newline="") as w:
        cw = csv.writer(w)
        cw.writerow(["journal_canonical", "article_count", "key_type", "key_value", "status", "source", "note"])
        cw.writerows(rows)

    print(f"journals total : {len(rows)}")
    for k in ("seed_verified","seed_correction","seed_ncid_fallback","ndl_unique","ndl_ambiguous","unresolved"):
        print(f"  {k:18}: {agg.get(k,0)}")
    resolved = sum(agg.get(k,0) for k in ("seed_verified","seed_correction","seed_ncid_fallback","ndl_unique"))
    print(f"resolved(一意キー確定): {resolved}/{len(rows)} = {resolved/max(len(rows),1):.1%}")
    print(f"wrote: {a.out}")

if __name__ == "__main__":
    main()
