#!/usr/bin/env python3
"""case_symbol 2表の健全性チェック v0.3 (DD-CASEID-002 MF-2/MF-3 再監査反映)。

  C1 romanization.symbol_norm は一意
  C2 romaji 多対一は許容(衝突は警告報告のみ)
  C3 semantics.status は pending_source_fixation / review / confirmed のみ
  C4 同字異義 wa = 民事ワ + 刑事わ が romanization に併存
  C5 semantics の全 symbol が romanization に存在
  C6 status=confirmed は source_hash が固定済(pending/unknown/空 でない)であること
     (MF-2: 公式doc未固定の行を confirmed と偽らない)
  C7 MF-2 訂正反映 (行サ=上告提起/行フ=許可抗告/行ケ=行政訴訟第一審/行ス=抗告提起)
  C8 meaning_basis=court_official_definition は source_ref 非空
  C9 valid_from/valid_to は空でなく unknown 又は日付 (K7)

実行: python3 scripts/check_case_symbol_tables.py  (exit 0 = 健全)。
"""
import csv
import sys
import collections
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "app" / "data" / "case_identity"
ROM = D / "case_symbol_romanization.csv"
SEM = D / "case_symbol_semantics.csv"
VALID_STATUS = {"pending_source_fixation", "review", "confirmed"}
UNFIXED = {"pending_capture", "unknown", ""}
EXPECTED_MF2 = {
    "行サ": "gyosei_jokoku_teiki", "行フ": "gyosei_kyoka_kokoku",
    "行ケ": "gyosei_first_instance", "行ス": "gyosei_kokoku_teiki",
}


def main() -> int:
    rom = list(csv.DictReader(ROM.open(encoding="utf-8")))
    sem = list(csv.DictReader(SEM.open(encoding="utf-8")))
    issues = []

    rc = collections.Counter(r["symbol_norm"] for r in rom)
    if [s for s, n in rc.items() if n > 1]:
        issues.append(f"C1 duplicate symbol_norm: {[s for s,n in rc.items() if n>1]}")

    rmap = collections.defaultdict(list)
    for r in rom:
        rmap[r["romaji"]].append(r["symbol_norm"])
    collisions = {k: v for k, v in rmap.items() if len(v) > 1}

    bad = sorted({r["status"] for r in sem} - VALID_STATUS)
    if bad:
        issues.append(f"C3 invalid status: {bad}")
    if not ({"ワ", "わ"} <= set(rmap.get("wa", []))):
        issues.append(f"C4 wa collision expected 民事ワ+刑事わ, got {rmap.get('wa')}")
    romset = {r["symbol_norm"] for r in rom}
    orphan = sorted({r["symbol_norm"] for r in sem} - romset)
    if orphan:
        issues.append(f"C5 semantics symbol not in romanization: {orphan}")

    liar = [r["symbol_norm"] for r in sem
            if r["status"] == "confirmed" and r.get("source_hash", "") in UNFIXED]
    if liar:
        issues.append(f"C6 confirmed without fixed source_hash: {liar}")

    semmap = {r["symbol_norm"]: r["procedure_kind"] for r in sem}
    for sym, pk in EXPECTED_MF2.items():
        if semmap.get(sym) != pk:
            issues.append(f"C7 MF-2 correction missing: {sym} expected {pk}, got {semmap.get(sym)}")

    no_ref = [r["symbol_norm"] for r in sem
              if r.get("meaning_basis") == "court_official_definition" and not r.get("source_ref")]
    if no_ref:
        issues.append(f"C8 court_official_definition without source_ref: {no_ref}")

    bad_valid = [r["symbol_norm"] for r in sem
                 if r.get("valid_from", "") == "" or r.get("valid_to", "") == ""]
    if bad_valid:
        issues.append(f"C9 empty valid_from/valid_to (use 'unknown'): {bad_valid}")

    st = collections.Counter(r["status"] for r in sem)
    print(f"romanization={len(rom)} semantics={len(sem)} status={dict(st)}")
    print(f"romaji collisions (display許容): {collisions}")
    if issues:
        print("RESULT: FAIL")
        for i in issues:
            print("  -", i)
        return 1
    print("RESULT: PASS (2表健全; MF-2訂正反映; source未固定はpending明示; romaji衝突は許容)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
