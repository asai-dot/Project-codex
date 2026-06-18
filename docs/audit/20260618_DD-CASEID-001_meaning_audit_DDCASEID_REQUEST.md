DDCASEID_REQUEST

---
request_id: 20260618_DD-CASEID-001_meaning_audit
gate: DDCASEID
audit_type: independent_meaning_audit (design DD)
requester: ALO / Codex (Project-codex session, owner 浅井)
request_date_jst: 2026-06-18
audited_artifact: DD-CASEID-001 candidate v0.1 (Box 2266457039407) + 31b_case_id_resolution_flow.md (Box 2264249368602)
result_expected_filename: 20260618_DD-CASEID-001_meaning_audit_DDCASEID_RESULT.md
execution_scope: design/meaning audit only — no implementation, no DDL, no DB write, no canonical case mint, no alo_edges write, no reviewed=true, no claim_support, no MCP/vector serve, no source mutation
---

## 0. 依頼の要旨

判例オブジェクトの中核設計 **DD-CASEID-001（判例ID確定システム）** を `_accepted_v1.0` へ昇格させる前提として、GPT Pro お目付け役の **独立意味監査**を依頼する。

オーナー（浅井）は本DDの前提設計 A–D に既に同意済み（2026-06-18）であり、**「accept前に意味監査を回す」**を明示的に選択した。本依頼はその意味監査である。

本依頼は実装GOを求めるものではない。監査が PASS でも、許されるのは設計確定（design accept → owner ratify）までで、DDL・DB write・canonical mint・alo_edges・claim_support・MCP serve は引き続き HOLD。

## 1. 背景

- DD-CASEID-001 は candidate v0.1（起票 2026-06-04）。机上検証（deterministic_self_verification）は **done**、independent_meaning_audit と owner_approval が **pending** のまま凍結されていた。
- このDDは「2つのメタ（NII判例RDF/TTL × D1KOS体系目次）× 個別データ（D1-Law × LIC）」を1 case_keyに名寄せする噛み合わせの体系を定義する。判例オブジェクトのクリティカルパス最上流（G1）。
- 確定済み前提思想（オーナー 2026-06-04 確定、A–D で再同意）: **「判例の特定（自然キー forum_code+判決日+case_number_norm）」と「事務所のID確定（名寄せ・採番 case_key）」は別レイヤである。**

## 2. 監査対象

- `DD-CASEID-001`（Box file_id 2266457039407）— 決定6項目 / why・alternatives_rejected / downstream / verification / 未決
- `31b_case_id_resolution_flow.md`（Box file_id 2264249368602）— ID確定フロー実装仕様（テーブル、S0–S5アルゴリズム、Tier A/B/C、品質ゲート9種）

## 3. 重要なHOLD（監査でも維持を確認してほしい）

次は本DDの accept でも禁止のまま：

- production / staging DB load、schema migration / DDL
- canonical case 行の作成、`alo_edges` write、`reviewed=true`、claim_support
- `case_observation` / `alo_forum_registry` 実テーブルの本番作成
- 商用ソース本文の外部送信、source / Box mutation（本監査の往復を除く）

`DDCASEID_PASS` は「設計確定GO」であって「実装GO」ではない。

## 4. GPTに見てほしい焦点（意味監査）

### A. レイヤ分離の妥当性
「特定（自然キー）」と「ID確定（case_key名寄せ）」を別レイヤにする設計は、(1)全件に公式番号が振られない/遡及しない、(2)匿名・未公開・受任・OCR崩れ、(3)商用が拾えない準司法（審判・裁決・答申・ADR）、(4)機関横断連鎖（答申↔取消訴訟判決・審級）、(5)源別 content_grade/license——の5点を本当に取りこぼさず収容できているか。分離しすぎ/足りない点はないか。

### B. case_key(ULID不変) anchor
case_key は採番後不変、canonical_uri は確定時のみ確定値（provisional→confirmed昇格で case_key不変・canonical_uri可変）という設計は、参照整合性・監査証跡・merge耐性の観点で安全か。ULID採用（serial連番でなく）の判断は妥当か。

### C. forum_code 一般化
court_code → forum_code（裁判所＋審判/審査会/ADR/仲裁/行政庁）への一般化は、31既存の case_type（judicial/adr/conciliation/adjudication）と矛盾なく整合するか。後方互換（court_code は forum_type='court' 部分集合、VIEW `v_cases_legacy_court` で温存、migration note必須）は十分か。

