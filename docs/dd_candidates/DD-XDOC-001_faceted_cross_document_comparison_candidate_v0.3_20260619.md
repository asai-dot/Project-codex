# DD-XDOC-001 v0.3 — faceted cross-document comparison & alignment（MODIFY round2 反映・自己完結）candidate

> **id**: DD-XDOC-001 / **version**: candidate v0.3 / **supersedes**: v0.2（および v0.1。本文書は normative schema/gate/HOLD を自己完結）
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-19 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/学習/embedding/production pair generation/clustering/FRBR・DD-LITID・DD-LITLINK 昇格/block_ref current 昇格/evidence・legal claim support は **HOLD**。
> **改訂理由（v0.2→v0.3）**: GPT Pro 再監査 `DDXDOC_MODIFY_REQUIRED`（RESULT Box 2295972983915）の残7ブロッカー（must_fix 10項目）を反映。独立DD継続・v0.3 は GO。
> **depends_on**: DD-LAYOUT-001 v0.5 accepted（安定アンカー・coverage・block_ref 正規定義）, DD-XMODAL-001 v0.4 accepted（independence・family registry）, DD-LITID-001, DD-LITLINK-001, 三軸 v0.3。**本DDは依存先の定義を狭めない**（§7）。

---

## 0. must_fix round2 反映（10項目）
| # | must_fix | v0.3 |
|---|---|---|
| 1 | 独立性を bool でなく tri-state ×2軸、unknown 保持 | §1 |
| 2 | object/passage-level content_origin_ref＋根拠 | §2 |
| 3 | comparison_intent ＋ 用途別 eligibility | §3 |
| 4 | 再現性契約（snapshot/revision/params/score components/deterministic id） | §4・§9 |
| 5 | record state を多軸に（validity/interpretation/2軸independence/target別eligibility/reason） | §6 |
| 6 | block_ref 境界を DD-LAYOUT v0.5 と整合（cross_doc あり得る） | §7 |
| 7 | cluster 契約（stability/support/lineage/non-equivalence） | §8 |
| 8 | CDC/pHash/visual embedding の能力補正＋allowed_relation_types 機械可読 | §5 |
| 9 | coverage を両側/member 単位、quality/revision 接地 | §4 coverage_a/b_ref |
| 10 | v0.3 を自己完結（normative schema/gate/HOLD） | 本文書全体 |

## 1. ★独立性＝2軸 tri-state（must#1, bool 廃止）
```text
content_independence_state    ∈ {independent, shared_origin, partially_shared, unknown}
observation_independence_state∈ {independent, shared_pipeline, partially_shared, unknown}
```
- **unknown を false へ潰さない**（unknown のまま保持）。
- 独立執筆2冊を同一OCRで処理＝content independent / observation shared_pipeline（抽出相互確認には使えるが法的内容独立裏付けではない）。
- 同一条文を別OCRで引用＝content shared_origin / observation independent（独立裏付けにならない）。
- **どの状態を要求するかは `comparison_intent` 毎に異なる**（§3）。

## 2. ★passage-level content origin（must#2、family は粗すぎ）
```text
content_origin_ref
  source_object_type∈{statute, case, manuscript, edition, commentary, dataset}
  source_object_id / source_version / source_passage_ref
  origin_relation∈{quote, reprint, adaptation, common_template, same_expression}
  origin_detection_method / version / confidence / review_state
```
異なる出版社 family でも**同一法令条項の引用**を検知できる＝こたつ記事防止 gate の機械化条件。

## 3. ★comparison_intent（must#3）＋ 用途別 eligibility
```text
comparison_intent∈{near_duplicate, text_reuse, citation_candidate, semantic_overlap,
                   edition_alignment, structure_comparison, table_template, figure_reuse}
```
shared origin は **intent で意味が反転**：text_reuse/citation＝正の発見／independent corroboration＝除外理由／edition_alignment＝期待される lineage。
→ relation 解釈と downstream eligibility は **intent 別に判定**（§6）。

## 4. xdoc_alignment（再現性契約・coverage 両側を内包）
```text
xdoc_alignment                         # 派生・claim_support_eligible=false
  alignment_id          # deterministic（method+params+normalized member set+snapshot から導出）
  facet∈{structure,text,table,figure} ; comparison_intent
  direction∈{a_to_b,b_to_a,symmetric} ; cardinality∈{1:1,1:n,n:1,n:m}
  members_a[unit@asset] ; members_b[unit@asset] ; pair_normalization
  edit_script[]         # structure: insert|delete|move|rename|split|merge
  method / method_version / method_parameter_profile
  normalization_profile / tokenization_profile
  similarity ; score_components{} ; calibration_version
  coverage_a_ref / coverage_b_ref     # 両側（member 単位可）→ asset_hash, text_revision, ocr/layout quality
  content_independence_state / observation_independence_state    # §1（bool でない）
  content_origin_refs[]               # §2
  corpus_snapshot_id / release_id
  status_block          # §6（多軸）
```

