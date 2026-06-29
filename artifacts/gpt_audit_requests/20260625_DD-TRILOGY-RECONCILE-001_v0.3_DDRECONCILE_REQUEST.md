---
request_id: DD-TRILOGY-RECONCILE-001-v0.3-20260625
supersedes_request_id: DD-TRILOGY-RECONCILE-001-v0.2-20260625
topic: 三部作整合付録 v0.3 — R1（独立性 lineage）を新 leaf DD DD-INDEP-LINEAGE-001 へ委譲・本付録は pin して consume（循環解消）／R6 を field-level canonicalization registry に昇格／R7 exact-pin に leaf 追加。joint release manifest と対で意味監査
gate: DDRECONCILE
status: queued
result_expected_filename: 20260625_DD-TRILOGY-RECONCILE-001_v0.3_DDRECONCILE_RESULT.md
target_mode: inline_embedded
source_hash: sha256:386266456b63d833c863cfb3b513fac2ba149e91d61465456d9e71afbe941edd
prior_result_file_id: 2306465882050
companion_artifacts:
  - DD-XMODAL-001 v0.6（DDXMODAL・同時起票・leaf 直 pin）source_hash sha256:4aede823e57247416ca29d7b0f0563d022b0154481e25523f9f74d8d2f1392a6
  - DD-TRILOGY-JOINT-RELEASE-MANIFEST v0.1（相互 pin・content_hash crosswalk）source_hash sha256:ffa3a7cec5888693ae45dce413c70801393346dc2e7bf6643f31074d3e24e710
  - DD-INDEP-LINEAGE-001 v0.1（leaf 正本・accepted）RESULT 2306834650821 / content_hash sha256:a7856be147a3f45b19fafe04d8ad2044565f00d7572a93cd477e144101629b43
review_scope:
  include:
    - R1 委譲: 独立性の定義・カウントを本付録から削除し leaf DD §5 を pin して consume する設計が、二重定義なく一方向参照（循環解消）になっているか
    - 非循環性: pin グラフ（RECONCILE/XMODAL/XDOC → INDEP）が INDEP を含む閉路を持たない DAG であること（leaf は in-edge のみ・out は LITID のみ）
    - R6 昇格: field-level canonicalization registry（field_path → set|multiset|sequence）が、一律 sort（順序破壊・誤独立）も一律 preserve（偽の重複）も塞ぐか。既定分類（evidence_refs=set / members・pages・reading_order=sequence / collapse 適用列=multiset）が妥当か。未登録 field_path を canonicalize 対象外にする規約
    - R7 exact pin: leaf を id+version+content_hash+acceptance_ref で pin・content_hash を joint manifest で確定する方式（プレースホルダ未解決は Phase1 gate fail）
    - 承継部 R2（law_authority_snapshot typed contract）/R3（facet・ALO/ヘッダフッタ非absence）/R4/R5（naming 非remint）を狭めていないか
  exclude:
    - DDL（source_snapshots law_authority 列）/DB/mint/OCR/embedding/production（HOLD）
    - DD-INDEP-LINEAGE-001 本体の再監査（accepted・DDINDEP_PASS_WITH_NOTES 済）
    - LAYOUT v0.5 / XDOC v0.9 本体（accepted・付録/addendum が cross-DD を governs）
regression_anchors:
  - DD-TRILOGY-RECONCILE-001 v0.2 RESULT（Box 2306465882050）DDRECONCILE_MODIFY_REQUIRED → v0.2 で R1〜R7 規範化
  - DD-INDEP-LINEAGE-001 v0.1 RESULT（Box 2306834650821）DDINDEP_PASS_WITH_NOTES（note5 保守化込み）
  - DD-XMODAL-001 v0.6（同時起票・DDXMODAL）
  - 横断整合監査 docs/research/trilogy_consistency_stability_audit_20260624.md
self_doubt:
  - R1 を leaf へ委譲した結果、RECONCILE が「写像のみ」になり実質が薄くないか（残実質は R2 law contract・R3 facet・R6 canonical・R7 pin）
  - field-level registry の collection_kind 判定（multiset の必要性）が実装で一意に決まるか。multiset を使う具体 field が collapse 適用列のみで十分か
  - content_hash を本文ファイルバイト sha256 にし、artifact 内部 ID は §6 registry に従う二層構成が監査者に明瞭か
questions_for_gpt:
  - R1 の leaf 委譲で XMODAL↔RECONCILE の循環が実際に解消したか（DAG 化の確認）
  - field-level canonicalization registry が R6 の MODIFY を十分閉じるか
  - joint release manifest による atomic acceptance（相互 pin・all-or-nothing）が版固定 R7 として堅牢か
  - 残ドリフトがあれば指摘
