# RECONCILIATION — 既存 NDL/蔵書パイプライン（実地調査で確定）

- 作成: 2026-06-20 / 更新: 2026-06-20（Box 実地調査で確定）
- 経緯: ここに R1/R2/R3 を新規作成したが、**成熟した既存パイプラインが存在**（月次自動運用中）と判明し撤回。
  本書は所在・データフロー・対応表・再利用方針。出典は公式 `ndl_pipeline_manual.md` v1.0 と各スクリプト現物。

## 1. 既存パイプラインの所在（確定）

Box: `すべてのファイル/浅井/claude/事務所内本棚DX化計画/`（Mac mirror `C:\Users\Asai\Box\浅井\claude\事務所内本棚DX化計画\`）
- `scripts/`（id 372082336187）: `ndl_harvest.py` / `ndl_normalize.py` / `ndl_integrate.py` / `ndl_clean.py` /
  `enrich_ndl_publisher.py` / `cinii_opac_overlay.py` / `s_court_analysis.py` / `google_books_isbn_recovery.py` / `opac_*` 他
- `scan_data/`（id 371757721226）: 稼働データ（下記）
- `app/data/books.json`: **蔵書DB正本 6,384冊**
- `docs/ndl_pipeline_manual.md`: 公式マニュアル v1.0（月次運用手順）
- mirror: `浅井/CODEX/scripts/`（id 372095733257, `match_titles_to_ndl.py` 等）

## 2. データフロー（マニュアルより。**OAI-PMH 月次差分**が本線）

```
NDL OAI-PMH API
  └ ndl_harvest.py(月次差分, scheduled task "ndl-monthly-harvest")
      → scan_data/ndl_harvest_delta.csv
  └ ndl_normalize.py(--target delta)  → *_normalized.csv
  └ ndl_integrate.py(--delta, books.json突合)
      → ndl_shelf_matched.csv / ndl_law_books_ndc320.csv / ndl_isbn_index.csv
```

## 3. owner の2問への回答（確定）

**Q1: 既存 scripts の所在** → §1 のとおり（`事務所内本棚DX化計画/scripts` ＋ `CODEX/scripts`）。

**Q2: 16.7GB ダンプは `ndl_normalize` の入力元か** → **いいえ。**
- 本線は **OAI-PMH の月次差分**（`ndl_harvest_delta.csv`）を normalize/integrate する**増分**運用。
- 16.7GB `NDL_書誌情報_raw`(161分割) は **アーカイブ全件スナップショット（約900万件）**。マニュアル §6「元データの所在」に
  記載の参照用。Box Drive では「オンラインのみ」推奨（同期しない）。
- **派生 ISBN 索引 `scan_data/ndl_isbn_index.csv`（851万件 / 1.9GB）は既に構築済・維持中。**

## 4. 既存成果物（＝私が作ろうとしたものは概ね存在）

| roadmap WS | 私の(撤回)案 | 既存実体 |
|---|---|---|
| WS-R R2 ISBN索引 | r2_build_index.py | **`scan_data/ndl_isbn_index.csv`(851万件)** 既存・月次更新 |
| WS-A1/A2 蔵書突合 | r3_coverage.py | `ndl_shelf_matched.csv`(5,257) / `ndl_shelf_integrated.csv` |
| WS-A2 ISBN復元(421/no-isbn) | 構想のみ | `google_books_isbn_recovery.csv` ＋ SRU `ndl_bibid_recovery.csv` |
| WS-B1 no-ISBN title照合(1,101) | 構想のみ | `match_titles_to_ndl.py`（版/刷除去込み） |
| 法律書サブセット | — | `ndl_law_books_ndc320.csv`(118,458) |
| 購入候補 | — | `s_court_analysis.csv`（購入候補 16,639冊） |
| 雑誌ISSN | — | `magazine_issn_assignment.csv`(92.4%) / `cinii_opac_overlay.csv` |

→ **WS-R/A2/B1 は新規構築不要**。既存出力を**読む**だけで cohort-A 被覆・421・1,101 の問いに答えられる。

## 5. 撤回（git 履歴に残置）
`isbn_util.py` / `r1_probe.py` / `r2_build_index.py` / `r3_coverage.py` / `selftest.py` / `run_all.sh` /
旧 README / 旧 RUNBOOK。コードレビュー監査は投函中止。

## 6. cohort-A の素性（lineage 確定）

調査で系譜が判明:
```
物理蔵書 / 自炊スキャン / 手入力
  → bookshelf_dx repo: app/data/books.json   ← ★正本(living source of truth)。H:\work\repos\bookshelf_dx
  → NDL pipeline enrich（ndl_integrate: NDL bibid / alo:book:isbn URI 付与）
  → bookshelf release candidate（export books.jsonl + toc_index 776,999 + covers 1,172）
  → Supabase import → biblio.bib_records (source=asai-bookshelf)  ← 下流スナップショット
```

**それぞれの由来（owner Q1 への回答）**
- **`books.json`（正本・上流）**: 蔵書アプリ `bookshelf_dx` の生きた蔵書DB。物理/スキャン/手入力＋NDL突合 enrich で更新。
  2026-04-04 時点 6,384 → 04-22 dry-run で **6,525**（成長中）。TOC・表紙も保持＝bib_records より情報が多い。
- **`bib_records`（Supabase・下流）**: 上記 release を **2026-06-03 18:59 に一括ロード**した時点スナップショット＝**6,524**。
  `raw`/`source_url`/`source_hash` は**全て空**（素のロードで provenance 列は未投入）。04-22 dry-run の books=6,525 とほぼ一致。

**結論**: **正本は `books.json`（bookshelf_dx）**。`bib_records` はその 2026-06-03 release snapshot。
identity 作業は DB(`bib_records`) を作業面にしてよいが、**provenance ルートは books.json/release**。両者の差(6,524↔6,525↔6,384)は時点差。

## 7. DD-LITID の「真の新規」部分（既存と重複しない）

既存パイプラインは **ISBN→NDL を manifestation 級で match** するが、以下は**やっていない**＝ここが DD-LITID の付加価値:
- **版/刷の confirmed 区別**（版＝edition を識別子で束ね、刷は無視）
- **2独立証拠での confirm / candidate≠confirmed / adjudication 記録**（D0/Q1 契約）
- work/edition/holding/access のカウント分離、confusion buckets、cohort×decision_type ゲート
→ ロードマップは「索引/突合の再実装」ではなく、**既存 match 出力の上に edition-identity ガバナンス層を載せる**ものと再定義。

## 8. owner / local への確認（最小）
1. cohort-A の「正」を DB(`bib_records`) と CSV(`books.json`/`ndl_shelf_matched.csv`) のどちらに置くか。
2. 既存 `ndl_shelf_matched.csv` / `ndl_isbn_index.csv` の最新版を read-only で参照してよいか（被覆は**再走不要・読むだけ**）。
3. 月次 harvest の最新実行日（`ndl_harvest_state.json`）＝鮮度基準。
