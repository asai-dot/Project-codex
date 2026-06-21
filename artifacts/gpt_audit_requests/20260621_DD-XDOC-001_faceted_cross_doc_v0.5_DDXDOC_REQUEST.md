---
request_id: DD-XDOC-001-v0.5-20260621
supersedes_request_id: DD-XDOC-001-v0.4-20260620
topic: faceted cross-document comparison & alignment candidate v0.5（round4 P0契約閉鎖・自己完結版）の独立意味監査
gate: DDXDOC
status: queued
result_expected_filename: 20260621_DD-XDOC-001_faceted_cross_doc_v0.5_DDXDOC_RESULT.md
target_mode: inline_embedded
source_hash: sha256:c32a8fa5cfeab8bc3e32fbf18c030f3971f590fe29ca6459ccdbfaff446ffc2d
prior_result_file_id: 2299235092570
review_scope:
  include:
    - P0-1: purpose_target_compatibility + eligibility_policy_rule（priority規則・default deny・各セルの単一result_eligibility）の完全性
    - P0-2: xdoc_independence_assessment オブジェクト（effective_status/effective_value・stale時fail-closed・invalid gate）の型正当性
    - P0-3: alignment_observation_id に comparison_intent が含まれたか。symmetric時のside正規化とcardinality再導出（n_one消去）が受入試験9を満たすか
    - P0-4: use_assessment 履歴contract（use_assessment_key_id/assessment_revision_id/revision_seq/status/supersedes）によるsilent mutation禁止の完全性
    - P0-5: method_capability_rule（CDC+content_hash複合・R-CDC-STANDALONE/R-CDC-HASH）とorigin×candidate→reviewed mapping table（規範16行）の正当性
    - P0-6: coverage_assessment（coordinate_space・selector_state・quality_score・covered/unknown_ranges型）とcoverage_policy（completeness_rule式）の自己完結性
    - P0-7: xdoc_support_edge（undirected・UNIQUE制約・canonical_low/high）とcluster_policy（schema全フィールド）の一意性とpairwise_support_coverage分子定義
    - P0-8: slash shorthand完全除去・origin_object_type/id/version分離・cluster_lineage_events[]配列化・detection_state導入
    - 受入試験12本が本文だけから全自動実装可能か（特に#1,#3,#6,#7,#9,#10）
    - purpose_target_compatibility の allowed=false 組合せで validation error（暗黙許可なし）
    - frbr_work_candidate×frbr_work の eligible 条件（human_reviewed必須・外部multi-facet契約の位置付け）
  exclude:
    - DDL/DB/mint/Box mutation/OCR/embedding/production実装（HOLD）
    - block_ref current / LITLINK accepted / FRBR/LITID identity promotion（HOLD）
    - DD-LAYOUT-001 v0.5 / DD-XMODAL-001 v0.4 の内容変更（依存先・既accepted）
regression_anchors:
  - DD-XDOC-001 v0.4 REQUEST（Box 2297872292822）
  - DD-XDOC-001 v0.4 RESULT（Box 2299235092570）label=DDXDOC_MODIFY_REQUIRED
  - DD-XDOC-001 v0.3 RESULT（Box 2297356004616）label=DDXDOC_MODIFY_REQUIRED
  - DD-LAYOUT-001 v0.5 accepted（Block_ref/projection/coverage定義の安定アンカー）
  - DD-XMODAL-001 v0.4 accepted（2軸independence/evaluation_purpose分離の先行定義）
self_doubt:
  - frbr_work_candidate×frbr_work の eligible 条件が「単一alignment use_assessment = 証拠の1片」で留まっており、multi-facet cluster契約が別途必要な点をGPTが blocking とみなすか
  - eligibility_policy_rule の priority=50 行で review_state=reviewed を条件に入れた妥当性（proof_corroboration等で自動判定を封じる意図）
  - method_capability_rule の required_companion_method_ids=[] の meaning（empty=単独可）が明確か
  - coverage_complete の unknown_ranges=[] 要件が受入試験6を満たすに十分か
questions_for_gpt:
  - P0-1〜P0-8 の全 blocking が今回で閉鎖されたか
  - 受入試験1,3,6,7,9,10 が本文のみで決定的に実装できるか
  - purpose_target_compatibility の allowed=false / default deny の表現で暗黙許可を除去できているか
  - xdoc_independence_assessment の effective_status=stale 時の effective_value=unknown（fail-closed）はproof安全境界として十分か
  - PASS 圏到達可否、追加 must_fix があれば列挙
decision_requested:
  - PASS可否 / P0-1〜P0-8の個別閉鎖判定 / 受入試験12本の実装可能性判定 / 追加blocking（あれば）
expected_label: DDXDOC_PASS_WITH_NOTES または DDXDOC_MODIFY_REQUIRED
---

