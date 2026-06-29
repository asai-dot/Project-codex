# DD-XDOC-001 v0.8 — faceted cross-document comparison & alignment（round7 B14〜B18・coverage完全性/support証拠拘束 閉鎖）candidate

> **id**: DD-XDOC-001 / **version**: candidate v0.8 / **supersedes**: v0.7
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-23 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/学習/embedding/production pair generation/clustering/FRBR・DD-LITID・DD-LITLINK 昇格/block_ref current 昇格/evidence・legal claim support は **HOLD**。
> **改訂理由（v0.7→v0.8）**: GPT Pro 独立監査 `DDXDOC_MODIFY_REQUIRED`（RESULT Box 2302727111997）の blocking B14〜B18 + non-blocking 5点を反映。新規レイヤ追加なし。coverage 必要scope完全性・claim_kind 型付き・support_basis conditional non-empty/FK整合/completeness・coverage logical key+numeric revision・prose gate の executable 化。
> **改訂理由（v0.7 で閉鎖済・維持）**: B9 companion ID 材料化・B10 reviewed none priority85・単一 cardinality/minItems/symmetric n_one 禁止・range_class adapter・append-only revision・determinism 字段。
> **depends_on**: DD-LAYOUT-001 v0.5 / DD-XMODAL-001 v0.4 / DD-LITID-001 / DD-LITLINK-001（いずれも定義を狭めない）。

---

## 0. round7 blocking 反映（B14〜B18 / non-blocking）
| B | 指摘 | § |
|---|---|---|
| B14 | coverage が登録済み scope しか検査せず必要 member/scope の欠落を見逃す・claim_kind 未型付け | §6,§9 |
| B15 | support_basis 空配列で vacuous truth（effective=true） | §10 |
| B16 | support_basis record が edge に未拘束（無関係 active/current 参照で effective） | §10 |
| B17 | coverage current 選択が非決定的（version string 順序・partition 不足・payload 非digest） | §9 |
| B18 | gate 接地表に prose 残（FACET_ANCHORED/DERIVED/NO_CLAIM_SUPPORT/CLUSTER_SUPPORT_CONTRACT/determinism equality） | §5,§6,§10,§11 |
| nb1 | companion を unique set・registry 存在・facet 互換に | §5,§8 |
| nb2 | capability rule 多重 match → method_capability_rule_id 保持（most-specific/exactly-one） | §5,§8 |
| nb3 | primary 又は companion が nondeterministic なら digest 必須 | §5,§8 |
| nb4 | calibration/score を ID に含めない理由＝immutable derivation contract 明記 | §5 |
| nb5 | independence global invalid 判定は active/current assessment に限定 | §7 |

## 1. オブジェクト分離（関心の分離）
- **xdoc_alignment**：observation（不変・常に存在・lifecycle なし）。`alignment_observation_id`。
- **xdoc_use_assessment**：alignment に 1:N。append-only revision（§6）。**claim_context** を内包（B14）。
- **xdoc_independence_assessment**：alignment × axis（§3）。global invalid は active/current 限定（nb5）。
- **content_origin_assertion** / **member_pipeline_provenance**：member 単位の証拠（§4）。
- **coverage_assessment** + **coverage_policy** + **coverage_claim_scope**：logical key + numeric revision（§9・B17）。
- **xdoc_cluster** ＋ **xdoc_support_edge** ＋ **cluster_policy** ＋ **cluster_lineage_edge**：support graph（§10）。
- **method_registry** / **method_capability_rule**：versioned・determinism・facet 互換（§8）。