## 5. method registry（must#8・機械可読 capability）
```text
method_registry(method, version, facet, capability, allowed_relation_types[], caveats)
```
| method | facet | capability（主張可） | allowed_relation_types | できない |
|---|---|---|---|---|
| MinHash/SimHash | text | 近重複・集合類似 | near_duplicate,text_reuse(候補) | 意味同一・引用方向 |
| embedding | text | 意味的近接 | semantic_overlap | 記号一致・逐語同一 |
| **CDC/Rabin** | text | **境界生成・安定 segmentation**（区間同一は content_hash 併用で初めて主張） | （単独で relation を確定しない） | 単独の区間同一主張 |
| table structure matching | table | 行列構造・セル対応 | table_template,structure_comparison | 図的内容 |
| **pHash** | figure | **near-duplicate 候補** | figure_reuse(候補) | 図版同一の確定 |
| **visual embedding** | figure | **視覚的近接候補** | figure_reuse(候補) | 図版同一の確定 |
- **G_XDOC_METHOD_CAPABILITY_DECLARED**：allowed_relation_types を超える relation を付けない。CDC は単独で「区間同一」と言わない。pHash/visual は「図版同一」を確定しない。

## 6. ★record state を多軸に（must#5、status 一軸廃止）
```text
status_block:
  alignment_validity∈{valid,invalid,unknown,abstain}          # 同じ箇所か
  relation_interpretation∈{quote,reprint,edition,same_topic,template,unknown}  # intent 文脈で
  content_independence_decision∈{independent,shared_origin,partially,unknown}
  pipeline_independence_decision∈{independent,shared_pipeline,partially,unknown}
  downstream_eligibility_by_target{                            # target 別に別判定
    litlink_candidate∈{eligible,ineligible,hold},
    formobj_variant∈{...}, frbr_work∈{...}, proof_corroboration∈{...} }
  review_reason / abstain_reason
```
「整列は正しい・shared origin・reuse候補には使えるが独立裏付けには使えない」を**1 record で表現**できる。

## 7. ★所有境界（must#6、DD-LAYOUT v0.5 と整合・依存先を狭めない）
切り口は「文書内/間」ではなく **edge の種類**：
| レイヤ | 所有 DD | 定義（依存先の正規定義に従う） |
|---|---|---|
| `block_ref` | **DD-LAYOUT v0.5** | 文書上**明示された参照** or resolver が確定した reference/stitching edge。**cross_doc もあり得る**（v0.5 controlled vocab に cross_doc 有り）。 |
| `lit_link` | **DD-LITLINK** | 引用・外部リンク関係の候補採否・下流 promotion |
| `xdoc_alignment` | **DD-XDOC（本DD）** | 類似・整列・reuse の**推定 observation** |
- **G_XDOC_OWNERSHIP_NO_REDEF**：XDOC は DD-LAYOUT/DD-LITLINK の定義を狭めて再定義しない。XDOC は推定 alignment を所有し、block_ref/lit_link へは**候補を渡すのみ**（生成・current 昇格しない）。

## 8. ★cluster 契約（must#7、gate 文でなく契約）
```text
xdoc_cluster
  cluster_id ; facet ; algorithm / version / parameter_profile / corpus_snapshot
  members[unit@asset] ; member_score ; representative_or_medoid
  cluster_stability / density / outlier_state ; pairwise_support_coverage
  cluster_lineage / supersedes
  cluster_semantics = candidate_set   # ★ NOT equivalence_class
```
- **G_XDOC_NO_TRANSITIVE_EQUIVALENCE**：cluster membership を同一性の推移関係として扱わない（consensus も自動連鎖し得るので membership=候補集合）。
- **G_XDOC_NO_TRANSITIVE_MEGACLUSTER**（v0.2 承継）：pairwise 推移閉包で巨大化しない。

## 9. 再現性契約（must#4・監査契約）
全 derived observation は：corpus_snapshot_id/release_id・asset revision/source_text_revision/selector state・method_parameter_profile・normalization/tokenization profile・score_components/calibration_version・deterministic alignment_id/pair_normalization を保持。**method_version＋scalar similarity だけにしない**（再現・比較・撤回のため）。

## 10. ゲート一覧
v0.1/v0.2 承継（DERIVED / NO_CLAIM_SUPPORT / HUMAN_PROMOTION_ONLY / NO_SELF_LOOP / FACET_ANCHORED / METHOD_CAPABILITY_DECLARED / COVERAGE_INHERITED / NO_SINGLE_FACET_WORK_ID / NO_TRANSITIVE_MEGACLUSTER）
＋ v0.3：**G_XDOC_INDEPENDENCE_TRISTATE**（bool 禁止・unknown 保持）／**G_XDOC_PASSAGE_ORIGIN_REQUIRED**（passage-level origin＋根拠）／**G_XDOC_INTENT_REQUIRED**（comparison_intent 必須・intent 別 eligibility）／**G_XDOC_REPRODUCIBILITY_CONTRACT**（§9）／**G_XDOC_MULTIAXIS_STATE**（status 一軸禁止）／**G_XDOC_OWNERSHIP_NO_REDEF**（§7）／**G_XDOC_NO_TRANSITIVE_EQUIVALENCE**（§8）／**G_XDOC_RELATION_TYPES_MACHINE_READABLE**（method registry の allowed_relation_types）。

## 11. GO / HOLD / loop_state
- **GO**：独立DD維持／design-only inventory probe／passage-level shared-origin detector の gold sample 設計／read-only candidate generation 計画。
- **HOLD**：v0.3 ratify／DDL/DB/mint/Box mutation／OCR/embedding/training／production pair generation・clustering／FRBR・DD-LITID 同一性昇格／DD-LITLINK accepted・block_ref current 自動昇格／evidence・legal claim support。
- loop_state = **patched（v0.3 自己完結）→ 再投函（再監査）候補**。
