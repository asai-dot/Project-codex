# DD-LITID D0 — Decision & Evidence 契約 v0.1（Q1/Q2 含む）

- 作成日: 2026-06-20
- 位置づけ: FORWARD_ROADMAP v0.3 §WS-D D0 ＋ WS-Q Q1/Q2 の設計契約。read-only 設計のみ（実装/DB書込なし）。
- 監査根拠: v0.3 RESULT residual_gaps #4(adjudication family) / #5(D0 event contract)、must_fix #6。
- 用語(監査 #7): identity の確定層は **`accepted_identity_state`（= canonical identity layer）** と呼ぶ。
  語彙 "hub" は使わない。NDL 索引は **L1 derived**（hub ではない）。

## 0. 層（再掲・固定）

```
L0 NDL dump snapshot + manifest + hashes           （原本・不変）
L1 derived offline blocking/index artifact (R2)     （discardable / rebuildable）
L2 assertion: "<source> says X" + source row pointer
Resolution: decision + evidence_bundle + adjudication（本契約）
accepted_identity_state: Resolution gate 通過後のみ（WS-E, HOLD）
```

## 1. decision event（append-only・silent mutation 禁止）

状態は**行更新でなくイベント追記**で表す。最新状態は event の畳み込みで導出。

### 1-1. status 語彙（state machine）

```
candidate    : 候補生成された（retrieval のみ。正誤未判定）
verified     : adjudication で正と裁定（decision_type 単位）
rejected     : adjudication で否
superseded   : 後続 decision に置換（旧は残す）
revoked      : 誤りと判明し取消
re_evaluated : 再評価イベント（snapshot/ルール変更起因）
abstain      : 証拠不足で判定保留 → manual_review_queue
```

許可遷移: `candidate→{verified,rejected,abstain}` / `verified→{superseded,revoked,re_evaluated}` /
`rejected→{re_evaluated}` / `abstain→{verified,rejected}`。**verified→（無言で)candidate へ戻す等は禁止**（必ず revoke/re_evaluate イベント）。

### 1-2. decision_event スキーマ

```text
event_id            : uuid
subject_ref         : 対象（例 holding_id / source_record_id / bib_id）
decision_type       : work | edition_manifestation | printing | holding_to_edition
target_ref          : 紐付け先候補（例 ndl_bib_id / edition_key）  ※candidate時は候補
event_type          : candidate | verified | rejected | superseded | revoked | re_evaluated | abstain
prev_event_id       : 直前 event（連鎖。初回 null）
evidence_bundle_id  : 根拠（§2）
basis_summary       : 判定根拠の要約
confidence          : 数値 or ラベル（profile 準拠）
decided_by          : adjudicator（人/ルール名+version）
decided_at          : timestamp
snapshot_id         : 評価時の source snapshot（再現性）
rule_version        : 適用したマッチ/裁定ルールの version
write_authorization : false（本契約段では常に false）
```

- **不変条件**: event は更新・削除しない。訂正は新 event。`accepted_identity_state` は verified かつ Q5 gate 通過時のみ派生（本段 HOLD）。

## 2. evidence_bundle と family collapse（Q1/Q2）

### 2-1. evidence_item スキーマ

```text
evidence_id
evidence_family    : NDL | publisher | colophon | legallib_provider | LION_catalog | self_scan_metadata | manual_review
origin_family      : 実際の出所系（転載元）。NDL転載は origin_family=NDL
same_origin_collapse_key : 同一出所をまとめるキー
capture_url
content_hash
parser_lineage     : parser/normalizer version 連鎖
source_snapshot_id
raw_pointer        : source_file + row/record_key
```

### 2-2. independence ルール（循環・二重計上の禁止）

- **同一 `origin_family` / 同一 `same_origin_collapse_key` の証拠は1つに collapse**（独立2証拠に数えない）。
- 具体 fixture（監査指定）:
  - **奥付画像 と そのOCR = 1証拠**（OCRは画像の派生表現。同一 origin に collapse）。
  - **出版社情報が NDL/vendor 由来の転載 = NDL/vendor と同一 family に collapse**。
  - NDL レコード内の複数フィールド（出版年＋版表示）= 1証拠。
- **confirm 条件**: decision_type ごとに「**異なる origin_family の独立証拠 ≥ 2**」かつ Q5 gate。
- **gold への流用禁止**: candidate 生成に使った source（特に NDL 索引 R2）を、同一 subject の正解ラベルに使わない（非循環＝Q1）。

### 2-3. adjudication record（Q1・人手裁定）

```text
adjudication_id / subject_ref / decision_type
reviewer / basis (colophon_image | physical | publisher_primary | ...)
source_hash / decision (verified|rejected|abstain) / confidence / decided_at
evidence_bundle_id
```
- adjudication の basis は **NDL と独立**な情報（奥付/現物/出版社一次）に限る。NDL は候補側。

## 3. この契約が止めるもの（HOLD 再確認）
- accepted_identity_state への昇格 / DB write / DDL / backfill / production matcher / promote / serving / embedding / 外部公開。
- R2 索引を truth 扱いすること。既存 ndl_bib_id の verified 一括化。

## 4. 次段
- Q3/Q4（confusion buckets・数値 sample plan）・Q5（decision table）と接続（別 doc）。
- D1 較正は本契約 fixture を入力に設計（較正実行・閾値 freeze は別 gate, HOLD）。