# DDXDOC 監査依頼: DD-XDOC-001 v0.5（faceted cross-document comparison & alignment・round4 P0契約閉鎖版）

- target_mode: inline_embedded（全文を下記に逐語埋め込み）。authoritative bytes = GitHub `asai-dot/Project-codex` ブランチ `claude/daiichi-houki-fact-system-qcn7ph` `docs/dd_candidates/DD-XDOC-001_faceted_cross_document_comparison_candidate_v0.5_20260621.md`（sha256:c32a8fa5…）。

---

<!-- BEGIN INLINE EMBED: DD-XDOC-001 v0.5 -->

# DD-XDOC-001 v0.5 — faceted cross-document comparison & alignment（round4 P0契約閉鎖・自己完結）candidate

> **id**: DD-XDOC-001 / **version**: candidate v0.5 / **supersedes**: v0.4
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-21 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/学習/embedding/production pair generation/clustering/FRBR・DD-LITID・DD-LITLINK 昇格/block_ref current 昇格/evidence・legal claim support は **HOLD**。
> **改訂理由（v0.4→v0.5）**: GPT Pro 再監査 `DDXDOC_MODIFY_REQUIRED`（RESULT Box 2299235092570）の P0-1〜P0-8 を反映。新規概念なし。purpose-target 互換表・policy rule table・独立性 assessment オブジェクト・use assessment 履歴契約・method 複合 capability rule・coverage 型・cluster policy・slash shorthand 除去・origin_object_ref 型分離を閉鎖。
> **depends_on**: DD-LAYOUT-001 v0.5 / DD-XMODAL-001 v0.4 / DD-LITID-001 / DD-LITLINK-001（いずれも定義を狭めない）。

---

## 0. round4 P0 反映（P0-1〜P0-8）
| P | 指摘 | § |
|---|---|---|
| P0-1 | eligibility matrix: purpose/target 再混在・非決定セル・default deny 欠落・priority 未定 | §7 |
| P0-2 | 独立性 assessment 規範オブジェクト欠落・effective=stale 型違反 | §3 |
| P0-3 | observation ID: comparison_intent 欠落・symmetric cardinality 正規化未定 | §5 |
| P0-4 | use assessment 履歴・撤回契約欠落（silent mutation） | §6 |
| P0-5 | method registry: 複合 capability rule・content_hash 行・origin×candidate→reviewed mapping table 欠落 | §8 |
| P0-6 | coverage contract: 型・coordinate_space・品質・complete 判定式未定 | §9 |
| P0-7 | cluster support graph: edge 一意性・undirected/directed・pairwise 分子定義・policy schema 未定 | §10 |
| P0-8 | slash shorthand 除去・computed_state 型不明・origin_object_ref 型不分離 | §2〜§6 全域 |

## 1. オブジェクト分離（関心の分離）
- **xdoc_alignment**：observation（何を・どの method で・どの member 間で検出したか）。不変。`alignment_observation_id`。
- **xdoc_use_assessment**：alignment に 1:N（evaluation_purpose × target ごとの eligibility＋policy）。**履歴 contract 付き**（P0-4）。
- **xdoc_independence_assessment**：alignment × axis ごとの computed/reviewed/effective 独立性（P0-2 新規）。
- **content_origin_assertion** / **member_pipeline_provenance**：member 単位の証拠。独立性は**これらから導出**（手入力しない）。
- **coverage_assessment** + **coverage_policy**：member-keyed。型付き座標・品質・complete 判定式（P0-6）。
- **xdoc_cluster** ＋ **xdoc_support_edge** ＋ **cluster_policy**：support graph（P0-7）。
- **method_registry** / **method_capability_rule** / **enum registry**（canonical・単一定義）。

