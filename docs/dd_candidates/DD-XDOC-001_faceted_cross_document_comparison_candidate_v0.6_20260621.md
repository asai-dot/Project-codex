# DD-XDOC-001 v0.6 — faceted cross-document comparison & alignment（round5 must_fix 9点・決定式閉鎖）candidate

> **id**: DD-XDOC-001 / **version**: candidate v0.6 / **supersedes**: v0.5
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-21 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/学習/embedding/production pair generation/clustering/FRBR・DD-LITID・DD-LITLINK 昇格/block_ref current 昇格/evidence・legal claim support は **HOLD**。
> **改訂理由（v0.5→v0.6）**: GPT Pro 再監査 `DDXDOC_MODIFY_REQUIRED`（RESULT Box 2299484641489）の must_fix 9点 + should_fix 5点を反映。新規レイヤ追加なし。symmetric cardinality 決定式・coverage scope 包含判定・origin unknown・decision_payload digest・valid support predicate・versioned method registry id・typed cluster rule・ellipsis/union 除去。
> **depends_on**: DD-LAYOUT-001 v0.5 / DD-XMODAL-001 v0.4 / DD-LITID-001 / DD-LITLINK-001（いずれも定義を狭めない）。

---

## 0. round5 must_fix 反映（B1〜B8 / must_fix 1〜9）
| must | B | 指摘 | § |
|---|---|---|---|
| 1 | B1 | symmetric cardinality を unordered side-size から決定・未定義分岐除去 | §5 |
| 2 | B2 | coverage に required claim scope/ranges 追加・covered union ⊇ required union 必須 | §9 |
| 3 | B3 | origin_relation に unknown 追加・mapping null 置換 | §2,§4,§8-3 |
| 4 | B4 | content/observation いずれか status=invalid なら eligible 禁止 machine rule | §7-2 |
| 5 | B5 | independence evidence ref 型・fingerprint canonicalization・review audit 条件付き必須・active uniqueness | §3 |
| 6 | B6 | decision_payload_digest 定義・revision uniqueness/current/supersedes contract | §6 |
| 7 | B7 | method capability を versioned registry id に結合・candidate_only 意味矛盾解消 | §8 |
| 8 | B8 | support_edge effective predicate・minimum_support_score・density 式・typed cluster rule | §10 |
| 9 | P0-8 | ellipsis・union 型・未定義 constant/field 除去（受入試験1機械通過） | 全域 |

## 1. オブジェクト分離（関心の分離）
- **xdoc_alignment**：observation（何を・どの method で・どの member 間で検出したか）。不変。`alignment_observation_id`。
- **xdoc_use_assessment**：alignment に 1:N（evaluation_purpose × target ごとの eligibility＋policy）。**append-only revision 履歴**（§6）。
- **xdoc_independence_assessment**：alignment × axis ごとの computed/reviewed/effective 独立性（§3）。
- **content_origin_assertion** / **member_pipeline_provenance**：member 単位の証拠。独立性は**これらから導出**（手入力しない）。
- **coverage_assessment** + **coverage_policy** + **coverage_claim_scope**：member-keyed・対象範囲包含判定（§9）。
- **xdoc_cluster** ＋ **xdoc_support_edge** ＋ **cluster_policy** ＋ **cluster_lineage_edge**：support graph（§10）。
- **method_registry** / **method_capability_rule**：versioned（§8）。

## 2. canonical enums（単一定義・全所で同一・ellipsis/union 不使用）
```text
facet                  = structure | text | table | figure
direction              = a_to_b | b_to_a | symmetric
cardinality            = one_one | one_n | n_m
  # symmetric は unordered side-size から決定（§5）。n_one enum は廃止（one_n に正規化）。
  # directional（a_to_b / b_to_a）は side 順序保持・サイズから one_one|one_n|n_one_directional|n_m を別関数で導出（§5）
cardinality_directional= one_one | one_n | n_one | n_m   # directional 専用（side 順序保持時）
comparison_intent      = near_duplicate | text_reuse | semantic_overlap | edition_alignment
                       | structure_comparison | table_template | figure_reuse | citation_candidate
candidate_relation_type= near_duplicate | lexical_overlap | semantic_proximity
                       | segment_identity_candidate | table_structure_match
                       | figure_near_duplicate | visual_proximity | structure_edit
reviewed_relation_type = quote | reprint | adaptation | common_template | same_expression
                       | edition_variant | same_topic | template_instance | figure_reuse
                       | near_duplicate | none
                       # none = レビュー済み・非該当。NULL = 未レビュー。型で区別。
origin_relation        = quote | reprint | adaptation | common_template | same_expression | unknown
                       # B3: unknown を enum に追加（required・NULL 不使用）。unknown = origin 不明だが観測済み。
evaluation_purpose     = proof_corroboration | extraction_corroboration | litlink_candidate
                       | edition_resolution | formobj_variant_candidate | frbr_work_candidate | dedup
target                 = proof | litlink | frbr_work | litid_identity | formobj_variant | block_ref
independence_value     = independent | shared | partially_shared | unknown
eligibility            = eligible | ineligible | hold
review_state           = unreviewed | reviewed | overridden | stale
effective_status       = current | stale | invalid
assessment_status      = active | superseded | revoked     # current view から導出（§6）
axis                   = content | observation
side                   = a | b
selector_state         = complete | partial | failed | not_applicable
coordinate_space       = page | char_offset | token | table_cell | figure_region
edit_op                = insert | delete | move | rename | split | merge
ref_type               = origin_assertion | pipeline_provenance
detection_state        = detected | verified | rejected
lineage_type           = split | merge | supersedes
outlier_rule_type      = member_score_lt | edge_degree_lt | custom_registered
missing_pair_rule_type = unknown | reject_cluster | require_review
```

