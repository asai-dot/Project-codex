#!/usr/bin/env python3
"""
build_authority_v15.py — ORCH-L4-COVERAGE-LIFT authority 増分 (v14 -> v15)

v14 を読み、orphan被覆引き上げのための「追記・status是正」だけを適用して v15 を書く。
既存の解決済 status/key は一切変更しない（99.28% を壊さない原則）。read-only な調査結果の反映のみ。

確証根拠:
  * NCID は NDL Search SRU (title="...") + CiNii Books OpenSearch(title) の serial 照合で取得。
    2026-06-27 worker調査。external_share は付与しない（owner gate 不変）。
  * 既存マージ(誤マージ)是正は note に旧根拠を残す。

read-only/dry-run: DB/Box/外部公開 なし。authority CSV の増分のみ。canonical昇格・accepted edge化なし。
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

SRC = "artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v14.csv"
DST = "artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v15.csv"

# journal_canonical -> (key_type, key_value, status, source, note)
# 値が None のフィールドは元行を維持する。
UPDATES = {
    # --- NDL/CiNii Books で serial NCID 取得 → direct/vol_issue 接合 (authority_unresolved 解消) ---
    "月刊債権管理": ("ncid", "AN10034403", "cinii_books_confirmed", "cinii_books_20260627",
        "CiNii Books: 『債権管理:月刊民事法情報号外』(民事法情報センター) NCID=AN10034403。"
        "旧誤マージ ISSN 1348-8953(季刊事業再生と債権管理)を破棄。direct通巻接合。"),
    "TKC税研時報": ("ncid", "AN1009402X", "cinii_books_confirmed", "ndl_sru+cinii_books_20260627",
        "NDL Search+CiNii Books: serial『TKC税研時報』NCID=AN1009402X(旧 NDL該当なしは誤り)。vol-issue接合。"),
    "訟務月報": ("ncid", "AN00327981", "cinii_books_confirmed", "ndl_sru+cinii_books_20260627",
        "NDL Search+CiNii Books: serial『訟務月報』(法務省訟務局→大臣官房) NCID=AN00327981。ISSN無(公的刊行物)。vol-issue接合。"),
    "立命館大学法学部ニューズレター": ("ncid", "AN10486595", "cinii_books_confirmed", "cinii_books_20260627",
        "CiNii Books: serial NCID=AN10486595(=立命館ロー・ニューズレター)。direct通巻接合。"),
    "保安と外勤": ("ncid", "AN0004113X", "cinii_books_confirmed", "cinii_books_20260627",
        "CiNii Books: serial『保安と外勤』(現 地域と保安) NCID=AN0004113X。direct/vol-issue接合。"),
    "明治大学法科大学院ジェンダー法センター年報": ("ncid", "AA1291592X", "cinii_books_confirmed", "cinii_books_20260627",
        "CiNii Books: serial NCID=AA1291592X。direct通巻(年報号数)接合。"),
    "建築関係法令の研究": ("ncid", "BN03460454", "cinii_books_confirmed", "cinii_books_20260627",
        "CiNii Books: 集合書誌『建築関係法令の研究』(日本建築学会近畿支部設計計画研究委員会) NCID=BN03460454。direct/vol-issue接合。"),
    "軍事民論": ("ncid", "AN00020468", "cinii_books_confirmed", "cinii_books_20260627",
        "CiNii Books: serial『軍事民論』(1975-2003廃刊) NCID=AN00020468。direct通巻接合。"),

    # --- status 是正(既存 key を活かして接合経路を開放) ---
    "法学論集(駒沢大学)": ("ncid", "AN00224683", "ndl_unique", "reconcile_resolved_20260627",
        "ORCH-L4: 駒沢のNCID基底 AN00224683 で direct通巻解決。青山法学論集ISSN 0518-1208とは分離済。collision_split解除。"),
    "法学セミナー別冊付録,p": ("issn", "0439-3295", "seed_verified", "seed:article_meta_confirmed",
        "ORCH-L4: 本誌『法学セミナー』(ISSN 0439-3295)へ統合。別冊扱い解除し発行年月(ym_terminal)で接合。"),
    "法学セミナー増刊,p": ("issn", "0439-3295", "seed_verified", "seed:article_meta_confirmed",
        "ORCH-L4: 本誌『法学セミナー』(ISSN 0439-3295)へ統合。増刊扱い解除し発行年月(ym_terminal)で接合。"),

    # --- 誤マージ防止: 機関混在を collision_split として明示し orphan受容(reasonをauthority_unresolvedへ) ---
    "判例研究": (None, None, "collision_split", None,
        "ORCH-L4: 金融判例研究(金融法務事情所収)等の機関混在のため触らず orphan受容。"
        "isbn_per_issue化すると誤マージのため collision_split に再分類(joinせず)。"),
}

# 商事法務(collision_split: 旬刊/国際/資料版)・タイム(多機関混在の判例タイムズ分)・
# 民事法研究/商法研究/現代刑事法(isbn_per_issue per-issue number)は run_article_join_dryrun.py 側
# (SPLIT_MAP / isbn番号フォールバック)で救済。authority 行は変更しない。

def main():
    src = Path(SRC)
    if not src.exists():
        print("ERROR src not found: %s" % src, file=sys.stderr); return 2
    rows = []
    with src.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        for r in reader:
            rows.append(r)

    applied = set()
    for r in rows:
        jc = (r.get("journal_canonical") or "").strip()
        if jc in UPDATES:
            kt, kv, st, src_, note = UPDATES[jc]
            if kt is not None: r["key_type"] = kt
            if kv is not None: r["key_value"] = kv
            if st is not None: r["status"] = st
            if src_ is not None: r["source"] = src_
            if note is not None: r["note"] = note
            applied.add(jc)

    missing = set(UPDATES) - applied
    if missing:
        print("WARN canonical not found in v14 (skipped): %s" % sorted(missing), file=sys.stderr)

    dst = Path(DST)
    with dst.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print("[done] %d updates applied -> %s (%d rows)" % (len(applied), DST, len(rows)), file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