## 2. canonical enums（単一定義・ellipsis/union/conditional-type 不使用）
```text
facet                  = structure | text | table | figure
direction              = a_to_b | b_to_a | symmetric
cardinality            = one_one | one_n | n_one | n_m
  # constraint: direction=symmetric → cardinality ≠ n_one（§5 で one_n に正規化）
comparison_intent      = near_duplicate | text_reuse | semantic_overlap | edition_alignment
                       | structure_comparison | table_template | figure_reuse | citation_candidate
candidate_relation_type= near_duplicate | lexical_overlap | semantic_proximity
                       | segment_identity_candidate | table_structure_match
                       | figure_near_duplicate | visual_proximity | structure_edit
reviewed_relation_type = quote | reprint | adaptation | common_template | same_expression
                       | edition_variant | same_topic | template_instance | figure_reuse
                       | near_duplicate | none      # none=レビュー済非該当 / NULL=未レビュー
origin_relation        = quote | reprint | adaptation | common_template | same_expression | unknown
evaluation_purpose     = proof_corroboration | extraction_corroboration | litlink_candidate
                       | edition_resolution | formobj_variant_candidate | frbr_work_candidate | dedup
target                 = proof | litlink | frbr_work | litid_identity | formobj_variant | block_ref
claim_kind             = presence | absence | difference | none           # B14: 型付き
claimed_side           = a | b | both                                     # B14
unit_kind              = toc_node | page_block                            # B18: FACET_ANCHORED 用 typed
independence_value     = independent | shared | partially_shared | unknown
eligibility            = eligible | ineligible | hold
review_state           = unreviewed | reviewed | overridden | stale
effective_status       = current | stale | invalid
assessment_status      = active | superseded | revoked
coverage_status        = current | superseded
cluster_status         = candidate                                        # B18: 定数（昇格は人手・別 DD）
axis                   = content | observation
side                   = a | b
selector_state         = complete | partial | failed | not_applicable
coordinate_space       = page | char_offset | token | table_cell | figure_region
range_class            = interval_1d | grid_2d | rect_2d
edit_op                = insert | delete | move | rename | split | merge
ref_type               = origin_assertion | pipeline_provenance
basis_ref_type         = use_assessment_revision | coverage_assessment    # B15/B16
detection_state        = detected | verified | rejected
lineage_type           = split | merge | supersedes
method_determinism     = deterministic | nondeterministic
outlier_rule_type      = member_score_lt | edge_degree_lt | custom_registered
missing_pair_rule_type = unknown | reject_cluster | require_review
```

## 3. xdoc_independence_assessment（v0.7 から不変・CLOSED）
```text
computed_evidence_ref { ref_type; ref_id; ref_version_or_hash }            # 全 required
xdoc_independence_assessment
  independence_assessment_id  # sha256(canonical_json(alignment_observation_id, axis,
                              #   computed_policy_id, computed_policy_version, computed_input_fingerprint))
  alignment_observation_id ; axis ; computed_value
  computed_policy_id ; computed_policy_version
  computed_evidence_refs[]    # computed_evidence_ref[]（minItems=1）
  computed_input_fingerprint  # sha256(sort(refs by ref_type,ref_id,ref_version_or_hash), policy_id, policy_version)
  reviewed_value              # independence_value | NULL
  review_state ; review_reason_code(条件) ; reviewed_by(条件) ; reviewed_at(条件) ; review_note?
  effective_value ; effective_status ; supersedes_assessment_id? ; assessment_status
```
**effective_value 算定（v0.7 同一）**：fingerprint 不一致→stale/unknown；reviewed≠computed∧reason無→invalid/unknown；reviewed→reviewed；else computed。
- **G_XDOC_INDEP_ACTIVE_UNIQUE**：`(alignment, axis, policy_id, policy_version)` の active ≤ 1。

## 4. member 単位の証拠（v0.7 から不変・CLOSED）
```text
content_origin_assertion
  assertion_id ; subject_member_ref ; subject_passage_ref
  origin_object_type(statute|case|manuscript|edition|commentary|dataset) ; origin_object_id ; origin_object_version
  origin_passage_ref ; origin_relation(unknown 含む・NULL不可)
  evidence_pointer_refs[](minItems=1) ; evidence_hashes[](sha256,minItems=1)
  detection_method_registry_id ; confidence ; detection_state ; review_state
member_pipeline_provenance
  member_ref ; scan_source_id ; ocr_engine ; ocr_version ; parser ; parser_version
  normalization_profile_id ; normalization_profile_version ; tokenization_profile_id ; tokenization_profile_version
  source_text_revision_id ; evidence_refs[](minItems=1)
```

