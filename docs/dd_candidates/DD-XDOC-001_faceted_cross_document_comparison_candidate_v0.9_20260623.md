# DD-XDOC-001 v0.9 — faceted cross-document comparison & alignment（round8 B19〜B23・claim完全性/support scope拘束 閉鎖）candidate

> **id**: DD-XDOC-001 / **version**: candidate v0.9 / **supersedes**: v0.8
> **lifecycle**: **accepted**（owner 浅井 ratify 2026-06-24、設計のみ）。GPT Pro 監査 `DDXDOC_PASS_WITH_NOTES`（RESULT Box 2303550755480・B19〜B23 設計レベル閉鎖・受入試験6/11 十分）。実装/DDL/DB/mint/Box mutation/OCR/embedding/production pair generation・clustering/昇格/claim-support は**別ゲートで HOLD**（accepted≠deployed）。
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-23 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/学習/embedding/production pair generation/clustering/FRBR・DD-LITID・DD-LITLINK 昇格/block_ref current 昇格/evidence・legal claim support は **HOLD**。
> **改訂理由（v0.8→v0.9）**: GPT Pro 独立再監査 `DDXDOC_MODIFY_REQUIRED`（RESULT Box 2303196102767・tests 6/11 FAIL）の blocking B19〜B23 + non-blocking 5点を反映。新規レイヤ追加なし。claim member selector 型付き・coverage scope binding・support coverage scope ref・support policy eligibility/non-empty・support edge revision。
> **v0.8 で CLOSED・維持**: B9 companion ID 材料化・B10 reviewed none・cardinality/minItems/symmetric・B17 numeric coverage revision・B18 typed unit_ref/literal claim_support_eligible/cluster_status const/determinism equality・§7 eligibility priority・§8 method capability。
> **depends_on**: DD-LAYOUT-001 v0.5 / DD-XMODAL-001 v0.4 / DD-LITID-001 / DD-LITLINK-001。

---

## 0. round8 blocking 反映（B19〜B23 / non-blocking）
| B | 指摘 | § |
|---|---|---|
| B19 | claimed_member_refs 過少申告で required scope を消せる（claim selector 未型付け） | §6 |
| B20 | coverage_claim_scope ↔ coverage_assessment の参照整合が無い | §9 |
| B21 | support edge が必要 coverage scope を参照しない（required_scope_for 未接地） | §10 |
| B22 | 空 required_basis_types・hold support を effective に通し得る | §10 |
| B23 | support edge の証拠変更を append-only に表現できない | §10 |
| nb1 | coverage payload の range を canonical sort/merge 後に digest | §9 |
| nb2 | coverage supersedes は直前 revision のみ・gap/branch 検査 | §9 |
| nb3 | concurrent revision 発番は advisory lock/retry（実装 gate） | §9 |
| nb4 | method specificity を決定式 or version 固定 rule priority registry に | §8 |
| nb5 | candidate_relation_types/rule 変更の observation reproducibility 保全 | §5 |

## 1. 変更オブジェクト（v0.8 から差分のみ・他は v0.8 維持）
- **xdoc_use_assessment / claim_context**：claim_member_selector を型付き（§6・B19）。
- **coverage_claim_scope**：logical key + unique + assessment binding（§9・B20）。
- **coverage_assessment**：payload range を canonical sort/merge 後 digest（§9・nb1）。
- **xdoc_support_edge**：coverage scope ref（§10・B21）＋ revision 契約（§10・B23）。
- **cluster_policy**：required_basis_types minItems=1 + allowed_support_eligibilities（§10・B22）。

## 2. canonical enums（v0.8 + 追加）
v0.8 の enum を全て維持。追加：
```text
claim_selector_mode    = all_on_side | explicit_subset                 # B19
support_status         = active | superseded | revoked                 # B23（revision 導出）
support_eligibility_use = eligible                                     # B22 既定（policy で拡張・hold は別状態）
tentative_support_state = effective | tentative                        # B22（hold を effective と分離）
```
（claim_kind / claimed_side / coverage_status / assessment_status / cardinality 等は v0.8 と同一。）

