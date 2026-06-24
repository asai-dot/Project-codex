# DD-INDEP-LINEAGE-001 v0.1 — 独立性 lineage 正本（反こたつ記事の核・leaf DD）candidate

> **id**: DD-INDEP-LINEAGE-001 / **version**: candidate v0.1 / **supersedes**: なし（新規・leaf）
> **lifecycle**: **accepted**（owner 浅井 ratify 2026-06-25、設計のみ）。GPT Pro 監査 `DDINDEP_PASS_WITH_NOTES`（RESULT Box 2306834650821・blocking なし）。実装/DDL/DB/mint/OCR/embedding/production/promotion/claim-support は**別ゲートで HOLD**（accepted≠deployed）。
> **accepted notes（非blocking・実装時遵守）**: (1) content 独立は content_independence_group の DISTINCT（object/record id でない） (2) observation 独立は observation_lineage_root の DISTINCT（OCR/parser/normalizer run でない） (3) content_lineage_binding は versioned・変更で stale/re-eval (4) consumer は本 DD を id+version+content_hash+acceptance_ref で pin（循環解消の条件） (5) **unknown lineage を既定で independent に格上げしない**（保守化・harness 反映済 GROUP_UNKNOWN）。
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-25 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/OCR/embedding/production/promotion/claim-support は **HOLD**。
> **目的**: 「独立2源でなければ confirmed/eligible にしない」の**唯一の正本**を定義。DDRECONCILE v0.1/v0.2・DDXMODAL v0.5 の両監査が一致して指摘した「object_id/scan_id は lineage root として不十分」「independence_group + collapse_key + versioned binding が要る」「相互依存を一方向に」を leaf DD として集約。
> **依存方向（循環解消）**: 本 DD は **leaf**（三部作に依存しない・DD-LITID-001 の asset/object 同定のみ参照）。**XMODAL / XDOC / RECONCILE が本 DD を一方向 consume** する（XMODAL↔RECONCILE の循環を解消）。
> **反映**: DDRECONCILE v0.2 RESULT（Box 2306546757530・R1/B1-B4）・DDXMODAL v0.5 RESULT（Box 2306559651772・B1-B4）。

---

## 0. 中核命題
独立票（独立した源の数）は **record ID でも object ID でも scan ID でも数えない**。
- **content 独立**＝ policy が算定する **content_independence_group の DISTINCT 数**（転載・派生・同一上流は1群へ collapse）。
- **observation 独立**＝ acquisition lineage の **root の DISTINCT 数**（同一 raw bytes の複製・別 run は1系統）。
派生・非canonical・claim_support_eligible=false・人手ゲート。

## 1. content identity（過剰分割と偽独立を両方塞ぐ）
```text
content_identity
  content_object_id           # 正確な条文/判例/版/passage（例 statute:民法541@2020 / case:最判平X / edition:Y/p123）
  content_revision_id         # その object の版
  source_artifact_ref         # どの artifact(book/record) からの観測か（DD-LITID asset）
```
- `content_object_id ≠ family_kind ≠ origin_object_type`：object は対象、family は分類、binding が独立群を決める。
- **B1/B4 の罠**：同一 authority の別条文は別 object_id だが**独立源とは限らない**（同一 editorial/authority 系譜なら1群）。逆に同一原稿の別 provider record は別 record だが**1群**。

## 2. ★content_lineage_binding（versioned・独立群の算定・B2）
```text
content_lineage_binding
  binding_id                  # = canonical hash（§7 canonicalization 準拠）
  source_artifact_ref ; content_object_id ; content_revision_id
  upstream_lineage_id         # 上流原稿/authority/editorial 系譜の同一性（転載元・原典）
  same_origin_collapse_key    # 転載・OCR・provider 派生 record を1票へ collapse する key
  content_independence_group_id  # ★独立票の単位（policy が算定する effective group）
  evidence_refs[]             # binding の根拠（minItems=1）
  independence_policy_id / independence_policy_version
  binding_status              # active | stale | superseded
```
- **binding 変更 → 既存 confirmed/eligible assessment を stale へ → re-evaluation**（silent に独立性を変えない・B2）。
- `content_independence_group_id` は **policy が upstream_lineage_id・same_origin_collapse_key から算定**（生の object_id ではない）。