## 3. xdoc_independence_assessment（B5・型・fingerprint・audit・uniqueness）
```text
computed_evidence_ref                  # B5: typed ref（union 廃止）
  ref_type                    # required; ref_type enum（origin_assertion | pipeline_provenance）
  ref_id                      # required; string
  ref_version_or_hash         # required; string

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
  computed_evidence_refs[]    # required; computed_evidence_ref[]（typed・空不可）
  computed_input_fingerprint  # required; §下記 canonical
  reviewed_value              # optional; independence_value | NULL
  review_state                # required; review_state enum（初期 = unreviewed）
  review_reason_code          # conditional required; review_state ∈ {reviewed, overridden, stale} のとき required
  reviewed_by                 # conditional required; review_state ∈ {reviewed, overridden} OR reviewed_value≠NULL のとき required
  reviewed_at                 # conditional required; 同上
  review_note                 # optional; string
  effective_value             # required; independence_value（下記算定）
  effective_status            # required; effective_status enum
  supersedes_assessment_id    # optional; NULL or 前の independence_assessment_id
  assessment_status           # required; active | superseded | revoked（current view 導出）
```
**computed_input_fingerprint canonicalization（B5・normative）**
```text
computed_input_fingerprint = sha256(canonical_json(
  sort(computed_evidence_refs by (ref_type, ref_id, ref_version_or_hash)),
  computed_policy_id,
  computed_policy_version))
current_fingerprint = 同式を「現在の証拠 ref 集合」で再計算した値
```
**effective_value 算定規則（normative）**
```text
1. computed_input_fingerprint ≠ current_fingerprint
     → effective_status = stale; effective_value = unknown（fail-closed）; STOP
2. reviewed_value ≠ NULL AND computed_value ≠ reviewed_value AND review_reason_code IS NULL
     → effective_status = invalid; effective_value = unknown; STOP
3. reviewed_value ≠ NULL → effective_status = current; effective_value = reviewed_value
4. reviewed_value = NULL → effective_status = current; effective_value = computed_value
```
- **G_XDOC_INDEP_ACTIVE_UNIQUE**：`(alignment_observation_id, axis, computed_policy_id, computed_policy_version)` につき `assessment_status=active` は最大1件。
- **G_XDOC_INDEP_DERIVED_FROM_EVIDENCE**：computed_value は computed_evidence_refs ＋ policy 由来（手入力禁止）。
- content と observation は**別軸**（独立執筆×同一OCR＝content independent / observation shared）。

## 4. member 単位の証拠（origin unknown 反映）
```text
content_origin_assertion
  assertion_id                # required; string
  subject_member_ref          # required; member@asset 参照
  subject_passage_ref         # required; DD-LAYOUT text_pos selector
  origin_object_type          # required; statute | case | manuscript | edition | commentary | dataset
  origin_object_id            # required; string
  origin_object_version       # required; string
  origin_passage_ref          # required; string
  origin_relation             # required; origin_relation enum（unknown 含む・NULL 不可）
  evidence_pointer_refs[]     # required; string[]
  evidence_hashes[]           # required; string[]（sha256）
  detection_method_registry_id# required; string（§8 method_registry_id）
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

## 5. xdoc_alignment（observation・不変 ID・symmetric cardinality 決定式 B1）
```text
member_tuple                   # 単一定義
  asset_id                    # required; string
  text_revision               # required; string
  unit_id                     # required; string

