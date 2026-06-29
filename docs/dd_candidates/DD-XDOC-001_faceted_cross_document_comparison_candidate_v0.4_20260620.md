# DD-XDOC-001 v0.4 — faceted cross-document comparison & alignment（MODIFY round3 反映・機械可読・自己完結）candidate

> **id**: DD-XDOC-001 / **version**: candidate v0.4 / **supersedes**: v0.3
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-20 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/学習/embedding/production pair generation/clustering/FRBR・DD-LITID・DD-LITLINK 昇格/block_ref current 昇格/evidence・legal claim support は **HOLD**。
> **改訂理由（v0.3→v0.4）**: GPT Pro 再監査 `DDXDOC_MODIFY_REQUIRED`（RESULT Box 2297356004616）の blocking B1–B8 ＋ 受入試験12を反映。**block_ref 境界（B6前回#6）は CLOSED 維持**。本文書は enum・schema・gate・受入試験を `{...}` なしで自己完結。
> **depends_on**: DD-LAYOUT-001 v0.5 / DD-XMODAL-001 v0.4 / DD-LITID-001 / DD-LITLINK-001（いずれも定義を狭めない）。

---

## 0. round3 反映（B1–B8）
| B | 指摘 | § |
|---|---|---|
| B1 | detector intent と evaluation purpose を分離（4語彙） | §2,§5,§6 |
| B2 | intent/purpose 別 eligibility を policy matrix に | §7 |
| B3 | origin/pipeline 証拠を member 単位 assertion に | §4 |
| B4 | computed/reviewed/effective state＋語彙一本化＋矛盾gate | §3 |
| B5 | observation_id と use_assessment_id を分離＋正規直列化 | §5,§6 |
| B6 | method registry 語彙型修正（intent と relation を分離） | §8 |
| B7 | coverage を member-keyed 契約に | §9 |
| B8 | cluster を support graph として拘束 | §10 |

## 1. オブジェクト分離（関心の分離）
- **xdoc_alignment**：observation（何を・どの method で・どの member 間で検出したか）。不変。`alignment_observation_id`。
- **xdoc_use_assessment**：alignment に 1:N（evaluation_purpose × target ごとの eligibility＋policy）。
- **content_origin_assertion** / **member_pipeline_provenance**：member 単位の証拠。独立性は**これらから導出**（手入力しない）。
- **coverage_assessment**：member-keyed。
- **xdoc_cluster** ＋ **xdoc_support_edge**：support graph。
- **method_registry** / **enum registry**（canonical・単一定義）。

## 2. canonical enums（単一定義・全所で同一）
```text
facet                  = structure | text | table | figure
direction              = a_to_b | b_to_a | symmetric
cardinality            = one_one | one_n | n_one | n_m
comparison_intent      = near_duplicate | text_reuse | semantic_overlap | edition_alignment
                         | structure_comparison | table_template | figure_reuse | citation_candidate
                         # ※ detector/retrieval goal。independent_corroboration は intent でない（§下記 evaluation_purpose）
candidate_relation_type= near_duplicate | lexical_overlap | semantic_proximity
                         | segment_identity_candidate | table_structure_match
                         | figure_near_duplicate | visual_proximity | structure_edit
reviewed_relation_type = quote | reprint | adaptation | common_template | same_expression
                         | edition_variant | same_topic | template_instance | figure_reuse
                         | near_duplicate | none
origin_relation        = quote | reprint | adaptation | common_template | same_expression
evaluation_purpose     = proof_corroboration | extraction_corroboration | litlink_candidate
                         | edition_resolution | formobj_variant_candidate | frbr_work_candidate | dedup
target                 = proof | litlink | frbr_work | litid_identity | formobj_variant | block_ref
independence_value     = independent | shared | partially_shared | unknown   # 両軸共通
eligibility            = eligible | ineligible | hold
state_layer            = computed | reviewed | effective
review_state           = unreviewed | reviewed | overridden | stale
```

## 3. 独立性＝2軸×3層（B4・語彙一本化・矛盾gate）
両軸とも **independence_value** を使用（名称統一・`pipeline_independence_decision` 廃止）。
```text
content_independence      : computed / reviewed / effective   (independence_value)
observation_independence  : computed / reviewed / effective   (independence_value)   # 旧 pipeline を observation に統一
```
- **precedence**：effective = reviewed があれば reviewed、無ければ computed。computed の入力（§4 assertion/provenance）が変われば effective=stale。
- **G_XDOC_INDEP_CONTRADICTION**：reviewed と computed が矛盾し review_reason 無し → invalid（gate で弾く）。
- content と observation は**別物**（独立執筆×同一OCR＝content independent / observation shared）。

