# migrations/lawtime — DD-LAWTIME-001 base (v0.2.2) + production patch (v0.2.3 / 2026-06-23 notes 反映 = v0.2.3a)

> **status: RATIFIED（design 確定 / owner asai 2026-06-25）。本番未 apply（HOLD 維持）。**
>
> ✅ **2026-06-25 owner ratify 済**: v0.2.4 C-option（`placement_v0.2.4/`）が lawtime 配置の**確定設計**。
> 決裁: [`docs/dd/DD-LAWTIME-001_v0.2.4_owner_ratify_packet.md`](../../docs/dd/DD-LAWTIME-001_v0.2.4_owner_ratify_packet.md) §6。
> 本番 apply / Supabase 本番反映 / branch 課金 dry-run / canonical / claim_support は **HOLD 継続**（別途 owner 明示 GO）。
> 段取り: [`docs/dd/DD-LAWTIME-001_v0.2.4_materialize_runbook.md`](../../docs/dd/DD-LAWTIME-001_v0.2.4_materialize_runbook.md)（PHASE A–E / 課金ゼロの DRAFT・実行待ち）。
> O1 決裁: [`docs/dd/DD-LAWTIME-001_v0.2.4_O1_decision.md`](../../docs/dd/DD-LAWTIME-001_v0.2.4_O1_decision.md) → **A 統一RESTRICT**（side-table FK = `ON DELETE RESTRICT`、設計反映済・smoke ガード PASS）。
>
> ✅ **2026-06-25 v0.2.4 監査 ratify 済**: RESULT `DDLAWTIME_V024_PLACEMENT_PASS_WITH_NOTES`
> （Box file_id 2306481004211）。C-option 採用可・**materialize branch dry-run へ GO**（branch/local/fixture/smoke
> 範囲限定）。本番 apply / Supabase 本番反映 / canonical / claim_support は **HOLD 継続**。
> 追加 Notes 3 件（lawref 分離 / CASCADE 削除運用 / **C-INT-1,2 を materialize 必須受入条件**）は
> `docs/dd/DD-LAWTIME-001_v0.2.4_placement.md` §11 に反映。
>
> ✅ **2026-06-24 配置 ratify 済 → 確定形は v0.2.4（C-option）。**
> 配置相談の RESULT `DDLAWTIME_PLACEMENT_PASS_WITH_NOTES`（Box file_id 2305621550301）で
> **C-option 確定**。確定形の SQL・設計は:
> - 設計: **[`docs/dd/DD-LAWTIME-001_v0.2.4_placement.md`](../../docs/dd/DD-LAWTIME-001_v0.2.4_placement.md)**
> - SQL 一式: **`migrations/lawtime/placement_v0.2.4/`**（母屋 fixture / lawtime schema / gates / serving / smoke）
>
> C-option の要点: citation edge 本体＝既存 **`d1law_taikei.alo_edges`**（母屋）、時間評価属性＝
> **`lawtime.citation_temporal`（edge_id keyed side-table）**、identity＝**URI**、名前解決＝**明示修飾（search_path 廃止）**、
> 出口＝**`serving` schema**、gate＝**house style `v_gate_lawtime_*_v20260624`**。
> ⇒ 本ディレクトリ直下の `001_base_v0.2.2.sql` / `010_patch_v0.2.3.sql`（独自 `lawtime.alo_edges` スタンドイン・
> text-id・search_path 追記）は **v0.2.4 で設計上 superseded**。v0.2.3a 構造スモーク artifact として残置するのみ。
>
> owner 決定（2026-06-24）で固定: **project は asai-dot's Project（d1law_taikei 同居）**／
> **alo-connect は空のまま（動的DB予約）**。
>
> 2026-06-23 監査（v0.2.3a `DDLAWTIME_PASS_WITH_NOTES`）の must_fix / notes 反映済:
> 列 provenance・enum 丸め規則は **[`COVERAGE.md`](./COVERAGE.md)**、追加 gate（N-1〜N-4）は `010_patch`。
> should_fix #1（R 列の置換可能性）は COVERAGE 冒頭、#2（gate 名 + 失敗時 owner action）は下表、
> #3（sample resolver の golden 固定）は `placement_v0.2.4/sample_resolver.sql`。
> production apply / materialize は **HOLD**（owner ratify 待ち）。
>
> ### gate 一覧と失敗時 owner action（should_fix #2）
> | gate（v0.2.4 house style） | 由来 | 失敗時 owner action |
> |---|---|---|
> | `v_gate_lawtime_citation_edge_missing_side_table_v20260624` | C-INT | resolver 再走 or unresolved_queue 投入 |
> | `v_gate_lawtime_side_table_orphan_or_noncitation_v20260624` | C-INT | side-table 行削除 or edge_type 是正 |
> | `v_gate_lawtime_resolved_revision_covers_asof_v20260624` | P0-2 | 版再解決（resolution_method 見直し） |
> | `v_gate_lawtime_claim_support_requires_resolved_v20260624` | P0-3 | claim_support_eligible を false へ / 条件充足 |
> | `v_gate_lawtime_succession_no_ambiguous_overlap_v20260624` | P0-4 | lineage_event_id 付与 or confidence 降格 |
> | `v_gate_lawtime_work_single_fallback_law_id_v20260624` | N-1 | succession 明示 or 版整理 |
> | `v_gate_lawtime_statute_revision_no_ambiguous_overlap_v20260624` | N-2 | 版区間 [from,to) の是正 |
> | `v_gate_lawtime_formal_status_inconsistent_v20260624` | N-3/N-4 | corpus 状態語の再マップ |
> | （v0.2.3a 旧名 `gate_*` は上記へ改名。`010_patch` の旧 gate は構造スモーク用に残置） |

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