edit_script_op                 # B9: ellipsis 廃止・全 field 定義
  op                          # required; edit_op enum
  src_unit_id                 # conditional required; op ∈ {delete, move, rename, split} のとき required
  dst_unit_id                 # conditional required; op ∈ {insert, move, merge} のとき required
  payload_digest              # optional; string（rename/split/merge の内容差分 sha256）

xdoc_alignment
  alignment_observation_id    # required; §下記 canonical
  schema_version              # required; string
  facet                       # required; facet enum
  comparison_intent           # required; comparison_intent enum（ID 材料）
  direction                   # required; direction enum
  cardinality                 # required; symmetric→cardinality / directional→cardinality_directional（§下記）
  members_a[]                 # required; member_tuple[]
  members_b[]                 # required; member_tuple[]
  edit_script[]               # optional; edit_script_op[]
  method_registry_id          # required; string（§8・versioned）
  parameter_profile_hash      # required; string（sha256）
  normalization_profile_id    # required; string
  normalization_profile_version# required; string
  tokenization_profile_id     # required; string
  tokenization_profile_version# required; string
  candidate_relation_types[]  # required; candidate_relation_type[]（method 出力候補）
  similarity                  # required; float
  calibration_id              # required; string
  calibration_version         # required; string
  score_components_ref        # required; string
  result_payload_digest       # conditional required; method が非決定的のとき required（should_fix#3）
  corpus_snapshot_id          # required; string
  release_id                  # required; string
```

**side canonicalization（B1・cardinality と分離）**
```text
member_canonical(m)      = canonical_json sorted tuple (asset_id, text_revision, unit_id)
side_canonical(members)  = sort_ascending([member_canonical(m) for m in members])（重複除去なし）

# side 順序（symmetric のみ）：
canonical_a, canonical_b =
  両 side の side_canonical を文字列比較し、小さい方を canonical_a、大きい方を canonical_b
```

**cardinality canonicalization（B1・unordered side-size から決定）**
```text
# symmetric: side 順序に依存しない unordered size から決定（未定義分岐なし）
sizes = sort_ascending([len(members_a), len(members_b)])
  [1, 1]        → one_one
  [1, n] (n>1)  → one_n
  [m, n] (m,n>1)→ n_m
# directional（a_to_b / b_to_a）: side 順序を保持し cardinality_directional を導出
  len(a)=1, len(b)=1 → one_one
  len(a)=1, len(b)>1 → one_n
  len(a)>1, len(b)=1 → n_one
  len(a)>1, len(b)>1 → n_m
```

**canonical alignment_observation_id**
```text
alignment_observation_id = sha256(canonical_json(
  schema_version, facet, comparison_intent,
  direction, cardinality,
  members_canonical,                 # symmetric: [canonical_a, canonical_b] / directional: [side_canonical(a), side_canonical(b)]（順序保持）
  method_registry_id, parameter_profile_hash,
  normalization_profile_id, normalization_profile_version,
  tokenization_profile_id, tokenization_profile_version,
  result_payload_digest,             # NULL 可（決定的 method）
  corpus_snapshot_id, release_id))

canonicalization 規則（normative）:
  - hash = sha256; Unicode = NFC; JSON object key = コードポイント昇順
  - symmetric: side 入替で同一 id（canonical_a/b・unordered cardinality が side 順序非依存）
  - directional: side 順序・cardinality_directional を保持 → 入替で別 id
  - review・eligibility・assessment 変更で id は不変
```

## 6. xdoc_use_assessment（append-only revision・B6）
```text
decision_payload                       # B6: digest 材料を明示
  eligibility                 # eligibility enum
  reason_codes_sorted         # sort(reason_codes[])
  evidence_refs_sorted        # sort(evidence_refs[])
  reviewed_relation_type      # reviewed_relation_type enum | NULL
  review_state                # review_state enum
  assessed_by                 # string
decision_payload_digest = sha256(canonical_json(decision_payload))

xdoc_use_assessment                    # append-only・不変 record
  use_assessment_key_id       # required; sha256(canonical_json(
                              #   alignment_observation_id, evaluation_purpose, target,
                              #   policy_id, policy_version))  ← logical key
  assessment_revision_id      # required; sha256(canonical_json(
                              #   use_assessment_key_id, decision_payload_digest, revision_seq))
  revision_seq                # required; integer（prior + 1、1 始まり）
  supersedes_revision_id      # required; NULL（初回）or 直前 revision の assessment_revision_id
  revoked                     # required; bool（true = この revision で撤回宣言）
  revocation_reason_code      # conditional required; revoked=true のとき required
  alignment_observation_id    # required; FK
  evaluation_purpose          # required; evaluation_purpose enum
  target                      # required; target enum
  eligibility                 # required; eligibility enum
  policy_id                   # required; string
  policy_version              # required; string
  reason_codes[]              # required; string[]
  evidence_refs[]             # optional; string[]
  reviewed_relation_type      # optional; reviewed_relation_type enum | NULL
  assessed_at                 # required; ISO8601 datetime
  assessed_by                 # required; string
  review_state                # required; review_state enum