## 3〜4. independence / member 証拠（v0.8 から不変・CLOSED）
§3 xdoc_independence_assessment（active uniqueness・effective_value 算定）、§4 content_origin_assertion /
member_pipeline_provenance は v0.8 と同一。independence global invalid は active/current 限定（v0.8 nb5）。

## 5. xdoc_alignment（v0.8 維持 + nb5 reproducibility 明記）
v0.8 §5 を全て維持（typed unit_ref・companion ID 材料・determinism equality・claim_support_eligible const false）。
**nb5（reproducibility 保全・normative）**：
```text
candidate_relation_types[] 又は method_capability_rule_id の変更は alignment_observation_id を変えない
（observation identity = member×method×companion×snapshot）。これらの変更は別 alignment ではなく
output_assessment（score_components_ref の content-addressed object）に記録し、再現性は
(parameter_profile_hash, result_payload_digest, score_components_ref) で保全する。
```

## 6. claim member selector（B19・必要scope の過少申告を封じる）
```text
claim_member_selector                       # B19: claim 対象 member 集合を型で固定
  use_assessment_key_id       # required; FK
  mode                        # required; claim_selector_mode（all_on_side | explicit_subset）
  claimed_side                # required; claimed_side enum（a | b | both）
  claimed_member_refs[]       # required; member_ref[]（minItems=1）
  subset_selector_id          # conditional required; mode=explicit_subset のとき
                              #   = sha256(canonical_json(sorted(claimed_member_refs), claimed_side))

claim_context                               # v0.8 から claim_member_selector に統合
  use_assessment_key_id ; claim_kind ; required_coordinate_space
  selector_ref                # required; claim_member_selector への FK
# claim_is_absence_or_difference ≡ claim_kind ∈ {absence, difference}
```
**expected_member_set（normative）**
```text
expected_member_set(alignment, claimed_side) =
  claimed_side=a    → set(members_a)
  claimed_side=b    → set(members_b)
  claimed_side=both → set(members_a) ∪ set(members_b)
```
**G_XDOC_CLAIM_MEMBER_COMPLETE（B19・normative）**
```text
absence/difference claim では:
  mode=all_on_side    ⇒ set(claimed_member_refs) = expected_member_set(alignment, claimed_side)（完全一致必須）
  mode=explicit_subset⇒ subset_selector_id NOT NULL かつ = sha256(...) かつ
                         set(claimed_member_refs) ⊆ expected_member_set（自由省略は hash 化された selector として記録）
# 「claimed_side=both で1 member だけ列挙」は all_on_side では不一致で reject、
#  explicit_subset では subset_selector_id 必須・記録される（silent な過少申告を封じる）
```
required_scope_keys は §9 で `expected_member_set` ではなく `claimed_member_refs`（selector で固定済）から導出。

## 7〜8. eligibility / method（v0.8 から不変・PASS / nb4）
§7 eligibility priority 表（110/105/100/90/85/80/70/50・none ineligible・active invalid block）は v0.8 と同一。
§8 method registry/capability（companion ⊆ applied・facet 互換・determinism equality）は v0.8 と同一。
**nb4**：`specificity` を自由値でなく決定式に固定 — `specificity = |required_companion_method_registry_ids| * 100 + |allowed_candidate_relation_types|`。同点は依然 validation error（most-specific 一意）。rule priority registry は policy_version 固定。

## 9. coverage（scope binding B20 / payload canonical nb1 / 必要scope完全性 維持）

### 9-1. range_class adapter（v0.8 §9-1 と同一）
interval_1d / grid_2d / rect_2d。各 range 非空・異 class 演算禁止。

### 9-2. coverage_assessment（payload を canonical sort/merge 後 digest・nb1）
```text
coverage_assessment                         # v0.8 + payload canonicalization
  coverage_assessment_key_id  # sha256(canonical_json(alignment_observation_id, member_ref, side, facet, coordinate_space, coverage_policy_id))
  coverage_revision_seq       # integer（prior+1）
  coverage_assessment_id      # sha256(canonical_json(key_id, revision_seq, coverage_policy_version, coverage_payload_digest))
  coverage_payload_digest     # nb1: sha256(canonical_json(asset_hash, source_text_revision_id, selector_state,
                              #   canonical_ranges(covered_ranges), canonical_ranges(unknown_ranges),
                              #   ocr_quality_score, layout_quality_score))
  alignment_observation_id ; member_ref ; side ; facet ; coordinate_space
  asset_hash ; source_text_revision_id ; selector_state
  covered_ranges[] ; unknown_ranges[] ; ocr_quality_score ; layout_quality_score
  coverage_policy_id ; coverage_policy_version ; supersedes_coverage_assessment_id? ; coverage_status
UNIQUE(coverage_assessment_key_id, coverage_revision_seq)
# canonical_ranges(R) = range_class adapter で sort/merge 正規化（入力順非依存・nb1）
coverage_status(ca) = revision_seq = max(seq) over key → current / else superseded
# nb2: supersedes_coverage_assessment_id は同一 key の直前 revision のみ（seq gap/branch は validation error）
```

