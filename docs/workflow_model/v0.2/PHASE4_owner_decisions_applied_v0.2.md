# Phase4 — owner グリル回答の v0.2 反映サマリ

- worker_task_id: W-20260624-180
- generated_at: 2026-06-24
- 一次入力（裁定＝最優先の真実）: `docs/workflow_model/v0.2/ALO_OWNER_GRILL_ANSWERS_v0.1.md`（浅井先生 20問への確定回答 G-01..G-20）
- 方針: 既存確定記録は上書きせず（決定ログは追記/status更新のみ）。owner裁定と worker推論を混同せず、各反映に根拠 G-xx を付した。未接続(Notta/MF/銀行通帳取込)由来は「未接続＝未測定」と明示。PII不記載。git操作なし。

## 1. 反映先ファイルと内容

### 決定ログ `ledger_v0.2/09_decision_log.csv`（append-only）
- D-001..D-014: 決定文は保持したまま status列を「未決→確定(owner裁定 G-xx W-180)」へ更新。7本化/3マスト/2段クローズ/4点必須/終了報告判定など修正点は status列に「確定→修正:…（詳細D-0xx）」と注記し、本文は消さず新IDへ委譲。
- D-021: U1..U5 を「確定(owner裁定で全解消)」へ更新。
- 新規追記 D-022..D-033（owner裁定 12件）:
  - D-022 状態機械7本確定(G-05) / D-023 人間ゲート3マスト(G-06) / D-024 2段クローズ(G-09)
  - D-025 新データ源確定(G-08/G-11/G-14) / D-026 相談票=合成(G-14) / D-027 終了報告書=成果物or報酬通知(G-15)
  - D-028 受任=複数シグナル合成+突合(G-11/G-04) / D-029 入金=通帳が正+MF突合(G-11)
  - D-030 失注理由enum+流入経路必須〜準必須(G-12) / D-031 AI出力は常に推定(G-19)
  - D-032 ~BROMIUMスコープ外(G-18) / D-033 期限正本=SF・多重チェック(G-20)

### データ源台帳 `ledger_v0.2/03_data_sources.csv`
- DS-013 Notta（相談記録ソース／**未接続**＝未測定／C1）
- DS-014 GoogleCalendar（相談予定紐付け＝相談記録ソース／**接続あり**＝実査可。「事件ウェブ」≈Calendar予定と解釈・要最終確認）
- DS-015/DS-016 MoneyForward（**未接続**＝未測定／C1。入金の正はDS-024、MFは突合先）
- DS-020 GoogleDocs（弁護士手打ち相談メモ＝相談記録ソース／**接続あり**＝実査可）
- 新規 DS-023 Chatworkタスク（担当・期限→WorkItem対応／到達）
- 新規 DS-024 銀行通帳（入金の真実の源＝正本／取込未接続＝未測定）

### カタログ `ALO_WORKFLOW_CATALOG_v0.2.yaml`
- `states`: 7機械を confirmed 化（SM-consultation/matter/work_item/document/finance + **SM-delivery** + **SM-deadline**）。`pending: owner_grill` 解消。`two_stage_close`（①法的終了／②事務クローズ完了=原本返却・預り金ゼロ・報酬確定、順序付き）を追加。`declared_observed_split` を confirmed 化(G-04)。
- `human_gates`: `mandatory_count: 3`＋`mandatory`配列（①利益相反 ②対外文書最終送付＝最終品質チェック ③金銭の確定）。HG-01/HG-04/HG-05/HG-06 を required=true、HG-02(受任成立)/HG-03(重要方針)/HG-07(終結) を optional。close_gate を2段クローズ・終了報告判定で更新。
- `systems`: DS-013/014/015/016/020 に connection/measured/needed_connector を付与、DS-023/024 を追加。新トップキー `data_source_owner_decisions`（相談記録合成 / 新データ源接続内訳）。
- `documents`: DOC-box-04 相談票＝専用様式なし→合成(G-14/U1解消)、DOC-box-10 終了報告書＝成果物or報酬通知(G-15/U2解消)、DOC-box-11 ~BROMIUM スコープ外(G-18/U4解消)。`layering` を3層 confirmed(G-16)。
- `work_items`: G-08 の4点必須（担当/期限/案件/次アクション）＋Chatworkタスク対応(DS-023)。
- `deliveries`/`finance_events`: Delivery独立機械 confirmed、client/payer分離 confirmed(G-10)、入金の正＝銀行通帳(payment_master, G-11)。
- `evidence_types.provenance_model.ai_boundary_rule`: AI出力は常に ai_estimated、人間承認でも確定昇格しない（Derived層規約, G-19/D-031）。
- `metrics`: 失注理由enum・流入経路必須〜準必須を定義確定。KPI-P1-06/07 を confirmed_definition（現状値は SF/コネクタ接続後＝未測定）。
- `decisions` catalog: D-001..014 を confirmed 化＋D-022..033 を追記（計26件）。