```
**status は履歴から導出（in-place 更新なし・B6）**
```text
current_revision(key)  = max revision_seq の record
assessment_status(r)   =
  revoked=true                          → revoked
  r = current_revision(key) かつ非revoked → active
  それ以外                               → superseded
```
- **G_XDOC_USE_ASSESSMENT_REVISION_UNIQUE**：`UNIQUE(use_assessment_key_id, revision_seq)`。
- **G_XDOC_USE_ASSESSMENT_ONE_ACTIVE**：key ごと active は最大1件（current view 導出）。
- **G_XDOC_NO_SILENT_MUTATION**：record は不変。変更は新 revision（revision_seq++・supersedes edge）として append。

## 7. purpose_target_compatibility + eligibility_policy_rule（B4 反映）

### 7-1. purpose_target_compatibility（valid 組合せ・default）
| evaluation_purpose | target | allowed | default_eligibility |
|---|---|---|---|
| proof_corroboration | proof | true | hold |
| extraction_corroboration | proof | true | hold |
| litlink_candidate | litlink | true | hold |
| edition_resolution | litid_identity | true | hold |
| formobj_variant_candidate | formobj_variant | true | hold |
| frbr_work_candidate | frbr_work | true | hold |
| dedup | block_ref | true | hold |
| *（上記以外の任意組合せ） | * | **false** | **ineligible** |

- allowed=false の組合せで use_assessment を作成すると validation error（作成禁止）。
- allowed=true で policy rule がいずれも非該当 → `default_eligibility = hold`。

### 7-2. eligibility_policy_rule（policy_id = XDOC-ELIG-001 / v1）

**condition_expression の型**：boolean 式。被参照変数は `independence(axis).effective_value`・`independence(axis).effective_status`・`reviewed_relation_type`・`review_state`・`coverage_complete_for_scope`（§9）・`claim_is_absence_or_difference`。
**priority 解決**：数字大＝高優先。同一 priority 複数該当 → `ineligible > hold > eligible`。全非該当 → 7-1 default。

| priority | purpose | target | condition_expression | result | reason_code |
|---|---|---|---|---|---|
| **110** | * | * | **exists independence assessment (any axis) where effective_status = invalid** | **ineligible** | INDEPENDENCE_INVALID_GLOBAL |
| **105** | proof_corroboration | proof | **observation_independence.effective_status = stale** | hold | OBSERVATION_INDEPENDENCE_STALE |
| 100 | proof_corroboration | proof | content_independence.effective_value ∈ {shared, partially_shared} | **ineligible** | CONTENT_NOT_INDEPENDENT |
| 100 | proof_corroboration | proof | content_independence.effective_value = unknown | hold | CONTENT_INDEPENDENCE_UNKNOWN |
| 100 | proof_corroboration | proof | observation_independence.effective_value ∈ {shared, partially_shared, unknown} | hold | OBSERVATION_NOT_INDEPENDENT_LEGAL |
| 100 | proof_corroboration | proof | content_independence.effective_status = stale | hold | CONTENT_INDEPENDENCE_STALE |
| 90 | * | * | claim_is_absence_or_difference AND coverage_complete_for_scope = false | **ineligible** | COVERAGE_INCOMPLETE |
| 80 | * | {litlink, frbr_work, litid_identity, block_ref} | reviewed_relation_type IS NULL | **ineligible** | REVIEWED_RELATION_REQUIRED |
| 70 | frbr_work_candidate | frbr_work | review_state ≠ reviewed | hold | HUMAN_REVIEW_REQUIRED |
| 50 | proof_corroboration | proof | content_independence.effective_value = independent AND content_independence.effective_status = current AND observation_independence.effective_value = independent AND observation_independence.effective_status = current AND reviewed_relation_type NOT NULL AND review_state = reviewed | eligible | INDEPENDENT_CORROBORATION |
| 50 | extraction_corroboration | proof | observation_independence.effective_value ∈ {independent, partially_shared} AND observation_independence.effective_status = current AND review_state = reviewed | eligible | EXTRACTION_CANDIDATE |
| 50 | litlink_candidate | litlink | reviewed_relation_type NOT NULL AND review_state = reviewed | eligible | LITLINK_CANDIDATE |
| 50 | edition_resolution | litid_identity | reviewed_relation_type = edition_variant AND review_state = reviewed | eligible | EDITION_CANDIDATE |
| 50 | formobj_variant_candidate | formobj_variant | reviewed_relation_type ∈ {template_instance, common_template} AND review_state = reviewed | eligible | FORMOBJ_CANDIDATE |
| 50 | frbr_work_candidate | frbr_work | review_state = reviewed AND reviewed_relation_type NOT NULL | eligible | FRBR_CANDIDATE |
| 50 | dedup | block_ref | reviewed_relation_type ∈ {near_duplicate, same_expression} AND review_state = reviewed | eligible | DEDUP_CANDIDATE |

**注1**：priority=110 により content/observation いずれかの軸が invalid なら全 purpose×target で ineligible（B4 の observation 穴を閉鎖）。
**注2（should_fix#4）**：法的裏付け（legal claim support）に転用してよいのは `evaluation_purpose = proof_corroboration` の eligible のみ。`extraction_corroboration × proof` の eligible は抽出観測の相互確認に限り、downstream guard `G_XDOC_PROOF_PURPOSE_ONLY_FOR_LEGAL` で法的裏付けへの転用を拒否。
**注3**：frbr_work_candidate × frbr_work の eligible は証拠の1片。FRBR Work 昇格には外部で multi-facet cluster 証拠が必要（HOLD）。

- **G_XDOC_INDEP_INVALID_BLOCKS_ELIGIBLE**（priority=110）。
- **G_XDOC_PROOF_REQUIRES_CONTENT_INDEPENDENT**（priority=100）。
- **G_XDOC_NO_COVERAGE_ABSENCE_CLAIM**（priority=90）。
- **G_XDOC_NO_CANDIDATE_PROMOTION**（priority=80）。

## 8. method_registry + method_capability_rule（versioned・B7）

### 8-1. method_registry（versioned id）
```text
method_registry
  method_registry_id          # required; sha256(canonical_json(method_id, version))  ← B7 versioned
  method_id                   # required; string
  version                     # required; string
  facet                       # required; facet enum
  emits_candidate_relation    # required; bool（candidate relation を出すか）
  allowed_non_candidate_assertion_types[]  # required; string[]（candidate 以外に出せる assertion。空＝candidate のみ）
  prohibited_assertion_types[]# required; string[]