## 2. canonical enums（単一定義・全所で同一・P0-8）
```text
facet                  = structure | text | table | figure
direction              = a_to_b | b_to_a | symmetric
cardinality            = one_one | one_n | n_one | n_m
  # symmetric 時 ID canonicalization: side 正規化後に one_n/n_one は one_n のみ（§5）
comparison_intent      = near_duplicate | text_reuse | semantic_overlap | edition_alignment
                       | structure_comparison | table_template | figure_reuse | citation_candidate
                       # independent_corroboration は intent でない（evaluation_purpose §7）
candidate_relation_type= near_duplicate | lexical_overlap | semantic_proximity
                       | segment_identity_candidate | table_structure_match
                       | figure_near_duplicate | visual_proximity | structure_edit
reviewed_relation_type = quote | reprint | adaptation | common_template | same_expression
                       | edition_variant | same_topic | template_instance | figure_reuse
                       | near_duplicate | none
                       # none = レビュー済み・非該当。null = 未レビュー。区別必須。
origin_relation        = quote | reprint | adaptation | common_template | same_expression
evaluation_purpose     = proof_corroboration | extraction_corroboration | litlink_candidate
                       | edition_resolution | formobj_variant_candidate | frbr_work_candidate | dedup
target                 = proof | litlink | frbr_work | litid_identity | formobj_variant | block_ref
independence_value     = independent | shared | partially_shared | unknown
eligibility            = eligible | ineligible | hold
review_state           = unreviewed | reviewed | overridden | stale
effective_status       = current | stale | invalid
  # stale: computed_input_fingerprint が現在の証拠と不一致 → effective_value = unknown（fail-closed）
  # invalid: reviewed ≠ computed かつ review_reason_code なし → gate で弾く
assessment_status      = active | superseded | revoked | stale
axis                   = content | observation
side                   = a | b
selector_state         = complete | partial | failed | not_applicable
coordinate_space       = page | char_offset | token | table_cell | figure_region
lineage_type           = split | merge | supersedes
detection_state        = detected | verified | rejected
```

## 3. 独立性＝2軸×3層 + xdoc_independence_assessment（P0-2・P0-8）

両軸とも **independence_value** を使用（名称統一）。`stale` は `effective_value` ではなく `effective_status` に分離。

```text
xdoc_independence_assessment
  independence_assessment_id  # required; sha256(canonical_json(
                              #   alignment_observation_id, axis,
                              #   computed_policy_id, computed_policy_version,
                              #   computed_input_fingerprint))
  alignment_observation_id    # required; FK → xdoc_alignment
  axis                        # required; content | observation
  computed_value              # required; independence_value
  computed_policy_id          # required; string
  computed_policy_version     # required; string
  computed_evidence_refs[]    # required; assertion_id[] or member_ref[] に応じ
  computed_input_fingerprint  # required; sha256(computed_evidence_refs + policy_id + policy_version)
  reviewed_value              # optional; independence_value | null
  review_state                # required; review_state enum（初期 = unreviewed）
  review_reason_code          # conditional required; review_state ∈ {overridden, stale} のとき required
  review_note                 # optional; string
  reviewed_by                 # conditional required; review_state = reviewed のとき required
  reviewed_at                 # conditional required; review_state = reviewed のとき required
  effective_value             # required; independence_value（下記算定規則）
  effective_status            # required; effective_status enum
  supersedes_assessment_id    # optional; null or 前の independence_assessment_id
```

**effective_value 算定規則**：
```text
reviewed_value ≠ null → effective_value = reviewed_value
reviewed_value = null → effective_value = computed_value
computed_input_fingerprint ≠ current_fingerprint → effective_status = stale; effective_value = unknown（fail-closed）
reviewed_value ≠ computed_value AND review_reason_code IS NULL → effective_status = invalid
```

- content と observation は**別軸**（独立執筆×同一OCR＝content independent / observation shared）。
- **G_XDOC_INDEP_DERIVED_FROM_EVIDENCE**：computed_value は evidence_refs ＋ policy 由来（手入力禁止）。
- **G_XDOC_INDEP_CONTRADICTION**：effective_status=invalid の assessment を有する alignment の全 use_assessment は eligibility=hold 以上（eligible 禁止）。

## 4. member 単位の証拠（P0-8: slash 除去・origin_object_ref 型分離）
```text
content_origin_assertion
  assertion_id                # required; string（canonical ID）
  subject_member_ref          # required; member@asset 参照
  subject_passage_ref         # required; DD-LAYOUT text_pos selector
  origin_object_type          # required; statute | case | manuscript | edition | commentary | dataset
  origin_object_id            # required; string
  origin_object_version       # required; string
  origin_passage_ref          # required; string（DD-LAYOUT selector または外部 ref）
  origin_relation             # required; origin_relation enum
  evidence_pointer_refs[]     # required; evidence object ID の配列（別 field）
  evidence_hashes[]           # required; sha256 of evidence objects at assertion time（別 field）
  detection_method            # required; string
  detection_version           # required; string
  confidence                  # required; float 0.0-1.0
  detection_state             # required; detection_state enum
  review_state                # required; review_state enum

member_pipeline_provenance
  member_ref                  # required; member@asset
  scan_source_id              # required; string
  ocr_engine                  # required; string
  ocr_version                 # required; string
  parser                      # required; string
  parser_version              # required; string
  normalization_profile_id    # required; string
  normalization_profile_version# required; string
  tokenization_profile_id     # required; string
  tokenization_profile_version# required; string
  source_text_revision_id     # required; string
  evidence_refs[]             # required; string[]
```

- **G_XDOC_INDEP_DERIVED_FROM_EVIDENCE**：pair/group の独立性 computed_value は evidence_refs ＋ policy 由来（状態値だけの手入力禁止）。

