---
worker_task_id: W-20260624-180
status: queued
priority: P0
owner: claude-code-worker
created_at: 2026-06-24
request: docs/workflow_model/REQUEST_v0.2.md
poc: PoC1
goal: 浅井先生のグリル20問回答(ALO_OWNER_GRILL_ANSWERS_v0.1.md)を v0.2 モデルへ反映する。決定ログをowner裁定で更新、状態機械を7本で確定、人間ゲートを3マストで確定、新データ源(Notta/GoogleDocs/Calendar/MoneyForward/Chatworkタスク)をデータ源台帳・catalogへ追加、相談票/終了報告書の「専用様式なし」をライフサイクルへ反映。
mode: implementation
requires_systems:
  - repo
depends_on:
  - W-20260624-130
  - W-20260624-150
allowed_paths:
  - docs/workflow_model/v0.2/
allowed_actions:
  - edit_files
  - write deliverable
forbidden_actions:
  - production_db_write
  - salesforce_write
  - box_write_move_rename_delete
  - file_move_rename_delete
  - ai_estimate_as_human_decision
  - pii_in_general_artifact
  - raw_source_mutation
  - human_gate_bypass
  - fill_unknown_with_generalities
  - overwrite_decided_log
exit_criteria:
  - 決定ログ D-001..014 に owner 裁定(確定/修正/根拠=G-xx)が反映され、追記は新IDで行う(上書き禁止)
  - 状態機械が7本(納品・期限独立)で確定し pending(owner_grill) が解消
  - 人間必須ゲートが3マストで確定
  - 新データ源(Notta/GoogleDocs/Calendar/MoneyForward/Chatworkタスク)がデータ源台帳とcatalogに接続状態付きで載る
  - 相談票/終了報告書が「専用様式なし・実体は分散ソース/成果物・報酬通知」で反映
  - RESULT を done/ または blocked/ に書く
  - 成果物は docs/workflow_model/v0.2/ 配下のみ
deliverables:
  - docs/workflow_model/v0.2/ledger_v0.2/09_decision_log.csv (追記更新)
  - docs/workflow_model/v0.2/ALO_WORKFLOW_CATALOG_v0.2.yaml (states/human_gates/systems/metrics をowner確定で更新)
  - docs/workflow_model/v0.2/PHASE4_owner_decisions_applied_v0.2.md (反映サマリ・新規)
max_attempts: 2
result_expected_filename: W-20260624-180_RESULT.md
---

# Task — Phase4: owner グリル回答の v0.2 反映

発注元: `docs/workflow_model/REQUEST_v0.2.md`。一次入力 = `docs/workflow_model/v0.2/ALO_OWNER_GRILL_ANSWERS_v0.1.md`（浅井先生の確定裁定）。

## やること
1. **決定ログ反映**(`ledger_v0.2/09_decision_log.csv`): D-001〜D-014 を owner 裁定で「確定/修正」に更新（status列等。**本文は上書きせず**、決定内容・根拠 G-xx を追記列/新Decision行で表現）。グリルで新規に確定した事項は D-022 以降で追記。append-only 厳守。
2. **状態機械**(catalog `states`/`transitions` ＋ ledger `06_state_transitions.csv`): **7本で確定**（Consultation/Matter/WorkItem/Document/Finance + Delivery独立 + Deadline独立）。`pending: owner_grill (G-05)` を解消し confirmed に。**2段クローズ**(①法的終了/②事務クローズ完了)を Matter/Finance/Document の終端として表現。
3. **人間ゲート**(catalog `human_gates`): **3マスト**＝①利益相反 ②対外文書の最終送付(最終品質チェック) ③金銭の確定(報酬確定・預り金精算・振替) を required=true。受任成立・終結は optional gate として保持。
4. **新データ源**(catalog `systems`/`triggers` ＋ ledger `03_data_sources.csv`): 追加＝Notta(議事録/未接続)・GoogleDocs(手打ちメモ/接続あり)・GoogleCalendar(相談予定/接続あり)・MoneyForward(会計/未接続)・銀行通帳(入金の正/源泉)・Chatworkタスク(担当・期限→WorkItem対応)。各に接続状態と主キー/結合キー(分かる範囲)を付す。
5. **相談記録の正本再定義**(ledger `04_documents.csv` ＋ catalog `documents`): 「相談票」専用様式は**無い**→ 相談記録 = Notta議事録 + GoogleDoc手打ちメモ + Calendar紐付け の**合成**。「業務終了報告書」専用様式は**無い**→ 成果物 or 報酬請求通知が兼ねる。Box-U1/U2 を解消済みとして記録。
6. **受任・入金の確定ロジック**: 受任=複数シグナル合成(委任状/契約書受領[Box最強]・SF相談→受任切替・受任通知発送)で observed を確定し declared と突合(G-04)。入金=銀行通帳を正に MoneyForward 突合。05_events / 07_sf_mapping に反映。
7. **失注理由を enum 化**: ①当方お断り ②先方失注/離脱 ③受任に至らず ④その他。流入経路は必須〜準必須。metrics(失注理由未入力率/流入経路不明率) の取得方法に反映。
8. **AI境界**(G-19): AI出力は常に「推定」、人間承認でのみ確定。Derived層の規約として明記。
9. **反映サマリ** `PHASE4_owner_decisions_applied_v0.2.md` 新規: 何をどのファイルにどう反映したか、未解消(要確認: 事件ウェブの最終確認、Notta/MF未接続)、次アクション。

## 厳守事項
- 決定ログ等の既存確定記録を**上書きしない**（追記のみ。修正は新ID or status列）。
- owner 裁定(確定)と、worker の推論/未確認を**混同しない**。各反映に根拠 G-xx を付す。
- 仮説で埋めない。未接続(Notta/MF)由来の値は「未接続=未測定」と明示。
- PII を書かない。**git操作なし**。成果物は docs/workflow_model/v0.2/ 配下のみ。

## 完了処理
RESULT を `done/W-20260624-180_RESULT.md`、1行目 `WORKER_PASS`（exit_criteria 充足）。CSV/YAML がパース可能か自己確認。worker_task_id 記載。
司令塔への戻り値: (a)PASS/BLOCKED (b)成果物パス (c)決定ログに反映/追記したID一覧 (d)状態機械7本・人間ゲート3マストの確定可否 (e)追加データ源の件数と接続状態内訳 (f)残・要確認 (g)次サイクル提案。