```
| method_id | version | facet | emits_candidate_relation | allowed_non_candidate_assertion_types | prohibited_assertion_types |
|---|---|---|---|---|---|
| MinHash | v1 | text | true | [] | semantic_identity, citation_direction |
| SimHash | v1 | text | true | [] | semantic_identity, citation_direction |
| embedding | v1 | text | true | [] | symbol_identity, verbatim_identity |
| CDC | v1 | text | false | [boundary_segmentation] | segment_identity_standalone |
| content_hash | v1 | text | true | [] | standalone_use |
| table_structure | v1 | table | true | [] | figure_content |
| pHash | v1 | figure | true | [] | reviewed_figure_identity |
| visual_embedding | v1 | figure | true | [] | reviewed_figure_identity |

- **B7 candidate_only 廃止**：`emits_candidate_relation`（candidate を出すか）と `allowed_non_candidate_assertion_types`（candidate 以外に出せる assertion・空＝candidate のみ）に再定義。全 method は `reviewed_relation_type` を**直接生成しない**（global gate）。
- CDC は `emits_candidate_relation=false`・`allowed_non_candidate_assertion_types=[boundary_segmentation]`（境界生成のみ・relation を出さない）。

### 8-2. method_capability_rule（複合・versioned 参照 B7）
```text
method_capability_rule
  rule_id                     # required; string
  primary_method_registry_id  # required; string（FK → method_registry.method_registry_id）
  required_companion_method_registry_ids[]  # required; string[]（空 = 単独使用可）
  allowed_comparison_intents[]    # required; comparison_intent[]
  allowed_candidate_relation_types[] # required; candidate_relation_type[]
