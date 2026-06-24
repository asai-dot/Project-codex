---
request_id: DD-TRILOGY-RECONCILE-001-v0.1-20260624
topic: 設計三部作（LAYOUT/XMODAL/XDOC）整合付録 v0.1 — 時的ドリフト6点（独立性2軸統一・snapshot住所・block_type→facet写像・命名/canonical/版固定）の独立意味監査
gate: DDRECONCILE
status: queued
result_expected_filename: 20260624_DD-TRILOGY-RECONCILE-001_v0.1_DDRECONCILE_RESULT.md
target_mode: inline_embedded
source_hash: sha256:3a78e12734efd5e5a839840f7bbf4b71d632eb3cf8f9c87d3309ccfb852d8c39
review_scope:
  include:
    - R1 独立性: shared_external_source_family（単一registry+independence_axis タグ）が XMODAL単一registry と XDOC 2軸を矛盾なく統合できるか。family_kind→axis 写像の網羅性。confirmed は content_origin DISTINCT のみ・observation は数えない、の consumer 規約の正当性
    - R2 snapshot: corpus_snapshot_id/law_snapshot_id を control.source_snapshots(snapshot_kind で識別)・release_id を control.releases に束ねる住所確定の妥当性。law_authority 区分新設の是非
    - R3 block_type(DocLayNet11)→facet(4) 写像表の正当性（Page-header/footer 除外・structure=toc_node ツリー・未収載 unknown）
    - R4 coverage 用語分離（projection_typing_coverage vs range_coverage）
    - R5 命名統一（asset_id / source_text_revision_id 正本・旧名写像）
    - R6 canonicalization 横断宣言（全 DD ハッシュ/ID を XDOC §5 に従わせる）
    - R7 depends_on 版固定（DD-LITID/DD-LITLINK）
    - 付録が各 DD の定義を狭めず横断写像のみ与える設計か（OWNERSHIP 侵食なし）
  exclude:
    - DDL（source_snapshots の law_authority 区分追加含む）/DB/mint/OCR/embedding/production（HOLD）
    - 各 DD 本体の再監査（LAYOUT v0.5 / XMODAL v0.4 / XDOC v0.9 は accepted・本付録は横断整合のみ）
regression_anchors:
  - 横断整合監査 docs/research/trilogy_consistency_stability_audit_20260624.md
  - DD-LAYOUT-001 v0.5 accepted / DD-XMODAL-001 v0.4 accepted / DD-XDOC-001 v0.9 accepted（PASS_WITH_NOTES Box 2303550755480）
  - 本番 control.source_snapshots(snapshot_kind raw_source/normalized_export)/releases(release_id)
  - DD-LITID_TOC_RECONCILIATION / DD-LITID_FORWARD_ROADMAP v0.2/v0.3（asset 同定 workstream）
self_doubt:
  - 独立性を共有 registry に一元化する際、XDOC content_origin_assertion.origin_object_type{statute,case,manuscript,edition,commentary,dataset} と family_kind の粒度差（cited object の種別 vs source-system family）を content_origin axis に束ねて十分か
  - XMODAL を v0.5 小パッチで2軸化する案と、付録で写像吸収する案のどちらが手戻り最小か
  - law_snapshot を source_snapshots の snapshot_kind=law_authority に載せる設計が、法令版時点（valid_at）の時系列管理に十分か
  - Formula を text facet に寄せたが、数式比較を別 facet にすべきか
questions_for_gpt:
  - R1〜R7 の写像/命名/版固定が三部作の実データ投入前ゲートとして十分か
  - 独立性共有 registry の axis タグ + consumer 規約で XMODAL confirmed と XDOC eligibility の独立性判定が一意に整合するか
  - 付録方式（各 DD 大改訂せず横断写像を束ねる）が妥当か、それとも各 DD への直接パッチが必要な項目があるか
  - 残る cross-DD ドリフト（本監査が見落としたもの）があれば指摘
decision_requested:
  - PASS可否 / R1〜R7 の個別妥当性 / 付録方式の是非 / 追加ドリフト指摘
expected_label: DDRECONCILE_PASS_WITH_NOTES または DDRECONCILE_MODIFY_REQUIRED
---

