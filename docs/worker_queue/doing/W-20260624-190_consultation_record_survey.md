---
worker_task_id: W-20260624-190
status: queued
priority: P0
owner: claude-code-worker
created_at: 2026-06-24
request: docs/workflow_model/REQUEST_v0.2.md
poc: PoC1
goal: G-14で確定した相談記録ソース(Googleカレンダー予定＋カレンダー紐付けGoogleドキュメント「事件メモ」＋弁護士手打ちGoogleドキュメント)を read-only 実査し、相談記録の合成可能性(構造・件数・カレンダー→事件メモの紐付け方式・受任シグナルの観測可否)を確認する。Nottaは未接続=未測定と明示。
mode: implementation
requires_systems:
  - Google Calendar (read-only, MCP)
  - Google Drive/Docs (read-only, MCP)
allowed_paths:
  - docs/workflow_model/v0.2/
allowed_actions:
  - read_google_calendar(read_only)
  - read_google_drive_metadata(read_only)
  - write deliverable
forbidden_actions:
  - calendar_write_create_update_delete
  - drive_write_create_update_delete
  - transcribe_privileged_content   # 相談メモ本文の転載禁止(秘匿特権)
  - pii_in_general_artifact
  - ai_estimate_as_human_decision
  - fill_unknown_with_generalities
  - file_move_rename_delete
exit_criteria:
  - カレンダーの相談予定の構造(タイトル様式/参加者数/本文や添付に事件メモGoogleDocへのリンクがあるか)を集計で把握
  - 事件メモ/手打ちメモGoogleDocの命名様式・件数・構造を把握(本文非転載)
  - カレンダー予定→事件メモGoogleDoc の紐付け方式を特定(リンク/添付/命名規則のどれか)
  - 相談記録を Notta(未接続)+事件メモ+手打ちメモ から合成する設計メモ
  - read-only証明(書込系を呼んでいないこと)・PII値の非転載(集計/構造のみ)
  - RESULT を done/ または blocked/ に書く
  - 成果物は docs/workflow_model/v0.2/ 配下のみ
deliverables:
  - docs/workflow_model/v0.2/PHASE5_consultation_record_survey_v0.2.md
max_attempts: 2
result_expected_filename: W-20260624-190_RESULT.md
---

# Task — Phase5 相談記録ソース(Google Calendar/Docs) read-only 実査

発注元: `docs/workflow_model/REQUEST_v0.2.md`。前提方針 = Box正本/SF制御塔/自然発生データ優先/Raw・Canonical・Derived分離。一次根拠 = `ALO_OWNER_GRILL_ANSWERS_v0.1.md` の G-14(相談記録=Notta+手打ちGoogleDoc+カレンダー紐付け事件メモGoogleDoc)。

## 接続
- Google Calendar MCP / Google Drive MCP（いずれも owner の Google Workspace、read-only）。
- Notta は未接続 → 議事録由来は「未接続=未測定」と明示し、推測で埋めない。

## やること（read-only・PII非転載）
1. **カレンダー実査**: 相談に該当する予定を抽出し、件数・タイトルの様式(命名規則。クライアント名等は**マスク**して様式だけ)・参加者数の分布・予定本文や添付に**事件メモGoogleDocへのリンク**が含まれるか、を集計。日付レンジ。
2. **Google Docs実査**: 事件メモ/相談メモに該当するDocを metadata 中心に把握(検索・命名様式・件数・更新日・所有者種別)。本文は原則開かない。構造把握に必要でも**内容は転載しない**(章立て有無等の構造のみ)。
3. **紐付け方式の特定**: カレンダー予定 → 事件メモGoogleDoc の結合が「予定本文中のリンク/添付ファイル/命名規則の一致」のどれで成立しているかを判定し、結合キー候補(event_id ↔ doc_id 等)を提示。
4. **受任シグナルの観測可否**: カレンダー/Docs 側から受任(委任契約・受任通知)の兆候が観測できるか/できないか(できないなら Gmail/Box/SF 側に依存、と明示)。
5. **合成設計メモ**: 相談記録(Consultation record)を Notta議事録(未接続)+手打ちメモ+事件メモ から合成する最小設計(どのキーで束ね、どれをCanonical/Derivedにするか)。Raw・Canonical・Derived分離に沿う。

## Do Not（§2/§7）
- カレンダー/Driveへ書き込まない・予定/ファイルを作成変更削除しない。
- **相談メモ本文(秘匿特権)を転載しない**。氏名・事件内容・金額を成果物に書かない。集計・構造・マスク様式のみ。
- 実物を見ずに一般論で埋めない。未接続(Notta)・未確認は明示。AI推定を人間判断にしない。

## 完了処理
RESULT を `done/W-20260624-190_RESULT.md`、1行目 `WORKER_PASS`(exit_criteria充足。データに届かなければ blocked/ に WORKER_BLOCKED で接続要求を明記)。worker_task_id 記載。
司令塔への戻り値: (a)PASS/BLOCKED (b)成果物パス (c)接続実体(Calendar/Docsに到達したか) (d)read-only自己宣言(書込系未呼出) (e)相談予定件数・事件メモDoc件数・紐付け方式 (f)受任シグナル観測可否 (g)合成設計の要点と残課題(Notta未接続等)。本文全文・PII本文は貼らない。