```
| rule_id | primary (method_id@version) | required_companions | allowed_intents | allowed_candidate_relation_types |
|---|---|---|---|---|
| R-MINHASH | MinHash@v1 | [] | near_duplicate, text_reuse | near_duplicate, lexical_overlap |
| R-SIMHASH | SimHash@v1 | [] | near_duplicate, text_reuse | near_duplicate, lexical_overlap |
| R-EMB | embedding@v1 | [] | semantic_overlap, citation_candidate | semantic_proximity |
| R-CDC-STANDALONE | CDC@v1 | [] | text_reuse | [] （relation 確定不可・境界のみ） |
| R-CDC-HASH | CDC@v1 | [content_hash@v1] | text_reuse, near_duplicate | segment_identity_candidate |
| R-TABLE | table_structure@v1 | [] | table_template, structure_comparison | table_structure_match |
| R-PHASH | pHash@v1 | [] | figure_reuse | figure_near_duplicate |
| R-VIS | visual_embedding@v1 | [] | figure_reuse | visual_proximity |

- **G_XDOC_METHOD_VOCAB**：method 出力は `reviewed_relation_type` を直接生成しない（常に NULL）。
- **G_XDOC_METHOD_CAPABILITY_DECLARED**：alignment.candidate_relation_types[] は適用 rule の allowed_candidate_relation_types の部分集合。
- **G_XDOC_METHOD_VERSION_BOUND**：capability rule は versioned method_registry_id を参照（version 変更で旧 capability 誤適用を防止）。

### 8-3. origin_relation × candidate_relation_type → reviewed_relation_type 対応表（規範・unknown 反映 B3）
全行 requires_human=true（method 出力の自動コピー禁止）。

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
| unknown | near_duplicate | near_duplicate, same_topic |
| unknown | semantic_proximity | same_topic |
| unknown | figure_near_duplicate | figure_reuse |
| unknown | visual_proximity | figure_reuse |
| unknown | table_structure_match | template_instance |
| unknown | structure_edit | edition_variant |

上記以外の組合せからの reviewed_relation_type 設定は validation error。

## 9. coverage（required scope 包含判定・B2）

### 9-1. range 型（coordinate_space 別・union 廃止 B2）
```text
range_page / range_char_offset / range_token
  start                       # required; integer（half-open [start, end)）
  end                         # required; integer
range_table_cell
  row_start ; row_end ; col_start ; col_end   # required; integer（half-open）
range_figure_region
  page ; x0 ; y0 ; x1 ; y1 ; coordinate_system  # required
```

### 9-2. coverage_assessment / coverage_policy / coverage_claim_scope
```text
coverage_assessment
  coverage_assessment_id      # required; sha256(canonical_json(
                              #   alignment_observation_id, member_ref, side, facet, assessment_version))
  alignment_observation_id    # required; FK
  member_ref                  # required; member@asset
  side                        # required; side enum
  facet                       # required; facet enum
  coordinate_space            # required; coordinate_space enum
  asset_hash                  # required; string（sha256）
  source_text_revision_id     # required; string
  selector_state              # required; selector_state enum
  covered_ranges[]            # required; coordinate_space に対応する range 型[]（空可）
  unknown_ranges[]            # required; 同 range 型[]（空可）
  ocr_quality_score           # required; float 0.0-1.0
  layout_quality_score        # required; float 0.0-1.0
  coverage_policy_id          # required; string
  coverage_policy_version     # required; string
  assessment_version          # required; string

coverage_policy
  policy_id ; policy_version  # required; string
  facet                       # required; facet enum
  required_coordinate_space   # required; coordinate_space enum
  minimum_ocr_quality         # required; float 0.0-1.0
  minimum_layout_quality      # required; float 0.0-1.0

coverage_claim_scope                   # B2: 対象範囲を明示
  use_assessment_key_id       # required; FK
  member_ref                  # required; member@asset
  required_coordinate_space   # required; coordinate_space enum
  required_ranges[]           # required; range 型[]（claim が覆うべき範囲）
  coverage_assessment_id      # required; FK → coverage_assessment
```

**coverage_complete_for_scope（B2・normative）**
```text
coverage_complete_for_scope(scope, ca, policy) ≡
  ca.selector_state = complete
  AND ca.ocr_quality_score   ≥ policy.minimum_ocr_quality
  AND ca.layout_quality_score ≥ policy.minimum_layout_quality
  AND ca.coordinate_space = scope.required_coordinate_space
  AND union(ca.covered_ranges) ⊇ union(scope.required_ranges)        # 包含必須
  AND intersection(ca.unknown_ranges, scope.required_ranges) = ∅     # 対象に unknown 不可
# union/intersection/⊇ は range 型ごとの half-open 区間演算で定義
```
- **G_XDOC_COVERAGE_MEMBER_KEYED**：n:m で member ごと判定。
- **G_XDOC_COVERAGE_SCOPE_CONTAINMENT**：absence/difference を根拠とする use_assessment は対象 member の `coverage_complete_for_scope = true` 必須（false → §7-2 priority=90 ineligible）。

## 10. cluster（valid support predicate・typed rule・B8）

### 10-1. xdoc_support_edge（undirected・effective predicate）
```text
xdoc_support_edge
  support_edge_id             # required; sha256(canonical_json(
                              #   cluster_facet, canonical_member_low, canonical_member_high,
                              #   alignment_observation_id))
  cluster_facet               # required; facet enum
  canonical_member_low        # required; string（min(member_a, member_b) by canonical string）
  canonical_member_high       # required; string（max(...)）
  alignment_observation_id    # required; FK
  support_score               # required; float 0.0-1.0
  calibration_id ; calibration_version  # required; string
  UNIQUE(canonical_member_low, canonical_member_high, alignment_observation_id)
  CONSTRAINT canonical_member_low ≠ canonical_member_high   # should_fix#2