## 5. xdoc_alignment（typed unit_ref B18 / companion 検査 nb1-3 / determinism equality B18 / sf4 nb4）
```text
unit_ref                                    # B18: FACET_ANCHORED を typed FK に
  unit_kind                   # required; unit_kind enum（toc_node | page_block）
  unit_id                     # required; string（DD-LAYOUT page_block.block_id 又は biblio.toc_nodes.toc_node_id へ解決可能）
member_tuple
  asset_id ; text_revision    # required; string
  unit_ref                    # required; unit_ref（B18: 生 string 廃止・typed）

edit_script_op { op; src_unit_id(条件); dst_unit_id(条件); payload_digest? }

xdoc_alignment                # 不変・常に存在（lifecycle なし）・派生
  claim_support_eligible      # required; const false（B18: DERIVED を literal field 化）
  alignment_observation_id    # §下記 canonical
  schema_version ; facet ; comparison_intent ; direction ; cardinality
  members_a[](minItems=1) ; members_b[](minItems=1)   # member_tuple[]
  edit_script[]?
  primary_method_registry_id
  applied_companion_method_registry_ids[]   # B9/nb1: unique set・registry 存在・facet 互換（§8 gate）
  method_capability_rule_id   # required; nb2: 適用 rule を一意保持（most-specific/exactly-one・§8）
  parameter_profile_hash
  normalization_profile_id ; normalization_profile_version ; tokenization_profile_id ; tokenization_profile_version
  candidate_relation_types[]
  similarity ; calibration_id ; calibration_version ; score_components_ref
  method_determinism          # B18: = method_registry(primary).method_determinism（equality constraint）
  result_payload_digest       # 条件 required; primary 又は any companion が nondeterministic のとき（nb3）
  corpus_snapshot_id ; release_id
```
**determinism equality（B18・nb3・normative）**
```text
alignment.method_determinism = method_registry(primary_method_registry_id).method_determinism   # equality 必須
require_result_digest = (primary.method_determinism=nondeterministic)
                        OR exists(c ∈ applied_companion): method_registry(c).method_determinism=nondeterministic
require_result_digest=true ⇒ result_payload_digest NOT NULL（§下記 ID 材料にも入る）
```
**companion 検査（nb1・normative）**
```text
- applied_companion_method_registry_ids は unique set（duplicate は validation error）
- 各 id は method_registry に存在し method_registry(id).facet が alignment.facet と互換（同一 facet 又は registry 宣言の cross-facet 許可）
```
**canonical alignment_observation_id**
```text
alignment_observation_id = sha256(canonical_json(
  schema_version, facet, comparison_intent, direction, cardinality,
  members_canonical,                          # symmetric: side 正規化[canonical_a,canonical_b] / directional: 順序保持
  primary_method_registry_id, sort_ascending(applied_companion_method_registry_ids),
  parameter_profile_hash, normalization_profile_id, normalization_profile_version,
  tokenization_profile_id, tokenization_profile_version,
  result_payload_digest,                      # NULL 可（require_result_digest=false）
  corpus_snapshot_id, release_id))
# members_canonical の member は (asset_id, text_revision, unit_ref) を canonical_json 化
# side non-empty・intra-side dup・self overlap は v0.7 §5 維持（G_XDOC_NO_SELF_LOOP）
# symmetric cardinality は unordered side-size 決定（n_one 不発生）
```
**nb4（ID 不変材料の immutable derivation contract）**
```text
calibration_id/version・score_components_ref・similarity は observation_id 材料に含めない。
理由: これらは同一 (member, method, companion, snapshot) 観測の派生スコアであり observation identity を変えない。
契約: score_components_ref は content-addressed immutable（sha256 of score components object・改変時は新 alignment ではなく新 score object）。
```

## 6. xdoc_use_assessment（claim_context 型付き B14 / append-only revision・CLOSED）
```text
claim_context                               # B14: claim_is_absence_or_difference を型付き入力に
  use_assessment_key_id       # required; FK
  claim_kind                  # required; claim_kind enum（presence|absence|difference|none）
  claimed_side                # required; claimed_side enum（a|b|both）
  claimed_member_refs[]       # required; member_ref[]（minItems=1・alignment members の部分集合）
  required_coordinate_space   # required; coordinate_space enum
# claim_is_absence_or_difference ≡ claim_context.claim_kind ∈ {absence, difference}（外部暗黙変数の廃止）

decision_payload { eligibility; reason_codes_sorted; evidence_refs_sorted;
  reviewed_relation_type; review_state; revoked; revocation_reason_code; assessed_by }
decision_payload_digest = sha256(canonical_json(decision_payload))

xdoc_use_assessment           # append-only・不変・派生
  claim_support_eligible      # required; const false（B18 DERIVED）
  use_assessment_key_id       # sha256(canonical_json(alignment_observation_id, evaluation_purpose, target, policy_id, policy_version))
  assessment_revision_id      # sha256(canonical_json(use_assessment_key_id, decision_payload_digest, revision_seq))
  revision_seq(integer,prior+1) ; supersedes_revision_id ; revoked ; revocation_reason_code(条件)
  alignment_observation_id ; evaluation_purpose ; target ; eligibility ; policy_id ; policy_version
  reason_codes[](minItems=1) ; evidence_refs[]? ; reviewed_relation_type? ; assessed_at ; assessed_by ; review_state
```
**status 導出**：current_revision(key)=max(revision_seq)；revoked→revoked / current∧非revoked→active / else superseded。
- **G_XDOC_USE_ASSESSMENT_REVISION_UNIQUE**：UNIQUE(key, revision_seq)。**ONE_ACTIVE**：active ≤ 1/key。**NO_SILENT_MUTATION**：append-only。