# DDRECONCILE 監査依頼: DD-TRILOGY-RECONCILE-001 v0.1（三部作整合付録・時的ドリフト解消）

- target_mode: inline_embedded（全文を下記に逐語埋め込み）。authoritative bytes = GitHub `asai-dot/Project-codex` ブランチ `claude/daiichi-houki-fact-system-qcn7ph` `docs/dd_candidates/DD-TRILOGY-RECONCILE-001_trilogy_consistency_reconciliation_candidate_v0.1_20260624.md`（sha256:3a78e127…）。
- 背景: 3 DD は時系列バラバラに作成（XMODAL v0.4 が XDOC v0.5→v0.9 の後発精緻化を未取込）。横断整合監査で6ドリフトを検出、本付録で束ねて解消する。各 DD は accepted で再監査対象外、本付録は横断写像のみ。

---

<!-- BEGIN INLINE EMBED: DD-TRILOGY-RECONCILE-001 v0.1 -->

# DD-TRILOGY-RECONCILE-001 v0.1 — 設計三部作 整合付録（LAYOUT/XMODAL/XDOC の時的ドリフト解消）candidate

> **id**: DD-TRILOGY-RECONCILE-001 / **version**: candidate v0.1 / **supersedes**: なし（新規・付録）
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-24 JST
> **gate**: 設計のみ candidate。各 DD を大改訂せず、**DD 間の写像・命名・版固定を束ねる付録**。DDL/DB/Box mutation/mint/OCR/embedding/production/promotion/claim-support は **HOLD**。
> **目的**: 横断整合性監査（`docs/research/trilogy_consistency_stability_audit_20260624.md`）が検出した6ドリフト（§1〜§7）を、実データ投入前に閉じる。XMODAL v0.4 が XDOC 後発精緻化（v0.5→v0.9）を未取込なことに起因する時的ずれを解消。
> **depends_on / governs**: DD-LAYOUT-001 v0.5（accepted）/ DD-XMODAL-001 v0.4（accepted）/ DD-XDOC-001 v0.9（accepted）/ DD-LITID-001 / DD-LITLINK-001。本付録は各 DD の定義を**狭めず、横断の正本写像を与える**。

---

## 0. 反映ドリフト一覧（監査 §1〜§7）
| R | ドリフト | 重大度 | 本付録 § |
|---|---|---|---|
| R1 | 独立性: XMODAL 単一 registry（content/pipeline 混在）vs XDOC 2軸 | 🔴 | §1 |
| R2 | snapshot: corpus_snapshot_id↔source_snapshot_id 別名・law_snapshot 住所未定 | 🔴 | §2 |
| R3 | block_type(DocLayNet11)→facet(4) 写像未定義 | 🔴 | §3 |
| R4 | "coverage" 意味衝突（型付け被覆 vs 範囲被覆） | 🟡 | §4 |
| R5 | asset/revision 命名不統一 | 🟡 | §5 |
| R6 | canonicalization 横断未宣言 | 🟡 | §6 |
| R7 | depends_on 版固定なし | 🟡 | §7 |

## 1. ★独立性＝共有 family registry（2軸・R1）
XMODAL の `external_source_family_registry` と XDOC の 2軸（content_independence × observation_independence）を、**1つの共有 registry** に統合。各 family に **independence_axis タグ**を付け、両 DD がこれを consume する。

