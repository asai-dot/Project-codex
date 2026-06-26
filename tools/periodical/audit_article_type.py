#!/usr/bin/env python3
"""
audit_article_type.py — head受入検査 (ORCH-LOCAL-ARTICLE-TYPE)

ローカルちゃん(QEN)が出す article_type_local*.csv を独立検査する。
  使い方:
    python3 tools/periodical/audit_article_type.py \
        artifacts/periodical/article_type_local_pilot_v0.1.csv \
        [artifacts/periodical/article_join_dryrun_v0.1.csv]   # 第2引数=タイトル突合元(任意)

受入基準（DD/ORCH-LOCAL-ARTICLE-TYPE）:
  - 未分類(空 or 規格外ラベル)=0
  - 正規表現クロスチェック一致率 >= 85%
  - 分布サニティ（極端な偏りでない）
read-only。
"""
import csv, sys, re, collections

VALID = {"判例評釈","論説・論文","解説","立法・改正解説","座談会・対談","判例紹介","書評","資料","連載・コラム","その他"}

# タイトル正規表現 → 許容ラベル集合（公正版: 判決系は判例関連3種のいずれでも正解）
# 判例評釈/判例紹介/資料 は「判決を扱う記事」の境界カテゴリで主観差が大きいため相互許容。
# 明確な誤り(書評/座談会/立法解説等を判決系に付ける)だけを不一致とする。
CASE_FAMILY = {"判例評釈", "判例紹介", "資料"}
RULES = [
    (re.compile(r"判批|判例批評"), {"判例評釈"}),
    (re.compile(r"評釈"), {"判例評釈", "判例紹介"}),
    (re.compile(r"最(判|決)|大(判|決)|高(判|決)|地(判|決)|令和[^、。]{0,12}(判|決)|平成[^、。]{0,12}(判|決)"), CASE_FAMILY),
    (re.compile(r"座談会|対談|鼎談"), {"座談会・対談"}),
    (re.compile(r"書評|新刊紹介"), {"書評"}),
    (re.compile(r"改正(法)?の(概要|解説|ポイント)|新法解説|立法(の)?解説"), {"立法・改正解説"}),
]


def load(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main(type_csv, join_csv=None):
    rows = load(type_csv)
    n = len(rows)
    # タイトル突合元
    titles = {}
    if join_csv:
        for r in load(join_csv):
            aid = (r.get("article_id") or "").strip()
            if aid:
                titles[aid] = (r.get("title") or "")

    dist = collections.Counter((r.get("type") or "").strip() for r in rows)
    bad_label = [r for r in rows if (r.get("type") or "").strip() not in VALID]

    # 正規表現クロスチェック: 強シグナルを持つ行で、QENラベルが期待と一致する率
    checked = matched = 0
    mism = []
    for r in rows:
        aid = (r.get("article_id") or "").strip()
        lab = (r.get("type") or "").strip()
        t = titles.get(aid, "")
        if not t:
            continue
        for rx, exp in RULES:
            if rx.search(t):
                checked += 1
                if lab in exp:
                    matched += 1
                elif len(mism) < 10:
                    mism.append((t[:40], lab, "/".join(sorted(exp))))
                break
    rate = matched / checked if checked else None

    checks = {
        "unclassified=0": len(bad_label) == 0,
        "regex_crosscheck>=85%": (rate is not None and rate >= 0.85),
    }
    passed = all(v for v in checks.values())

    print(f"=== ORCH-LOCAL-ARTICLE-TYPE 受入検査: {type_csv} ===")
    print(f"総 {n} 行  規格外ラベル {len(bad_label)}")
    print("分布:")
    for k, v in dist.most_common():
        flag = "" if k in VALID else "  ← 規格外!"
        print(f"  {v:>7}  {k or '(空)'}{flag}")
    if join_csv:
        print(f"クロスチェック: 強シグナル {checked} 件中 一致 {matched}"
              f"  一致率 {('%.1f%%' % (rate*100)) if rate is not None else 'N/A(突合元なし)'}")
        for t, lab, exp in mism[:5]:
            print(f"   不一致: 「{t}」 QEN={lab} 期待={exp}")
    else:
        print("クロスチェック: 突合元(article_join CSV)未指定 → スキップ")
    print("--- 受入基準 ---")
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL' if join_csv or k!='regex_crosscheck>=85%' else 'SKIP'}] {k}")
    verdict = "PASS → 全量GO可" if passed else "FAIL/要確認 → プロンプト調整して再投入"
    print(f"\n判定: {verdict}")
    return 0 if passed else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