### 9-3. coverage_claim_scope（logical key + assessment binding・B20）
```text
coverage_claim_scope
  coverage_claim_scope_id     # B20: sha256(canonical_json(scope_key_id, coverage_assessment_id))
  scope_key_id                # B20: sha256(canonical_json(use_assessment_key_id, member_ref, required_coordinate_space))
  use_assessment_key_id ; member_ref ; required_coordinate_space
  required_ranges[]（minItems=1・各非空・正規化済）
  coverage_assessment_id      # FK → coverage_assessment（current）
UNIQUE(scope_key_id)          # 同一 scope key に scope は1件
```
**coverage_scope_binding_valid（B20・normative）**
```text
coverage_scope_binding_valid(scope, ca, use_assessment, alignment, policy) ≡
  ca = current_ca(scope.coverage_assessment_id) AND ca ≠ NULL
  AND scope.member_ref = ca.member_ref
  AND ca.alignment_observation_id = use_assessment.alignment_observation_id
  AND ca.side = side_of_member(alignment, scope.member_ref)
  AND ca.facet = alignment.facet
  AND ca.coverage_policy_id = policy.policy_id AND ca.coverage_policy_version = policy.policy_version
  AND exists exactly one current ca for ca.coverage_assessment_key_id
# 無関係 member の完全 coverage を差し替えられない（B20 閉鎖）
```

### 9-4. 必要scope完全性（B14 維持 + binding・B19/B20 統合）
```text
required_scope_keys(key) = { (m, claim_context.required_coordinate_space) : m ∈ selector.claimed_member_refs }
  # selector は §6 で expected_member_set と整合（過少申告封じ済）
actual_scope_keys(key)   = { (s.member_ref, s.required_coordinate_space) : s ∈ coverage_claim_scope[key] }

coverage_complete_for_scope(scope, ca, policy) ≡            # v0.8 + range_class adapter
  ca.coverage_status=current AND ca.selector_state=complete
  AND ca.ocr_quality_score ≥ policy.minimum_ocr_quality AND ca.layout_quality_score ≥ policy.minimum_layout_quality
  AND ca.coordinate_space = scope.required_coordinate_space
  AND adapter.contains(ca.covered_ranges, scope.required_ranges)
  AND NOT adapter.intersects(ca.unknown_ranges, scope.required_ranges)

coverage_complete_for_use_assessment(key) ≡                # B14+B19+B20
  G_XDOC_CLAIM_MEMBER_COMPLETE(selector, alignment)        # §6: 過少申告封じ
  AND required_scope_keys(key) ⊆ actual_scope_keys(key)
  AND every(scope ∈ coverage_claim_scope[key]):
        coverage_scope_binding_valid(scope, current_ca(scope.coverage_assessment_id), use_assessment, alignment, policy)
        AND coverage_complete_for_scope(scope, current_ca(...), policy)
```
- **G_XDOC_COVERAGE_REQUIRED_SCOPE_COMPLETE**（B14）/ **CLAIM_MEMBER_COMPLETE**（B19）/ **COVERAGE_SCOPE_BINDING**（B20）/ **COVERAGE_PAYLOAD_CANONICAL**（nb1）。

## 10. cluster / support（coverage scope ref B21 / policy B22 / revision B23）

