---
worker_task_id: W-20260624-230
status: queued
priority: P1
owner: claude-code-worker
created_at: 2026-06-24
request: docs/workflow_model/REQUEST_v0.2.md
poc: PoC1
goal: 「相談」語が個別案件と公益活動(当番弁護士/区役所/勉強会/会議議題)で混在する問題に対し、相談(個別案件)/非相談 の判別ルールを精緻化し、判定アルゴリズム(入力シグナル・優先順位・確信度・人手確認境界)を確定する。接続不要(既存所見からの設計)。
mode: implementation
requires_systems:
  - repo
depends_on:
  - W-20260624-190
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
  - 相談/非相談の判別ルールが入力シグナル(添付Doc有無/参加者/分野語/availability・transparency/差出人ML等)の重み付き条件で定義
  - 型A-E(W-190)と Gmailノイズ(京都弁護士会ML等, W-210)を網羅的に分類できる
  - 確信度区分と「人手確認に回す境界(HITL)」が定義
  - AI推定は候補どまり・人間承認で確定(G-19)を厳守
  - PII(実件名)非記載
  - RESULT を done/ または blocked/ に書く
deliverables:
  - docs/workflow_model/v0.2/POC1_consultation_discrimination_rule_v0.2.md
max_attempts: 2
result_expected_filename: W-20260624-230_RESULT.md
---

# Task — 相談/非相談 判別ルール精緻化（接続不要）

## 背景
W-190/W-210 で「`相談` 語が個別案件と公益活動(当番弁護士・区役所法律相談・勉強会・なんでも相談会)・事務所会議議題行で混在」「Gmail `subject:相談` の大半が京都弁護士会MLノイズ」と判明。相談記録合成・KPI分母の精度を上げるため、判別ルールを精緻化する。**外部システム非アクセス**(既存所見からの設計)。

## 入力(docs/workflow_model/v0.2/)
- PHASE5_consultation_record_survey_v0.2.md (W-190, 型A-E・複合判別ルール一次版・参加者非構造化)
- POC1_dryrun_result_v0.2.md (W-210, 14/25採用・型D10/型E1除外・Gmail MLノイズ)
- POC1_measurement_design_v0.2.md (W-200)
- ALO_WORKFLOW_CATALOG_v0.2.yaml (consultation状態機械/metrics)

## やること
1. **入力シグナルの棚卸し**: 判別に使えるシグナル(事件メモDoc添付の有無/availability=FREE・transparency=transparent(=会議掲示)/分野語の有無/参加者構成/差出人がML(京都弁護士会等)/タイトル語彙)を列挙し、各シグナルの判別力を評価。
2. **判別アルゴリズム**: 個別相談/非相談(公益・勉強会・会議議題/ノイズ)を分類する重み付き条件(決定木 or スコアリング)を定義。W-190型A-E・W-210のGmailノイズを全て正しく落とせること。
3. **確信度とHITL境界**: 自動で個別相談と確定できる条件／自動で非相談と除外できる条件／**人手確認に回す灰色帯**を定義。AI推定は候補どまり・人間承認で確定(G-19)。
4. **適用先**: Calendar予定・Gmailスレッド・Doc の各々への適用方法。KPI分母(個別相談件数)の算出にどう効くか。
5. **検証**: W-210の25件(個別14/型D10/型E1)に当てはめ、ルールが同じ分類を再現するかを机上検証(件数のみ・PII無)。

## 厳守事項
- 外部システム非アクセス(設計のみ)。PII(実件名)非記載=様式/プレースホルダ/件数のみ。owner裁定とworker推論を区別。AI推定を人間判断にしない。**git操作なし**。成果物は v0.2 配下のみ。捏造禁止。

## 完了処理
RESULT を `done/W-20260624-230_RESULT.md`、1行目 `WORKER_PASS`(exit_criteria充足)。worker_task_id 記載。無理なら blocked/。
司令塔への戻り値: (a)PASS/BLOCKED (b)成果物パス (c)判別アルゴリズムの確定可否 (d)型A-E＋Gmailノイズを網羅できたか (e)HITL境界の定義有無 (f)W-210 25件での机上検証結果 (g)残課題。本文全文は貼らない。
