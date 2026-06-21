#!/usr/bin/env python3
"""case_symbol 2表の健全性チェック v0.2 (DD-CASEID-002 MF-2/MF-3)。

検証:
  C1 romanization.symbol_norm は一意 (identity候補)
  C2 romaji は多対一を許す(衝突は警告報告のみ・FAILにしない=display専用の体現)
  C3 semantics.status は confirmed / review のみ
  C4 同字異義 wa = 民事ワ + 刑事わ が romanization に併存
  C5 semantics の全 symbol が romanization に存在 (2表の参照健全)
  C6 status=review 行の source_basis は court_official ではない
     (公式典拠未確定を confirmed と偽らない。MF-2 閉鎖条件)
  C7 MF-2 訂正が反映 (行サ=上告提起/行フ=許可抗告/行ケ=行政訴訟第一審/行ス=抗告提起)

実行: python3 scripts/check_case_symbol_tables.py  (exit 0 = 健全)。
"""
import csv
import sys
import collections
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "app" / "data" / "case_identity"
ROM = D / "case_symbol_romanization.csv"
SEM = D / "case_symbol_semantics.csv"
VALID_STATUS = {"confirmed", "review"}

EXPECTED_MF2 = {
    "行サ": "gyosei_jokoku_teiki",
    "行フ": "gyosei_kyoka_kokoku",
    "行ケ": "gyosei_first_instance",
    "行ス": "gyosei_kokoku_teiki",
}


def main() -> int:
    rom = list(csv.DictReader(ROM.open(encoding="utf-8")))
    sem = list(csv.DictReader(SEM.open(encoding="utf-8")))
    issues, warns = [], []

    # C1
    rc = collections.Counter(r["symbol_norm"] for r in rom)
    if [s for s, n in rc.items() if n > 1]:
        issues.append(f"C1 duplicate symbol_norm: {[s for s,n in rc.items() if n>1]}")

    # C2 romaji 衝突 (報告のみ)
    rmap = collections.defaultdict(list)
    for r in rom:
        rmap[r["romaji"]].append(r["symbol_norm"])
    collisions = {k: v for k, v in rmap.items() if len(v) > 1}

    # C3
    bad = sorted({r["status"] for r in sem} - VALID_STATUS)
    if bad:
        issues.append(f"C3 invalid status: {bad}")

    # C4
    if not ({"ワ", "わ"} <= set(rmap.get("wa", []))):
        issues.append(f"C4 wa collision expected 民事ワ+刑事わ, got {rmap.get('wa')}")

    # C5 参照健全
    romset = {r["symbol_norm"] for r in rom}
    orphan = sorted({r["symbol_norm"] for r in sem} - romset)
    if orphan:
        issues.append(f"C5 semantics symbol not in romanization: {orphan}")

    # C6 review 行は court_official を名乗らない
    liar = [r["symbol_norm"] for r in sem
            if r["status"] == "review" and r["source_basis"] == "court_official"]
    if liar:
        issues.append(f"C6 review row claims court_official: {liar}")

    # C7 MF-2 訂正
    semmap = {r["symbol_norm"]: r["procedure_kind"] for r in sem}
    for sym, pk in EXPECTED_MF2.items():
        if semmap.get(sym) != pk:
            issues.append(f"C7 MF-2 correction missing: {sym} expected {pk}, got {semmap.get(sym)}")

    conf = sum(1 for r in sem if r["status"] == "confirmed")
    print(f"romanization={len(rom)} semantics={len(sem)} confirmed={conf} review={len(sem)-conf}")
    print(f"romaji collisions (display許容): {collisions}")
    if issues:
        print("RESULT: FAIL")
        for i in issues:
            print("  -", i)
        return 1
    print("RESULT: PASS (2表健全; MF-2訂正反映; romaji衝突は設計上許容)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
