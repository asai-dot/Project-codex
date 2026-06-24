# DD-XMODAL-001 v0.6 — cross-modal triangulation（独立性は leaf DD を直接 pin して consume）candidate

> **id**: DD-XMODAL-001 / **version**: candidate v0.6 / **supersedes**: v0.5
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-25 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/学習/embedding/OCR は HOLD。
> **改訂理由（v0.5→v0.6）**: 独立性の正本が新 leaf DD `DD-INDEP-LINEAGE-001 v0.1`（DDINDEP_PASS_WITH_NOTES・RESULT 2306834650821）に確定。v0.5 は RECONCILE §1 経由で lineage を consume していたが、**循環解消のため XMODAL は leaf DD を id+version+content_hash+acceptance_ref で直接 pin** する。confirmed の独立カウントは leaf §5 の `content_independent` をそのまま使用。v0.5 の D0/D1/D2・5ガードレール・ストレステスト・law contract・inventory-probe は**不変**（本 patch は §1 の参照先を leaf へ振り替え＋note5 取り込みのみ）。
> **承継（不変）**: v0.3/v0.4 §1（D0/D1/D2 三分割）・confirmed に D2・possible_reason・external_source_family registry の語彙・5ガードレール・inventory-probe・v0.5 §2 law_authority_snapshot contract。
> **depends_on（pin）**: **DD-INDEP-LINEAGE-001 v0.1**（独立性 lineage 正本・§1 を直接 consume）/ DD-TRILOGY-RECONCILE-001 v0.3（law contract §2・facet/canonical 写像）/ DD-LAYOUT-001 v0.5 / DD-XDOC-001 v0.9 / DD-LITID-001。

---

## 0. 本 patch の射程
v0.5 で confirmed の独立を「content 起源 lineage 根の DISTINCT ≥ 2」に確定したが、その**定義の正本**は当時 RECONCILE §1 にあり、RECONCILE↔XMODAL が相互参照していた。leaf DD `DD-INDEP-LINEAGE-001` の新設・accept により、**正本は leaf §5 単独**になった。v0.6 は参照先を RECONCILE 経由から **leaf 直 pin** に振り替え、leaf note5（不明系譜を既定で independent にしない）を confirmed 条件に取り込む。意味（confirmed の閾値）は不変。

## 1. ★confirmed の独立性＝leaf DD を直接 pin（DD-INDEP-LINEAGE-001 §5 consume）
`external_source_count ≥ 2` の「2」は **leaf DD の `content_independent`**（content_independence_group の DISTINCT ≥ 2・same-origin collapse 後）で数える。
```text
# 正本は leaf DD（DD-INDEP-LINEAGE-001 §5）。pin して consume：
#   pin = id:DD-INDEP-LINEAGE-001 / version:v0.1 / content_hash:<joint manifest> / acceptance_ref:RESULT 2306834650821
confirmed の必要条件（v0.6 確定）:
  external_evidence_involved = true（D2）
  AND content_independent(D2 群の content_lineage_binding) = true   # leaf §5
      # = DISTINCT content_independence_group_id (active binding) ≥ 2
  # observation pipeline（OCR/parser/normalization）の distinct は confirmed の独立票に数えない（leaf §3/§5）
  # note5: upstream/collapse 不明の binding だけでは独立を立てない（leaf GROUP_UNKNOWN・保守化）
```
- **artifact→binding**：D2 evidence は leaf §2 `content_lineage_binding`（content_object_id・upstream_lineage_id・same_origin_collapse_key・content_independence_group_id）に binding。`external_source_family` は分類タグでありカウント単位でない（`family_kind ≠ origin_object_type`）。
- **same-origin collapse / unknown lineage**：同一 upstream_lineage_id・同一 collapse_key は1票（leaf §5）。不明系譜は既定で独立にしない（leaf note5）。
- **G_XMODAL_CONFIRMED_LEAF_LINEAGE**（v0.5 G_XMODAL_CONFIRMED_CONTENT_LINEAGE を改称・正本を leaf に明示）：confirmed の独立は leaf DD `content_independent`。部品数・family_id 数では数えない。XMODAL は独自に再定義せず leaf を pin して consume。
- **G_XMODAL_LEAF_PIN_REQUIRED**（v0.6 新規）：本 DD は leaf を id+version+content_hash+acceptance_ref で pin（joint manifest が content_hash を確定）。pin 欠落は gate fail。
- v0.4 の `external_source_family_registry`（DISTINCT family_id）は leaf §5 の lineage 規範に置換（registry は分類語彙として残す）。correlation_group（artifact_coupled = V/T/D1）の実効票割引は不変。

