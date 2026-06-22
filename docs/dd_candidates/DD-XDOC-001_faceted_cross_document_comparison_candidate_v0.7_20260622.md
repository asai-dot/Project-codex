# DD-XDOC-001 v0.7 — faceted cross-document comparison & alignment（round6 B9〜B13・接続字段/predicate 閉鎖）candidate

> **id**: DD-XDOC-001 / **version**: candidate v0.7 / **supersedes**: v0.6
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-22 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/学習/embedding/production pair generation/clustering/FRBR・DD-LITID・DD-LITLINK 昇格/block_ref current 昇格/evidence・legal claim support は **HOLD**。
> **改訂理由（v0.6→v0.7）**: GPT Pro 独立再監査（訂正版）`DDXDOC_MODIFY_REQUIRED`（RESULT Box 2301891158281）の blocking B9〜B13 + should_fix 4点を反映。新規レイヤ追加なし。companion method の実行事実字段化・reviewed `none` の global negative rule・coverage 空scope/全scope集約・support_edge の実在 evidence refs 接地・単一 cardinality 型/side non-empty/method determinism/gate 接地。
> **depends_on**: DD-LAYOUT-001 v0.5 / DD-XMODAL-001 v0.4 / DD-LITID-001 / DD-LITLINK-001（いずれも定義を狭めない）。

---

## 0. round6 blocking 反映（B9〜B13 / should_fix）
| B | 指摘 | § |
|---|---|---|
| B9 | required companion method を alignment が保持せず検証不能（must_fix B7 再open） | §5,§8 |
| B10 | reviewed_relation_type=none が positive eligibility を満たす意味矛盾 | §7 |
| B11 | coverage の required_ranges 空・全member/全scope 集約未定義・figure_region 2D 演算 | §9 |
| B12 | support_edge_effective が参照する active/coverage 字段が実在しない | §10 |
| B13 | 単一 cardinality 型・side non-empty・method determinism・未接地 gate（受入試験1） | §2,§5,§8,§11 |
| sf1 | decision_payload に revoked/revocation_reason_code を含める | §6 |
| sf2 | coverage_assessment_id に input fingerprint（asset_hash/source_revision/policy_version） | §9 |
| sf3 | cluster outlier を member-level でも追跡 | §10 |
| sf4 | score_components_ref の参照型と immutability | §5 |

## 1. オブジェクト分離（関心の分離）
- **xdoc_alignment**：observation（何を・どの method 群で・どの member 間で検出したか）。**不変・常に存在**（lifecycle を持たない・§5）。`alignment_observation_id`。
- **xdoc_use_assessment**：alignment に 1:N（evaluation_purpose × target ごとの eligibility＋policy）。append-only revision 履歴（§6）。
- **xdoc_independence_assessment**：alignment × axis ごとの computed/reviewed/effective 独立性（§3）。
- **content_origin_assertion** / **member_pipeline_provenance**：member 単位の証拠。独立性は**これらから導出**（手入力しない）。
- **coverage_assessment** + **coverage_policy** + **coverage_claim_scope**：member-keyed・対象範囲包含判定・revision 付き（§9）。
- **xdoc_cluster** ＋ **xdoc_support_edge** ＋ **cluster_policy** ＋ **cluster_lineage_edge**：support graph（§10）。
- **method_registry** / **method_capability_rule**：versioned・determinism 付き（§8）。

## 2. canonical enums（単一定義・全所で同一・ellipsis/union/conditional-type 不使用）
```text
facet                  = structure | text | table | figure
direction              = a_to_b | b_to_a | symmetric
cardinality            = one_one | one_n | n_one | n_m
  # B13: 単一 enum（conditional 2-enum 廃止）。
  # constraint: direction=symmetric → cardinality ∈ {one_one, one_n, n_m}（n_one 禁止・§5 で one_n に正規化）
  # constraint: direction ∈ {a_to_b, b_to_a} → 4値すべて可（side 順序保持）
comparison_intent      = near_duplicate | text_reuse | semantic_overlap | edition_alignment
                       | structure_comparison | table_template | figure_reuse | citation_candidate
candidate_relation_type= near_duplicate | lexical_overlap | semantic_proximity
                       | segment_identity_candidate | table_structure_match
                       | figure_near_duplicate | visual_proximity | structure_edit
reviewed_relation_type = quote | reprint | adaptation | common_template | same_expression
                       | edition_variant | same_topic | template_instance | figure_reuse
                       | near_duplicate | none
                       # none = レビュー済み・非該当（positive eligibility 不可・§7）。NULL = 未レビュー。型で区別。
origin_relation        = quote | reprint | adaptation | common_template | same_expression | unknown
evaluation_purpose     = proof_corroboration | extraction_corroboration | litlink_candidate
                       | edition_resolution | formobj_variant_candidate | frbr_work_candidate | dedup
target                 = proof | litlink | frbr_work | litid_identity | formobj_variant | block_ref
independence_value     = independent | shared | partially_shared | unknown
eligibility            = eligible | ineligible | hold
review_state           = unreviewed | reviewed | overridden | stale
effective_status       = current | stale | invalid
assessment_status      = active | superseded | revoked
coverage_status        = current | superseded
axis                   = content | observation
side                   = a | b
selector_state         = complete | partial | failed | not_applicable
coordinate_space       = page | char_offset | token | table_cell | figure_region
range_class            = interval_1d | grid_2d | rect_2d   # §9 coordinate_space→range_class 写像
edit_op                = insert | delete | move | rename | split | merge
ref_type               = origin_assertion | pipeline_provenance
detection_state        = detected | verified | rejected
lineage_type           = split | merge | supersedes
method_determinism     = deterministic | nondeterministic   # B13
outlier_rule_type      = member_score_lt | edge_degree_lt | custom_registered
missing_pair_rule_type = unknown | reject_cluster | require_review
```

