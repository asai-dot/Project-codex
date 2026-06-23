# migrations/lawtime — DD-LAWTIME-001 base (v0.2.2) + production patch (v0.2.3)

> **status: candidate（RECONSTRUCTED）。監査 + owner ratify が前提。本番未 apply。**

## なぜ「reconstructed」か
オリジナルの **v0.2.2 base DDL がこのリポジトリに存在しなかった**（`docs/dd/DD-LAWTIME-001_v0.2.3_production_patch.md` という
**差分パッチの設計ドキュメントだけ**があった）。本ディレクトリの `001_base_v0.2.2.sql` は、その patch doc が
「既にある」前提で参照しているテーブル/列/resolver/gate と、`migrations/lawsubtrans/*` が消費する列から
**起こし直した best-effort 再構成**である。値域に `(recon)` と注記した CHECK は推定であり、
**production apply 前に正本の v0.2.x 設計と必ず突き合わせること**。

## 実体化状況（2026-06-22 確認）
- Supabase 2 プロジェクト（`alo-connect` / `asai-dot's Project`）の**いずれにも法令レイヤは未実体化**。
  `alo_edges` / `alo_statutes` / lawtime 系テーブルは一つも存在しない（＝完全なグリーンフィールド）。
- ⇒ backfill が書き換える**既存本番データは無い**。有料 Supabase branch の存在価値（実データでの予行）は
  本件には当たらないため、検証はローカル PG 構造スモークで足りる（branch 課金は不要）。

## 配置（owner 決定 2026-06-22）
- **スキーマ `lawtime`** に隔離（`public` 平置きにしない。`DROP SCHEMA lawtime CASCADE` で一括撤去可）。
  実倉庫 `asai-dot's Project` はドメイン別スキーマ運用のため、その流儀に沿わせた。
- **`alo_edges` は D2 edge レイヤ**で本来 lawtime とは別層だが、どこにも未実体化のため
  本再構成が**最小スタンドインとして自前生成**する（owner 決定）。`lawtime` 内に置くが、
  **実 D2 設計との整合は後で必須**（README 末尾 TODO）。
- 消費側（DD-LAWSUBTRANS・smoke fixture）は非修飾参照のため、`001_base` 末尾で
  **DB の search_path 末尾に `lawtime` を追記**（`"$user", public, lawtime`）。`public` 優先は維持し、
  lawtime は fallback。lawsubtrans を書き換えずに名前解決が通る。

## ファイルと適用順
| # | ファイル | 内容 |
|---|---|---|
| 001 | `001_base_v0.2.2.sql` | alo_law_work / alo_statutes / alo_edges(D2列含む) / alo_law_succession_edge / alo_law_ref_temporal_eval_event / fn_resolve_law_reference_at(二段・LIMIT 1) / eval append-only |
| 010 | `010_patch_v0.2.3.sql` | P0-1 (NOT VALID→backfill→VALIDATE) / P0-2 両端検査 / P0-3 current,superseded 絞り / P0-4 succession 曖昧検出 / R-1 view (v_lawtime_formal_status, v_lawtime_resolved_ref) |
| ── | `verify_dry_run.sql` | lawtime gate 群が 0 件であることを assert |

`001` の `alo_edges` は **two-tier CHECK を持たない**（legacy 行を temporal_status NULL で表現できる）。
CHECK は `010` が NOT VALID で先置き → backfill → `gate_backfill_unknown_unchecked` 空 → VALIDATE で入る。
これは patch doc P0-1 の本番手順を忠実に再現したもの。

## 検証
- ローカル構造スモーク：`../lawsubtrans/smoke_local/run_smoke.sh` が
  **lawtime(001→010) → lawsubtrans(001→005)** を連結して apply し、両 verify_dry_run を実行する。
  ⚠️ これは構造検査。backfill/formal_status/lawtime_resolved の**実データ**検証は materialize 済み環境を要する。
- 本番 dry-run は別途（materialize 先決定後）。本セッションは owner 指示により**課金なし＝ローカル構造スモークのみ**。

## 未確定 / TODO（audit で要確認）
- `fn_resolve_law_reference_at` のシグネチャ・tier1/2 の正確な挙動（v0.2.2 正本との一致）。
- `(recon)` 値域（as_of_basis / temporal_status / temporal_caveat / revision_status / relation_type / confidence）。
- v0.2.2 が持っていた**他の gate view**（patch doc は P0-2/3/4 のみ明示。網羅性は正本要確認）。
- `alo_edges` の generic 列（src_id/dst_id は最小再構成）。**実 D2 edge レイヤの設計と要整合**
  （本ファイルの alo_edges は lawtime スキーマ内のスタンドイン。実 D2 が別スキーマ/別形なら移設・接続が要る）。
- lawtime を `lawtime` スキーマに置いたことで、将来 D2/lawsubtrans を実体化する際の
  **スキーマ間 FK・search_path 運用**が本番ポリシーと整合するか（audit で確認）。
