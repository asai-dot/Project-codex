# migrations/lawsubtrans — DD-LAWSUBTRANS-001 v0.1.3 production DDL（P1 先行分）

設計受理済み（owner ratified 2026-06-10, design）DD を **実 SQL** に書き起こしたもの。
PLAN v0.1 の **P1** に相当。**まだ本番 apply していない。**

## ファイルと適用順

| # | ファイル | 内容 |
|---|---|---|
| 001 | `001_tables.sql` | T1–T6 テーブル＋index（T5 を T2–T4 より先に定義） |
| 002 | `002_append_only_triggers.sql` | T1–T4,T6 の content 不変トリガ（T5 は除外） |
| 003 | `003_current_views.sql` | §3.7 current view（review-event 優先・T2 は candidate 起点） |
| 004 | `004_gates.sql` | §4 品質 gate 13本（違反行を返す view。CI で空を assert） |

## 依存

- **既存 law layer**: `alo_law_work` / `alo_statutes` / `alo_edges`（30_law_layer, DD-LAWTIME）
- **DD-LAWTIME v0.2.3 R-1 view**: `v_lawtime_formal_status` / `v_lawtime_resolved_ref`
  （gate 4・9・13 が参照）。**lawtime v0.2.3 が ratify・apply される前は当該 gate のみ HOLD**、
  他テーブル・トリガ・view・gate（lawtime 非依存）は先行 apply 可能。

## 検証方針（重要）

- **検証は Supabase `alo-connect` の branch dry-run で行う**（本物の alo_* テーブル＋既存行＋R-1 view 上）。
- **空のローカル DB で通っても無意味（偽陽性）**：base テーブルも既存行も無く、特に lawtime backfill 系・
  formal_status 整合・lawtime_resolved 結合は「存在するデータ」が論点だから。本ディレクトリの SQL は
  ローカル empty DB での「通った」を成功とみなさない。
- dry-run 手順: branch 作成 → 001〜004 apply → 合成データ投入（本リポジトリの producer fixture 由来）→
  **全 gate view が 0 行**を assert（わざと違反行を入れて検出されることも確認）→ dry-run レポートを
  `gate=DDLAWSUBTRANS` で監査 → owner ratify → 本番 apply。

## 既知の production 精緻化ポイント（PLAN §10 / 監査 note 由来）

- gate 9（formal_status 整合）は `superseding_revision_id → alo_statutes.law_id → v_lawtime_formal_status`
  の近似結合。article 単位の精緻化は article_crosswalk 接続後。
- gate 4/13 の `lawtime_resolved` 結合キー（work 単位 vs edge 単位）を ingest スキーマ確定（P2）で固定。
- gate 13 を T3/T4 の claim_support にも UNION 拡張（現状は T2 のみ実装、注記済み）。
- evidence_count は当面 `evidence_pointer_id IS NOT NULL`＝1（Note B。multi-evidence は join table 新設時）。

## 安全弁（DDL レベルで効いているもの）

- `claim_support_eligible` 既定 false ＋ CHECK（evidence あり ∧ counter 無し）＋ gate 4 で accepted/
  lawtime_resolved を要求 → **既定で出口に出ない**。
- 全 assertion content は append-only。status/rank は T6 event。**accepted は人手 review-event の専権**。
- ingest（P2）は accepted / claim_support=true を書けない（DB 制約＋CI で二重禁止）。