### D. 名寄せ Tier 境界（自動/人手）
S1決定的自然キー一致→S2強外部ID一致→S3 fuzzy→S4/S5採番、の固定順と Tier A/B/C 境界（A=強外部ID＋機関＋言渡日一致 or 自然キー完全一致のみ機械可、B=初回人手、C=auto禁止）は、**誤統合（false merge）と誤分離（false split）**を防ぐのに過不足ないか。特に「強外部ID単独でのbind禁止（ID＋裁判所＋日時の整合必須）」は妥当か。

### E. 連鎖の merge 禁止
審級・答申↔取消訴訟判決を **merge禁止**（別case_keyのまま `alo_edges` relative_resolved / origin_decision でlink）とする設計は、「同一事件性」概念と矛盾しないか。別caseにする境界（別の判断＝別case）は実務上妥当か。

### F. content_grade と受任案件(jufu)の隔離
源別 content_grade（full/summary/stats_only）と、受任案件の手元判決（jufu＝事実として最強だが非公開）を「identity確定には使うが配布面で隔離」する設計は、機密・ライセンス・利益相反の観点で安全か。

### G. DD-CASE-001(cases母型)との reconcile
本DDの確定フローが DD-CASE-001（cases母型・準司法ワークストリーム）の上に乗る／重複排除する関係は、責務境界として明確か（オーナーは本reconcileメモ=S2をaccept条件に含めることに同意済み）。

### H. 初回実投入の誤統合リスク
初回流し込み **NII 65,855 ＋ D1 ≈192,885**（※D1は訂正後の実取得値。旧資料の67,966/27%は2026-06-01のstale値で、6/5 ingest後の実態は約192,885件・77%）を、fingerprint（saikosai_id 6桁 / d1law_id 8桁）＋自然キーで名寄せする計画は、机上検証で実証済みの **NII∩D1 norm一致 12,661件** を踏まえ、誤統合リスクを管理できているか。残りの非一致をどう安全に扱うべきか。

## 5. 参考情報（Boxで確認済みの事実）

| source | fact |
|---|---|
| DD-CASEID-001 §4 | deterministic_self_verification=done: case_number_norm解析率 NII 100.00%(65,853/65,855) / D1 99.94%(68,099/68,141)、NII∩D1 norm一致 12,661、forum未マップ0で123コード、fixture pass |
| 31b §8 | 品質ゲート9種（gate_case_has_observation / confirmed_uri_consistent / provisional_uri_form / natural_key_dup / fp_collision / observation_source_id_dup / merged_target_exists / resolution_logged / provisional_has_review）すべて目標0 |
| D1 ingest log 20260605 / acquired_hanrei_ids_20260605.txt | D1取得 ≈192,885 distinct（68,080 + 6/5 NEW 124,805、txt 1,928,850B÷10で二経路一致）。母数249,863（民事セレクション）に対し ≈77% |
| 31_case_layer.md / 35_link_layer.md | cases自然キー / fingerprints / resolution_log の既存スキーマを再利用（新設最小化） |

商用ソース本文・生引用本文は同梱しない。監査対象は設計の意味・境界・整合・誤統合耐性である。

## 6. 判定ラベル

先頭行は必ずラベルのみ：

- `DDCASEID_PASS`
- `DDCASEID_PASS_WITH_NOTES`
- `DDCASEID_MODIFY_REQUIRED`
- `DDCASEID_NEED_MORE`
- `DDCASEID_REJECT`

本文は通常のGPT監査形式で、`source_request_file_id`, `reviewed_at_jst`, `reviewer`, `gate`, `scope`, `execution_scope`, `verdict` を置き、続けて `## 0. 総合判定`, `## 1. Findings`(A–H各論点), `## 2. must_fix`, `## 3. should_fix`, `## 4. GO / HOLD`, `## 5. final` を書いてほしい。

## 7. GO / HOLD の期待

`DDCASEID_PASS` / `PASS_WITH_NOTES`（blocking無）の場合の GO は次だけ：

- DD-CASEID-001 を `_accepted_v1.0`（または `_accepted_v1.0_with_notes`）へ design accept（owner ratify 経由）
- DD-CASE-001 reconcile メモ（S2）の起票
- 下位DD（CASEID-002 符号正規化等）の着手根拠化

HOLD は維持：

- DDL / DB write / migration
- canonical case 作成 / `alo_edges` / `reviewed=true` / claim_support
- 実テーブル本番作成 / MCP / vector serve / source mutation