## 4. member 単位の証拠（B3・独立性は導出）
```text
content_origin_assertion
  assertion_id
  subject_member_ref          # どの member@asset のどの passage についての主張か
  subject_passage_ref
  origin_object_ref           # source_object_type(statute|case|manuscript|edition|commentary|dataset)+id+version
  origin_passage_ref
  origin_relation             # enum
  evidence_pointer_refs[] / evidence_hashes[]
  detection_method / detection_version / confidence
  computed_state / review_state
member_pipeline_provenance
  member_ref
  scan_source_id ; ocr_engine / ocr_version ; parser / parser_version
  normalization_profile / version ; tokenization_profile / version
  source_text_revision ; evidence_refs[]
```
- pair/group の独立性 decision は **これらの assertion/provenance refs ＋ policy_version を根拠**に持つ（状態値だけの手入力禁止）。**G_XDOC_INDEP_DERIVED_FROM_EVIDENCE**。

## 5. xdoc_alignment（observation・不変 ID）
```text
xdoc_alignment
  alignment_observation_id    # §下記 canonical 直列化
  schema_version ; facet ; comparison_intent
  direction ; cardinality
  members_a[member_ref(asset_id, text_revision, unit_id)] ; members_b[...]
  edit_script[]               # structure: insert|delete|move|rename|split|merge
  method / method_version / parameter_profile_hash
  normalization_profile / tokenization_profile
  candidate_relation_types[]  # method が出した候補関係（reviewed でない）
  similarity ; score_components_ref ; calibration_version
  corpus_snapshot_id / release_id
  # 独立性・origin・coverage は member 証拠(§4,§9)を参照、本体に状態を焼かない
```
**canonical alignment_observation_id（B5）**
```text
alignment_observation_id = sha256(canonical_json(
  schema_version, facet, direction, cardinality,
  members_canonical,                     # 各 member=(asset_id,text_revision,unit_id)
  method, method_version, parameter_profile_hash,
  normalization_profile, tokenization_profile,
  corpus_snapshot_id, release_id))
canonicalization 規則（normative）:
  - hash = sha256 ; Unicode = NFC ; JSON object key = コードポイント昇順
  - array = 規定キーで安定ソート（members は (asset_id,text_revision,unit_id) 昇順）
  - direction=symmetric: members_a/b を side 正規化（2 side を集合として昇順）→ side 入替で同一ID
  - direction≠symmetric: side 順序を保持 → 入替で別ID
  - review 結果・eligibility 変更で observation_id は変えない
```

## 6. xdoc_use_assessment（1:N・用途別・B1/B2/B5）
```text
xdoc_use_assessment
  use_assessment_id           # = sha256(canonical_json(alignment_observation_id, evaluation_purpose, target, policy_id, policy_version))
  alignment_observation_id
  evaluation_purpose ; target
  eligibility                 # enum
  policy_id / policy_version
  reason_codes[] ; evidence_refs[]
  reviewed_relation_type      # 人手/承認済み解釈（method 出力は直接ここに入れない）
  assessed_at / assessed_by ; review_state
```
1 alignment は複数 purpose で評価され得る → eligibility は alignment 本体でなく本表（1:N）に持つ。**G_XDOC_USE_ASSESSMENT_1N**。

## 7. eligibility policy matrix（B2・宣言文でなく表）
`policy(evaluation_purpose, target, conditions) → eligibility + reason_codes`。必須規則（policy_id=XDOC-ELIG-001/v1）：
| purpose | 条件 | eligibility |
|---|---|---|
| proof_corroboration | content_independence.effective ∈ {shared, partially_shared, unknown} | **ineligible/hold（eligible 禁止）** |
| proof_corroboration | observation_independence.effective ∈ {shared, partially_shared, unknown} | extraction_corroboration とは可、**法的内容独立裏付けは不可** |
| 任意 | coverage 不完全域を根拠とする absence/difference（§9） | **eligible 禁止** |
| frbr_work / litid_identity / litlink / block_ref | candidate_relation_type のみ（reviewed_relation_type 無し） | **昇格 eligible 禁止**（候補のみ） |
| frbr_work | 単一 facet のみ | ineligible（多 facet＋人手必須） |
- **G_XDOC_PROOF_REQUIRES_CONTENT_INDEPENDENT**／**G_XDOC_NO_COVERAGE_ABSENCE_CLAIM**／**G_XDOC_NO_CANDIDATE_PROMOTION**。

## 8. method_registry（B6・語彙型修正）
```text
method_registry(method, version, facet,
  allowed_comparison_intents[],
  allowed_candidate_relation_types[],
  requires_companion_methods[],
  candidate_only: bool,
  prohibited_assertion_types[])
```
| method | allowed_candidate_relation_types | requires_companion | candidate_only | prohibited |
|---|---|---|---|---|
| MinHash/SimHash | near_duplicate, lexical_overlap | — | false | semantic identity, citation direction |
| embedding | semantic_proximity | — | false | symbol identity, verbatim |
| CDC/Rabin | **[]**（単独で relation 確定不可） | **content_hash**（segment_identity_candidate に必須） | true | 単独 segment identity |
| table structure matching | table_structure_match | — | false | figure content |
| pHash | figure_near_duplicate | — | **true** | reviewed「図版同一」 |
| visual embedding | visual_proximity | — | **true** | reviewed「図版同一」 |
- method 出力は `reviewed_relation_type` を**直接生成しない**。対応表 `origin_relation × candidate_relation_type × reviewed_relation_type` を registry に置く。**G_XDOC_METHOD_VOCAB**。