## 3. xdoc_independence_assessment（v0.6 から不変・CLOSED）
```text
computed_evidence_ref
  ref_type                    # required; ref_type enum
  ref_id                      # required; string
  ref_version_or_hash         # required; string

xdoc_independence_assessment
  independence_assessment_id  # required; sha256(canonical_json(
                              #   alignment_observation_id, axis,
                              #   computed_policy_id, computed_policy_version,
                              #   computed_input_fingerprint))
  alignment_observation_id    # required; FK
  axis                        # required; content | observation
  computed_value              # required; independence_value
  computed_policy_id          # required; string
  computed_policy_version     # required; string
  computed_evidence_refs[]    # required; computed_evidence_ref[]（minItems=1）
  computed_input_fingerprint  # required; sha256（§下記）
  reviewed_value              # optional; independence_value | NULL
  review_state                # required; review_state enum
  review_reason_code          # conditional required; review_state ∈ {reviewed, overridden, stale}
  reviewed_by                 # conditional required; review_state ∈ {reviewed, overridden} OR reviewed_value≠NULL
  reviewed_at                 # conditional required; 同上
  review_note                 # optional; string
  effective_value             # required; independence_value
  effective_status            # required; effective_status enum
  supersedes_assessment_id    # optional; NULL or 前の independence_assessment_id
  assessment_status           # required; assessment_status enum（current view 導出）
```
**computed_input_fingerprint / effective_value 算定**（v0.6 と同一・normative）
```text
computed_input_fingerprint = sha256(canonical_json(
  sort(computed_evidence_refs by (ref_type, ref_id, ref_version_or_hash)),
  computed_policy_id, computed_policy_version))
current_fingerprint = 同式を現在の証拠 ref 集合で再計算
1. computed_input_fingerprint ≠ current_fingerprint → effective_status=stale; effective_value=unknown; STOP
2. reviewed_value≠NULL AND computed_value≠reviewed_value AND review_reason_code IS NULL → effective_status=invalid; effective_value=unknown; STOP
3. reviewed_value≠NULL → effective_status=current; effective_value=reviewed_value
4. reviewed_value=NULL → effective_status=current; effective_value=computed_value
```
- **G_XDOC_INDEP_ACTIVE_UNIQUE**：`(alignment_observation_id, axis, computed_policy_id, computed_policy_version)` の active は最大1件。
- **G_XDOC_INDEP_DERIVED_FROM_EVIDENCE**：computed_value は evidence_refs ＋ policy 由来。

## 4. member 単位の証拠（v0.6 から不変・CLOSED）
```text
content_origin_assertion
  assertion_id ; subject_member_ref ; subject_passage_ref      # required; string
  origin_object_type          # required; statute | case | manuscript | edition | commentary | dataset
  origin_object_id ; origin_object_version ; origin_passage_ref# required; string
  origin_relation             # required; origin_relation enum（unknown 含む・NULL 不可）
  evidence_pointer_refs[]     # required; string[]（minItems=1）
  evidence_hashes[]           # required; string[]（sha256・minItems=1）
  detection_method_registry_id# required; string（§8）
  confidence                  # required; float 0.0-1.0
  detection_state             # required; detection_state enum
  review_state                # required; review_state enum

member_pipeline_provenance
  member_ref ; scan_source_id ; ocr_engine ; ocr_version       # required; string
  parser ; parser_version                                      # required; string
  normalization_profile_id ; normalization_profile_version     # required; string
  tokenization_profile_id ; tokenization_profile_version       # required; string
  source_text_revision_id                                      # required; string
  evidence_refs[]             # required; string[]（minItems=1）
```

## 5. xdoc_alignment（observation・不変・companion method 字段化 B9 / side non-empty B13 / sf4）
```text
member_tuple
  asset_id ; text_revision ; unit_id   # required; string

edit_script_op
  op                          # required; edit_op enum
  src_unit_id                 # conditional required; op ∈ {delete, move, rename, split}
  dst_unit_id                 # conditional required; op ∈ {insert, move, merge}
  payload_digest              # optional; string（sha256）

xdoc_alignment                # 不変・常に存在（lifecycle を持たない・B12）
  alignment_observation_id    # required; §下記 canonical
  schema_version              # required; string
  facet                       # required; facet enum
  comparison_intent           # required; comparison_intent enum（ID 材料）
  direction                   # required; direction enum
  cardinality                 # required; cardinality enum（単一型・§下記 constraint）
  members_a[]                 # required; member_tuple[]（minItems=1・B13）
  members_b[]                 # required; member_tuple[]（minItems=1・B13）
  edit_script[]               # optional; edit_script_op[]
  primary_method_registry_id  # required; string（§8・versioned）
  applied_companion_method_registry_ids[]  # required; string[]（B9・canonical sort・companion 無しは []）
  parameter_profile_hash      # required; string（sha256）
  normalization_profile_id ; normalization_profile_version   # required; string
  tokenization_profile_id ; tokenization_profile_version     # required; string
  candidate_relation_types[]  # required; candidate_relation_type[]
  similarity                  # required; float
  calibration_id ; calibration_version  # required; string
  score_components_ref        # required; string（sf4: = sha256 of immutable score_components object・content-addressed・改変不可）
  method_determinism          # required; method_determinism enum（§8 primary method から継承・冗長保持で ID 安定）
  result_payload_digest       # conditional required; method_determinism=nondeterministic のとき required（sha256）
  corpus_snapshot_id ; release_id  # required; string
```