```text
shared_external_source_family            # 正本（人手管理・両 DD 共有）
  family_id                   # required; string
  family_kind                 # required; §下記 enum
  independence_axis           # required; content_origin | observation_pipeline   ★axis タグ
  independence_notes          # optional; string

family_kind = statute_text | case_law | legal_dictionary | classification_scheme
            | commentary_publisher | editorial_source | court_db        # → content_origin
            | ocr_engine | parser | normalization_profile | scan_source  # → observation_pipeline
```
**family_kind → independence_axis 写像（normative）**
```text
content_origin       : statute_text, case_law, legal_dictionary, classification_scheme,
                       commentary_publisher, editorial_source, court_db
observation_pipeline : ocr_engine, parser, normalization_profile, scan_source
```
**consumer 規約（normative）**
```text
XMODAL confirmed:
  external_source_count ≥ 2 で数える family は independence_axis=content_origin の DISTINCT family。
  （D2 外部証拠＝内容起源の独立性。OCR エンジン等の観測系は confirmed の独立票に数えない。）
XDOC eligibility:
  content_independence    ＝ content_origin family が DISTINCT（content_origin_assertion 由来）
  observation_independence＝ observation_pipeline family が DISTINCT（member_pipeline_provenance 由来）
```
**crosswalk（既存語彙 → 共有 registry）**
| 既存 | 所属 | independence_axis |
|---|---|---|
| XMODAL family_kind: statute_text/legal_dictionary/commentary_publisher/editorial_source/court_db/classification_scheme | XMODAL registry | content_origin |
| XMODAL family_kind: ocr_engine | XMODAL registry | observation_pipeline |
| XDOC content_origin_assertion.origin_object_type {statute,case,manuscript,edition,commentary,dataset} | XDOC content軸 | content_origin |
| XDOC member_pipeline_provenance {ocr_engine,parser,normalization_profile,scan_source} | XDOC observation軸 | observation_pipeline |
- **G_RECONCILE_INDEP_SINGLE_REGISTRY**：独立性カウントは shared_external_source_family を唯一の正本とし、axis を跨いで family を混在カウントしない。
- **反映**：XMODAL は v0.5 小パッチで family_kind に independence_axis を付す（2軸化）。本付録が正本写像。

## 2. snapshot / release の住所確定（R2）
```text
corpus_snapshot_id  → control.source_snapshots.source_snapshot_id（snapshot_kind ∈ {raw_source, normalized_export}・例 source_system=bencom-library）
law_snapshot_id     → control.source_snapshots.source_snapshot_id（snapshot_kind = law_authority・新区分）  ★別軸（法令原文版）
release_id          → control.releases.release_id（✅ 既に一致）
```
- **corpus_snapshot と law_snapshot は別軸**：corpus＝文献コーパスの版、law＝法令/判例 authority の版。両者とも `control.source_snapshots` に載せ、`snapshot_kind` で識別。
- XDOC `corpus_snapshot_id`・XMODAL `law_snapshot_id` は **DD 表記を維持しつつ、正本は control.source_snapshots**（alias）。
- **G_RECONCILE_SNAPSHOT_HOME**：全 DD の snapshot/release は control.* を正本とし、DD ローカルに別実体を作らない。
- 投入前 TODO（owner）：source_snapshots に `snapshot_kind=law_authority` を1区分追加（DDL は HOLD・設計合意のみ）。

## 3. ★block_type → facet 写像（R3・データ投入の前提）
LAYOUT `block_type`（DocLayNet 11＋ALO subtype）→ XDOC `facet`（structure|text|table|figure）の正本写像：
| block_type | facet |
|---|---|
| Table | table |
| Picture | figure |
| Text / List-item / Caption / Footnote | text |
| Section-header / Title | structure |
| Formula | text（数式は本文系・別扱い要時は subtype で） |
| Page-header / Page-footer | （除外・facet 比較対象外） |
| ALO subtype（注/柱/条文囲み/判例引用ブロック/要旨） | base ラベルの facet に従う（注→text, 条文囲み→text, 判例引用→text, 要旨→text） |
- **structure facet は block 単独でなく toc_node ツリー**（Section-header/Title＋biblio.toc_nodes の親子）から構成。
- **G_RECONCILE_FACET_MAP**：XDOC が LAYOUT block を facet 別に取る時、本表に従う。未収載 block_type は facet 比較に入れない（unknown 扱い・断定しない）。

## 4. "coverage" 用語の曖昧性除去（R4）
| 用語（正本） | DD | 意味 |
|---|---|---|
| `projection_typing_coverage` | LAYOUT | 射影母集団のうち型付け済みブロックの割合（未型付けを存在しないと断定しない） |
| `range_coverage` | XDOC | member の required_ranges を covered_ranges が包含する被覆（coverage_assessment 系） |
- 矛盾なし・別概念。実装/データでは上記正本語で区別（DD 本文の "coverage" は文脈限定で従来表記可）。
- **G_RECONCILE_COVERAGE_TERMS**：横断文書/コードで coverage を使う時は projection_typing / range を明示。