## 5. xdoc_alignment（observation・不変 ID・P0-3）
```text
xdoc_alignment
  alignment_observation_id    # required; §下記 canonical 直列化
  schema_version              # required; string
  facet                       # required; facet enum
  comparison_intent           # required; comparison_intent enum（ID 材料に含む・P0-3）
  direction                   # required; direction enum
  cardinality                 # required; cardinality enum（symmetric 時は §下記 canonical 値）
  members_a[]                 # required; [{asset_id, text_revision, unit_id}]
  members_b[]                 # required; [{asset_id, text_revision, unit_id}]
  edit_script[]               # optional; [{op: insert|delete|move|rename|split|merge, ...}]
  method                      # required; string
  method_version              # required; string
  parameter_profile_hash      # required; sha256
  normalization_profile_id    # required; string
  normalization_profile_version# required; string
  tokenization_profile_id     # required; string
  tokenization_profile_version# required; string
  candidate_relation_types[]  # required; candidate_relation_type[]（method 出力候補・reviewed でない）
  similarity                  # required; float（calibration_id のスケール内でのみ有意）
  calibration_id              # required; string
  calibration_version         # required; string
  score_components_ref        # required; string（詳細スコア参照先）
  corpus_snapshot_id          # required; string
  release_id                  # required; string
```

**canonical alignment_observation_id（P0-3）**
```text
alignment_observation_id = sha256(canonical_json(
  schema_version, facet, comparison_intent,        # comparison_intent を ID 材料に追加（P0-3）
  direction, cardinality_canonical,
  members_canonical,
  method, method_version, parameter_profile_hash,
  normalization_profile_id, normalization_profile_version,
  tokenization_profile_id, tokenization_profile_version,
  corpus_snapshot_id, release_id))

canonicalization 規則（normative）:
  - hash = sha256; Unicode = NFC; JSON object key = コードポイント昇順
  - members_canonical: 各 member = (asset_id, text_revision, unit_id) tuple を昇順ソート
  - direction = symmetric:
      side 正規化: canonical_json(members_a_sorted) と canonical_json(members_b_sorted) を
                  文字列比較し、小さい方を canonical_a、大きい方を canonical_b とする。
      cardinality_canonical: 正規化後の |canonical_a| と |canonical_b| から再導出。
        |a|=1 ∧ |b|=1 → one_one
        |a|=1 ∧ |b|>1 → one_n   （正規化後に n_one は発生しない）
        |a|>1 ∧ |b|>1 → n_m
      結果: side 入替で同一 alignment_observation_id（正規化後 side 順序が一致するため）
  - direction ≠ symmetric: side 順序・cardinality を保持 → 入替で別 ID
  - review・eligibility・assessment 変更で alignment_observation_id は変えない
```

## 6. xdoc_use_assessment（1:N・用途別・履歴 contract・P0-4）
```text
xdoc_use_assessment
  use_assessment_key_id       # required; sha256(canonical_json(
                              #   alignment_observation_id, evaluation_purpose,
                              #   target, policy_id, policy_version))  ← logical key
  assessment_revision_id      # required; sha256(canonical_json(
                              #   use_assessment_key_id, decision_payload_digest, revision_seq))  ← event ID
  revision_seq                # required; integer（1 始まり、単調増加）
  status                      # required; assessment_status enum
  supersedes_revision_id      # optional; null（初回）または前の assessment_revision_id
  revocation_reason_code      # conditional required; status=revoked のとき required
  alignment_observation_id    # required; FK → xdoc_alignment
  evaluation_purpose          # required; evaluation_purpose enum
  target                      # required; target enum
  eligibility                 # required; eligibility enum
  policy_id                   # required; string
  policy_version              # required; string
  reason_codes[]              # required; string[]
  evidence_refs[]             # optional; string[]
  reviewed_relation_type      # optional; reviewed_relation_type enum | null（method 出力は直接入れない）
  assessed_at                 # required; ISO8601 datetime
  assessed_by                 # required; string
  review_state                # required; review_state enum
```
- **G_XDOC_USE_ASSESSMENT_1N**：1 alignment は複数 purpose×target で評価可。eligibility は本表（1:N）に持つ。
- **G_XDOC_NO_SILENT_MUTATION**：既存 revision の in-place 更新禁止。変更は新 revision（revision_seq++）を作成し、旧 revision を superseded へ移行。

## 7. purpose_target_compatibility + eligibility_policy_rule（P0-1）