decision_requested:
  - PASS可否 / R1 委譲の是非 / R6 registry / R7+manifest / 非循環性 / 追加指摘
expected_label: DDRECONCILE_PASS_WITH_NOTES または DDRECONCILE_MODIFY_REQUIRED
---

# DDRECONCILE 監査依頼: DD-TRILOGY-RECONCILE-001 v0.3（R1 を leaf DD へ委譲・field-level canonicalization・joint manifest）

- target_mode: inline_embedded。authoritative bytes = GitHub `asai-dot/Project-codex` `docs/dd_candidates/DD-TRILOGY-RECONCILE-001_trilogy_consistency_reconciliation_candidate_v0.3_20260625.md`（sha256:386266456b…）。
- 対監査: **DD-XMODAL-001 v0.6（DDXMODAL）と対**。両 PASS で **joint release manifest v0.1** により leaf+三部作を atomic ratify。
- leaf 正本: **DD-INDEP-LINEAGE-001 v0.1**（accepted・RESULT 2306834650821）。本付録は leaf を pin して一方向 consume するだけで独立性を再定義しない。

---

<!-- BEGIN INLINE EMBED: DD-TRILOGY-RECONCILE-001 v0.3 -->

# DD-TRILOGY-RECONCILE-001 v0.3 — 設計三部作 整合付録（R1 を leaf DD へ委譲・field-level canonicalization）candidate

> **id**: DD-TRILOGY-RECONCILE-001 / **version**: candidate v0.3 / **supersedes**: v0.2
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-25 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/OCR/embedding/production/promotion/claim-support は **HOLD**。
> **改訂理由（v0.2→v0.3）**: (a) **R1（独立性 lineage）を新 leaf DD `DD-INDEP-LINEAGE-001` へ委譲**。本付録は独立カウントの定義を持たず、leaf DD を id+version+content_hash+acceptance_ref で **pin して一方向 consume**（XMODAL↔RECONCILE の循環を解消）。(b) **R6 を field-level canonicalization registry に昇格**（field_path → set|multiset|sequence）。(c) R7 exact-pin 表に leaf DD を追加。R2（law typed contract）/R3/R4/R5 は v0.2 を承継。
> **依存方向（循環解消）**: 本付録は **DD-INDEP-LINEAGE-001 を consume する側**（leaf に依存・leaf は本付録に依存しない）。独立性の正本は leaf DD §5。
> **二本立て**: 本付録は cross-DD の規範写像・契約。**XMODAL confirmed の意味は DD-XMODAL-001 v0.6 が leaf DD を直接 pin して consume**。XDOC v0.9 は leaf DD 準拠の addendum 一行注記で統治（再 ratify 不要）。
> **governs**: DD-LAYOUT-001 v0.5 / DD-XMODAL-001 v0.6（leaf pin）/ DD-XDOC-001 v0.9（+addendum）/ DD-LITID-001 / DD-LITLINK-001。各 DD の定義を狭めない。

---

## 0. 監査 R1〜R7 判定と本版対応
| R | 由来判定 | v0.3 対応 | § |
|---|---|---|---|
| R1 独立性 | MODIFY（v0.2 で lineage 化） | **leaf DD `DD-INDEP-LINEAGE-001 v0.1` へ委譲・本付録は pin して consume**（定義は leaf §5 が正本） | §1 |
| R2 snapshot | PARTIAL | corpus/release 住所＝PASS。**law_authority_snapshot を typed contract 化**（v0.2 承継） | §2 |
| R3 facet | PASS_WITH_NOTES | 写像維持＋notes（ALO は base と組・header/footer 除外を absence に使わない・Formula=text+subtype） | §3 |
| R4 coverage | PASS | projection_typing_coverage / range_coverage 分離 | §4 |
| R5 naming | PASS_WITH_NOTES | asset_id / source_text_revision_id＋typed ref/namespace/version 保持・既存ID 再発行禁止 | §5 |
| R6 canonical | MODIFY | **field-level canonicalization registry**（field_path → set|multiset|sequence・artifact ごと profile_id/version・遡及読替禁止） | §6 |
| R7 版固定 | MODIFY | **exact pin**（id+version+content_hash+acceptance_ref・空欄は Phase1 gate fail）＋leaf DD 追加 | §7 |

## 1. ★独立性＝leaf DD へ委譲（R1・循環解消・consume only）
独立観測数の定義・カウント規則は本付録に**置かない**。正本は **`DD-INDEP-LINEAGE-001 v0.1` §5（独立カウント normative）**。本付録は leaf を pin して参照するだけ（一方向 consume）。