**side non-empty / self 規則（B13）**
```text
- members_a, members_b は各 minItems=1（0:n を禁止 → cardinality 分岐は §2 の4値で閉じる）
- 正規化後同一 (asset_id, text_revision, unit_id) を両 side に持つ self overlap は G_XDOC_NO_SELF_LOOP で reject
- 同一 side 内 duplicate member は reject（集合として扱う）
```

**side canonicalization（symmetric のみ・cardinality と分離）**
```text
member_canonical(m)      = canonical_json (asset_id, text_revision, unit_id)
side_canonical(members)  = sort_ascending([member_canonical(m) for m in members])
canonical_a, canonical_b = 両 side の side_canonical を文字列比較し小さい方を canonical_a
```

**cardinality 決定（単一 field・B1 維持 / B13 統合）**
```text
sizes = sort_ascending([len(members_a), len(members_b)])
direction=symmetric:                       # n_one を作らない（unordered）
  [1,1]→one_one ; [1,n](n>1)→one_n ; [m,n](m,n>1)→n_m
direction ∈ {a_to_b, b_to_a}:              # side 順序保持
  len(a)=1,len(b)=1→one_one ; len(a)=1,len(b)>1→one_n
  len(a)>1,len(b)=1→n_one  ; len(a)>1,len(b)>1→n_m
constraint: direction=symmetric ⇒ cardinality ≠ n_one（違反は validation error）
```

**canonical alignment_observation_id（companion を ID 材料に含む B9）**
```text
alignment_observation_id = sha256(canonical_json(
  schema_version, facet, comparison_intent, direction, cardinality,
  members_canonical,                          # symmetric: [canonical_a, canonical_b] / directional: [side_canonical(a), side_canonical(b)]
  primary_method_registry_id,
  sort_ascending(applied_companion_method_registry_ids),   # B9: companion set も ID 材料
  parameter_profile_hash,
  normalization_profile_id, normalization_profile_version,
  tokenization_profile_id, tokenization_profile_version,
  result_payload_digest,                      # NULL 可（deterministic）
  corpus_snapshot_id, release_id))
# review・eligibility・assessment・cluster 変更で id は不変
```

## 6. xdoc_use_assessment（append-only revision・decision digest に revoked 含む sf1）
```text
decision_payload                       # sf1: revoked/revocation_reason_code を含め decision 全体を digest
  eligibility                 # eligibility enum
  reason_codes_sorted         # sort(reason_codes[])
  evidence_refs_sorted        # sort(evidence_refs[])
  reviewed_relation_type      # reviewed_relation_type enum | NULL
  review_state                # review_state enum
  revoked                     # bool
  revocation_reason_code      # string | NULL
  assessed_by                 # string
decision_payload_digest = sha256(canonical_json(decision_payload))

xdoc_use_assessment                    # append-only・不変 record
  use_assessment_key_id       # required; sha256(canonical_json(
                              #   alignment_observation_id, evaluation_purpose, target, policy_id, policy_version))
  assessment_revision_id      # required; sha256(canonical_json(
                              #   use_assessment_key_id, decision_payload_digest, revision_seq))
  revision_seq                # required; integer（prior+1、1 始まり）
  supersedes_revision_id      # required; NULL or 直前 revision の assessment_revision_id
  revoked                     # required; bool
  revocation_reason_code      # conditional required; revoked=true
  alignment_observation_id    # required; FK
  evaluation_purpose ; target # required; enum
  eligibility                 # required; eligibility enum
  policy_id ; policy_version  # required; string
  reason_codes[]              # required; string[]（minItems=1）
  evidence_refs[]             # optional; string[]
  reviewed_relation_type      # optional; reviewed_relation_type enum | NULL
  assessed_at                 # required; ISO8601 datetime
  assessed_by                 # required; string
  review_state                # required; review_state enum
```
**status 導出（in-place 更新なし）**
```text
current_revision(key) = max revision_seq の record
assessment_status(r)  = revoked=true → revoked
                        r=current_revision(key) かつ非revoked → active
                        それ以外 → superseded
```
- **G_XDOC_USE_ASSESSMENT_REVISION_UNIQUE**：`UNIQUE(use_assessment_key_id, revision_seq)`。
- **G_XDOC_USE_ASSESSMENT_ONE_ACTIVE**：key ごと active 最大1件。
- **G_XDOC_NO_SILENT_MUTATION**：record 不変・変更は新 revision として append。