## 7. eligibility（v0.7 §7 + nb5 active/current 限定）

### 7-1. purpose_target_compatibility（v0.7 同一）
proof_corroboration→proof / extraction_corroboration→proof / litlink_candidate→litlink / edition_resolution→litid_identity / formobj_variant_candidate→formobj_variant / frbr_work_candidate→frbr_work / dedup→block_ref（いずれも default hold）。**他は allowed=false（作成禁止）。**

### 7-2. purpose_positive_reviewed_relations（v0.7 同一・none/NULL は全非該当）
proof:{quote,reprint,adaptation,same_expression}／litlink:{quote,reprint,adaptation,same_expression,same_topic,near_duplicate,edition_variant,template_instance,figure_reuse}／edition_resolution:{edition_variant}／formobj:{template_instance,common_template}／frbr:{edition_variant,same_expression,adaptation,reprint}／dedup:{near_duplicate,same_expression}／extraction:（reviewed_relation 非依存）。

### 7-3. eligibility_policy_rule（policy_id=XDOC-ELIG-001/v1・priority 解決：大優先・同priority は ineligible>hold>eligible・全非該当→7-1 default）
| priority | purpose | target | condition | result | reason |
|---|---|---|---|---|---|
| 110 | * | * | **exists independence assessment (any axis) where assessment_status=active AND effective_status=invalid**（nb5: active/current 限定） | ineligible | INDEPENDENCE_INVALID_GLOBAL |
| 105 | proof_corroboration | proof | observation_independence(active).effective_status=stale | hold | OBSERVATION_INDEPENDENCE_STALE |
| 100 | proof_corroboration | proof | content_independence(active).effective_value ∈ {shared,partially_shared} | ineligible | CONTENT_NOT_INDEPENDENT |
| 100 | proof_corroboration | proof | content_independence(active).effective_value=unknown | hold | CONTENT_INDEPENDENCE_UNKNOWN |
| 100 | proof_corroboration | proof | observation_independence(active).effective_value ∈ {shared,partially_shared,unknown} | hold | OBSERVATION_NOT_INDEPENDENT_LEGAL |
| 100 | proof_corroboration | proof | content_independence(active).effective_status=stale | hold | CONTENT_INDEPENDENCE_STALE |
| 90 | * | * | claim_context.claim_kind ∈ {absence,difference} AND coverage_complete_for_use_assessment=false | ineligible | COVERAGE_INCOMPLETE |
| 85 | * | {proof,litlink,frbr_work,litid_identity,formobj_variant,block_ref} | reviewed_relation_type=none | ineligible | REVIEWED_RELATION_NONE |
| 80 | * | {litlink,frbr_work,litid_identity,formobj_variant,block_ref} | reviewed_relation_type IS NULL | ineligible | REVIEWED_RELATION_REQUIRED |
| 70 | frbr_work_candidate | frbr_work | review_state≠reviewed | hold | HUMAN_REVIEW_REQUIRED |
| 50 | proof_corroboration | proof | content_independence(active)=independent/current AND observation_independence(active)=independent/current AND is_positive(proof_corroboration,reviewed_relation_type) AND review_state=reviewed | eligible | INDEPENDENT_CORROBORATION |
| 50 | extraction_corroboration | proof | observation_independence(active).effective_value ∈ {independent,partially_shared} AND .effective_status=current AND review_state=reviewed | eligible | EXTRACTION_CANDIDATE |
| 50 | litlink_candidate | litlink | is_positive(litlink_candidate,reviewed_relation_type) AND review_state=reviewed | eligible | LITLINK_CANDIDATE |
| 50 | edition_resolution | litid_identity | is_positive(edition_resolution,reviewed_relation_type) AND review_state=reviewed | eligible | EDITION_CANDIDATE |
| 50 | formobj_variant_candidate | formobj_variant | is_positive(formobj_variant_candidate,reviewed_relation_type) AND review_state=reviewed | eligible | FORMOBJ_CANDIDATE |
| 50 | frbr_work_candidate | frbr_work | is_positive(frbr_work_candidate,reviewed_relation_type) AND review_state=reviewed | eligible | FRBR_CANDIDATE |
| 50 | dedup | block_ref | is_positive(dedup,reviewed_relation_type) AND review_state=reviewed | eligible | DEDUP_CANDIDATE |

