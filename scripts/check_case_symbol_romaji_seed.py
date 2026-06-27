#!/usr/bin/env python3
"""case_symbol_display_romaji_seed.csv の健全性チェック (DD-CASEID-002)。

検証する不変条件:
  C1 symbol は一意 (identity 候補なので重複不可)
  C2 romaji は多対一を許す = 衝突が存在しても FAIL にしない。ただし衝突を *明示報告*
     (display専用・identity非使用の体現。DD-CASEID-001 §2 / DD-CASEID-002 §1.2)
  C3 status は confirmed / review のみ
  C4 同字異義の代表例 (民事カナ「ワ」/ 刑事かな「わ」→ともに romaji=wa) が
     別 symbol として併存している (display衝突を許容している証拠)

実行: python3 scripts/check_case_symbol_romaji_seed.py
終了コード0=健全 (衝突は警告であって失敗ではない)。
"""
import csv
import sys
import collections
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent / "app" / "data" / "case_identity" / "case_symbol_display_romaji_seed.csv"
VALID_STATUS = {"confirmed", "review"}


def main() -> int:
    rows = list(csv.DictReader(SEED.open(encoding="utf-8")))
    failures = []

    # C1 symbol 一意
    sym_counts = collections.Counter(r["symbol"] for r in rows)
    dup_sym = [s for s, n in sym_counts.items() if n > 1]
    if dup_sym:
        failures.append(f"C1 duplicate symbol: {dup_sym}")

    # C3 status 値域
    bad_status = sorted({r["status"] for r in rows} - VALID_STATUS)
    if bad_status:
        failures.append(f"C3 invalid status: {bad_status}")

    # C2 romaji 衝突 (報告のみ・FAILにしない)
    romaji_map = collections.defaultdict(list)
    for r in rows:
        romaji_map[r["romaji"]].append(r["symbol"])
    collisions = {k: v for k, v in romaji_map.items() if len(v) > 1}

    # C4 同字異義 wa の併存
    wa = romaji_map.get("wa", [])
    if not ({"ワ", "わ"} <= set(wa)):
        failures.append(f"C4 expected both 民事ワ/刑事わ under romaji=wa, got {wa}")

    n_conf = sum(1 for r in rows if r["status"] == "confirmed")
    n_rev = sum(1 for r in rows if r["status"] == "review")
    print(f"rows={len(rows)} distinct_symbol={len(sym_counts)} confirmed={n_conf} review={n_rev}")
    print(f"romaji collisions (display専用ゆえ許容・要UI注意): {collisions if collisions else 'none'}")

    if failures:
        print("RESULT: FAIL")
        for f in failures:
            print("  -", f)
        return 1
    print("RESULT: PASS (seed well-formed; romaji collisions are allowed by design)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