## 7. eligibility（purpose別 positive relation 集合・none global negative B10）

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
| *（上記以外） | * | **false** | **ineligible**（validation error で作成禁止） |

### 7-2. purpose_positive_reviewed_relations（B10・NOT NULL を列挙に置換）
positive eligibility に必要な reviewed_relation_type 集合を purpose ごとに**明示列挙**。`none` と NULL は**全 purpose で非該当**。
| evaluation_purpose | positive_reviewed_relations |
|---|---|
| proof_corroboration | quote, reprint, adaptation, same_expression |
| extraction_corroboration | （reviewed_relation_type に依存しない・観測独立性で判定） |
| litlink_candidate | quote, reprint, adaptation, same_expression, same_topic, near_duplicate, edition_variant, template_instance, figure_reuse |
| edition_resolution | edition_variant |
| formobj_variant_candidate | template_instance, common_template |
| frbr_work_candidate | edition_variant, same_expression, adaptation, reprint |
| dedup | near_duplicate, same_expression |

### 7-3. eligibility_policy_rule（policy_id = XDOC-ELIG-001 / v1）
**condition_expression 型**：boolean 式。被参照変数 = `independence(axis).effective_value` / `.effective_status` / `reviewed_relation_type` / `review_state` / `coverage_complete_for_use_assessment`（§9） / `claim_is_absence_or_difference` / `is_positive(purpose, reviewed_relation_type)`（§7-2 集合の所属）。
**priority 解決**：数字大＝高優先。同一 priority 複数該当 → `ineligible > hold > eligible`。全非該当 → 7-1 default。

| priority | purpose | target | condition_expression | result | reason_code |
|---|---|---|---|---|---|
| 110 | * | * | exists independence assessment (any axis) where effective_status = invalid | **ineligible** | INDEPENDENCE_INVALID_GLOBAL |
| 105 | proof_corroboration | proof | observation_independence.effective_status = stale | hold | OBSERVATION_INDEPENDENCE_STALE |
| 100 | proof_corroboration | proof | content_independence.effective_value ∈ {shared, partially_shared} | **ineligible** | CONTENT_NOT_INDEPENDENT |
| 100 | proof_corroboration | proof | content_independence.effective_value = unknown | hold | CONTENT_INDEPENDENCE_UNKNOWN |
| 100 | proof_corroboration | proof | observation_independence.effective_value ∈ {shared, partially_shared, unknown} | hold | OBSERVATION_NOT_INDEPENDENT_LEGAL |
| 100 | proof_corroboration | proof | content_independence.effective_status = stale | hold | CONTENT_INDEPENDENCE_STALE |
| 90 | * | * | claim_is_absence_or_difference AND coverage_complete_for_use_assessment = false | **ineligible** | COVERAGE_INCOMPLETE |
| **85** | * | {proof, litlink, frbr_work, litid_identity, formobj_variant, block_ref} | **reviewed_relation_type = none** | **ineligible** | REVIEWED_RELATION_NONE |
| 80 | * | {litlink, frbr_work, litid_identity, formobj_variant, block_ref} | reviewed_relation_type IS NULL | **ineligible** | REVIEWED_RELATION_REQUIRED |
| 70 | frbr_work_candidate | frbr_work | review_state ≠ reviewed | hold | HUMAN_REVIEW_REQUIRED |
| 50 | proof_corroboration | proof | content_independence.effective_value=independent AND content_independence.effective_status=current AND observation_independence.effective_value=independent AND observation_independence.effective_status=current AND is_positive(proof_corroboration, reviewed_relation_type) AND review_state=reviewed | eligible | INDEPENDENT_CORROBORATION |
| 50 | extraction_corroboration | proof | observation_independence.effective_value ∈ {independent, partially_shared} AND observation_independence.effective_status=current AND review_state=reviewed | eligible | EXTRACTION_CANDIDATE |
| 50 | litlink_candidate | litlink | is_positive(litlink_candidate, reviewed_relation_type) AND review_state=reviewed | eligible | LITLINK_CANDIDATE |
| 50 | edition_resolution | litid_identity | is_positive(edition_resolution, reviewed_relation_type) AND review_state=reviewed | eligible | EDITION_CANDIDATE |
| 50 | formobj_variant_candidate | formobj_variant | is_positive(formobj_variant_candidate, reviewed_relation_type) AND review_state=reviewed | eligible | FORMOBJ_CANDIDATE |
| 50 | frbr_work_candidate | frbr_work | is_positive(frbr_work_candidate, reviewed_relation_type) AND review_state=reviewed | eligible | FRBR_CANDIDATE |
| 50 | dedup | block_ref | is_positive(dedup, reviewed_relation_type) AND review_state=reviewed | eligible | DEDUP_CANDIDATE |

**注1**：priority=110 で任意軸 invalid → 全 purpose×target ineligible。
**注2（sf/guard）**：法的裏付け転用可は `proof_corroboration` の eligible のみ（`G_XDOC_PROOF_PURPOSE_ONLY_FOR_LEGAL`）。`extraction_corroboration` eligible は抽出観測の相互確認限定。
**注3**：priority=85 により `none`（レビュー済み非該当）は positive target で必ず ineligible（B10 の意味矛盾を閉鎖）。`is_positive` 集合に none/NULL は含まれないため priority=50 でも eligible にならない（二重防御）。
**注4**：frbr_work_candidate eligible は証拠の1片。Work 昇格は外部 multi-facet cluster 証拠が必要（HOLD）。