### 7-1. purpose_target_compatibility（valid 組合せ・default 挙動）
| evaluation_purpose | target | allowed | default_eligibility |
|---|---|---|---|
| proof_corroboration | proof | true | hold |
| extraction_corroboration | proof | true | hold |
| litlink_candidate | litlink | true | hold |
| edition_resolution | litid_identity | true | hold |
| formobj_variant_candidate | formobj_variant | true | hold |
| frbr_work_candidate | frbr_work | true | hold |
| dedup | block_ref | true | hold |
| *（上記以外の任意の組合せ） | * | **false** | **ineligible** |

- allowed=false の組合せで use_assessment を作成しようとした場合は validation error（作成禁止）。
- 上記 allowed=true の組合せで、後述 policy rule がいずれにも該当しない場合は `default_eligibility = hold`。

### 7-2. eligibility_policy_rule（policy_id = XDOC-ELIG-001 / v1）

**priority 解決規則**：数字大＝高優先。同一 priority で複数ルール該当 → `ineligible > hold > eligible`。
すべてのルールが非該当 → 7-1 の `default_eligibility` を適用。

| priority | purpose | target | condition_expression | result_eligibility | reason_code |
|---|---|---|---|---|---|
| 100 | proof_corroboration | proof | content_independence.effective_value ∈ {shared, partially_shared} | **ineligible** | CONTENT_NOT_INDEPENDENT |
| 100 | proof_corroboration | proof | content_independence.effective_value = unknown | hold | CONTENT_INDEPENDENCE_UNKNOWN |
| 100 | proof_corroboration | proof | observation_independence.effective_value ∈ {shared, partially_shared, unknown} | hold | OBSERVATION_NOT_INDEPENDENT_LEGAL |
| 100 | proof_corroboration | proof | content_independence.effective_status ∈ {stale, invalid} | hold | INDEPENDENCE_ASSESSMENT_STALE_OR_INVALID |
| 90 | * | * | absence/difference 主張 かつ 対象 member の coverage_complete = false | **ineligible** | COVERAGE_INCOMPLETE |
| 80 | * | {litlink, frbr_work, litid_identity, block_ref} | reviewed_relation_type IS NULL | **ineligible** | REVIEWED_RELATION_REQUIRED |
| 70 | frbr_work_candidate | frbr_work | review_state ≠ reviewed | hold | HUMAN_REVIEW_REQUIRED |
| 50 | proof_corroboration | proof | content_independence.effective_value = independent AND observation_independence.effective_value = independent AND reviewed_relation_type NOT NULL AND review_state = reviewed | eligible | INDEPENDENT_CORROBORATION |
| 50 | extraction_corroboration | proof | observation_independence.effective_value ∈ {independent, partially_shared} AND review_state = reviewed | eligible | EXTRACTION_CANDIDATE |
| 50 | litlink_candidate | litlink | reviewed_relation_type NOT NULL AND review_state = reviewed | eligible | LITLINK_CANDIDATE |
| 50 | edition_resolution | litid_identity | reviewed_relation_type = edition_variant AND review_state = reviewed | eligible | EDITION_CANDIDATE |
| 50 | formobj_variant_candidate | formobj_variant | reviewed_relation_type ∈ {template_instance, common_template} AND review_state = reviewed | eligible | FORMOBJ_CANDIDATE |
| 50 | frbr_work_candidate | frbr_work | review_state = reviewed AND reviewed_relation_type NOT NULL | eligible | FRBR_CANDIDATE |
| 50 | dedup | block_ref | reviewed_relation_type ∈ {near_duplicate, same_expression} AND review_state = reviewed | eligible | DEDUP_CANDIDATE |

**注**：frbr_work_candidate × frbr_work の eligible（priority=50）は単一 alignment の use_assessment が証拠の 1 片を示すものに過ぎない。FRBR Work 昇格には外部で multi-facet cluster 証拠の確立が必要（cluster-level 契約・HOLD）。

- **G_XDOC_PROOF_REQUIRES_CONTENT_INDEPENDENT**（priority=100 CONTENT_NOT_INDEPENDENT）。
- **G_XDOC_NO_COVERAGE_ABSENCE_CLAIM**（priority=90）。
- **G_XDOC_NO_CANDIDATE_PROMOTION**（priority=80 REVIEWED_RELATION_REQUIRED）。

## 8. method_registry + method_capability_rule + mapping table（P0-5）

### 8-1. method_registry（method 単体の能力宣言）
```text
method_registry
  method_id                   # required; string
  version                     # required; string
  facet                       # required; facet enum
  candidate_only              # required; bool（true: 単独で reviewed relation を生成しない）
  prohibited_assertion_types[] # required; string[]
```
| method_id | facet | candidate_only | prohibited_assertion_types |
|---|---|---|---|
| MinHash | text | false | semantic_identity, citation_direction |
| SimHash | text | false | semantic_identity, citation_direction |
| embedding | text | false | symbol_identity, verbatim_identity |
| CDC | text | **true**（standalone） | segment_identity_standalone |
| content_hash | text | false（companion only） | standalone_use |
| table_structure | table | false | figure_content |
| pHash | figure | **true** | reviewed_figure_identity |
| visual_embedding | figure | **true** | reviewed_figure_identity |