### 10-1. xdoc_support_edge（coverage scope ref + revision・B21/B23）
```text
support_basis_coverage_scope_ref            # B21: scope と assessment を対で参照
  coverage_claim_scope_id     # FK → coverage_claim_scope（required_ranges + coverage_assessment_id を内包）
  member_ref                  # low/high のいずれか

xdoc_support_edge                           # B23: revision 契約
  support_edge_key_id         # = sha256(canonical_json(cluster_facet, canonical_member_low, canonical_member_high, alignment_observation_id))
  support_edge_revision_id    # = sha256(canonical_json(support_edge_key_id, basis_digest, calibration_id, calibration_version, policy_id, policy_version, revision_seq))
  revision_seq                # integer（prior+1）
  supersedes_revision_id      # NULL or 直前 revision
  support_status              # active | superseded | revoked（導出: revoked→revoked / max seq 非revoked→active / else superseded）
  cluster_facet ; canonical_member_low ; canonical_member_high ; alignment_observation_id
  support_score ; calibration_id ; calibration_version ; policy_id ; policy_version
  support_basis_use_assessment_revision_ids[]     # unique・minItems は policy.required_basis_types に従う
  support_basis_coverage_scope_refs[]             # B21: support_basis_coverage_scope_ref[]・unique
  basis_digest                # = sha256(canonical_json(sorted(use_assessment_revision_ids), sorted(coverage_scope_ids)))
  CONSTRAINT canonical_member_low ≠ canonical_member_high
  UNIQUE(support_edge_key_id, revision_seq)
# basis 追加/撤回は新 revision（revision_seq++・supersedes）として append（silent mutation 禁止・B23）
```

### 10-2. support_basis_valid + effective（coverage scope 接地 B21 / policy eligibility B22）
```text
support_basis_valid_ua(edge, r, policy) ≡                  # use_assessment_revision ref
  assessment_status(r)=active AND r.alignment_observation_id = edge.alignment_observation_id
  AND r.target ∈ policy.allowed_support_targets AND r.evaluation_purpose ∈ policy.allowed_support_purposes
  AND r.eligibility ∈ policy.allowed_support_eligibilities          # B22: 既定 {eligible}（hold は不可）

support_basis_valid_scope(edge, sref, use_assessment, alignment, policy) ≡   # B21: coverage scope ref
  scope = coverage_claim_scope(sref.coverage_claim_scope_id)
  AND sref.member_ref ∈ {edge.canonical_member_low, edge.canonical_member_high}
  AND scope.member_ref = sref.member_ref
  AND ca = current_ca(scope.coverage_assessment_id)
  AND ca.facet = edge.cluster_facet
  AND coverage_scope_binding_valid(scope, ca, use_assessment, alignment, policy)   # §9-3
  AND coverage_complete_for_scope(scope, ca, policy)                                # current だけでなく complete

support_edge_effective(edge, policy, ctx) ≡               # active revision のみ
  edge.support_status = active
  AND edge.support_score ≥ policy.minimum_support_score
  AND edge.calibration_id = policy.calibration_id AND edge.calibration_version = policy.calibration_version
  AND non_empty_required(edge, policy)                     # B22: required_basis_types minItems=1
  AND every(r ∈ edge.support_basis_use_assessment_revision_ids): support_basis_valid_ua(edge, r, policy)
  AND covers_all_required_members(edge, policy)            # B21: low/high 双方に complete scope
  AND every(sref ∈ edge.support_basis_coverage_scope_refs): support_basis_valid_scope(edge, sref, ...)

covers_all_required_members(edge, policy) ≡               # B21: 複数 scope 必要なら全 AND
  'coverage_assessment' ∈ policy.required_basis_types ⇒
    { edge.canonical_member_low, edge.canonical_member_high }
      ⊆ { sref.member_ref : sref ∈ edge.support_basis_coverage_scope_refs（valid なもの） }
```

### 10-3. cluster_policy（required_basis_types minItems=1 + eligibility・B22）
```text
cluster_policy
  policy_id ; policy_version ; algorithm ; stability_metric_id
  minimum_stability ; minimum_density ; minimum_support_score ; calibration_id ; calibration_version ; maximum_size
  outlier_rule_type ; outlier_threshold ; missing_pair_rule_type
  required_basis_types[]               # B22: minItems=1・unique・{use_assessment_revision, coverage_assessment} 部分集合
  allowed_support_targets[] ; allowed_support_purposes[]
  allowed_support_eligibilities[]      # B22: minItems=1・既定=[eligible]（hold は別 tentative_support で扱う）
# G_XDOC_SUPPORT_POLICY_NONEMPTY: required_basis_types/allowed_support_eligibilities は空不可
# hold を tentative graph に使う場合は support_status=active でなく tentative_support=tentative（effective と分離）
```

