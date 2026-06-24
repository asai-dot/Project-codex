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
