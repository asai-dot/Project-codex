---
request_id: DD-TRILOGY-RECONCILE-001-v0.2-20260625
supersedes_request_id: DD-TRILOGY-RECONCILE-001-v0.1-20260624
topic: 三部作整合付録 v0.2 — 監査 R1〜R7 反映（独立性 lineage 正本・law typed contract・canonical profile・exact dep pin）の独立意味監査
gate: DDRECONCILE
status: queued
result_expected_filename: 20260625_DD-TRILOGY-RECONCILE-001_v0.2_DDRECONCILE_RESULT.md
target_mode: inline_embedded
source_hash: sha256:1ac49a1167a377b8551221b1be42d34362a45b4ad4a9a286caeb8e833643ea9c
prior_result_file_id: 2306465882050
review_scope:
  include:
    - R1 独立性: lineage 正本（content same-origin collapse / observation scan_source 根）で部品数カウントを排したか。artifact→family binding・family_kind≠origin_object_type。confirmed は content のみ（XMODAL v0.5 へ意味変更を直接記載）
    - R2 law_authority_snapshot typed contract（jurisdiction/captured_at/known_at/valid_at/revision_set_hash/source_hash）が bitemporal として十分か
    - R3 facet: ALO base 組評価・header/footer 除外を absence に使わない・Formula=text+subtype
    - R5 naming: 既存 ID 再発行禁止・typed ref/namespace/version 保持（alias レベル統一）
    - R6 canonicalization profile: artifact ごと profile_id/version・set のみ sort/dedup・ordered(member/page) 順序保持・遡及読替禁止・profile 変更時 crosswalk
    - R7 exact dependency pin（id+version+content_hash+acceptance_ref・空欄は Phase1 gate fail）
    - 付録方式（cross-DD 写像/契約）と DD 直接パッチ（XMODAL v0.5）の分担が妥当か
    - 監査必須 fixture 5点（同一版元転載=1票/同一scan OCR違い≠独立/ordered非sort/dep欠落でPhase1拒否/header-footer非absence）が受入試験に入ったか
  exclude:
    - DDL（source_snapshots law_authority 列追加含む）/DB/mint/OCR/embedding/production（HOLD）
    - LAYOUT v0.5 / XDOC v0.9 本体の再監査（accepted・付録が cross-DD を governs）
regression_anchors:
  - DD-TRILOGY-RECONCILE-001 v0.1 RESULT（Box 2306465882050）DDRECONCILE_MODIFY_REQUIRED
  - 横断整合監査 docs/research/trilogy_consistency_stability_audit_20260624.md
  - DD-XMODAL-001 v0.5 patch（同時起票・DDXMODAL）
  - 本番 control.source_snapshots/releases
self_doubt:
  - content_origin_root を origin_object_id にしたが、同一条文の異なる適用版（valid_at 違い）を同根に collapse してよいか（版差は law_authority_snapshot で別管理する設計）
  - XDOC を再 ratify せず一行注記＋付録 governs で §1 を consume させる方式で意味の一貫性が保てるか
  - canonicalization の set/ordered 区別を「ID 材料の文脈」で判定する規約が実装で一意か
questions_for_gpt:
  - R1〜R7 が v0.2 付録＋XMODAL v0.5 で閉じたか
  - 独立性 lineage 正本（same-origin collapse / scan_source 根）が反こたつ記事として十分堅牢か
  - 付録＋DD直接パッチの分担が正しいか（XDOC を付録 governs で済ませる是非）
  - 残ドリフトがあれば指摘
decision_requested:
  - PASS可否 / R1〜R7 個別 / 分担の是非 / 追加指摘
expected_label: DDRECONCILE_PASS_WITH_NOTES または DDRECONCILE_MODIFY_REQUIRED
---

# DDRECONCILE 監査依頼: DD-TRILOGY-RECONCILE-001 v0.2（監査 R1〜R7 反映・lineage 正本）

- target_mode: inline_embedded。authoritative bytes = GitHub `asai-dot/Project-codex` `docs/dd_candidates/DD-TRILOGY-RECONCILE-001_trilogy_consistency_reconciliation_candidate_v0.2_20260625.md`（sha256:1ac49a11…）。XMODAL v0.5 patch を DDXMODAL で同時起票。