- **G_XDOC_INDEP_INVALID_BLOCKS_ELIGIBLE**（110）/ **G_XDOC_REVIEWED_NONE_NOT_POSITIVE**（85）/ **G_XDOC_NO_CANDIDATE_PROMOTION**（80）/ **G_XDOC_PROOF_REQUIRES_CONTENT_INDEPENDENT**（100）/ **G_XDOC_NO_COVERAGE_ABSENCE_CLAIM**（90）。

## 8. method_registry + method_capability_rule（versioned・determinism・companion 検査 B9/B13）

### 8-1. method_registry
```text
method_registry
  method_registry_id          # required; sha256(canonical_json(method_id, version))
  method_id ; version         # required; string
  facet                       # required; facet enum
  method_determinism          # required; method_determinism enum（B13）
  emits_candidate_relation    # required; bool
  allowed_non_candidate_assertion_types[]  # required; string[]（空＝candidate のみ）
  prohibited_assertion_types[]# required; string[]
```
| method_id | version | facet | method_determinism | emits_candidate_relation | allowed_non_candidate_assertion_types | prohibited_assertion_types |
|---|---|---|---|---|---|---|
| MinHash | v1 | text | deterministic | true | [] | semantic_identity, citation_direction |
| SimHash | v1 | text | deterministic | true | [] | semantic_identity, citation_direction |
| embedding | v1 | text | nondeterministic | true | [] | symbol_identity, verbatim_identity |
| CDC | v1 | text | deterministic | false | [boundary_segmentation] | segment_identity_standalone |
| content_hash | v1 | text | deterministic | true | [] | standalone_use |
| table_structure | v1 | table | deterministic | true | [] | figure_content |
| pHash | v1 | figure | deterministic | true | [] | reviewed_figure_identity |
| visual_embedding | v1 | figure | nondeterministic | true | [] | reviewed_figure_identity |

- embedding/visual_embedding は `nondeterministic` → alignment.result_payload_digest が required（§5）。

### 8-2. method_capability_rule（複合・companion 実行集合検査 B9）
```text
method_capability_rule
  rule_id                     # required; string
  primary_method_registry_id  # required; string（FK）
  required_companion_method_registry_ids[]  # required; string[]（空＝単独可）
  allowed_comparison_intents[]    # required; comparison_intent[]
  allowed_candidate_relation_types[] # required; candidate_relation_type[]
```
| rule_id | primary (id@ver) | required_companions | allowed_intents | allowed_candidate_relation_types |
|---|---|---|---|---|
| R-MINHASH | MinHash@v1 | [] | near_duplicate, text_reuse | near_duplicate, lexical_overlap |
| R-SIMHASH | SimHash@v1 | [] | near_duplicate, text_reuse | near_duplicate, lexical_overlap |
| R-EMB | embedding@v1 | [] | semantic_overlap, citation_candidate | semantic_proximity |
| R-CDC-STANDALONE | CDC@v1 | [] | text_reuse | [] |
| R-CDC-HASH | CDC@v1 | [content_hash@v1] | text_reuse, near_duplicate | segment_identity_candidate |
| R-TABLE | table_structure@v1 | [] | table_template, structure_comparison | table_structure_match |
| R-PHASH | pHash@v1 | [] | figure_reuse | figure_near_duplicate |
| R-VIS | visual_embedding@v1 | [] | figure_reuse | visual_proximity |

**G_XDOC_METHOD_CAPABILITY_DECLARED（B9 強化・normative）**
```text
適用 rule r を alignment に当てるとき:
  1. alignment.primary_method_registry_id = r.primary_method_registry_id
  2. set(r.required_companion_method_registry_ids) ⊆ set(alignment.applied_companion_method_registry_ids)   # 実行集合に包含
  3. alignment.candidate_relation_types[] ⊆ r.allowed_candidate_relation_types
  4. alignment.comparison_intent ∈ r.allowed_comparison_intents
# 例: CDC@v1 単独 alignment（applied_companion=[]）には R-CDC-HASH を適用できない（条件2違反）
#     → segment_identity_candidate を出せるのは content_hash@v1 を applied_companion に含む alignment のみ（受入試験7）
```
- **G_XDOC_METHOD_VOCAB**：method 出力は reviewed_relation_type を直接生成しない（常に NULL）。
- **G_XDOC_METHOD_VERSION_BOUND**：capability は versioned method_registry_id を参照。

### 8-3. origin_relation × candidate_relation_type → reviewed_relation_type 対応表（規範・v0.6 と同一）
全行 requires_human=true。
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

## 9. coverage（range_class 別演算・non-empty scope・全scope 集約 B11 / sf2）