```
**support_edge_effective（B8・normative）**
```text
support_edge_effective(edge, policy) ≡
  alignment(edge.alignment_observation_id) exists
  AND alignment は revoked use_assessment に依存しない（active observation）
  AND edge.calibration_id = policy.calibration_id
  AND edge.calibration_version = policy.calibration_version
  AND edge.support_score ≥ policy.minimum_support_score
  AND 当該 pair の required coverage_assessment.selector_state = complete（current）
```

### 10-2. xdoc_cluster（density 式を pairwise_support_coverage に一本化 B8）
```text
xdoc_cluster
  cluster_id                  # required; string
  facet                       # required; facet enum
  algorithm ; algorithm_version ; parameter_profile_id ; corpus_snapshot_id  # required; string
  members[]                   # required; cluster_member[]（§下記・size ≥ 2）
  representative_or_medoid    # optional; member_ref | NULL
  cluster_stability           # required; float 0.0-1.0
  stability_metric_id         # required; string
  pairwise_support_coverage   # required; float 0.0-1.0（= density・§下記単一定義）
  outlier_state               # required; bool
  policy_id ; policy_version  # required; string
cluster_member
  member_ref                  # required; string
  member_score                # required; float 0.0-1.0
```
**pairwise_support_coverage（= density・単一式 B8）**
```text
pairwise_support_coverage =
  count(canonical_member_pair で support_edge_effective を満たす edge が1件以上)
  ÷ count(クラスタ内 canonical_member_pair 総数)
# クラスタの密度指標はこの単一値（別 density field は持たない）
# size ≥ 2 を強制し分母 0 を防ぐ（should_fix#1）
```

### 10-3. cluster_policy（typed rule B8）
```text
cluster_policy
  policy_id ; policy_version  # required; string
  algorithm                   # required; string
  stability_metric_id         # required; string
  minimum_stability           # required; float 0.0-1.0
  minimum_density             # required; float 0.0-1.0（pairwise_support_coverage 下限）
  minimum_support_score       # required; float 0.0-1.0（support_edge_effective 用）
  calibration_id ; calibration_version  # required; string
  maximum_size                # required; integer
  outlier_rule_type           # required; outlier_rule_type enum
  outlier_threshold           # required; float
  missing_pair_rule_type      # required; missing_pair_rule_type enum
```

### 10-4. cluster_lineage_edge（append-only・配列埋込廃止 should_fix#5 / B9）
```text
cluster_lineage_edge
  lineage_edge_id             # required; sha256(canonical_json(
                              #   lineage_type, source_cluster_id, target_cluster_id, event_at))
  lineage_type                # required; lineage_type enum
  source_cluster_id           # required; string
  target_cluster_id           # required; string（split: 1→N の各 N / merge: N→1）
  event_at                    # required; ISO8601 datetime