```text
# 正本は leaf DD（DD-INDEP-LINEAGE-001 §5）。ここでは pin と consumer 規約の写像のみ。
content_independent(bindings)     ≡ leaf §5: DISTINCT content_independence_group_id (active) ≥ 2
observation_independent(runs)     ≡ leaf §5: DISTINCT observation_lineage_root_id ≥ 2
unknown lineage                    : leaf note5 — 不明系譜を既定で independent に格上げしない（保守化）
```
**consumer 規約（normative・写像）**：
```text
XMODAL confirmed（→ XMODAL v0.6 が leaf を直接 pin）:
  D2 独立＝ leaf content_independent（content_independence_group の DISTINCT ≥ 2）。
  observation pipeline（OCR/parser/normalization）の distinct は confirmed の独立票に数えない。
XDOC eligibility（XDOC v0.9 + addendum が leaf 準拠）:
  content_independence    ＝ leaf content_independent（content_lineage_binding 由来）
  observation_independence＝ leaf observation_independent（raw_input_hash 由来 root）
```
- **G_RECONCILE_INDEP_DELEGATED**：独立性の定義・カウントは leaf DD `DD-INDEP-LINEAGE-001` が正本。本付録・XMODAL・XDOC は leaf を pin して consume し、独自に再定義しない。
- **G_RECONCILE_LEAF_PIN_REQUIRED**：consumer は leaf を id+version+content_hash+acceptance_ref で pin（§7）。pin 欠落は Phase1 gate fail。
- v0.2 §1 にあった `content_origin_root`/`observation_lineage_root`/同一 collapse の定義は **leaf §2〜§5 に移管**（本付録からは削除・leaf が単一の正本）。

## 2. snapshot / release（R2・law を typed contract に・v0.2 承継）
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
- XMODAL D2 の `law_snapshot/source_version/valid_at` は本 contract に束ねる（XMODAL v0.6 で参照）。
- **G_RECONCILE_LAW_SNAPSHOT_TYPED**：法令版は kind ラベルだけでなく bitemporal（captured/known/valid）＋hash を持つ。
- TODO（owner・HOLD）：source_snapshots に snapshot_kind=law_authority＋上記列（DDL は HOLD）。

## 3. block_type → facet 写像（R3・PASS_WITH_NOTES・v0.2 承継）
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

## 4. coverage 用語（R4・PASS・v0.2 承継）
`projection_typing_coverage`（LAYOUT・射影の型付け被覆）／ `range_coverage`（XDOC・範囲被覆）を分離。**G_RECONCILE_COVERAGE_TERMS**。

## 5. naming（R5・PASS_WITH_NOTES・v0.2 承継）
- 新規 schema/コードは `asset_id` / `source_text_revision_id` を正本。
- **既存 ID を再発行しない**（rename はしない）。**typed ref＋namespace＋version を保持**（旧名は alias 写像で吸収・物理 ID は不変）。
- **G_RECONCILE_NAMING_NO_REMINT**：命名統一は alias レベル。既存 mint 済 ID の再生成禁止。

## 6. ★field-level canonicalization registry（R6・MODIFY 反映・v0.2 から昇格）
v0.2 の「artifact ごと profile」を維持しつつ、**畳み方は配列ごと（field_path 単位）に registry で宣言**する。配列を一律 sort（誤独立や順序破壊）も一律 preserve（集合の偽の重複）も禁止。
```text
canonicalization_profile
  profile_id / profile_version
  hash_algo(sha256) ; unicode_form(NFC) ; json_key_order(codepoint_asc)
  field_canonicalization_registry[]        # ★field_path ごとの畳み方を宣言
field_canonicalization_registry entry:
  field_path                # 例 evidence_refs / members / pages / reading_order
  collection_kind           # set | multiset | sequence
  # set      : sort + dedup（順序・重複は非情報）
  # multiset : sort、dedup しない（重複は情報・順序は非情報）
  # sequence : 順序保持・dedup しない（順序が情報）
artifact each: { canonicalization_profile_id ; canonicalization_profile_version ; hash_scope_version }
```
既定の field 分類（leaf/三部作で共有）：
| field_path | collection_kind | 理由 |
|---|---|---|
| evidence_refs[] | set | 根拠参照は集合（順序・重複は非情報） |
| content_independence_group の集計 | set | DISTINCT カウント＝集合 |
| observation_lineage_root の集計 | set | DISTINCT カウント＝集合 |
| members[] / pages[] / reading_order[] | sequence | 順序が情報（XDOC §5 symmetric/directional 規則に従属） |
| collapse_rules の適用列 | multiset | 適用回数が情報・順序は非情報 |
- **G_RECONCILE_FIELD_CANONICAL_REGISTRY**：各配列 field は registry の collection_kind（set|multiset|sequence）に従って canonicalize。未登録 field_path は canonicalize 対象に入れない（明示登録必須）。
- **G_RECONCILE_ORDERED_PRESERVE**：sequence は sort しない。set/multiset のみ sort（dedup は set のみ）。
- **G_RECONCILE_NO_RETRO_REHASH**：既存 ID を別 profile/registry で再計算・読替えしない。変更時は explicit crosswalk（旧→新 ID 対応表）を作る。
- 注：leaf DD §7 は本 §6 registry を consume（binding_id 等のハッシュは field_path→collection_kind に従う）。

