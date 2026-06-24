---
worker_task_id: W-20260624-220
status: queued
priority: P1
owner: claude-code-worker
created_at: 2026-06-24
request: docs/workflow_model/REQUEST_v0.2.md
poc: PoC1
goal: 受任通知(Gmail)が件名非標準で自動検出できない問題(W-210 S3=候補22件・確定不可)に対し、受任通知の標準件名様式＋自動検出ルール(正規表現/判定条件)＋移行運用案を設計する。接続不要(既存所見からの設計)。
mode: implementation
requires_systems:
  - repo
depends_on:
  - W-20260624-210
allowed_paths:
  - docs/workflow_model/v0.2/
allowed_actions:
  - edit_files
  - write deliverable
forbidden_actions:
  - production_db_write
  - external_system_access
  - pii_in_general_artifact
  - ai_estimate_as_human_decision
  - fill_unknown_with_generalities
  - file_move_rename_delete
exit_criteria:
  - 標準件名様式(トークン構成)が定義され、自動検出の正規表現/判定条件が示されている
  - 受任通知が満たすべき構造化メタ(案件参照・宛先種別・送信種別)が定義
  - 移行運用案(現行の非標準件名をどう扱うか・移行期の二重検出)がある
  - schema_v0.2 のイベント(engagement_signed/受任通知系)・catalog metricsとの整合
  - PII(実件名)を含めない(様式・プレースホルダのみ)
  - RESULT を done/ または blocked/ に書く
deliverables:
  - docs/workflow_model/v0.2/POC1_engagement_notice_subject_rule_v0.2.md
max_attempts: 2
result_expected_filename: W-20260624-220_RESULT.md
---

# Task — 受任通知 件名様式 標準化ルール案（接続不要）

## 背景
W-210 で受任通知(Gmail)は `subject:(受任通知)` で候補22件ヒットするが、件名が非標準・所内連絡や外部一般メールと混在し、**クライアント宛の構造化受任通知を確実に判別できない**(S3=候補どまり)。これを自動検出可能にする標準様式を設計する。**外部システムにアクセスしない**(W-210/W-200/W-190 の所見からの設計作業)。

## 入力(docs/workflow_model/v0.2/)
- POC1_dryrun_result_v0.2.md (W-210, S3の現状・候補件数・ノイズ源)
- POC1_measurement_design_v0.2.md (W-200, 受任=3シグナル/S3定義)
- ALO_OWNER_GRILL_ANSWERS_v0.1.md (G-11 受任=複数シグナル/G-08 案件参照)
- alo_workflow_event_schema_v0.2.json (engagement_signed 等のevent_type)
- ALO_WORKFLOW_CATALOG_v0.2.yaml (metrics KPI-P1-04 契約成立時間)

## やること
1. **標準件名様式の定義**: トークン構成を設計(例: `[受任通知] <案件参照> / <宛先種別>` のような型。実件名は使わずプレースホルダで)。案件参照に背骨ID(SF Matter/Consultation Id, G-01)を埋める設計。
2. **自動検出ルール**: 標準様式にマッチする正規表現/判定条件。所内連絡・外部一般メール・MF自動通知を除外する条件(差出人/宛先/本文有無のヒューリスティクスは構造のみ)。検出の確信度区分(確定/候補)。
3. **構造化メタ**: 受任通知が持つべきメタ(案件参照・宛先種別=client/payer/third、送信種別=正式受任通知か否か)。S1(委任契約書)・S2(SFステータス)との突合点。
4. **移行運用案**: 現行の非標準件名をどう扱うか。移行期は「標準様式の新規分=確定検出／旧分=候補(人間確認)」の二重運用。受任成立ゲート(HG-02 optional)での人間承認との接続。
5. **整合**: schema_v0.2 の engagement_signed 等へのマッピング、KPI-P1-04(契約成立時間)が標準化後に測定可能になる道筋。

## 厳守事項
- 外部システム非アクセス(設計のみ)。PII(実件名)非記載=プレースホルダ/様式のみ。owner裁定とworker推論を区別(根拠 G-xx/D-xx)。AI推定を人間判断にしない。**git操作なし**。成果物は v0.2 配下のみ。捏造禁止。

## 完了処理
RESULT を `done/W-20260624-220_RESULT.md`、1行目 `WORKER_PASS`(exit_criteria充足)。worker_task_id 記載。無理なら blocked/。
司令塔への戻り値: (a)PASS/BLOCKED (b)成果物パス (c)標準様式と検出ルールの確定可否 (d)現行ノイズ除外条件の有無 (e)移行運用案の有無 (f)KPI-P1-04測定可能化の道筋 (g)残課題。本文全文は貼らない。
