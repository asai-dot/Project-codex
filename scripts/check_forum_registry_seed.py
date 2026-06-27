#!/usr/bin/env python3
"""forum_registry_seed.csv 整合チェック (DD-CASEID-003 / DD-CASE-001 accept後)。

Mac CC で build_forum_registry_seed.py が出力した seed を、accept 済の不変則で検査する。
実 csv は Mac ローカル生成のため、ここでは `--selftest` で合成 fixture を用いて
checker 自体の妥当性を確認できる (実行 PASS=exit 0)。

検査不変則:
  K1 forum_code 非空・一意
  K2 forum_type は許可値域 (builder 実装の集合)
  K3 __REVIEW__ / unmapped を含む forum_code は canonical_ready=False (mint不可・人手確定要)
  K4 準司法23 (QUASI台帳) の source_system が全て forum seed に存在
  K5 parent_forum_code は実在 forum_code を指す (空は可)
  K6 jufu は forum_type=court で存在。出口隔離は source registry 側で can_global_index=false
     (DD-CASE-001 AC-3)。本 checker は source registry と突合できる場合に検証。

使い方:
  python3 check_forum_registry_seed.py PATH/forum_registry_seed.csv \
      [--source-registry PATH/alo_source_registry_seed.jsonl]
  python3 check_forum_registry_seed.py --selftest
"""
import csv
import sys
import json
import io
import collections
from pathlib import Path

VALID_FORUM_TYPES = {
    "court", "administrative_tribunal", "administrative_review",
    "agency", "adr", "arbitration", "other",
}
# DD-CASE-001 §2 の coarse forum_type への対応 (情報提供。値域検査は VALID_FORUM_TYPES)
FORUM_TYPE_TO_CASE_GROUP = {
    "court": "court", "administrative_tribunal": "tribunal",
    "administrative_review": "administrative", "agency": "advisory",
    "adr": "adr", "arbitration": "adr", "other": "other",
}
# build_forum_registry_seed.py QUASI 台帳の source_system (23)
EXPECTED_QUASI = {
    "kokuzei-fufuku-shinpan", "churoi", "jftc", "gyofuku-shinsakai", "roho-shinsakai",
    "shaho-shinsakai", "kochoi", "kainan-shinpan", "sesc", "finmac", "zenginkyo-adr",
    "nichibenren-adr", "jsaa", "jp-drp", "kokusen-hanrei", "kokusen-adr", "pmda-kyufu",
    "bpo", "retio", "denki-tsushin-funso", "soumu-johokokai-toshin", "zaiya-seihodb", "jufu",
}


def validate(rows, source_registry=None):
    issues = []
    codes = [r.get("forum_code", "") for r in rows]

    # K1 非空・一意
    if any(not c for c in codes):
        issues.append("K1 empty forum_code present")
    dups = [c for c, n in collections.Counter(codes).items() if n > 1 and c]
    if dups:
        issues.append(f"K1 duplicate forum_code: {dups}")

    # K2 forum_type 値域
    bad_ft = sorted({r.get("forum_type", "") for r in rows} - VALID_FORUM_TYPES)
    if bad_ft:
        issues.append(f"K2 invalid forum_type: {bad_ft}")

    # K3 __REVIEW__ / unmapped は canonical_ready=False であるべき
    review_codes = [c for c in codes if "__REVIEW__" in c]
    not_blocked = [c for c in review_codes
                   if str(next(r.get("canonical_ready", "") for r in rows if r.get("forum_code") == c)).lower()
                   in ("true", "1", "yes")]
    if not_blocked:
        issues.append(f"K3 __REVIEW__ code marked canonical_ready: {not_blocked}")

    # K4 準司法23 が全て存在
    present = set(codes)
    missing_quasi = sorted(EXPECTED_QUASI - present)
    if missing_quasi:
        issues.append(f"K4 missing quasi source_system: {missing_quasi}")

    # K5 parent 参照健全
    codeset = set(codes)
    bad_parent = sorted({r.get("parent_forum_code", "") for r in rows}
                        - codeset - {""})
    if bad_parent:
        issues.append(f"K5 parent_forum_code not found: {bad_parent}")

    # K6 jufu 存在 + 出口隔離 (source registry と突合できる場合)
    jufu = [r for r in rows if r.get("forum_code") == "jufu"]
    if not jufu:
        issues.append("K6 jufu forum_code missing")
    elif jufu[0].get("forum_type") != "court":
        issues.append(f"K6 jufu forum_type != court ({jufu[0].get('forum_type')})")
    if source_registry is not None:
        srj = [s for s in source_registry if s.get("source_system") == "jufu"]
        if srj and srj[0].get("can_global_index") is not False:
            issues.append("K6 jufu can_global_index must be false in source registry (AC-3)")
    return issues


def _selftest():
    good = [
        {"forum_code": "tokyo-chisai", "forum_type": "court", "parent_forum_code": ""},
        {"forum_code": "tokyo-chisai-tachikawa", "forum_type": "court", "parent_forum_code": "tokyo-chisai"},
    ] + [{"forum_code": q, "forum_type": "court" if q == "jufu" else "agency",
          "parent_forum_code": ""} for q in EXPECTED_QUASI]
    src = [{"source_system": "jufu", "can_global_index": False}]
    ok = validate(good, src)
    assert ok == [], f"selftest expected clean, got {ok}"

    bad = [
        {"forum_code": "tokyo-chisai", "forum_type": "court", "parent_forum_code": ""},
        {"forum_code": "tokyo-chisai", "forum_type": "spaceship", "parent_forum_code": "ghost"},
        {"forum_code": "__REVIEW__:foo", "forum_type": "court", "parent_forum_code": "", "canonical_ready": "true"},
    ]  # quasi欠落 + 重複 + 値域 + parent不在 + REVIEW canonical + jufu欠落
    bad_src = [{"source_system": "jufu", "can_global_index": True}]
    issues = validate(bad, bad_src)
    got = {i.split()[0] for i in issues}
    for k in ("K1", "K2", "K3", "K4", "K5", "K6"):
        assert k in got, f"selftest: expected {k} flagged, issues={issues}"
    print("selftest: PASS (clean fixture clean; broken fixture flags K1-K6)")
    return 0


def main(argv):
    if "--selftest" in argv:
        return _selftest()
    if len(argv) < 2:
        print(__doc__)
        return 2
    rows = list(csv.DictReader(Path(argv[1]).open(encoding="utf-8")))
    source_registry = None
    if "--source-registry" in argv:
        p = Path(argv[argv.index("--source-registry") + 1])
        source_registry = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    issues = validate(rows, source_registry)
    print(f"rows={len(rows)} distinct_forum_code={len({r.get('forum_code') for r in rows})}")
    if issues:
        print("RESULT: FAIL")
        for i in issues:
            print("  -", i)
        return 1
    print("RESULT: PASS (forum_registry_seed consistent with accepted invariants)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