- **nb5**：independence 参照は常に active/current assessment（superseded/revoked は無視）。
- guard：法的裏付け転用可は proof_corroboration の eligible のみ（**G_XDOC_PROOF_PURPOSE_ONLY_FOR_LEGAL**）。

## 8. method_registry + method_capability_rule（facet 互換 nb1 / exactly-one nb2 / determinism）
```text
method_registry { method_registry_id=sha256(method_id,version); method_id; version; facet;
  method_determinism; emits_candidate_relation; allowed_non_candidate_assertion_types[]; prohibited_assertion_types[] }
method_capability_rule { rule_id; primary_method_registry_id;
  required_companion_method_registry_ids[]; allowed_comparison_intents[]; allowed_candidate_relation_types[];
  specificity }    # nb2: most-specific selection 用（companion 数・制約数で順位）
```
registry（v0.7 同一）：MinHash/SimHash/embedding(nondet)/CDC(emits=false,[boundary_segmentation])/content_hash/table_structure/pHash/visual_embedding(nondet)。
capability（v0.7 同一）：R-CDC-STANDALONE(companion=[]→relation=[]) / R-CDC-HASH(companion=[content_hash@v1]→segment_identity_candidate) 等。
**G_XDOC_METHOD_CAPABILITY_DECLARED（B9 維持・normative）**
```text
alignment に rule r を当てるとき:
 1. r.rule_id = alignment.method_capability_rule_id（nb2: alignment が保持・多重 match は most-specific=最大 specificity で一意化、同点は validation error）
 2. r.primary_method_registry_id = alignment.primary_method_registry_id
 3. set(r.required_companion_method_registry_ids) ⊆ set(alignment.applied_companion_method_registry_ids)
 4. alignment.candidate_relation_types[] ⊆ r.allowed_candidate_relation_types
 5. alignment.comparison_intent ∈ r.allowed_comparison_intents
```
- **G_XDOC_METHOD_VOCAB**：method は reviewed_relation_type を生成しない（NULL）。**METHOD_VERSION_BOUND**：versioned id 参照。**METHOD_FACET_COMPAT**（nb1）。

## 9. coverage（logical key + numeric revision B17 / 必要scope完全性 B14 / range_class adapter）

### 9-1. coordinate_space→range_class と range 型（v0.7 同一）
page/char_offset/token=interval_1d{start,end:int half-open}；table_cell=grid_2d{row_start,row_end,col_start,col_end}；figure_region=rect_2d{page,x0,y0,x1,y1,coordinate_system}。各 range 非空必須・異 range_class 間演算禁止。adapter=interval_1d/grid_2d/rect_2d の union/intersection/contains。

### 9-2. coverage_assessment（logical key + numeric revision・B17）
```text
coverage_assessment
  coverage_assessment_key_id  # required; B17: sha256(canonical_json(
                              #   alignment_observation_id, member_ref, side, facet, coordinate_space, coverage_policy_id))
  coverage_revision_seq       # required; integer（prior+1、1 始まり）
  coverage_assessment_id      # required; B17: sha256(canonical_json(
                              #   coverage_assessment_key_id, coverage_revision_seq, coverage_policy_version, coverage_payload_digest))
  coverage_payload_digest     # required; sha256(canonical_json(
                              #   asset_hash, source_text_revision_id, selector_state,
                              #   covered_ranges, unknown_ranges, ocr_quality_score, layout_quality_score))
  alignment_observation_id ; member_ref ; side ; facet ; coordinate_space
  asset_hash ; source_text_revision_id ; selector_state
  covered_ranges[]（range[]・空可・各非空） ; unknown_ranges[]（同）
  ocr_quality_score ; layout_quality_score ; coverage_policy_id ; coverage_policy_version
  supersedes_coverage_assessment_id?
  coverage_status             # 導出（§下記）
UNIQUE(coverage_assessment_key_id, coverage_revision_seq)
coverage_status(ca) = ca.coverage_revision_seq = max(revision_seq) over key → current / else superseded
# partition に coordinate_space と coverage_policy_id を含むため、別 space/policy が相互 supersede しない（B17）
coverage_policy { policy_id; policy_version; facet; required_coordinate_space; minimum_ocr_quality; minimum_layout_quality }
coverage_claim_scope { use_assessment_key_id; member_ref; required_coordinate_space;
  required_ranges[](minItems=1・各非空・正規化済) ; coverage_assessment_id(FK→current) }
```