## 5. asset / revision 命名統一（R5）
```text
asset 同定        : asset_id            （正本。LAYOUT asset_ref/asset_variant は asset_id+variant に対応・DD-LITID が asset identity 正本）
テキスト版        : source_text_revision_id （正本。XDOC member_tuple の text_revision は source_text_revision_id の別名→以後 source_text_revision_id へ寄せる）
```
- **G_RECONCILE_NAMING**：新規 schema/コードは asset_id / source_text_revision_id を使用。既存 DD 本文の旧名は本付録の正本へ写像。

## 6. canonicalization 横断宣言（R6）
- **全 DD のハッシュ・ID は XDOC v0.9 §5 の canonicalization に従う**：`sha256` / Unicode `NFC` / JSON object key コードポイント昇順 / 区切り最小 / 配列は規定キーで安定ソート。
- 対象：LAYOUT hash bundle 5種・XMODAL の id/hash・XDOC observation/coverage/support id。
- 既証：適合性ハーネスは全モジュールで単一 canonical_json を共有済（de-facto 実装一致）。
- **G_RECONCILE_CANONICAL_ONE**：cross-DD のハッシュ照合は単一 canonicalization 前提。

## 7. depends_on 版固定（R7）
```text
DD-LITID-001   : 版固定（実データ投入時点の latest accepted を pin）。asset 同定・FRBR/WEMI の正本。
DD-LITLINK-001 : 版固定（同上）。外部/法的リンクの正本。
```
- LITID は活発進行（DD-LITID_TOC_RECONCILIATION・FORWARD_ROADMAP v0.2/v0.3）→ 版ずれ波及大。
- **G_RECONCILE_DEP_PIN**：三部作の depends_on は版を明記。LITID/LITLINK の版更新時は本付録を再確認。
- owner TODO：投入時に LITID/LITLINK の accepted 版番号を確定し本付録へ記入。

## 8. ゲート一覧
INDEP_SINGLE_REGISTRY / SNAPSHOT_HOME / FACET_MAP / COVERAGE_TERMS / NAMING / CANONICAL_ONE / DEP_PIN。
（いずれも cross-DD 写像の正本宣言。各 DD のローカルゲートを上書きせず、横断の整合を保証。）

## 9. 受入試験（全自動 PASS が条件）
1. shared_external_source_family の全 family_kind が content_origin / observation_pipeline のいずれか一意に写像（§1 表に未収載 kind なし）。
2. XMODAL confirmed の独立カウントが content_origin axis の DISTINCT family のみ／observation_pipeline は数えない、を本付録だけから判定できる。
3. corpus_snapshot_id / law_snapshot_id / release_id がそれぞれ control.* の一意 column に写像（別名衝突なし・law は snapshot_kind で識別）。
4. DocLayNet 11 の各ラベル＋Page-header/footer 除外が facet に一意写像（未収載ラベルは unknown 扱い）。
5. coverage 用語が projection_typing_coverage / range_coverage に一意分離。
6. asset_id / source_text_revision_id が正本、旧名（asset_ref/text_revision）が写像で吸収される。
7. 全 DD のハッシュ/ID が単一 canonicalization（XDOC §5）に従う宣言が存在。
8. depends_on（DD-LITID/DD-LITLINK）に版固定の枠がある。

## 10. GO / HOLD / loop_state
- **GO**：本付録の design ratify／XMODAL v0.5 小パッチ（§1 2軸化）／block_type→facet・snapshot 住所の設計合意。
- **HOLD**：DDL（source_snapshots の law_authority 区分追加含む）／DB/mint/Box mutation／OCR/embedding/production／promotion／claim-support。
- loop_state = **candidate（新規付録）→ GPT 監査（gate=DDRECONCILE）候補**。PASS 後に各 DD へ「本付録準拠」の一文を付し、Phase 1 実データ着手。

<!-- END INLINE EMBED: DD-TRILOGY-RECONCILE-001 v0.1 -->
