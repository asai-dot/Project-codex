# DD-CASEID-001 — 判例ID確定システム（特定とID確定の分離・自然キー＋名寄せ採番） **accepted v1.0_with_notes**

- 起票日時: 2026-06-04 JST ／ **accept(ratify)日時: 2026-06-19 JST（浅井さん ratify）**
- lifecycle: candidate v0.1 → **`_accepted_v1.0_with_notes`**（GPT Pro 独立意味監査 `DDCASEID_PASS_WITH_NOTES`／blocking無 → owner ratify 経由）
- 監査: `20260618_DD-CASEID-001_meaning_audit_DDCASEID_RESULT.md`（Box 2294753110991, 2026-06-19）
- reconcile 前提資料: `DD-CASE-001_DDCASEID_reconcile_20260618.md`（不変則 N-1〜N-4）
- domain: CASEID（判例ID確定 / ALOナレッジDB 判例レイヤ SPEC-02拡張）
- 実装仕様（下位）: `31b_case_id_resolution_flow.md`（フロー）/ `31c_case_number_norm_spec.md`（符号正規化）/ `31d_forum_code_registry_spec.md`（機関コード）
- parent: `31_case_layer.md`(SPEC-02 v1.4) / `35_link_layer.md`
- related: `DD-CASE-001`(judicial cases母型／要field-level reconcile) / `DD-DYNDB-CASES-001`(受任案件master＝**別オブジェクト**, 衝突なし) / `DDCASESOURCE`(準司法・機密一次所有)

> **本書は accepted 正本**。candidate v0.1（Box 2266457039407）の決定を据え置き、監査 accept-notes と reconcile 不変則を付した版。DESIGN-01 登録簿 / DD_REGISTRY.json / `_AUDIT_LEDGER.jsonl` への登録は Mac CC 単一書き手で実施（本リモートはマウント無のため §末尾の残務参照）。

---

## 0. スコープと確定済み設計思想

判例の **特定**（自然キー `forum_code + 判決日 + case_number_norm`）と、事務所の **判例ID確定**（複数源・未公開・匿名版・準司法・受任案件を1本に名寄せし安定IDを採番する行為）は **別レイヤ**である。自然キーでは特定はできても **ID確定には足りない**——浅井さん確定の前提（2026-06-04）。本DDはそれを実装粒度に落とす。

オーナー同意（2026-06-18, A–D）＋ GPT Pro 意味監査（2026-06-19, PASS_WITH_NOTES）＋ owner ratify（2026-06-19）により accepted。

## 1. 決定（candidate から据え置き）

1. **firm `case_key`(ULID, 採番後不変)** を事務所IDの anchor とする。`canonical_uri`(自然キー文字列)は `identity_status=confirmed` の時のみ確定値、不能時は provisional URI `alo:case:jp:_prov:{case_key}`。
2. 機関コードは `court_code` → **`forum_code`**（`alo_forum_registry`、裁判所＋審判/審査会/ADR/仲裁/行政庁）へ一般化。`fn_generate_case_uri_v2(forum_code, decision_date, case_number_norm)`、v1据置。
3. **`case_number_norm`** は事件符号を**かな/漢字のまま保持**する正準形 `{ERA}{year}-{符号}-{number}`（ローマ字化しない）。
4. 全入力は **`case_observation`**（源別の生同一性レコード、content_grade full/summary/stats_only 付）に着地。名寄せは **決定的自然キー → 強外部ID → fuzzy → 人手** の順、全決定を `resolution_log` に記録（35層 fingerprints/decision_external_ids 再利用）。Tier A/B/C は ID＋裁判所＋日時準拠。
5. 自然キー不能（匿名/未公開/受任/OCR崩れ）は **provisional 採番＋人手で confirmed 昇格**（case_key不変）。
6. 機関横断の連鎖（審級 / 答申↔取消訴訟判決）は **merge禁止・`alo_edges` link**（relative_resolved / origin_decision）で表現。

## 1.5 Accept-notes（ratify時に確定・必須明記）★accepted版で追加

監査 must_fix（blocking無・accept note 必須）と reconcile 不変則を本文則に格上げ：

- **AN-1**: `case_key ≠ canonical_uri ≠ natural_key`。case_key=内部surrogate不変anchor（法的・文献的意味を持たせない純surrogate）／canonical_uri=外部表示・解決名（可変）／natural_key=観測属性。
- **AN-2**: **merge禁止原則**＝「別判断＝別case_key、関係は edge」。審級・原処分・取消訴訟・答申・ADRは同一事件性があっても別case_key（`appeal_of`/`review_of`/`annuls`/`remands`/`origin_decision`/`relative_resolved`）。merge は最終手段、case_key廃止でなく **tombstone / superseded_by**。
- **AN-3**: **jufu（受任手元判決）**は identity evidence には使えるが、**claim_support / MCP / export は全面不可**（出口機密は DDCASESOURCE が一次所有）。
- **AN-4**: **初回投入は false merge を最も警戒**（false split より危険）。NII∩D1 一致 12,661 を「正解」と過信せず、非一致・片側・番号崩れ・表記揺れは **Tier B/C へ逃がし、初期は split 寄り**。Tier A 自動bind は高信頼サブセットの少量から。
- **AN-5**: 本 accept は **設計確定のみ**。**DDL / DB write / canonical case mint / alo_edges / reviewed=true / claim_support / MCP・vector serve / source mutation / jufu出口利用は HOLD**（G2 production-readiness gate で別審査）。