### 9-3. 必要scope完全性（B14・normative）
```text
required_scope_keys(key) =      # claim_context から導出（登録漏れを検出）
  { (m, claim_context.required_coordinate_space) :
      m ∈ claim_context.claimed_member_refs }            # claimed_side で a/b を解決
actual_scope_keys(key) =
  { (s.member_ref, s.required_coordinate_space) : s ∈ coverage_claim_scope WHERE use_assessment_key_id=key }

coverage_complete_for_scope(scope, ca, policy) ≡        # current+complete の両方（B16 でも参照）
  ca.coverage_status=current AND ca.selector_state=complete
  AND ca.ocr_quality_score ≥ policy.minimum_ocr_quality AND ca.layout_quality_score ≥ policy.minimum_layout_quality
  AND ca.coordinate_space = scope.required_coordinate_space
  AND contains(union(ca.covered_ranges), union(scope.required_ranges))
  AND intersection(union(ca.unknown_ranges), union(scope.required_ranges)) = ∅

coverage_complete_for_use_assessment(key) ≡            # B14: 必要 key 完全性 + 各 complete
  required_scope_keys(key) ⊆ actual_scope_keys(key)     # 未登録 key があれば false
  AND every(scope ∈ coverage_claim_scope[key]):
        coverage_complete_for_scope(scope, current_ca(scope.coverage_assessment_id), policy)
# missing member/scope → required ⊄ actual → false（受入試験6 が成立）
```
- **G_XDOC_COVERAGE_REQUIRED_SCOPE_COMPLETE**（B14）/ **COVERAGE_LOGICAL_KEY_DETERMINISTIC**（B17）/ **COVERAGE_MEMBER_KEYED**。

## 10. cluster（support_basis non-empty B15 / FK 整合 B16 / cluster_status B18）

### 10-1. xdoc_support_edge（typed basis・conditional non-empty B15）
```text
xdoc_support_edge
  support_edge_id             # sha256(canonical_json(cluster_facet, canonical_member_low, canonical_member_high, alignment_observation_id))
  cluster_facet ; canonical_member_low ; canonical_member_high ; alignment_observation_id
  support_score ; calibration_id ; calibration_version
  support_basis_use_assessment_revision_ids[]   # B15: unique items
  support_basis_coverage_assessment_ids[]        # B15: unique items
  UNIQUE(canonical_member_low, canonical_member_high, alignment_observation_id)
  CONSTRAINT canonical_member_low ≠ canonical_member_high
```
**support_basis_valid（B16・型別 FK 整合・normative）**
```text
support_basis_valid(edge, ref) ≡ match ref.basis_ref_type:
  use_assessment_revision:
     r = use_assessment_revision(ref); assessment_status(r)=active
     AND r.alignment_observation_id = edge.alignment_observation_id
     AND r.target ∈ cluster_policy.allowed_support_targets AND r.evaluation_purpose ∈ cluster_policy.allowed_support_purposes
     AND r.eligibility ≠ ineligible
  coverage_assessment:
     c = coverage_assessment(ref); coverage_status(c)=current
     AND c.alignment_observation_id = edge.alignment_observation_id
     AND c.member_ref ∈ {edge.canonical_member_low, edge.canonical_member_high}
     AND c.facet = edge.cluster_facet
     AND coverage_complete_for_scope(required_scope_for(edge, c.member_ref), c, coverage_policy)  # current だけでなく complete
```
**support_edge_effective（B15/B16・normative）**
```text
support_edge_effective(edge, policy) ≡
  edge.support_score ≥ policy.minimum_support_score
  AND edge.calibration_id = policy.calibration_id AND edge.calibration_version = policy.calibration_version
  AND non_empty_required(edge, policy)                 # B15: policy.required_basis_types の配列は minItems=1
  AND every(ref ∈ edge.support_basis_use_assessment_revision_ids ∪ support_basis_coverage_assessment_ids):
        support_basis_valid(edge, ref)                 # B16: 空なら every は vacuous だが non_empty_required で阻止
non_empty_required(edge, policy) ≡
  ('use_assessment_revision' ∈ policy.required_basis_types ⇒ len(edge.support_basis_use_assessment_revision_ids) ≥ 1)
  AND ('coverage_assessment' ∈ policy.required_basis_types ⇒ len(edge.support_basis_coverage_assessment_ids) ≥ 1)
# policy.required_basis_types が両方を要求する既定では、空配列 edge は effective=false（B15 閉鎖）
```