## 3. ★observation_acquisition_lineage（root を取得事象から導出・B3）
```text
observation_acquisition_lineage
  acquisition_event_id        # 取得事象（いつ・どこから raw を得たか）
  physical_source_ref / external_source_ref
  raw_input_hash              # ★raw bytes の同一性（複製 scan を畳む）
  captured_at
  upstream_parent_id?         # 親系譜（再取得/複製の親）
  observation_lineage_root_id # = policy が raw_input_hash + acquisition から導出する根
observation_run               # OCR/parser/normalizer は系譜の子（独立票でない）
  run_id ; observation_lineage_root_id   # FK（根に従属）
  ocr_engine ; parser ; normalization_profile
```
- **同一 raw_input_hash の別 run（別 OCR/parser）→ 同一 observation_lineage_root → 独立1系統**。
- 別 scan ID でも raw_input_hash が同一なら同根（複製で系統を増やせない・B3）。

## 4. independence_policy（算定規則・versioned）
```text
independence_policy
  policy_id / policy_version
  content_group_rule          # upstream_lineage_id/collapse_key → content_independence_group_id 算定
  collapse_rules              # 転載/同一authority/同一editorial/同一raw bytes の畳み方
  observation_root_rule       # raw_input_hash/acquisition → observation_lineage_root_id 算定
```

## 5. ★独立カウント（normative・両 DD が consume）
```text
content_independent(bindings) ≡
  DISTINCT { b.content_independence_group_id : b ∈ active bindings } ≥ 2
observation_independent(runs) ≡
  DISTINCT { lineage_root_of(r) : r ∈ runs } ≥ 2

collapse（1票に畳む）:
  同一 upstream_lineage_id          → 同一 content group
  同一 same_origin_collapse_key     → 同一 content group（転載/派生 record）
  同一 raw_input_hash               → 同一 observation lineage root
not-collapse（2票になり得る）:
  別 object でも独立 authority/editorial lineage → 別 content group（B4-3）
```
**consumer 規約**：
```text
XMODAL confirmed:  content_independent（content group DISTINCT ≥ 2）。observation は confirmed の独立票に数えない。
XDOC eligibility:  content_independence ＝ content_independent / observation_independence ＝ observation_independent。
                   XDOC は lineage_binding_ref・independence_policy_version・effective group・input_fingerprint・本 DD version/hash pin を保持。
```
- **G_INDEP_GROUP_NOT_OBJECT_ID**：独立票は content_independence_group の DISTINCT。object_id/record_id/scan_id では数えない。
- **G_INDEP_OBSERVATION_RAW_LINEAGE**：observation 独立は raw_input_hash 由来の root。OCR/parser/normalizer は子で独立票でない。
- **G_INDEP_BINDING_VERSIONED**：binding は versioned・変更で既存 assessment を stale/re-eval。

## 6. ゲート一覧
INDEP_GROUP_NOT_OBJECT_ID / INDEP_OBSERVATION_RAW_LINEAGE / INDEP_BINDING_VERSIONED / INDEP_POLICY_VERSIONED / DERIVED / NO_CLAIM_SUPPORT / HUMAN_PROMOTION_ONLY。

## 7. canonicalization（RECONCILE field-level registry を consume）
binding_id 等のハッシュは RECONCILE v0.3 §6 の **field-level canonicalization registry**（field_path → set|multiset|sequence）に従う。evidence_refs 等の集合は set（sort+dedup）、順序ある列は sequence（順序保持）。本 DD は profile_id/version を artifact に保持。

## 8. 受入試験（監査必須 fixture・全自動 PASS が条件）
1. **別 record ID でも upstream lineage 同一 → 1票**（同一原稿の別 provider record を独立2源にしない）。
2. **別 object でも independence_group 同一 → 1票**（同一上流の別条文 record を独立2源にしない）。
3. **同一 object type でも独立 authority/editorial lineage なら2票になり得る**（別系譜は独立）。
4. **同一 raw_input_hash の別 run（別 OCR/parser）→ observation 1系統**（複製/再OCRで系統を増やせない）。
5. **binding 変更 → 既存 confirmed assessment が stale → re-evaluation**（silent mutation なし）。
6. content_independence_group / observation_lineage_root が policy_version に紐付き、policy 変更で effective group が再算定される。
7. 独立カウントが object_id/record_id/scan_id の DISTINCT では**なく** group/root の DISTINCT で行われる。

## 9. GO / HOLD / loop_state
- **GO**：v0.1 design ratify／lineage schema fixture／independence_policy 草案／XMODAL v0.6・XDOC addendum・RECONCILE v0.3 が本 DD を一方向 consume する整合。
- **HOLD**：DDL/DB/mint/Box mutation/OCR/embedding/production/promotion/claim-support／既存 ID 一括再生成。
- loop_state = **accepted（owner ratify 2026-06-25・DDINDEP PASS_WITH_NOTES）**。次：XMODAL v0.6 / RECONCILE v0.3 / XDOC addendum が本 DD を id+version+content_hash+acceptance_ref で pin して一方向 consume → joint release manifest で atomic acceptance（循環解消）。