### 状態遷移/イベント/SFマッピング ledger
- `06_state_transitions.csv`: Matter closing→closed を2段クローズ表現、Finance reconciled=金銭の確定、Delivery/Deadline 行を「未確認(pending)」→「確定(owner裁定 7本化)」へ更新。
- `05_events.csv`: engagement_signed=複数シグナル合成→declared突合(optional gate)、invoice_sent/payment_received/deliverable_sent をマスト3点・入金の正(通帳)へ更新。
- `07_sf_mapping.csv`: 流入経路(必須〜準必須)・失注理由(enum)・Deadline(正本=SF)・変換関係(受任=複数シグナル突合) を確定。

## 2. exit_criteria 充足

| criteria | 結果 |
|---|---|
| 決定ログ D-001..014 に owner裁定(確定/根拠G-xx)反映・追記は新ID(上書き禁止) | OK（status更新＋D-022..033追記、本文保持） |
| 状態機械7本確定・pending(owner_grill)解消 | OK（machine_count:7、SM-delivery/SM-deadline confirmed） |
| 人間必須ゲート3マスト確定 | OK（mandatory_count:3、HG-01/04/05+06、受任/終結はoptional） |
| 新データ源がデータ源台帳・catalogに接続状態付きで載る | OK（DS-013/014/015/016/020 更新＋DS-023/024 追加） |
| 相談票/終了報告書=専用様式なし反映(U1/U2解消) | OK（DOC-box-04/10、04_documents、D-026/027） |
| RESULT を done/ に記載 | OK |
| 成果物は docs/workflow_model/v0.2/ 配下のみ | OK |

CSV は csv.reader、YAML は yaml.safe_load でパース確認済（列不整合 0、YAML top-level 健全）。

## 3. 残・要確認
- **「事件ウェブ」**＝GoogleCalendar予定に紐づく相談情報、との解釈は **要・最終確認**（owner裁定の派生注記）。
- **Notta / MoneyForward / 銀行通帳取込が未接続**＝未測定。相談実施区間（Notta）と入金消込確定（MF/通帳）の機械化には接続が前提。次コネクタ C1 = Notta / MoneyForward。
- **SF実査(W-20260624-110) はコネクタ不在で未観測**継続。入力率系 KPI（流入経路不明率/失注理由未入力率/各時間KPI）は定義のみ確定、現状値は SF接続後に算出。
- SFスキーマ拡張（流入経路/失注理由enum/個別日付/担当列/WorkItem別表/Deadline別表）は b_addfield・c_newtable として設計判断待ち（07_sf_mapping、Q2/Q3/Q4）。
- Chatworkタスク粒度の取込可否（DS-023）は要確認。
- BROMIUM の確証は不要（owner が推定で可と判断、D-032）。

## 4. 次サイクル提案
1. コネクタ C1 整備（Notta議事録／MoneyForward会計／銀行通帳取込）→ 相談記録の完全合成（Calendar+GoogleDoc+Notta）と入金消込確定の機械化。
2. SF実査(W-110)の再起動＝ETL/コネクタ。確定済の定義(7本/3マスト/enum)に対し現状入力率を実測しKPI初期値を確定。
3. SFスキーマ拡張設計票（流入経路/失注理由enum/個別日付/担当/WorkItem別表/Deadline別表/client・payer分離）の起案（c_newtable/b_addfield の実装定義）。
4. 「事件ウェブ」定義の最終確認（owner 1問）。
5. PoC1（相談→受任ファネル）の実装着手：相談記録合成（接続済のCalendar+GoogleDocから先行）＋受任=複数シグナル合成の突合ロジック（observed↔declared）。