---

<!-- BEGIN INLINE EMBED: DD-TRILOGY-RECONCILE-001 v0.2 -->

# DD-TRILOGY-RECONCILE-001 v0.2 — 設計三部作 整合付録（監査 R1〜R7 反映・lineage 正本）candidate

> **id**: DD-TRILOGY-RECONCILE-001 / **version**: candidate v0.2 / **supersedes**: v0.1
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-25 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/OCR/embedding/production/promotion/claim-support は **HOLD**。
> **改訂理由（v0.1→v0.2）**: GPT Pro 監査 `DDRECONCILE_MODIFY_REQUIRED`（RESULT Box 2306465882050）反映。R3/R4/R5 採用、R1/R2/R6/R7 を規範契約化。**独立性は部品数でなく lineage 根で数える**（R1 の本質修正）。
> **二本立て**: 本付録は cross-DD の規範写像・契約。**XMODAL confirmed の意味変更は DD-XMODAL-001 v0.5 へ直接パッチ**（本付録 §1 を consume）。XDOC v0.9 は §1 準拠の一行注記で統治（再 ratify 不要・付録が cross-DD を governs）。
> **governs**: DD-LAYOUT-001 v0.5 / DD-XMODAL-001 v0.5（patch 同時起票）/ DD-XDOC-001 v0.9 / DD-LITID-001 / DD-LITLINK-001。各 DD の定義を狭めない。

---

## 0. 監査 R1〜R7 判定と本版対応
| R | v0.1 判定 | v0.2 対応 | § |
|---|---|---|---|
| R1 独立性 | MODIFY | **lineage 正本に修正**（部品数禁止）・family binding・same-origin collapse・confirmed は content のみ。意味変更は XMODAL v0.5 | §1 |
| R2 snapshot | PARTIAL | corpus/release 住所＝PASS。**law_authority_snapshot を typed contract 化** | §2 |
| R3 facet | PASS_WITH_NOTES | 写像維持＋notes（ALO は base と組・header/footer 除外を absence に使わない・Formula=text+subtype） | §3 |
| R4 coverage | PASS | projection_typing_coverage / range_coverage 分離 | §4 |
| R5 naming | PASS_WITH_NOTES | asset_id / source_text_revision_id＋**typed ref/namespace/version 保持・既存ID 再発行禁止** | §5 |
| R6 canonical | MODIFY | **canonicalization profile 化**（artifact ごと profile_id/version・set のみ sort・ordered 保持・遡及読替禁止） | §6 |
| R7 版固定 | MODIFY | **exact pin**（id+version+content_hash+acceptance_ref・空欄は Phase1 gate fail） | §7 |

## 1. ★独立性＝lineage 正本（R1・規範契約・両 DD consume）
独立観測数を **pipeline 部品（ocr_engine/parser/normalization）の DISTINCT 数で数えない**。**lineage の根の DISTINCT 数**で数える。

```text
# content 独立（same-origin collapse）
content_origin { origin_object_id ; editorial_source ; passage_ref }
content_origin_root(o) = o.origin_object_id            # 同一条文/判例/版は1源（版元転載も同根）
content_independent(origins) ≡ DISTINCT content_origin_root ≥ 2

# observation 独立（run lineage 根）
observation_run { scan_source_id ; ocr_engine ; parser ; normalization_profile ; run_id }
observation_lineage_root(r) = r.scan_source_id          # 同一 raw scan は1源（部品違いは別観測でない）
observation_independent(runs) ≡ DISTINCT observation_lineage_root ≥ 2
```
**artifact→family binding（R1）**：観測/証拠は **content_origin（内容起源）と observation_run（観測系譜）に binding** され、family_kind は分類タグであってカウント単位ではない。`family_kind ≠ origin_object_type`（前者＝source family 分類、後者＝対象 object 種別）。
**consumer 規約（normative）**：
```text
XMODAL confirmed（→ XMODAL v0.5）:
  D2 独立＝content_independent（same-origin collapse 後 DISTINCT ≥ 2）。
  observation pipeline の distinct は confirmed の独立票に数えない。
XDOC eligibility（XDOC v0.9 が §1 準拠）:
  content_independence    ＝ content_independent（content_origin_assertion 由来・same-origin collapse）
  observation_independence＝ observation_independent（member_pipeline_provenance 由来・scan_source lineage 根）
```
- **G_RECONCILE_INDEP_LINEAGE**：独立性は lineage 根の DISTINCT。部品数・family_id 数で数えない。
- **G_RECONCILE_SAME_ORIGIN_COLLAPSE**：同一 origin_object/同一 scan は1源に collapse。