### 10-2. xdoc_cluster（cluster_status 定数 B18・member-level outlier）
```text
xdoc_cluster
  claim_support_eligible      # const false（B18 DERIVED）
  cluster_id ; facet ; algorithm ; algorithm_version ; parameter_profile_id ; corpus_snapshot_id
  members[]（cluster_member[]・minItems=2） ; representative_or_medoid?
  cluster_stability ; stability_metric_id ; pairwise_support_coverage ; cluster_outlier_state
  cluster_status              # const candidate（B18: 昇格 state を schema に持たせ promotion を別 DD/人手に固定）
  policy_id ; policy_version
cluster_member { member_ref; member_score; member_outlier_state }
pairwise_support_coverage = count(canonical_member_pair で support_edge_effective を満たす edge≥1) ÷ count(pair 総数)
```

### 10-3. cluster_policy（required_basis_types/allowed_support_* 追加 B15/B16）
```text
cluster_policy { policy_id; policy_version; algorithm; stability_metric_id;
  minimum_stability; minimum_density; minimum_support_score; calibration_id; calibration_version; maximum_size;
  outlier_rule_type; outlier_threshold; missing_pair_rule_type;
  required_basis_types[]               # B15: {use_assessment_revision, coverage_assessment} の部分集合・既定=両方
  allowed_support_targets[]            # B16: support に使える target（例 litlink, formobj_variant）
  allowed_support_purposes[] }         # B16: support に使える purpose
```

### 10-4. cluster_lineage_edge（v0.7 同一）
```text
cluster_lineage_edge { lineage_edge_id=sha256(canonical_json(lineage_type, source_cluster_id, target_cluster_id, event_at));
  lineage_type; source_cluster_id; target_cluster_id; event_at }
```
- **G_XDOC_SUPPORT_BASIS_NONEMPTY**（B15）/ **SUPPORT_BASIS_FK_BOUND**（B16）/ **CLUSTER_STATUS_CANDIDATE**（B18 const）/ NO_TRANSITIVE_EQUIVALENCE / NO_TRANSITIVE_MEGACLUSTER / CLUSTER_SUPPORT_CONTRACT。

## 11. ゲート → executable predicate 接地表（B18・prose 残を全廃）
| gate | executable predicate |
|---|---|
| FACET_ANCHORED | §5 member_tuple.unit_ref（typed unit_kind+unit_id）が DD-LAYOUT page_block.block_id 又は toc_nodes.toc_node_id に解決（FK・未解決は validation error） |
| DERIVED | §5/§6/§10 各 object に `claim_support_eligible` literal const false が存在 |
| NO_CLAIM_SUPPORT | claim_support_eligible=false の record を claim/evidence support として参照する export は validation error（record-level predicate） |
| CLUSTER_SUPPORT_CONTRACT | §10-2 cluster_status=candidate const・support_edge_effective+stability+policy 無しの確定は不可（promotion field 無し＝昇格不可） |
| METHOD_DETERMINISM_EQUALITY | §5 alignment.method_determinism = method_registry(primary).method_determinism（equality） |
| INDEP_ACTIVE_UNIQUE | §3 |
| INDEP_INVALID_BLOCKS_ELIGIBLE | §7-3 priority 110（active/current 限定） |
| REVIEWED_NONE_NOT_POSITIVE | §7-3 priority 85 |
| NO_CANDIDATE_PROMOTION | §7-3 priority 80 |
| PROOF_REQUIRES_CONTENT_INDEPENDENT | §7-3 priority 100 |
| COVERAGE_REQUIRED_SCOPE_COMPLETE | §9-3 required_scope_keys ⊆ actual_scope_keys ∧ every complete |
| COVERAGE_LOGICAL_KEY_DETERMINISTIC | §9-2 numeric revision_seq + key + payload_digest |
| SUPPORT_BASIS_NONEMPTY | §10-1 non_empty_required |
| SUPPORT_BASIS_FK_BOUND | §10-1 support_basis_valid |
| USE_ASSESSMENT_REVISION_UNIQUE / ONE_ACTIVE / NO_SILENT_MUTATION | §6 |
| METHOD_CAPABILITY_DECLARED / VOCAB / VERSION_BOUND / FACET_COMPAT | §8 |
| NO_TRANSITIVE_EQUIVALENCE / NO_TRANSITIVE_MEGACLUSTER | §10 |
| REPRODUCIBILITY_CONTRACT | §5 ID 材料（snapshot/revision/param/normalization/tokenization/result_digest） |
| OWNERSHIP_NO_REDEF | XDOC は DD-LAYOUT block_ref / DD-LITLINK lit_link を再定義しない |
| HUMAN_PROMOTION_ONLY | §7-3 priority 50 群 review_state=reviewed |
| NO_SELF_LOOP | §5 self overlap / intra-side dup reject |