### reconcile 不変則（`DD-CASE-001_DDCASEID_reconcile` より）
- **N-1**: `case_key`(判例) と `alo_matter_id`(受任案件 `alo:matter:`) は別オブジェクト。相互代入・FK・混在禁止。
- **N-2**: `case_type` 定義 = DD-CASE-001 ／ `forum_code` registry = 本DD。CASEID は case_type を新規定義しない（参照・整合のみ）。
- **N-3**: 機密・配布可否 = DDCASESOURCE が一次所有。本DDの `content_grade` は identity 観測限定、配布判断しない。
- **N-4**: 本DD=「ID確定の上流機能」、DD-CASE-001=「判例ノードのエンティティ母型」。重ねない。

## 2. why / alternatives_rejected（据え置き）

- **why**: 自然キーは特定できても (a)全件に公式番号が振られず遡及しない、(b)匿名/未公開/受任は自然キーを作れない、(c)差別化は商用が拾えない準司法・在野にある、(d)同一事案が機関をまたいで連鎖する——ため、ID確定は別途の名寄せ・採番レイヤを要する。
- **rejected**: D1/最高裁番号を主キー化（全件付与・遡及せず、源依存で不版不能）／自然キーのみ（匿名・未公開・準司法・名寄せ取りこぼし）／商用依存（準司法・在野・受任を覆えない）／符号ローマ字化（同字異義と長い裾で対応表不完全→dedup破壊）。

## 3. downstream_effect / 初回流し込み（据え置き＋訂正）

- 新設 `alo_forum_registry` / `case_observation`、`cases` 拡張（case_key / forum_code / identity_status / merged_into_case_key）、`fn_generate_case_uri_v2`。`ck_cases_canonical_uri_consistent` 条件化＝**migration note 必須**。
- 初回流し込み: **NII 65,855 ＋ D1 ≈192,885**（※D1訂正後の実取得。旧67,966/27%は2026-06-01 stale、6/5 ingest後≈192,885/77%）を fingerprint（saikosai_id 6桁 / d1law_id 8桁）＋自然キーで名寄せ。種 `forum_registry_seed.csv`(123 forum_code)。**実投入は G2 経由・少量から（AN-4）**。

## 4. verification（昇格3条件＝すべて充足）

- **deterministic_self_verification = done**: case_number_norm 解析率 NII 100.00%(65,853/65,855) / D1 99.94%(68,099/68,141)、NII∩D1 norm一致 **12,661**、forum未マップ0で123コード、fixture pass。
- **independent_meaning_audit = PASS_WITH_NOTES（2026-06-19, GPT Pro）**: blocking無、accept-notes 5点（→§1.5）。
- **owner_approval = ratified（2026-06-19, 浅井さん）**。

## 5. follow-up（accept後の課題）

- **should_fix（監査）**: ①Tier B/C レビュー最低表示項目（裁判所表記/日付/事件番号/外部ID/source_system/content_grade）→ `CASE_HUMAN_REVIEW_SAMPLE_FRAME` 反映。②`resolution_log` に decision_basis/evidence_observation_ids/decided_by/decided_at/supersedes_resolution_id。③tombstone/superseded_by 化。④forum registry に forum_type/jurisdiction_scope/source_basis/valid_from-to。⑤fuzzy は review queue 生成限定。
- **reconcile 残**: DD-CASE-001（individual_judgment_canonical_node draft）正本が Box 不在（2026-06-06 BLOCKED確認）。**正本所在を確定し field-level reconcile を CASEID-002 以前に完了**（case_type 正準enum / node schema 依存）。
- **下位DD**: CASEID-002（事件符号→display romaji 表 / 符号正規化）／forum支部162種 / CASEID-003（forum seed）／ CASEID-005（jufu取込境界）／ 明治期・旧法機関。

## 6. accepted 正本の残務（Mac CC 単一書き手）

- DESIGN-01 登録簿 / `DD_REGISTRY.json` への `_accepted_v1.0_with_notes` 登録。
- `_AUDIT_LEDGER.jsonl` に reflect/closed 追記、approval_queue カードの clear（`alo_gpt_audit.py reflect <id> --apply`）。
- 旧 candidate（2266457039407）は非削除で併存（lifecycle 上書きせず）。