## 9. coverage_assessment（B7・member-keyed）
```text
coverage_assessment
  member_ref ; side(a|b) ; facet
  asset_hash ; source_text_revision ; selector_state
  ocr_quality ; layout_quality
  covered_ranges[] ; unknown_ranges[] ; assessment_version
```
- **G_XDOC_COVERAGE_MEMBER_KEYED**：n:m で**どの member の coverage が欠けたか**判定可能に。全 member の必要 coverage が揃わない場合、その member に関する absence/difference を `valid` にしない（unknown）。

## 10. cluster＝support graph（B8）
```text
xdoc_support_edge(member_a, member_b, alignment_observation_id, support_score)
xdoc_cluster
  cluster_id ; facet ; algorithm / version / parameter_profile / corpus_snapshot
  members[member_ref] ; member_score ; representative_or_medoid
  cluster_stability ; density ; outlier_state
  pairwise_support_coverage   # = 実在 support_edge 数 / クラスタ内 member ペア総数
  policy_id / policy_version  # min_density / max_size / outlier 判定
  cluster_lineage(split|merge|supersedes)
  cluster_semantics = candidate_set         # NOT equivalence_class
```
- **G_XDOC_NO_TRANSITIVE_EQUIVALENCE**（A~B,B~C,A!~C で A=C を推論しない）／**G_XDOC_CLUSTER_SUPPORT_CONTRACT**（support graph・stability・policy 無しのクラスタ確定禁止）／cluster から FRBR/LITID/proof へ直接 promotion しない。

## 11. ゲート一覧（機械可読・全体）
INDEP_TRISTATE / INDEP_CONTRADICTION / INDEP_DERIVED_FROM_EVIDENCE / PASSAGE_ORIGIN_REQUIRED / INTENT_REQUIRED / USE_ASSESSMENT_1N / PROOF_REQUIRES_CONTENT_INDEPENDENT / NO_COVERAGE_ABSENCE_CLAIM / NO_CANDIDATE_PROMOTION / METHOD_VOCAB / METHOD_CAPABILITY_DECLARED / COVERAGE_MEMBER_KEYED / NO_TRANSITIVE_EQUIVALENCE / NO_TRANSITIVE_MEGACLUSTER / CLUSTER_SUPPORT_CONTRACT / OWNERSHIP_NO_REDEF / REPRODUCIBILITY_CONTRACT / DERIVED / NO_CLAIM_SUPPORT / HUMAN_PROMOTION_ONLY / NO_SELF_LOOP / FACET_ANCHORED。

## 12. 受入試験（v0.4・全自動 PASS が条件）
1. schema/enum/target に `{...}`・未定義値が無い。
2. 同一 alignment を text_reuse と proof_corroboration で別々の use_assessment に評価できる。
3. shared origin の2 passage を proof_corroboration に入れると必ず ineligible/hold（eligible にならない）。
4. content independent / observation shared の組合せで、法的内容独立性と抽出観測独立性が**別々に**出力。
5. 各 content_origin_assertion から subject member passage・origin passage・根拠 pointer/hash まで追跡可能。
6. n:m で片側1 member だけ coverage 不完全なら、その member の absence/diff は unknown。
7. CDC 単独では relation 確定不可、content_hash 併用時のみ許容候補型を出す。
8. pHash/visual 単独では reviewed「図版同一」を生成しない。
9. symmetric は side 入替で同一 observation_id、directional は入替で別 id。
10. facet/asset・text revision/method version/parameter/normalization/snapshot のいずれか変化で ID 又は lineage が変わる。
11. A~B,B~C,A!~C で cluster が identity/equivalence を推移推論しない。
12. XDOC から block_ref current・LITLINK accepted・FRBR/LITID identity・claim support へ直接昇格できない。

## 13. 非blocking 改善（反映）
- `reviewed_relation_type` を registry 化（adaptation/common_template/same_expression/figure_reuse 等を表現）。
- `G_XDOC_NO_SELF_LOOP`：正規化後の同一 asset_revision・同一 unit 範囲の重複を self とみなし除外。
- `review_reason` = reason_code ＋ 補足文。
- confidence は calibration_set/version に紐付け、method 間で scalar を直接比較しない。

## 14. GO / HOLD / loop_state
- **GO**：独立DD維持／v0.4 design patch／passage origin・pipeline provenance の gold sample／固定 snapshot 上の read-only candidate generation 試験／eligibility policy matrix・cluster support policy 作成。
- **HOLD**：v0.4 ratify／DDL/DB/mint/Box mutation／OCR/embedding/training／production pair generation・clustering／FRBR・DD-LITID・DD-LITLINK・block_ref current 自動昇格／evidence・legal claim support。
- loop_state = **patched（v0.4 機械可読・自己完結）→ 再投函（再監査）候補**。
