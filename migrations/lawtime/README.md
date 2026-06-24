# migrations/lawtime — DD-LAWTIME-001 base (v0.2.2) + production patch (v0.2.3 / 2026-06-23 notes 反映 = v0.2.3a)

> **status: candidate（RECONSTRUCTED）。監査 + owner ratify が前提。本番未 apply。**
>
> ⚠️ **2026-06-24 重要訂正 — 前提（グリーンフィールド）が崩れた。**
> 本 README は当初「法令層はどこにも未 materialize」「`alo_edges` はどこにも無いのでスタンドインを自前生成」と
> 記していたが、**これは誤り**。asai-dot's Project に既に **`d1law_taikei` schema（URI ベースの法令体系 KOS）が在り、
> 本物の `alo_edges`（`src_uri/edge_type/dst_uri/...`）と claim_support gate・serving view の流儀が確立済**だった。
> ⇒ 再構成の `lawtime.alo_edges` スタンドイン・`law_work_id` text-id・search_path 追記は **実態と衝突する疑い**。
> **schema 配置は GPT お目付け役へ再相談中**（`docs/dd/20260624_lawtime_supabase_placement_DDLAWTIME_REQUEST.md`,
> Box file_id 2305223370418）。回答 ratify までこのディレクトリの SQL の schema 設計は**確定でない**。
>
> owner 決定（2026-06-24）で固定: **project は asai-dot's Project（d1law_taikei 同居）**／
> **alo-connect は空のまま（動的DB予約）**。残る論点は project 内の schema/モデル形（A/B/C 案）。
>
> 2026-06-23 監査（`DDLAWTIME_MODIFY_REQUIRED`）の must_fix / notes は反映済:
> 列 provenance・enum 丸め規則は **[`COVERAGE.md`](./COVERAGE.md)**、追加 gate（N-1〜N-4）は `010_patch`。
> production apply / materialize は **HOLD**（owner ratify 待ち）。

## なぜ「reconstructed」か
オリジナルの **v0.2.2 base DDL がこのリポジトリに存在しなかった**（`docs/dd/DD-LAWTIME-001_v0.2.3_production_patch.md` という
**差分パッチの設計ドキュメントだけ**があった）。本ディレクトリの `001_base_v0.2.2.sql` は、その patch doc が
「既にある」前提で参照しているテーブル/列/resolver/gate と、`migrations/lawsubtrans/*` が消費する列から
**起こし直した best-effort 再構成**である。値域に `(recon)` と注記した CHECK は推定であり、
**production apply 前に正本の v0.2.x 設計と必ず突き合わせること**。

## 実体化状況（当初 2026-06-22 → 2026-06-24 訂正）
- ~~Supabase 2 プロジェクトのいずれにも法令レイヤは未実体化＝完全なグリーンフィールド~~ … **誤り（訂正）**。
- **正:** `asai-dot's Project` には **`d1law_taikei`（URI ベースの D1 法令体系 KOS）が既に在り**、
  本物の `alo_edges`（`edge_id/src_uri/edge_type/dst_uri/source_system/source_version/valid_from`）と
  `alo_terms` ほか alo_* 一式、claim_support gate（`v_gate_..._excluded_from_claim_support_v<date>`）、
  `serving` schema の current/accepted view が**確立済**。`alo_statutes` / 版・succession・temporal-eval 系の
  テーブルだけは**まだ無い**（statute 時間軸は未実体化）。
- ⇒ backfill が触る既存「法令版」データは無いが、**`alo_edges` は既存・本番データ有り**。検証は引き続き
  ローカル PG 構造スモークで足りるが、**配置は実 `d1law_taikei` を前提に再設計が要る**（下記相談中）。