### 10-4. xdoc_cluster / lineage（v0.8 維持）
cluster_status=candidate const・members minItems=2・pairwise_support_coverage（support_edge_effective 充足 edge≥1 の pair 比）・cluster_lineage_edge は v0.8 と同一。

## 11. ゲート → executable predicate（v0.8 + B19〜B23 追加）
v0.8 §11 を全て維持。追加：
| gate | predicate |
|---|---|
| CLAIM_MEMBER_COMPLETE | §6 G_XDOC_CLAIM_MEMBER_COMPLETE（all_on_side=完全一致 / explicit_subset=hash 固定 selector） |
| COVERAGE_SCOPE_BINDING | §9-3 coverage_scope_binding_valid（member/side/facet/policy 一致・current 1件） |
| COVERAGE_PAYLOAD_CANONICAL | §9-2 canonical_ranges で sort/merge 後 digest |
| SUPPORT_COVERAGE_SCOPE_REF | §10-2 support_basis_valid_scope + covers_all_required_members |
| SUPPORT_POLICY_NONEMPTY | §10-3 required_basis_types/allowed_support_eligibilities minItems=1 |
| SUPPORT_ELIGIBILITY_ALLOWED | §10-2 r.eligibility ∈ allowed_support_eligibilities（既定 eligible・hold 不可） |
| SUPPORT_EDGE_REVISION_APPEND_ONLY | §10-1 key+revision_seq+supersedes・basis 変更は新 revision |
| CLUSTER_SUPPORT_CONTRACT | §10-2 support_edge_effective（coverage scope 接地済）+ stability + policy |

## 12. 受入試験（v0.9・全自動 PASS が条件・6/11 を閉鎖）
1〜5, 7〜10, 12: v0.8 と同一（PASS 維持）。
6. **claim 完全性**: (a) claimed_side=both で1 member だけ列挙 → all_on_side で reject / explicit_subset で subset_selector_id 必須。(b) scope の member_ref ≠ assessment.member_ref / assessment.alignment ≠ use_assessment.alignment / facet 不一致 / policy 不一致 → coverage_scope_binding_valid false → coverage_complete_for_use_assessment false → absence/difference は priority 90 ineligible。(c) 必要 member の scope 未登録 → required ⊄ actual → false。
11. **support scope 接地**: (a) required_basis_types 空 policy は作成不可（minItems=1）。(b) hold の use_assessment は allowed_support_eligibilities（既定 eligible）外 → support_basis_valid_ua false。(c) edge が low/high 双方の complete coverage scope を持たない → covers_all_required_members false → effective false。(d) coverage scope が別 alignment/member/facet に binding → support_basis_valid_scope false。(e) basis 追加で同一 key の新 revision（supersedes）・旧 revision は superseded（silent mutation なし）。(f) A~B,B~C で effective edge(A,C) 無し → A-C は missing_pair_rule_type=unknown。

## 13. 追加 negative fixture（v0.9 必須・GO）
claim-member-undercount（both+1member・B19）／wrong-member-scope・wrong-side-scope・wrong-policy-scope（B20）／support-coverage-scope-missing-member（B21）／empty-required-basis-types・hold-support（B22）／support-basis-revise-supersede（B23）／coverage-payload-range-reorder（nb1：入力順で digest 不変）。

## 14. GO / HOLD / loop_state
- **GO**：独立 DD 維持／v0.9 限定 patch／上記 negative fixtures／read-only validator 試作。
- **HOLD**：v0.9 ratify／DDL/DB/mint/Box mutation／OCR/embedding/training／production pair generation・clustering／FRBR・DD-LITID・DD-LITLINK・block_ref current 昇格／evidence・legal claim support。
- loop_state = **accepted（owner ratify 2026-06-24・GPT PASS_WITH_NOTES）。設計三部作 LAYOUT/XMODAL/XDOC 完成**。実装は Phase 1 以降・別ゲート。