### 8-2. method_capability_rule（複合 capability・P0-5）
```text
method_capability_rule
  rule_id                     # required; string
  primary_method_id           # required; string（FK → method_registry.method_id）
  required_companion_method_ids[] # required; string[]（空 = 単独使用可）
  allowed_comparison_intents[]    # required; comparison_intent[]
  allowed_candidate_relation_types[] # required; candidate_relation_type[]
```
| rule_id | primary | required_companions | allowed_intents | allowed_candidate_relation_types |
|---|---|---|---|---|
| R-MINHASH | MinHash | [] | near_duplicate, text_reuse | near_duplicate, lexical_overlap |
| R-SIMHASH | SimHash | [] | near_duplicate, text_reuse | near_duplicate, lexical_overlap |
| R-EMB | embedding | [] | semantic_overlap, citation_candidate | semantic_proximity |
| R-CDC-STANDALONE | CDC | [] | text_reuse（boundary 生成のみ） | **[]**（relation 確定不可） |
| R-CDC-HASH | CDC | [content_hash] | text_reuse, near_duplicate | segment_identity_candidate |
| R-TABLE | table_structure | [] | table_template, structure_comparison | table_structure_match |
| R-PHASH | pHash | [] | figure_reuse | figure_near_duplicate |
| R-VIS | visual_embedding | [] | figure_reuse | visual_proximity |

- **G_XDOC_METHOD_VOCAB**：method 出力は `reviewed_relation_type` を**直接生成しない**（常に null）。
- **G_XDOC_METHOD_CAPABILITY_DECLARED**：`candidate_relation_types[]` は適用 rule の `allowed_candidate_relation_types` の部分集合のみ許可。

### 8-3. origin_relation × candidate_relation_type → reviewed_relation_type 対応表（規範・P0-5）

method 出力（candidate_relation_type）と content_origin_assertion の origin_relation の組合せから、人手レビューで設定可能な reviewed_relation_type を制約する。**全行 requires_human = true**（method 出力の自動コピー禁止）。

| origin_relation | candidate_relation_type | allowed_reviewed_relation_types[] |
|---|---|---|
| quote | segment_identity_candidate | quote |
| quote | lexical_overlap | quote |
| reprint | near_duplicate | reprint |
| reprint | segment_identity_candidate | reprint |
| adaptation | semantic_proximity | adaptation |
| adaptation | near_duplicate | adaptation |
| common_template | table_structure_match | template_instance, common_template |
| common_template | structure_edit | common_template, edition_variant |
| same_expression | lexical_overlap | same_expression, near_duplicate |
| same_expression | segment_identity_candidate | same_expression |
| null（origin 不明） | near_duplicate | near_duplicate, same_topic |
| null | semantic_proximity | same_topic |
| null | figure_near_duplicate | figure_reuse |
| null | visual_proximity | figure_reuse |
| null | table_structure_match | template_instance |
| null | structure_edit | edition_variant |

上記以外の origin_relation × candidate_relation_type 組合せからの reviewed_relation_type 設定は validation error。

## 9. coverage_assessment + coverage_policy（P0-6）

```text
coverage_assessment
  coverage_assessment_id      # required; sha256(canonical_json(
                              #   alignment_observation_id, member_ref, side, facet, assessment_version))
  alignment_observation_id    # required; FK → xdoc_alignment
  member_ref                  # required; member@asset
  side                        # required; a | b
  facet                       # required; facet enum
  coordinate_space            # required; coordinate_space enum
  asset_hash                  # required; sha256
  source_text_revision_id     # required; string
  selector_state              # required; selector_state enum
  covered_ranges[]            # required; [{start: int|string, end: int|string, coordinate_space}]
  unknown_ranges[]            # required; [{start: int|string, end: int|string, coordinate_space}]（空配列可）
  ocr_quality_score           # required; float 0.0-1.0
  layout_quality_score        # required; float 0.0-1.0
  coverage_policy_id          # required; string
  coverage_policy_version     # required; string
  assessment_version          # required; string

coverage_policy
  policy_id                   # required; string
  policy_version              # required; string
  facet                       # required; facet enum
  required_coordinate_space   # required; coordinate_space enum
  minimum_ocr_quality         # required; float 0.0-1.0
  minimum_layout_quality      # required; float 0.0-1.0
  completeness_rule           # required; string（下記の規範式を参照）
```