### 9-1. coordinate_space → range_class 写像 と range 型
```text
coordinate_space  range_class   range 型
  page            interval_1d   {start:int, end:int}            # half-open [start,end), start<end
  char_offset     interval_1d   {start:int, end:int}
  token           interval_1d   {start:int, end:int}
  table_cell      grid_2d       {row_start,row_end,col_start,col_end:int}  # half-open 双方向, row_start<row_end, col_start<col_end
  figure_region   rect_2d       {page:int, x0,y0,x1,y1:float, coordinate_system:string}  # x0<x1, y0<y1
```
**range_class 別 set 演算 adapter（normative）**
```text
interval_1d : 1次元 half-open 区間の union/intersection/contains
grid_2d     : 2次元グリッド矩形（row×col half-open）の union/intersection/contains
rect_2d     : 2次元矩形（同一 page・同一 coordinate_system 内）の union/intersection/contains
# 各 range は非空必須（degenerate 区間は validation error）。異なる range_class 間の演算は禁止。
```

### 9-2. coverage_assessment（revision 付き B12）/ coverage_policy / coverage_claim_scope
```text
coverage_assessment
  coverage_assessment_id      # required; sf2: sha256(canonical_json(
                              #   alignment_observation_id, member_ref, side, facet,
                              #   asset_hash, source_text_revision_id, coverage_policy_version, assessment_version))
  alignment_observation_id    # required; FK
  member_ref                  # required; string
  side                        # required; side enum
  facet                       # required; facet enum
  coordinate_space            # required; coordinate_space enum
  asset_hash                  # required; string（sha256）
  source_text_revision_id     # required; string
  selector_state              # required; selector_state enum
  covered_ranges[]            # required; range_class(coordinate_space) の range[]（空可・各非空）
  unknown_ranges[]            # required; 同 range[]（空可・各非空）
  ocr_quality_score ; layout_quality_score  # required; float 0.0-1.0
  coverage_policy_id ; coverage_policy_version  # required; string
  assessment_version          # required; string
  supersedes_coverage_assessment_id  # optional; NULL or 前の coverage_assessment_id
  coverage_status             # required; coverage_status enum（§下記導出）

coverage_policy
  policy_id ; policy_version  # required; string
  facet                       # required; facet enum
  required_coordinate_space   # required; coordinate_space enum
  minimum_ocr_quality ; minimum_layout_quality  # required; float 0.0-1.0

coverage_claim_scope          # B11/B2: 対象範囲（非空必須）
  use_assessment_key_id       # required; FK
  member_ref                  # required; string
  required_coordinate_space   # required; coordinate_space enum
  required_ranges[]           # required; range[]（**minItems=1**・各非空・正規化済み）
  coverage_assessment_id      # required; FK → coverage_assessment（current）
```
**coverage_status 導出**
```text
coverage_status(ca) = ca が (alignment, member, side, facet) 内で max assessment_version → current / それ以外 → superseded
```
**coverage 包含判定（B11・normative）**
```text
coverage_complete_for_scope(scope, ca, policy) ≡
  ca.coverage_status = current
  AND ca.selector_state = complete
  AND ca.ocr_quality_score   ≥ policy.minimum_ocr_quality
  AND ca.layout_quality_score ≥ policy.minimum_layout_quality
  AND ca.coordinate_space = scope.required_coordinate_space
  AND scope.required_ranges は minItems=1（空 scope は不成立）
  AND contains(union(ca.covered_ranges), union(scope.required_ranges))      # range_class adapter
  AND intersection(union(ca.unknown_ranges), union(scope.required_ranges)) = ∅
# covered_ranges=[] のとき union=∅、非空 required を包含できない → 必ず false（B11 主張が成立）
# covered と unknown が対象内で重複する場合は validation error（unknown 優先で安全側に倒すなら別途宣言）

coverage_complete_for_use_assessment(key) ≡           # B11: 全 member・全 scope を AND 集約
  scopes = coverage_claim_scope WHERE use_assessment_key_id = key
  scopes 非空 AND every(scope ∈ scopes):
    coverage_complete_for_scope(scope, current_ca(scope.coverage_assessment_id), policy)
```
- **G_XDOC_COVERAGE_MEMBER_KEYED** / **G_XDOC_COVERAGE_SCOPE_NONEMPTY**（required_ranges minItems=1）/ **G_XDOC_COVERAGE_ALL_SCOPE_AGG**（全 scope AND）。
- absence/difference claim は `coverage_complete_for_use_assessment = true` 必須（false → §7-3 priority=90 ineligible）。

## 10. cluster（support_edge を実在 evidence refs に接地 B12 / member-level outlier sf3）

### 10-1. xdoc_support_edge（typed evidence refs・undirected）
```text
xdoc_support_edge
  support_edge_id             # required; sha256(canonical_json(
                              #   cluster_facet, canonical_member_low, canonical_member_high, alignment_observation_id))
  cluster_facet               # required; facet enum
  canonical_member_low        # required; string（min by canonical string）
  canonical_member_high       # required; string（max）
  alignment_observation_id    # required; FK（不変観測・常に存在）
  support_score               # required; float 0.0-1.0
  calibration_id ; calibration_version  # required; string
  support_basis_use_assessment_revision_ids[]  # required; string[]（B12・この edge の妥当性が依存する assessment revision）
  support_basis_coverage_assessment_ids[]      # required; string[]（B12・依存する coverage_assessment）
  UNIQUE(canonical_member_low, canonical_member_high, alignment_observation_id)
  CONSTRAINT canonical_member_low ≠ canonical_member_high
```
**support_edge_effective（B12・実在字段のみで再記述・normative）**
```text
support_edge_effective(edge, policy) ≡
  edge.support_score ≥ policy.minimum_support_score
  AND edge.calibration_id = policy.calibration_id
  AND edge.calibration_version = policy.calibration_version
  AND every(r ∈ edge.support_basis_use_assessment_revision_ids): assessment_status(r) = active   # §6 導出（非revoked かつ current）
  AND every(c ∈ edge.support_basis_coverage_assessment_ids): coverage_status(c) = current        # §9 導出
# alignment は不変観測として常に存在（lifecycle 字段を持たない）。
# edge の妥当性は「参照する assessment revision が active」「参照 coverage が current」だけで決まる（B12 閉鎖）。
```