## 7. dependency exact pin（R7・MODIFY 反映・leaf DD 追加）
```text
dependency_pin
  dependency_id               # 例 DD-INDEP-LINEAGE-001
  version                     # 具体版（latest 等の語は不可）
  content_hash                # その版の content hash（§6 profile に従う）
  acceptance_ref              # accepted の証跡（RESULT file_id 等）
# 空欄/未確定があれば Phase 1 gate を FAIL させる（投入させない）
```
| dependency | version | content_hash | acceptance_ref |
|---|---|---|---|
| **DD-INDEP-LINEAGE-001** | **v0.1** | （manifest で確定） | **accepted 2026-06-25 / RESULT 2306834650821（DDINDEP_PASS_WITH_NOTES）** |
| DD-LITID-001 | （owner 記入）TBD | TBD | TBD |
| DD-LITLINK-001 | （owner 記入）TBD | TBD | TBD |
| DD-LAYOUT-001 | v0.5 | （記入）| accepted 2026-06-19 |
| DD-XMODAL-001 | v0.6 | （manifest で確定）| leaf pin・joint manifest 同時 |
| DD-XDOC-001 | v0.9（+addendum）| （記入）| accepted 2026-06-24 / RESULT 2303550755480 |
- **G_RECONCILE_DEP_PIN_EXACT**：id+version+content_hash+acceptance_ref を全て埋める。空欄は Phase1 gate fail。content_hash は joint release manifest（§10）で確定する。

## 8. ゲート一覧
INDEP_DELEGATED / LEAF_PIN_REQUIRED / SNAPSHOT_HOME / LAW_SNAPSHOT_TYPED / FACET_MAP / NO_HEADER_FOOTER_ABSENCE / COVERAGE_TERMS / NAMING_NO_REMINT / FIELD_CANONICAL_REGISTRY / ORDERED_PRESERVE / NO_RETRO_REHASH / DEP_PIN_EXACT。

## 9. 受入試験（全自動 PASS が条件・監査必須 fixture 反映）
1. 独立性の定義が本付録に**無い**こと（leaf DD §5 を pin して参照しているのみ）。
2. consumer（XMODAL/XDOC）が leaf を id+version+content_hash+acceptance_ref で pin している（欠落で gate fail）。
3. canonicalization：**sequence field（members/pages/reading_order）を sort しない**・**set field（evidence_refs）は sort+dedup**・**multiset は sort のみ dedup しない**。
4. 未登録 field_path は canonicalize されない（registry 明示登録必須）。
5. dependency：version/content_hash/acceptance_ref のいずれか欠落 → Phase 1 gate FAIL。
6. facet：Page-header/footer 除外 range を absence/difference 証拠に使えない。
7. snapshot：law_authority_snapshot が bitemporal（captured/known/valid）＋revision_set_hash＋source_hash を持つ。
8. naming：asset_id/source_text_revision_id 統一が alias レベル（既存 ID 再発行なし）。
9. block_type→facet 写像が一意・未収載は unknown。
10. corpus_snapshot_id/release_id が control.* に一意写像。

## 10. GO / HOLD / loop_state
- **GO**：v0.3 付録 ratify／leaf DD pin 整合（XMODAL v0.6・XDOC addendum と相互 pin）／field-level canonicalization registry 表／**joint release manifest で trilogy+leaf の content_hash を atomic に確定**。
- **HOLD**：v0.3 ratify 前の Phase 1 実データ／DDL（source_snapshots law_authority 列追加含む）／DB/mint/OCR/embedding/production/promotion/claim-support／既存 ID 一括再生成。
- loop_state = **patched（v0.3・R1 を leaf へ委譲・循環解消・field-level canonical）→ 再投函（DDRECONCILE 再監査）候補**。XMODAL v0.6・XDOC addendum・joint manifest と対で監査。

<!-- END INLINE EMBED: DD-TRILOGY-RECONCILE-001 v0.3 -->