**coverage_complete(coverage_assessment ca, coverage_policy p) 規範式**：
```text
coverage_complete ≡
  ca.selector_state = complete
  AND ca.ocr_quality_score ≥ p.minimum_ocr_quality
  AND ca.layout_quality_score ≥ p.minimum_layout_quality
  AND ca.unknown_ranges = []
  AND ca.coordinate_space = p.required_coordinate_space
```

- **G_XDOC_COVERAGE_MEMBER_KEYED**：n:m で**どの member の coverage が欠けたか**判定可能。
- absence/difference を根拠とする use_assessment は、対象 member の `coverage_complete = true` を必須とする（false → eligibility=ineligible, reason_code=COVERAGE_INCOMPLETE, priority=90 by §7-2）。

## 10. xdoc_cluster + xdoc_support_edge + cluster_policy（P0-7）

### 10-1. xdoc_support_edge（undirected・一意性・P0-7）
```text
xdoc_support_edge
  support_edge_id             # required; sha256(canonical_json(
                              #   cluster_facet, canonical_member_low, canonical_member_high,
                              #   alignment_observation_id))
  cluster_facet               # required; facet enum
  canonical_member_low        # required; canonical member string（min(member_a, member_b)）
  canonical_member_high       # required; canonical member string（max(member_a, member_b)）
  alignment_observation_id    # required; FK → xdoc_alignment
  support_score               # required; float 0.0-1.0
  calibration_id              # required; string
  calibration_version         # required; string
  UNIQUE(canonical_member_low, canonical_member_high, alignment_observation_id)
```

- エッジは **undirected**（canonical_low = min、canonical_high = max by canonical string）。
- `(A,B)` と `(B,A)` は同一エッジ（canonical_low/high で統一）。
- 同一 member pair に複数 alignment がある場合、`alignment_observation_id` が異なる別 support_edge を作成する。

### 10-2. xdoc_cluster
```text
xdoc_cluster
  cluster_id                  # required; string
  facet                       # required; facet enum
  algorithm                   # required; string
  algorithm_version           # required; string
  parameter_profile_id        # required; string
  corpus_snapshot_id          # required; string
  members[]                   # required; [{member_ref: string, member_score: float 0.0-1.0}]
  representative_or_medoid    # optional; member_ref | null
  cluster_stability           # required; float 0.0-1.0（stability_metric_id に基づく）
  stability_metric_id         # required; string（e.g., avg_silhouette | nmi | custom）
  density                     # required; float 0.0-1.0
  outlier_state               # required; bool
  pairwise_support_coverage   # required; float 0.0-1.0（§下記定義）
  policy_id                   # required; string
  policy_version              # required; string
  cluster_lineage_events[]    # optional; [{lineage_type, target_cluster_id, event_at}]
  cluster_semantics = candidate_set  # NOT equivalence_class
```

**pairwise_support_coverage 定義（P0-7）**：
```text
pairwise_support_coverage =
  count(canonical_member_pairs で support_edge が 1 件以上存在するもの)
  ÷
  count(クラスタ内 canonical_member_pairs の総数)

canonical_member_pair = {low, high}（unordered、low < high by canonical string）
分子: "少なくとも 1 つ有効 support_edge を持つ canonical member pair 数"（複数 alignment のある pair は 1 と数える）
```

### 10-3. cluster_policy（P0-7）
```text
cluster_policy
  policy_id                   # required; string
  policy_version              # required; string
  algorithm                   # required; string
  stability_metric_id         # required; string
  minimum_stability           # required; float 0.0-1.0
  minimum_density             # required; float 0.0-1.0（pairwise_support_coverage 下限）
  maximum_cluster_size        # required; integer
  outlier_rule                # required; string（e.g., "member_score < 0.3 → outlier_state=true"）
  missing_pair_rule           # required; "support_edge 未存在 pair → unknown（非類似の推論禁止）"
```

- **G_XDOC_NO_TRANSITIVE_EQUIVALENCE**（A~B,B~C,A!~C で A=C を推論しない）。
- **G_XDOC_NO_TRANSITIVE_MEGACLUSTER**（pairwise 推移閉包で巨大化しない）。
- **G_XDOC_CLUSTER_SUPPORT_CONTRACT**（support graph・stability・policy 無しのクラスタ確定禁止）。
- cluster から FRBR/LITID/proof へ直接 promotion しない。

## 11. ゲート一覧（機械可読・全体）
INDEP_TRISTATE / INDEP_CONTRADICTION / INDEP_DERIVED_FROM_EVIDENCE / PASSAGE_ORIGIN_REQUIRED / INTENT_REQUIRED / USE_ASSESSMENT_1N / NO_SILENT_MUTATION / PROOF_REQUIRES_CONTENT_INDEPENDENT / NO_COVERAGE_ABSENCE_CLAIM / NO_CANDIDATE_PROMOTION / METHOD_VOCAB / METHOD_CAPABILITY_DECLARED / COVERAGE_MEMBER_KEYED / NO_TRANSITIVE_EQUIVALENCE / NO_TRANSITIVE_MEGACLUSTER / CLUSTER_SUPPORT_CONTRACT / OWNERSHIP_NO_REDEF / REPRODUCIBILITY_CONTRACT / DERIVED / NO_CLAIM_SUPPORT / HUMAN_PROMOTION_ONLY / NO_SELF_LOOP / FACET_ANCHORED。