## 2. snapshot / release（R2・law を typed contract に）
```text
corpus_snapshot_id → control.source_snapshots.source_snapshot_id（snapshot_kind ∈ {raw_source, normalized_export}）
release_id         → control.releases.release_id（✅ 一致）
```
**law_authority_snapshot（R2・typed contract・kind だけでは不足）**
```text
law_authority_snapshot
  law_snapshot_id             # required; control.source_snapshots（snapshot_kind=law_authority）
  jurisdiction                # required; 例 JP
  captured_at                 # required; 取得時刻（システム観測時点）
  known_at                    # required; その版を「知った」時点（bitemporal）
  valid_at / as_of            # required; 法令の効力時点（適用版の基準）
  revision_set_hash           # required; 法令版集合の hash（条文群の同一性）
  source_hash                 # required; 取得源バイトの hash
```
- XMODAL D2 の `law_snapshot/source_version/valid_at` は本 contract に束ねる（XMODAL v0.5 で参照）。
- **G_RECONCILE_LAW_SNAPSHOT_TYPED**：法令版は kind ラベルだけでなく bitemporal（captured/known/valid）＋hash を持つ。
- TODO（owner・HOLD）：source_snapshots に snapshot_kind=law_authority＋上記列（DDL は HOLD）。

## 3. block_type → facet 写像（R3・PASS_WITH_NOTES）
| block_type | facet |
|---|---|
| Table | table |
| Picture | figure |
| Text / List-item / Caption / Footnote | text |
| Section-header / Title | structure（toc_node ツリーと併せ構成） |
| Formula | text（subtype=formula で識別） |
| Page-header / Page-footer | **除外**（facet 比較対象外） |
| ALO subtype | **base block type と組で評価**（注/条文囲み/判例引用/要旨→ base の facet） |
- **G_RECONCILE_FACET_MAP**：未収載 block_type は unknown（facet 比較に入れない）。
- **G_RECONCILE_NO_HEADER_FOOTER_ABSENCE**（notes）：**Page-header/footer の除外 range を absence/difference の証拠に使わない**（除外は「無い」ではない）。

## 4. coverage 用語（R4・PASS）
`projection_typing_coverage`（LAYOUT・射影の型付け被覆）／ `range_coverage`（XDOC・範囲被覆）を分離。**G_RECONCILE_COVERAGE_TERMS**。

## 5. naming（R5・PASS_WITH_NOTES）
- 新規 schema/コードは `asset_id` / `source_text_revision_id` を正本。
- **既存 ID を再発行しない**（rename はしない）。**typed ref＋namespace＋version を保持**（旧名は alias 写像で吸収・物理 ID は不変）。
- **G_RECONCILE_NAMING_NO_REMINT**：命名統一は alias レベル。既存 mint 済 ID の再生成禁止。