## 12. 受入試験（v0.8・全自動 PASS が条件）
1. schema に ellipsis/union/conditional-type/prose-only gate が無い。cardinality 単一・minItems・method_determinism 字段・unit_ref typed・claim_support_eligible literal・cluster_status const。§11 で全 gate が executable predicate に接地。
2. 同一 alignment を別 purpose×target で別 use_assessment_key_id に評価できる。
3. shared origin→ineligible / unknown→hold / 任意軸 active invalid→110 ineligible（superseded invalid は無視）。
4. content/observation の axis ごと independence_assessment・active 各1件・global invalid は active のみ参照。
5. content_origin_assertion の全 typed field 追跡可・origin_relation=unknown 可。
6. **必要scope完全性**：claim_context.claimed_member_refs の member の scope が1つでも未登録なら required ⊄ actual → coverage_complete_for_use_assessment=false → absence/difference は priority=90 ineligible。covered_ranges=[] は包含不成立で false。
7. R-CDC-STANDALONE→relation=[]・R-CDC-HASH（content_hash@v1 を applied_companion に含む）のみ segment_identity_candidate。companion は unique set・registry 存在・facet 互換。
8. pHash@v1 は reviewed_figure_identity prohibited・reviewed_relation 直接生成不可。
9. symmetric side-swap→同一 id・n_one 不発生 / directional 入替→別 id・n_one 保持。
10. comparison_intent/facet/asset/text_revision/unit_ref/primary・companion set/parameter/normalization/tokenization/result_payload_digest/corpus_snapshot のいずれか変化で id 変化。
11. **support_edge_effective**：(a) support_basis 両配列空→non_empty_required で false（vacuous true 不成立） (b) 参照 use_assessment/coverage が edge の alignment と異なる→support_basis_valid false (c) coverage が selector_state=failed の current→complete でない→false (d) coverage facet≠cluster_facet→false。A~B,B~C で effective edge(A,C) 無し→A-C は missing_pair_rule_type=unknown・分子に数えず推移推論しない。
12. reviewed=none→priority85 ineligible・XDOC から block_ref current/LITLINK accepted/FRBR/LITID identity/claim support へ直接昇格不可（claim_support_eligible=false・cluster_status=candidate）。

## 13. coverage current 決定性 & 追加 fixture（v0.8 必須）
- `coverage_revision_seq` は integer。`v9/v10` 等の string 順序に依存しない（B17）。
- 追加 negative fixture（GO）：missing-member-scope（B14）・empty-support-basis（B15）・foreign-assessment-ref（B16）・failed-current-coverage（B16）・`v9/v10` revision ordering（B17）・wrong-facet coverage（B16）。

## 14. GO / HOLD / loop_state
- **GO**：独立 DD 維持／v0.8 限定 patch／synthetic read-only validator + 上記 negative fixtures／purpose-target・policy・method registry・cluster policy 作成。
- **HOLD**：v0.8 ratify／DDL/DB/mint/Box mutation／OCR/embedding/training／production pair generation・clustering／FRBR・DD-LITID・DD-LITLINK・block_ref current 自動昇格／evidence・legal claim support。
- loop_state = **patched（v0.8 B14〜B18・coverage完全性/support証拠拘束 閉鎖）→ 再投函（再監査）候補**。