## 12. 受入試験（v0.5・全自動 PASS が条件）
1. schema/enum/target に `{...}`・未定義値・slash shorthand が無い。全 field に型・required/optional・enum が定義されている。purpose×target の未定義組合せは validation error。
2. 同一 alignment を litlink_candidate×litlink と proof_corroboration×proof で別々の use_assessment（異なる use_assessment_key_id）に評価できる。
3. shared origin の 2 passage を proof_corroboration×proof に入れると priority=100 CONTENT_NOT_INDEPENDENT → ineligible（eligible にならない）。unknown origin → hold（CONTENT_INDEPENDENCE_UNKNOWN）。
4. content_independence.effective_value=independent / observation_independence.effective_value=shared の組合せで、軸ごとの xdoc_independence_assessment が 2 件（axis=content と axis=observation）独立して存在し、各 effective_value が別々に出力される。
5. 各 content_origin_assertion から assertion_id・subject_member_ref・subject_passage_ref・origin_object_type/id/version・origin_passage_ref・evidence_pointer_refs[]・evidence_hashes[] まで全フィールドが個別に追跡可能。
6. n:m で片側 1 member だけ coverage_complete=false（e.g., unknown_ranges 非空）なら、その member を根拠とする absence/difference 主張の use_assessment eligibility = ineligible（reason=COVERAGE_INCOMPLETE, §7-2 priority=90）。
7. R-CDC-STANDALONE（CDC 単独）→ allowed_candidate_relation_types=[]。R-CDC-HASH（CDC+content_hash）→ segment_identity_candidate のみ許容。CDC 単独での segment_identity 主張は validation error。
8. pHash は candidate_only=true かつ reviewed_figure_identity が prohibited_assertion_types に含まれる。pHash/visual_embedding 単独では reviewed_relation_type を生成しない（null 必須）。
9. symmetric: canonical_json(members_a_sorted) と canonical_json(members_b_sorted) を比較して小さい方を canonical_a とし、側を入れ替えた入力でも同一 alignment_observation_id を得る。cardinality は正規化後サイズから再導出（n_one は正規化後に発生しない）。
10. comparison_intent を変更した場合に alignment_observation_id が変わる。facet/asset/text_revision/method_version/parameter_profile_hash/normalization_profile_id/tokenization_profile_id/corpus_snapshot_id のいずれか変化でも ID が変わる。
11. A~B,B~C,A!~C（support_edge(A,C) 不存在）でクラスタが A=C を推移推論しない。missing_pair_rule により A-C pair は unknown（非類似の推論禁止）。
12. XDOC から block_ref current・LITLINK accepted・FRBR/LITID identity・claim support へ直接昇格できない（HOLD gate 維持）。

## 13. 非blocking 改善（v0.5 反映）
- `direction=symmetric` と `cardinality=n_one` の組合せを schema gate で reject（正規化後に n_one は発生しない）。
- `members_a/b` 内の duplicate member・両 side 同一 member・正規化後同一 asset_revision+unit_id の重複を G_XDOC_NO_SELF_LOOP で reject。
- `similarity` は `calibration_id` と `calibration_version` を必須化。method 間での scalar 直接比較禁止。
- `reviewed_relation_type=none`（レビュー済み・非該当）と null（未レビュー）を型で区別（§2 にて定義済み）。
- `origin_object_type/id/version` を個別フィールドとして定義（文字列連結禁止、§4 反映済み）。
- `cluster_lineage_events[]` を lineage edge 配列として定義（単一フィールド禁止、§10-2 反映済み）。

## 14. GO / HOLD / loop_state
- **GO**：独立 DD 維持／v0.5 design patch／passage origin・pipeline provenance・coverage の gold fixture 設計／固定 snapshot 上の read-only candidate generation 試験／purpose-target 互換表・eligibility policy・method composite capability・cluster policy 作成。
- **HOLD**：v0.5 ratify／DDL/DB/mint/Box mutation／OCR/embedding/training／production pair generation・clustering／FRBR・DD-LITID・DD-LITLINK・block_ref current 自動昇格／evidence・legal claim support。
- loop_state = **patched（v0.5 P0 契約閉鎖・自己完結）→ 再投函（再監査）候補**。

<!-- END INLINE EMBED: DD-XDOC-001 v0.5 -->