## 配置（2026-06-24 — 再相談中。下の設計は暫定で確定でない）
- **owner 確定**: project = **asai-dot's Project**（d1law_taikei 同居）。**alo-connect は空のまま**（動的DB予約）。
- **未確定（お目付け役へ相談中, file_id 2305223370418）**: project 内の schema/モデル形。
  - 当初案＝新 `lawtime` schema に独自 `alo_edges` スタンドイン＋search_path 追記。
    → **実 `d1law_taikei.alo_edges` と名前衝突・identity 不一致・既存 gate 流儀の再発明**の疑いで保留。
  - 検討中の代替: (A) d1law_taikei の alo_* へ統合し citation を既存 `alo_edges` の行＋edge_id keyed side-table /
    (B) 別 schema＋実 `alo_edges` 跨ぎ参照・search_path 廃止 / (C) 折衷。
  - ⇒ ratify 後にこのディレクトリの SQL を確定形へ改める（現状は構造スモーク用の暫定 DDL）。
- 消費側（DD-LAWSUBTRANS・smoke fixture）は非修飾参照のため、`001_base` 末尾で
  **DB の search_path 末尾に `lawtime` を追記**（`"$user", public, lawtime`）。`public` 優先は維持し、
  lawtime は fallback。lawsubtrans を書き換えずに名前解決が通る。

## ファイルと適用順
| # | ファイル | 内容 |
|---|---|---|
| 001 | `001_base_v0.2.2.sql` | alo_law_work / alo_statutes / alo_edges(D2列含む) / alo_law_succession_edge / alo_law_ref_temporal_eval_event / fn_resolve_law_reference_at(二段・LIMIT 1) / eval append-only |
| 010 | `010_patch_v0.2.3.sql` | P0-1 (NOT VALID→backfill→VALIDATE) / P0-2 両端検査 / P0-3 current,superseded 絞り / P0-4 succession 曖昧検出 / **N-1 fallback law_id 一意 / N-2 版区間重なり / N-3,N-4 formal-status 整合** / R-1 view (v_lawtime_formal_status, v_lawtime_resolved_ref) |
| ── | `verify_dry_run.sql` | lawtime gate 群（P0-2/3/4 + N-1/N-2/N-3/N-4）が 0 件であることを assert |
| ── | `COVERAGE.md` | 列 provenance（P/L/R 分類）・enum 値域と丸め規則・resolver 非決定性保証（監査 must_fix #1/#3/#4） |

`001` の `alo_edges` は **two-tier CHECK を持たない**（legacy 行を temporal_status NULL で表現できる）。
CHECK は `010` が NOT VALID で先置き → backfill → `gate_backfill_unknown_unchecked` 空 → VALIDATE で入る。
これは patch doc P0-1 の本番手順を忠実に再現したもの。

## 検証
- ローカル構造スモーク：`../lawsubtrans/smoke_local/run_smoke.sh` が
  **lawtime(001→010) → lawsubtrans(001→005)** を連結して apply し、両 verify_dry_run を実行する。
  ⚠️ これは構造検査。backfill/formal_status/lawtime_resolved の**実データ**検証は materialize 済み環境を要する。
- 本番 dry-run は別途（materialize 先決定後）。本セッションは owner 指示により**課金なし＝ローカル構造スモークのみ**。

## 監査で閉じた点（2026-06-23 RESULT 反映）
- `fn_resolve_law_reference_at` の LIMIT 1 非決定性 → N-1/N-2 gate で 0 件保証（`COVERAGE.md` §4）。
- `(recon)` 値域の出典分類と丸め規則 → `COVERAGE.md` §2/§3。
- formal-status の状態整合（CurrentEnforced 重複 / Repeal 同居）→ N-3/N-4 gate。

## 未確定 / TODO（ratify 前に残る）
- `fn_resolve_law_reference_at` のシグネチャ・tier1/2 の挙動の**正本 v0.2.2 との最終一致**（gate で非決定性は封じたが正本照合は別）。
- `revision_status` 状態機械の corpus 実態での最終照合（N-3 強化）。
- `alo_edges` の generic 列（src_id/dst_id は最小再構成）。**実 D2 edge レイヤの設計と要整合**
  （本ファイルの alo_edges は lawtime スキーマ内のスタンドイン。実 D2 が別スキーマ/別形なら移設・接続が要る）。
- lawtime を `lawtime` スキーマに置いたことで、将来 D2/lawsubtrans を実体化する際の
  **スキーマ間 FK・search_path 運用**が本番ポリシーと整合するか（audit で確認）。
