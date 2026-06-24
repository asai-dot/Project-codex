#!/usr/bin/env python3
"""
audit_article_join.py — head受入検査 (ORCH-ARTICLE-JOIN)

Worker Claude Code が出す article_join_dryrun_*.csv を独立検査し、
DD-PERIODICAL-002_PROGRESS_REVIEW D3 の受入基準に対する PASS/FAIL を返す。

使い方:
  python3 tools/periodical/audit_article_join.py \
      artifacts/periodical/article_join_dryrun_v0.1.csv

read-only。入力CSVを読むだけ。DB/Box/ネット一切触らない。
受入基準:
  - article_collision = 0  (同一 article_id に異なる title)
  - 接合被覆 >= 95%        (joined / total)
  - 別冊ジュリスト(BN01263667/百選)衝突 = 0
  - orphan は理由分類済 (authority_unresolved は許容)
"""
import csv, json, sys, collections

TOTAL_EXPECTED = 302130           # D1文献編 総記事(参考)
COVERAGE_MIN = 0.95
HYAKUSEN_HINT = ("判例百選", "別冊ジュリスト", "BN01263667")


def load(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def audit(path):
    rows = load(path)
    n = len(rows)
    joined = [r for r in rows if (r.get("join_status") or "").strip() == "joined"]
    orphan = [r for r in rows if (r.get("join_status") or "").strip() == "orphan"]
    cov = len(joined) / n if n else 0.0

    # 1. article_id 衝突: 同一 article_id に異なる title
    by_aid = collections.defaultdict(set)
    for r in joined:
        aid = (r.get("article_id") or "").strip()
        if aid:
            by_aid[aid].add((r.get("title") or "").strip())
    collisions = {a: t for a, t in by_aid.items() if len(t) >= 2}

    # 2. issue_id 衝突: 同一 issue_id に異なる journal_canonical (誤接合の兆候)
    by_iid = collections.defaultdict(set)
    for r in joined:
        iid = (r.get("issue_id") or "").strip()
        if iid:
            by_iid[iid].add((r.get("journal_canonical") or "").strip())
    iid_mix = {i: j for i, j in by_iid.items() if len(j) >= 2}

    # 3. 別冊ジュリスト/百選 が同一 issue_id に複数百選で衝突していないか
    hyaku = [r for r in joined if any(h in (r.get("journal_canonical") or "")
             or h in (r.get("key_value") or "") for h in HYAKUSEN_HINT)]
    hyaku_iid = collections.defaultdict(set)
    for r in hyaku:
        hyaku_iid[(r.get("issue_id") or "").strip()].add(r.get("journal_canonical") or "")
    hyaku_collision = {i: j for i, j in hyaku_iid.items() if len(j) >= 2}
    hyaku_keytypes = collections.Counter((r.get("key_type") or "").strip() for r in hyaku)

    # 4. orphan 理由分類
    orphan_reason = collections.Counter((r.get("orphan_reason") or "").strip() for r in orphan)
    orphan_unclassified = [r for r in orphan if not (r.get("orphan_reason") or "").strip()]

    checks = {
        "article_collision=0": len(collisions) == 0,
        f"coverage>={COVERAGE_MIN:.0%}": cov >= COVERAGE_MIN,
        "bessatsu_jurist_collision=0": len(hyaku_collision) == 0,
        "orphan_all_classified": len(orphan_unclassified) == 0,
    }
    passed = all(checks.values())

    print(f"=== ORCH-ARTICLE-JOIN 受入検査: {path} ===")
    print(f"総記事 {n}  joined {len(joined)}  orphan {len(orphan)}  被覆 {cov:.2%}")
    print(f"article_id衝突 {len(collisions)}  issue_id混在 {len(iid_mix)}")
    print(f"百選記事 {len(hyaku)}  key_type内訳 {dict(hyaku_keytypes)}  百選issue_id衝突 {len(hyaku_collision)}")
    print(f"orphan理由 {dict(orphan_reason)}")
    print("--- 受入基準 ---")
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    if collisions:
        print("  衝突 article_id 例:")
        for a, t in list(collisions.items())[:5]:
            print(f"    {a}: {list(t)[:2]}")
    if hyaku_collision:
        print("  百選 issue_id 衝突例:")
        for i, j in list(hyaku_collision.items())[:5]:
            print(f"    {i}: {sorted(j)[:3]}")
    print(f"\n判定: {'PASS → L4接合認定可' if passed else 'FAIL → 主因返却・再実行'}")

    summary = {
        "path": path, "total": n, "joined": len(joined), "orphan": len(orphan),
        "coverage": round(cov, 4), "article_collision": len(collisions),
        "issue_id_mixed": len(iid_mix), "hyakusen_collision": len(hyaku_collision),
        "orphan_reason": dict(orphan_reason), "checks": checks, "pass": passed,
    }
    return summary, passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    summary, passed = audit(sys.argv[1])
    out = sys.argv[1].rsplit(".", 1)[0] + ".audit.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n監査結果 → {out}")
    sys.exit(0 if passed else 1)