### 10-2. xdoc_cluster（member-level outlier sf3・density 一本化）
```text
xdoc_cluster
  cluster_id ; facet          # required
  algorithm ; algorithm_version ; parameter_profile_id ; corpus_snapshot_id  # required; string
  members[]                   # required; cluster_member[]（minItems=2）
  representative_or_medoid    # optional; member_ref | NULL
  cluster_stability           # required; float 0.0-1.0
  stability_metric_id         # required; string
  pairwise_support_coverage   # required; float 0.0-1.0（= density・単一値）
  cluster_outlier_state       # required; bool（cluster 全体）
  policy_id ; policy_version  # required; string
cluster_member
  member_ref                  # required; string
  member_score                # required; float 0.0-1.0
  member_outlier_state        # required; bool（sf3: member-level 追跡）
```
**pairwise_support_coverage（= density・単一式）**
```text
pairwise_support_coverage =
  count(canonical_member_pair で support_edge_effective を満たす edge が1件以上)
  ÷ count(クラスタ内 canonical_member_pair 総数)
# members minItems=2 で分母 0 を防止
```

### 10-3. cluster_policy（typed rule）
```text
cluster_policy
  policy_id ; policy_version ; algorithm ; stability_metric_id  # required; string
  minimum_stability ; minimum_density ; minimum_support_score   # required; float 0.0-1.0
  calibration_id ; calibration_version  # required; string
  maximum_size                # required; integer
  outlier_rule_type           # required; outlier_rule_type enum
  outlier_threshold           # required; float
  missing_pair_rule_type      # required; missing_pair_rule_type enum
```

### 10-4. cluster_lineage_edge（append-only）
```text
cluster_lineage_edge
  lineage_edge_id             # required; sha256(canonical_json(lineage_type, source_cluster_id, target_cluster_id, event_at))
  lineage_type                # required; lineage_type enum
  source_cluster_id ; target_cluster_id  # required; string
  event_at                    # required; ISO8601 datetime
```
- **G_XDOC_NO_TRANSITIVE_EQUIVALENCE** / **G_XDOC_NO_TRANSITIVE_MEGACLUSTER** / **G_XDOC_CLUSTER_SUPPORT_CONTRACT** / **G_XDOC_CLUSTER_SEMANTICS_CANDIDATE**（cluster は常に candidate_set）。
- cluster から FRBR/LITID/proof へ直接 promotion しない。

## 11. ゲート → predicate 接地表（B13・各 gate を本文 predicate に一対一接地）
| gate | 接地（predicate / §） |
|---|---|
| INDEP_ACTIVE_UNIQUE | §3 `(alignment, axis, policy_id, policy_version)` active ≤ 1 |
| INDEP_DERIVED_FROM_EVIDENCE | §3 computed_value は computed_evidence_refs+policy から算出 |
| INDEP_INVALID_BLOCKS_ELIGIBLE | §7-3 priority=110 |
| PASSAGE_ORIGIN_REQUIRED | §4 content_origin_assertion.subject_passage_ref/origin_passage_ref required |
| INTENT_REQUIRED | §5 xdoc_alignment.comparison_intent required・ID 材料 |
| USE_ASSESSMENT_REVISION_UNIQUE | §6 UNIQUE(key, revision_seq) |
| USE_ASSESSMENT_ONE_ACTIVE | §6 assessment_status active ≤ 1 / key |
| NO_SILENT_MUTATION | §6 record 不変・append-only |
| PROOF_REQUIRES_CONTENT_INDEPENDENT | §7-3 priority=100 CONTENT_NOT_INDEPENDENT |
| PROOF_PURPOSE_ONLY_FOR_LEGAL | §7-3 注2（proof_corroboration eligible のみ法的転用可） |
| REVIEWED_NONE_NOT_POSITIVE | §7-3 priority=85 |
| NO_COVERAGE_ABSENCE_CLAIM | §7-3 priority=90 + §9 coverage_complete_for_use_assessment |
| COVERAGE_SCOPE_NONEMPTY | §9 required_ranges minItems=1 |
| COVERAGE_ALL_SCOPE_AGG | §9 coverage_complete_for_use_assessment = every(scope) |
| COVERAGE_MEMBER_KEYED | §9 coverage_assessment は member_ref/side keyed |
| NO_CANDIDATE_PROMOTION | §7-3 priority=80 |
| METHOD_VOCAB | §8-2 method 出力は reviewed_relation_type=NULL |
| METHOD_CAPABILITY_DECLARED | §8-2 4条件（companion ⊆ applied 含む） |
| METHOD_VERSION_BOUND | §8 method_registry_id=sha256(method_id,version) |
| NO_TRANSITIVE_EQUIVALENCE | §10-4 cluster は equivalence を推移推論しない |
| NO_TRANSITIVE_MEGACLUSTER | §10-4 推移閉包で巨大化しない |
| CLUSTER_SUPPORT_CONTRACT | §10-1/10-2 support_edge_effective+stability+policy 無しは確定不可 |
| CLUSTER_SEMANTICS_CANDIDATE | §10-4 cluster_semantics=candidate_set（定数） |
| OWNERSHIP_NO_REDEF | XDOC は DD-LAYOUT block_ref / DD-LITLINK lit_link を再定義しない（依存先定義に従う） |
| REPRODUCIBILITY_CONTRACT | §5 ID 材料に snapshot/revision/param/normalization/tokenization/result_digest |
| DERIVED | 全 XDOC object は派生・claim_support_eligible=false |
| NO_CLAIM_SUPPORT | §7-3 注2 + §0 gate（evidence/legal claim support HOLD） |
| HUMAN_PROMOTION_ONLY | §7-3 priority=50 群 review_state=reviewed 必須 |
| NO_SELF_LOOP | §5 正規化後同一 (asset,revision,unit) を両 side に持つ self overlap を reject |
| FACET_ANCHORED | §5 members は DD-LAYOUT unit_id（型付きブロック）に接地・生テキスト素朴比較禁止 |