```
- **G_XDOC_NO_TRANSITIVE_EQUIVALENCE**（A~B,B~C,A!~C で A=C を推論しない）。
- **G_XDOC_NO_TRANSITIVE_MEGACLUSTER**（推移閉包で巨大化しない）。
- **G_XDOC_CLUSTER_SUPPORT_CONTRACT**（support_edge_effective・stability・policy 無しのクラスタ確定禁止）。
- **G_XDOC_CLUSTER_SEMANTICS_CANDIDATE**：cluster は常に candidate_set（equivalence_class でない・定数制約）。
- cluster から FRBR/LITID/proof へ直接 promotion しない。

## 11. ゲート一覧（機械可読・全体）
INDEP_ACTIVE_UNIQUE / INDEP_DERIVED_FROM_EVIDENCE / INDEP_INVALID_BLOCKS_ELIGIBLE / PASSAGE_ORIGIN_REQUIRED / INTENT_REQUIRED / USE_ASSESSMENT_REVISION_UNIQUE / USE_ASSESSMENT_ONE_ACTIVE / NO_SILENT_MUTATION / PROOF_REQUIRES_CONTENT_INDEPENDENT / PROOF_PURPOSE_ONLY_FOR_LEGAL / NO_COVERAGE_ABSENCE_CLAIM / COVERAGE_SCOPE_CONTAINMENT / NO_CANDIDATE_PROMOTION / METHOD_VOCAB / METHOD_CAPABILITY_DECLARED / METHOD_VERSION_BOUND / COVERAGE_MEMBER_KEYED / NO_TRANSITIVE_EQUIVALENCE / NO_TRANSITIVE_MEGACLUSTER / CLUSTER_SUPPORT_CONTRACT / CLUSTER_SEMANTICS_CANDIDATE / OWNERSHIP_NO_REDEF / REPRODUCIBILITY_CONTRACT / DERIVED / NO_CLAIM_SUPPORT / HUMAN_PROMOTION_ONLY / NO_SELF_LOOP / FACET_ANCHORED。

## 12. 受入試験（v0.6・全自動 PASS が条件）
1. schema/enum/field に ellipsis(`...`)・union(`int|string`,`A[] or B[]`)・未定義 constant/digest/fingerprint・origin_relation=NULL が無い。全 field に型・required/optional/conditional・enum が定義。purpose×target 未定義組合せは validation error。
2. 同一 alignment を litlink_candidate×litlink と proof_corroboration×proof で別 use_assessment（別 use_assessment_key_id）に評価できる。
3. shared origin の 2 passage を proof_corroboration×proof → priority=100 CONTENT_NOT_INDEPENDENT → ineligible。unknown → hold。いずれかの軸 invalid → priority=110 ineligible。
4. content effective_value=independent/current / observation effective_value=shared の組合せで、軸ごとの independence_assessment が2件・各 effective_value/effective_status を別々に出力。active は軸ごと最大1件。
5. 各 content_origin_assertion から assertion_id・subject/origin の全 typed field・evidence_pointer_refs[]・evidence_hashes[] を個別追跡可能。origin_relation=unknown も表現可能。
6. n:m で対象 member の required_ranges を covered_ranges が包含しない（または unknown と交差）なら coverage_complete_for_scope=false → absence/difference 主張は priority=90 ineligible。covered_ranges=[] では包含不成立で必ず false。
7. R-CDC-STANDALONE → allowed_candidate_relation_types=[]。R-CDC-HASH（CDC@v1+content_hash@v1）→ segment_identity_candidate のみ。method version 違いの capability rule は別 method_registry_id で参照され誤適用されない。
8. pHash@v1 は emits_candidate_relation=true だが reviewed_figure_identity が prohibited。pHash/visual から reviewed_relation_type 直接生成は不可（NULL 必須）。
9. symmetric: members_a/b を入替えても unordered side-size から cardinality を決定し、side_canonical 順序で canonical_a/b を固定するため同一 alignment_observation_id。multi-member side が辞書順先頭でも n_m/one_n が一意（未定義分岐なし）。directional は入替で別 id・cardinality_directional に n_one を保持。
10. comparison_intent 変更で id 変化。facet/asset/text_revision/method_registry_id/parameter_profile_hash/normalization/tokenization/result_payload_digest/corpus_snapshot_id 変化でも id 変化。
11. A~B,B~C で support_edge_effective(A,C) を満たす edge が無ければ A-C pair は missing_pair_rule_type=unknown 扱い、pairwise_support_coverage 分子に数えず、identity/equivalence を推移推論しない。
12. XDOC から block_ref current・LITLINK accepted・FRBR/LITID identity・claim support へ直接昇格できない。extraction_corroboration の eligible は法的裏付けに転用不可（G_XDOC_PROOF_PURPOSE_ONLY_FOR_LEGAL）。

## 13. should_fix 反映
- #1 cluster size ≥ 2 強制（pairwise 分母 0 防止・§10-2）。
- #2 canonical_member_low ≠ canonical_member_high constraint（§10-1）。
- #3 非決定 method は result_payload_digest を observation lineage に保持（§5）。
- #4 extraction_corroboration の eligible を法的裏付けに転用しない downstream guard（§7-2 注2・G_XDOC_PROOF_PURPOSE_ONLY_FOR_LEGAL）。
- #5 cluster lineage を埋込配列でなく append-only edge object に分離（§10-4）。

## 14. GO / HOLD / loop_state
- **GO**：独立 DD 維持／v0.6 design-only patch／synthetic fixture（symmetric ID・coverage range containment・origin unknown mapping）／purpose-target・policy・method registry・cluster policy の read-only validator 試作／passage origin・pipeline provenance・coverage の gold fixture 設計。
- **HOLD**：v0.6 ratify／DDL/DB/mint/Box mutation／OCR/embedding/training／production pair generation・clustering／FRBR・DD-LITID・DD-LITLINK・block_ref current 自動昇格／evidence・legal claim support。
- loop_state = **patched（v0.6 must_fix 9点・決定式閉鎖）→ 再投函（再監査）候補**。
