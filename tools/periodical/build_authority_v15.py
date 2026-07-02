#!/usr/bin/env python3
"""
build_authority_v15.py — ORCH-L4-COVERAGE-LIFT authority 増分 (v14 -> v15)

v14 を読み、orphan被覆引き上げのための「追記・status是正」だけを適用して v15 を書く。
既存の解決済 status/key は一切変更しない（99.28% を壊さない原則）。read-only な調査結果の反映のみ。

確証根拠:
  * NCID は NDL Search SRU (title="...") + CiNii Books OpenSearch(title) の serial 照合で取得。
    2026-06-27 worker調査。external_share は付与しない（owner gate 不変）。
  * 既存マージ(誤マージ)是正は note に旧根拠を残す。

durability fold (ORCH-AUTHORITY-WIRING-20260702):
  reconciled v15 は「一回性ファイル」だった。head が段1/段2で確定した以下を build に取り込み、
  再実行で reconciled v15(924行) と一致するようにした。入力は committed changelog
  `artifacts/periodical/journal_apply_changelog_20260701.csv`（casename bd28b62 由来）を決定論適用:
    * NORMALIZE 341     — journal_canonical のサフィックス除去(所収p/研究叢書等)。名補完のみ、統合せず。
    * MERGE_TO_EXISTING  — 創刊号,p / 別冊付録,p / 増刊,p の 7 行を本誌へ統合(source除去+target ac加算)。
    * ISSN_RESOLVED      — 税理 の key を ncid AN00080095 → issn 0514-2512 (NDL SRU 確定)。
  producer UPDATES と head changelog は(除去される2行を除き)非重複。順序非依存で reconciled と一致。

read-only/dry-run: DB/Box/外部公開 なし。authority CSV の増分のみ。canonical昇格・accepted edge化なし。
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

SRC = "artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v14.csv"
DST = "artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v15.csv"
CHANGELOG = "artifacts/periodical/journal_apply_changelog_20260701.csv"

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


def _load_changelog(path: Path):
    """head 確定分(NORMALIZE/MERGE/ISSN_RESOLVED)を changelog から決定論的に読む。

    返り値:
      normalize: {before_journal_canonical: after_journal_canonical}
      merges:    [(source_key, source_article_count:int, target_key)] を changelog 出現順で。
                 source-removed[i] と target-updated[i] は同順で対応(ac 差分が一致することを確認済)。
      issn_fix:  {journal_canonical: (key_type, key_value, source)}
    """
    normalize, issn_fix = {}, {}
    src_removed, tgt_updated = [], []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            op = r["op"]
            if op == "NORMALIZE":
                normalize[r["before"]] = r["after"]
            elif op == "MERGE_TO_EXISTING(source removed)":
                parts = [p.strip() for p in r["before"].split("|")]
                src_removed.append((parts[0], int(parts[1])))
            elif op == "MERGE_TO_EXISTING(target updated)":
                tgt_updated.append(r["key"])
            elif op == "ISSN_RESOLVED":
                kt, kv, so = r["after"].split("/")
                issn_fix[r["key"]] = (kt, kv, so)
    if len(src_removed) != len(tgt_updated):
        raise ValueError("MERGE source/target row count mismatch: %d vs %d"
                         % (len(src_removed), len(tgt_updated)))
    merges = [(s[0], s[1], t) for s, t in zip(src_removed, tgt_updated)]
    return normalize, merges, issn_fix


def _apply_changelog(rows, changelog_path: Path):
    """v14(+producer UPDATES) 行列に head 確定分を fold する。行順は保持。"""
    normalize, merges, issn_fix = _load_changelog(changelog_path)
    by_jc = {}
    for r in rows:
        by_jc.setdefault((r.get("journal_canonical") or "").strip(), r)

    # 1) MERGE: target を先に更新(source の ac / note を確定)してから source を除去。
    remove_keys = set()
    for src_key, src_ac, tgt_key in merges:
        tgt = by_jc.get(tgt_key)
        if tgt is None:
            raise ValueError("MERGE target not found: %r" % tgt_key)
        tgt["article_count"] = str(int(tgt["article_count"] or 0) + src_ac)
        appended = "merged<-%s(ac=%d) apply_20260701" % (src_key, src_ac)
        base = tgt.get("note") or ""
        tgt["note"] = (base + " | " + appended) if base else appended
        remove_keys.add(src_key)

    # 2) ISSN_RESOLVED: 税理 等の key 昇格。
    for jc, (kt, kv, so) in issn_fix.items():
        row = by_jc.get(jc)
        if row is None:
            raise ValueError("ISSN_RESOLVED target not found: %r" % jc)
        row["key_type"], row["key_value"], row["source"] = kt, kv, so

    # 3) NORMALIZE: journal_canonical のサフィックス除去(名補完のみ、他列不変)。
    for r in rows:
        jc = (r.get("journal_canonical") or "").strip()
        if jc in normalize:
            r["journal_canonical"] = normalize[jc]

    # 4) source 行を除去(行順は v14 由来を保持)。
    kept = [r for r in rows if (r.get("journal_canonical") or "").strip() not in remove_keys]
    return kept, len(merges), len(normalize), len(issn_fix)


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

    # durability fold: head 確定分(NORMALIZE/MERGE/ISSN_RESOLVED)を取り込む。
    cl = Path(CHANGELOG)
    n_merge = n_norm = n_issn = 0
    if cl.exists():
        rows, n_merge, n_norm, n_issn = _apply_changelog(rows, cl)
    else:
        print("WARN changelog not found, skipping durability fold: %s" % cl, file=sys.stderr)

    dst = Path(DST)
    with dst.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print("[done] UPDATES=%d NORMALIZE=%d MERGE=%d ISSN=%d -> %s (%d rows)"
          % (len(applied), n_norm, n_merge, n_issn, DST, len(rows)), file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