## 2. law_snapshot を typed contract に（RECONCILE v0.3 §2 consume・v0.5 承継）
D2 観測の `law_snapshot/source_version/valid_at` を **law_authority_snapshot（bitemporal＋hash）**に束ねる。
```text
d2_evidence(... , law_authority_snapshot_ref -> RECONCILE v0.3 §2 law_authority_snapshot)
law_authority_snapshot:
  jurisdiction ; captured_at ; known_at ; valid_at/as_of ; revision_set_hash ; source_hash
```
- **G_XMODAL_LAW_SNAPSHOT_TYPED**：法令版は kind ラベルでなく bitemporal＋revision_set_hash＋source_hash。
- ストレステスト#1（綺麗だが誤った版）・#5（法改正/版違い）は valid_at/revision_set_hash で落とす（不変・接地強化）。

## 3. 不変（v0.4/v0.5 承継）
D0/D1/D2 三分割・D1=T結合非独立・confirmed に D2・possible_reason 機械可読・5ガードレール・既存/白地分離・inventory-probe（knowledge_yield に D2率）・ストレステスト5本・law contract。

## 4. ゲート（v0.5 ＋ v0.6 差分）
v0.4 既存（D_AXIS_SPLIT / NO_EXTERNAL_OVERCLAIM / DEPENDENCY_GRAPH_REQUIRED / EXTERNAL_EVIDENCE_REQUIRED_FOR_CONFIRMED / NO_VT_CONFIRMATION / HUMAN_PROMOTION_ONLY / EXTERNAL_FAMILY_REGISTRY / POSSIBLE_REASON_REQUIRED）＋ v0.5（G_XMODAL_LAW_SNAPSHOT_TYPED）
＋ v0.6：**G_XMODAL_CONFIRMED_LEAF_LINEAGE**（独立は leaf `content_independent`・note5 保守化込み）／**G_XMODAL_LEAF_PIN_REQUIRED**（leaf を exact pin）。
- 注：EXTERNAL_FAMILY_REGISTRY の「DISTINCT family」は CONFIRMED_LEAF_LINEAGE に従い leaf の lineage 根で数える（family registry は分類語彙）。

## 5. 受入試験（差分）
1. 同一条文を引く2 D2 / 同一版元転載（同一 upstream_lineage_id）→ content_independence_group collapse で1源 → confirmed にならない。
2. 同一 raw_input_hash の OCR/parser 違い D2 → observation lineage 根が同一 → 独立票でない（そもそも observation は confirmed の独立票に数えない）。
3. content 2源（別 independence_group）＋ D2 → confirmed 可。
4. D2 が law_authority_snapshot（captured/known/valid＋revision_set_hash＋source_hash）を持たない → confirmed 不可（typed contract 必須）。
5. **leaf pin（id+version+content_hash+acceptance_ref）が欠落 → gate fail**（独立性の正本未固定で confirmed を出さない）。
6. **upstream/collapse 不明の binding 2件のみ → confirmed にならない**（note5・GROUP_UNKNOWN は数えない）。

## 6. GO / HOLD / loop_state
- **GO**：v0.6 design ratify／leaf DD `DD-INDEP-LINEAGE-001 v0.1` pin 整合（content_hash は joint manifest で確定）／RECONCILE v0.3・XDOC addendum と相互 pin／lineage fixture。
- **HOLD**：DDL/DB/mint/Box mutation/学習/embedding/OCR/production/promotion/claim-support。
- loop_state = **patched（v0.6・独立性を leaf 直 pin・note5 取り込み）→ DDXMODAL 再監査候補**。RECONCILE v0.3・XDOC addendum・joint manifest と対で監査。