## 12. 受入試験（v0.7・全自動 PASS が条件）
1. schema に ellipsis・union・conditional-type が無く、`cardinality` は単一 enum、`members_a/b` は minItems=1、`method_determinism` は registry 字段、全 gate が §11 で predicate 接地。purpose×target 未定義組合せは validation error。
2. 同一 alignment を litlink_candidate×litlink と proof_corroboration×proof で別 use_assessment（別 key）に評価できる。
3. shared origin 2 passage を proof×proof → priority=100 ineligible。unknown → hold。任意軸 invalid → priority=110 ineligible。
4. content independent/current・observation shared の組合せで axis ごと independence_assessment 2件・active 各1件。
5. content_origin_assertion から全 typed field・evidence_pointer_refs[]・evidence_hashes[] 追跡可能。origin_relation=unknown 表現可。
6. 全 scope 集約：あるキーで required_ranges を covered が包含しない member が1つでもあれば coverage_complete_for_use_assessment=false → absence/difference は priority=90 ineligible。required_ranges=[] は validation error（空 scope で true にならない）。covered_ranges=[] は非空 required を包含できず必ず false。
7. **CDC@v1 単独 alignment（applied_companion=[]）には R-CDC-HASH を適用できず segment_identity_candidate を出せない。content_hash@v1 を applied_companion に含む alignment のみ R-CDC-HASH 適用可（companion ⊆ applied 検査）。**
8. pHash@v1 は reviewed_figure_identity prohibited・method 出力は reviewed_relation_type=NULL。
9. symmetric: side 入替で同一 id（unordered cardinality・side_canonical 順序）。members non-empty で n_one は symmetric で発生せず one_n に正規化、constraint で n_one を弾く。directional は入替で別 id・n_one 保持。
10. comparison_intent・facet・asset・text_revision・primary/applied companion set・parameter_profile_hash・normalization・tokenization・result_payload_digest・corpus_snapshot のいずれか変化で id 変化。**companion set の変化も id に反映。**
11. **support_edge_effective が edge.support_basis_use_assessment_revision_ids の active と support_basis_coverage_assessment_ids の current を実在字段で判定。A~B,B~C で effective edge(A,C) 無し → A-C pair は missing_pair_rule_type=unknown・分子に数えず推移推論しない。**
12. **reviewed_relation_type=none かつ review_state=reviewed は positive target で priority=85 ineligible（eligible にならない）。** XDOC から block_ref current/LITLINK accepted/FRBR/LITID identity/claim support へ直接昇格不可。extraction の eligible は法的裏付け転用不可。

## 13. should_fix 反映
- sf1 decision_payload に revoked/revocation_reason_code を含め digest（§6）。
- sf2 coverage_assessment_id に asset_hash/source_text_revision_id/coverage_policy_version を含む input fingerprint（§9-2）。
- sf3 cluster_member.member_outlier_state を追加（§10-2）。
- sf4 score_components_ref を content-addressed immutable ref（sha256）に定義（§5）。

## 14. GO / HOLD / loop_state
- **GO**：独立 DD 維持／v0.7 design-only patch／synthetic fixture（symmetric side-swap・coverage non-empty/all-scope・none-negative・CDC companion・A-C missing pair）／read-only validator 試作／purpose-target・positive-relation・method registry・cluster policy 作成。
- **HOLD**：v0.7 ratify／DDL/DB/mint/Box mutation／OCR/embedding/training／production pair generation・clustering／FRBR・DD-LITID・DD-LITLINK・block_ref current 自動昇格／evidence・legal claim support。
- loop_state = **patched（v0.7 B9〜B13・接続字段/predicate 閉鎖）→ 再投函（再監査）候補**。
