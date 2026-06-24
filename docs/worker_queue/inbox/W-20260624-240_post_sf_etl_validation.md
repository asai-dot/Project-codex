---
worker_task_id: W-20260624-240
status: held
priority: P0
owner: claude-code-worker
created_at: 2026-06-24
request: docs/workflow_model/REQUEST_v0.2.md
poc: PoC1
held_reason: SF-ETL 未実行(dynamic.cases 0行=制御塔データ不在, W-110)。SF-ETLが走り cases/変換関係が投入されてから着手。先回りで仕様だけ確定しておく。
goal: SF-ETL起動後に、背骨ID(SF Matter/Consultation Id)が入った状態でクロス系突合・declared/observed乖離・比率系KPIを実測し、W-210で0%だった源跨ぎ突合がどこまで解決するかを検証する。
mode: implementation
requires_systems:
  - Supabase dynamic schema (read-only, SELECT) ※SF-ETL投入後
  - Google Calendar/Docs, Gmail, Box (read-only)
depends_on:
  - W-20260624-210
  - SF-ETL-RUN (外部前提・owner/SE)
allowed_paths:
  - docs/workflow_model/v0.2/
allowed_actions:
  - read_supabase(select_only)
  - read_google_calendar(read_only)
  - read_gmail(read_only)
  - read_box(read_only)
  - write deliverable
forbidden_actions:
  - production_db_write
  - transcribe_privileged_content
  - pii_in_general_artifact
  - fabricate_cross_links
  - ai_estimate_as_human_decision
  - fill_unknown_with_generalities
exit_criteria:
  - dynamic.cases に行が入っていることを確認(0行ならBLOCK継続=着手前提未達)
  - 背骨ID解決率(相談event↔SF Consultation/Matter↔Box↔Gmail)を実測し、W-210の源跨ぎ0%からの改善を定量化
  - declared(SF受任ステータス)↔observed(委任契約書/受任通知)の乖離率(KPI-P1-07)を実測
  - 比率系KPI(次行動未設定/流入経路不明/失注理由未入力)を実測
  - PII非転載・read-only証明・背骨ID無き突合は候補どまり
  - RESULT を done/ または blocked/ に書く
deliverables:
  - docs/workflow_model/v0.2/POC1_post_etl_validation_v0.2.md
max_attempts: 2
result_expected_filename: W-20260624-240_RESULT.md
---

# Task — SF-ETL後 クロス系突合・KPI 実測検証（SF-ETL待ちで held）

## 位置づけ
**着手前提 = SF-ETL が走り `dynamic.cases` に案件(Consultation/Matter)が投入され、背骨ID(sf_record_id)と変換関係が揃っていること。** 現状 W-110 で cases 0行=制御塔データ不在のため held。SF-ETL起動後に inbox へ移し claim する。本票は**先回りの仕様確定**。

## 検証内容（SF-ETL後）
1. **背骨ID解決率**: W-210 で源跨ぎ確定突合=0%だった「相談(Calendar)→見積(Box)→契約/受任(Gmail)」を、SF Matter/Consultation Id を背骨に何%束ねられるか実測。W-210比較で改善を定量化。
2. **declared/observed 乖離(G-04/KPI-P1-07)**: SF受任ステータス(declared)と、委任契約書[Box]・受任通知[Gmail]から立てた observed_受任 の一致/乖離率。
3. **比率系KPI(P1-05/06/07相当)**: 次行動未設定率・流入経路不明率・失注理由未入力率(失注はenum, G-12)を SF実データで実測。
4. **KPI-P1-02/03/04**: 背骨ID解決後に相談確定/見積送付/契約成立 時間が算出可能になるか実測。
5. W-210 dry-run結果との before/after 比較表。

## 厳守事項
- cases が 0行のままなら着手前提未達=BLOCK(捏造で進めない)。read-only(SELECT)・PII非転載・背骨ID無き突合は候補どまり・AI推定は人間承認まで非確定。**git操作なし**。成果物は v0.2 配下のみ。

## 完了処理
RESULT を `done/W-20260624-240_RESULT.md` 先頭 `WORKER_PASS`(前提達成＋実測)/前提未達なら `blocked/` WORKER_BLOCKED。司令塔戻り値: 背骨ID解決率/乖離率/比率系KPI実測値/W-210比較/残課題。
