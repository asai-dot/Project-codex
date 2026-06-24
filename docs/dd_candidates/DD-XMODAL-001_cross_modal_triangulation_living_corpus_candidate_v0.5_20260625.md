# DD-XMODAL-001 v0.5 — cross-modal triangulation（独立性 lineage 正本・confirmed 意味確定）candidate

> **id**: DD-XMODAL-001 / **version**: candidate v0.5 / **supersedes**: v0.4
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-25 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/学習/embedding/OCR は HOLD。
> **改訂理由（v0.4→v0.5）**: 三部作整合監査（DD-TRILOGY-RECONCILE-001 v0.2・RESULT Box 2306465882050）の R1 を XMODAL 本体へ直接反映。**confirmed の独立性の意味を lineage 正本に確定**し、law_snapshot を typed contract に束ねる。v0.4 の D0/D1/D2・5ガードレール・ストレステスト・inventory-probe は**不変**（本 patch は §1 独立性カウントと §2 law contract のみ）。
> **承継（不変）**: v0.3/v0.4 §1（D0/D1/D2 三分割）・confirmed に D2・possible_reason・external_source_family registry の語彙・5ガードレール・inventory-probe。
> **depends_on**: DD-TRILOGY-RECONCILE-001 v0.2（§1 lineage 規範を consume）/ DD-LAYOUT-001 v0.5 / DD-XDOC-001 v0.9 / DD-LITID-001。

---

## 0. 本 patch の射程
v0.4 まで `confirmed` は「external_source_count ≥ 2（独立 family）」だったが、**「独立」を family_id/部品の DISTINCT 数で数える**読み方が残っていた。監査 R1：**OCR/parser 等は1 pipeline の部品で、distinct 部品数を独立観測数に数えてはいけない**。本 v0.5 で **lineage 正本**に確定する。

## 1. ★confirmed の独立性＝lineage 正本（R1・RECONCILE §1 consume）
`external_source_count ≥ 2` の「2」は **content 起源の lineage 根の DISTINCT ≥ 2**（same-origin collapse 後）で数える。
```text
# RECONCILE v0.2 §1 を consume（正本はそちら）
content_origin_root(o)     = o.origin_object_id          # 同一条文/判例/版＝1源（版元転載も同根）
observation_lineage_root(r)= r.scan_source_id            # 同一 raw scan＝1源（OCR/parser 違いは別観測でない）

confirmed の必要条件（v0.5 確定）:
  external_evidence_involved = true（D2）
  AND content_independent ≡ DISTINCT content_origin_root(D2 群) ≥ 2
  # observation pipeline（OCR/parser/normalization）の distinct は confirmed の独立票に数えない
```
- **artifact→family binding**：D2 evidence は `content_origin{origin_object_id, editorial_source}` に binding。`external_source_family` は分類タグであってカウント単位でない（`family_kind ≠ origin_object_type`）。
- **same-origin collapse**：同一 origin_object_id（同一条文の複数版元転載含む）は1票。
- **G_XMODAL_CONFIRMED_CONTENT_LINEAGE**（v0.5 新規）：confirmed の独立は content_origin_root の DISTINCT。部品数・family_id 数では数えない。
- v0.4 の `external_source_family_registry`（DISTINCT family_id）規約は **RECONCILE §1 の lineage 規範に置換**（registry は語彙・分類として残すがカウントは lineage 根）。
- correlation_group（artifact_coupled = V/T/D1）の実効票割引は不変。

## 2. ★law_snapshot を typed contract に（R2・RECONCILE §2 consume）
v0.4 の D観測 `law_snapshot/source_version/valid_at` を **law_authority_snapshot（bitemporal＋hash）**に束ねる。
```text
d2_evidence(... , law_authority_snapshot_ref -> RECONCILE §2 law_authority_snapshot)
law_authority_snapshot:
  jurisdiction ; captured_at ; known_at ; valid_at/as_of ; revision_set_hash ; source_hash
```
- **G_XMODAL_LAW_SNAPSHOT_TYPED**（v0.4 の G_XMODAL_LAW_SNAPSHOT_REQUIRED を強化）：法令版は kind ラベルでなく bitemporal＋revision_set_hash＋source_hash。
- ストレステスト#1（綺麗だが誤った版）・#5（法改正/版違い）は本 contract の valid_at/revision_set_hash で落とす（不変・接地強化）。

## 3. 不変（v0.4 承継）
D0/D1/D2 三分割・D1=T結合非独立・confirmed に D2・possible_reason 機械可読・5ガードレール・既存/白地分離・inventory-probe（knowledge_yield に D2率）・ストレステスト5本。

## 4. ゲート（v0.4 ＋ v0.5 差分）
v0.4 既存（D_AXIS_SPLIT / NO_EXTERNAL_OVERCLAIM / DEPENDENCY_GRAPH_REQUIRED / EXTERNAL_EVIDENCE_REQUIRED_FOR_CONFIRMED / NO_VT_CONFIRMATION / HUMAN_PROMOTION_ONLY / EXTERNAL_FAMILY_REGISTRY / POSSIBLE_REASON_REQUIRED）
＋ v0.5：**G_XMODAL_CONFIRMED_CONTENT_LINEAGE**（独立は lineage 根）／**G_XMODAL_LAW_SNAPSHOT_TYPED**（bitemporal＋hash）。
- 注：EXTERNAL_FAMILY_REGISTRY の「DISTINCT family」は CONFIRMED_CONTENT_LINEAGE に従い lineage 根で数える（family registry は分類語彙）。

## 5. 受入試験（差分）
1. 同一条文を引く2 D2 / 同一版元転載 → content_origin_root collapse で1源 → confirmed にならない。
2. 同一 raw scan の OCR/parser 違い D2 → observation lineage 根が同一 → 独立票でない（そもそも observation は confirmed の独立票に数えない）。
3. content 2源（別条文/別判例）＋ D2 → confirmed 可。
4. D2 が law_authority_snapshot（captured/known/valid＋revision_set_hash＋source_hash）を持たない → confirmed 不可（typed contract 必須）。

## 6. GO / HOLD / loop_state
- **GO**：v0.5 design ratify／RECONCILE v0.2 と整合確認／lineage fixture。
- **HOLD**：DDL/DB/mint/Box mutation/学習/embedding/OCR/production/promotion/claim-support。
- loop_state = **patched（v0.5・R1 lineage 確定＋law contract）→ DDXMODAL 再監査候補**。RECONCILE v0.2 と対で監査。