## 6. canonicalization profile（R6・MODIFY 反映）
**全 ID を XDOC profile へ遡及読替えしない。** 各 artifact が profile を持つ。
```text
canonicalization_profile
  profile_id / profile_version
  hash_algo(sha256) ; unicode_form(NFC) ; json_key_order(codepoint_asc)
  set_array_rule(sort+dedup)           # ★set 配列のみ
  ordered_array_rule(preserve_order)   # ★member/page 等の ordered 配列は順序保持
artifact each: { canonicalization_profile_id ; canonicalization_profile_version ; hash_scope_version }
```
- **G_RECONCILE_CANONICAL_PROFILED**：artifact は自身の profile_id/version を保持。
- **G_RECONCILE_ORDERED_PRESERVE**：ordered 配列（members/pages/reading order）は canonicalization で sort しない。set 配列のみ sort/dedup。
- **G_RECONCILE_NO_RETRO_REHASH**：既存 ID を別 profile で再計算/読替えしない。profile 変更時は explicit crosswalk（旧→新 ID 対応表）を作る。
- 注：適合性ハーネスの canonical_json は **set 文脈で使用**（observation_id 材料は規定キーで安定ソート＝set 的）。member 配列は ID 材料で順序規約を別途持つ（XDOC §5 の symmetric/directional 規則がこれに該当）。

## 7. dependency exact pin（R7・MODIFY 反映）
```text
dependency_pin
  dependency_id               # 例 DD-LITID-001
  version                     # 具体版（latest 等の語は不可）
  content_hash                # その版の content hash
  acceptance_ref              # accepted の証跡（RESULT file_id 等）
# 空欄/未確定があれば Phase 1 gate を FAIL させる（投入させない）
```
| dependency | version | content_hash | acceptance_ref |
|---|---|---|---|
| DD-LITID-001 | （owner 記入）TBD | TBD | TBD |
| DD-LITLINK-001 | （owner 記入）TBD | TBD | TBD |
| DD-LAYOUT-001 | v0.5 | （記入）| accepted 2026-06-19 |
| DD-XMODAL-001 | v0.5 | （記入）| patch 同時起票 |
| DD-XDOC-001 | v0.9 | （記入）| accepted 2026-06-24 / RESULT 2303550755480 |
- **G_RECONCILE_DEP_PIN_EXACT**：id+version+content_hash+acceptance_ref を全て埋める。空欄は Phase1 gate fail。

## 8. ゲート一覧
INDEP_LINEAGE / SAME_ORIGIN_COLLAPSE / SNAPSHOT_HOME / LAW_SNAPSHOT_TYPED / FACET_MAP / NO_HEADER_FOOTER_ABSENCE / COVERAGE_TERMS / NAMING_NO_REMINT / CANONICAL_PROFILED / ORDERED_PRESERVE / NO_RETRO_REHASH / DEP_PIN_EXACT。

## 9. 受入試験（全自動 PASS が条件・監査必須 fixture 反映）
1. content：同一条文を2冊が引く / 同一版元転載 → same-origin collapse で1源（独立でない）。
2. observation：同一 raw scan の OCR/parser 違い → lineage 根が同一 → 独立でない。
3. confirmed：content 独立のみで判定・observation distinct は数えない。
4. canonicalization：**ordered 配列（members/pages）を sort しない**（set 配列のみ sort/dedup）。
5. dependency：version/content_hash/acceptance_ref のいずれか欠落 → Phase 1 gate FAIL。
6. facet：Page-header/footer 除外 range を absence/difference 証拠に使えない。
7. snapshot：law_authority_snapshot が bitemporal（captured/known/valid）＋revision_set_hash＋source_hash を持つ。
8. naming：asset_id/source_text_revision_id 統一が alias レベル（既存 ID 再発行なし）。
9. block_type→facet 写像が一意・未収載は unknown。
10. corpus_snapshot_id/release_id が control.* に一意写像。

## 10. GO / HOLD / loop_state
- **GO**：v0.2 付録 ratify／XMODAL v0.5 小パッチ（§1 consume＋law contract）／lineage fixture／canonicalization profile 表／exact dependency pin 記入。
- **HOLD**：v0.2 ratify 前の Phase 1 実データ／DDL（source_snapshots law_authority 列追加含む）／DB/mint/OCR/embedding/production/promotion/claim-support／既存 ID 一括再生成。
- loop_state = **patched（v0.2・R1〜R7 規範化・lineage 正本）→ 再投函（DDRECONCILE 再監査）候補**。XMODAL v0.5 を DDXMODAL で同時起票。

<!-- END INLINE EMBED: DD-TRILOGY-RECONCILE-001 v0.2 -->
