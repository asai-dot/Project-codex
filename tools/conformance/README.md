# conformance — 設計三部作 適合性ハーネス（Phase 0）

DD-LAYOUT-001 / DD-XMODAL-001 / DD-XDOC-001 の**受入試験を実行可能コードにする**依存ゼロ
ハーネス。「accepted」を「executable & tested」へ。**production に一切触れない純関数のみ。**

> 原則（DD-IMPL-ROADMAP-001 §2-6）：DDL より前に「設計が機械的に通る」ことを証明し、
> 以降の本番実装を de-risk する。GPT 監査が最も誤実装を警戒した箇所を最初に固める。

## 現状（v0.8 反映分・55 tests green）

| module | DD 箇所 | 内容 |
|---|---|---|
| `xdoc_canonical.py` | XDOC §5 | `alignment_observation_id` 正規化（symmetric side 正規化・単一 cardinality・companion を ID 材料・self-loop gate） |
| `xdoc_eligibility.py` | XDOC §7 | eligibility policy engine（purpose×target 互換・positive relation 集合・priority 解決・none/invalid 防御） |
| `xdoc_coverage.py` | XDOC v0.8 §9 | coverage 必要scope完全性（B14）・logical key + numeric revision（B17）・interval_1d adapter・current/complete |
| `xdoc_support.py` | XDOC v0.8 §10 | support_edge 証拠拘束（B15 non_empty_required・B16 support_basis_valid FK整合・support_edge_effective） |
| `xdoc_ranges.py` | XDOC v0.8 §9-1 | range_class 別 set 演算 adapter（interval_1d / grid_2d=table_cell / rect_2d=figure_region・厳密 contains/intersects） |
| `xdoc_method.py` | XDOC v0.8 §8 | method capability 検査（required companion ⊆ applied・CDC+content_hash・facet互換・determinism equality・most-specific rule） |
| `xdoc_claim.py` | XDOC v0.9 §6 | claim member selector（all_on_side=完全一致 / explicit_subset=hash 固定・過少申告封じ B19） |
| `xdoc_coverage.py` の `coverage_scope_binding_valid` | XDOC v0.9 §9-3 | coverage scope↔assessment binding（member/side/facet/policy 一致・current 1件・B20） |
| `xdoc_support_revision.py` | XDOC v0.9 §10 | support edge の coverage scope ref（B21）・policy non-empty/eligibility（B22）・revision append-only（B23） |
| `xmodal_agreement.py` | XMODAL v0.4 §1-2 | confirmed/possible 判定（反こたつ記事の核・external_source_family DISTINCT 計数・D2必須・NO_VT_CONFIRMATION・possible_reason） |
| `layout_projection.py` | LAYOUT v0.5 §3 | reading projection（型別読み・脚注/図表/本文だけ）・coverage 可視化（未型付けを断定しない）・reading_order 挿入耐性 |
| `layout_hashbundle.py` | LAYOUT v0.5 §2 | hash bundle 5種の用途別分割（再OCR→text_range のみ・軽量版再生成→image のみ・bbox 微調整→selector のみ変化） |
| `reconcile_indep_registry.py` | RECONCILE v0.1 §1 | 独立性 共有 registry（content_origin / observation_pipeline 2軸・XMODAL confirmed は content のみ数える・XMODAL 既存 kind 全写像） |

## 受入試験カバレッジ（XDOC §12）

| # | 試験 | テスト |
|---|---|---|
| 2 | purpose×target 別 key | `test_02_distinct_keys_per_purpose_target` |
| 3 | shared origin → ineligible / unknown → hold / invalid → 110 | `TestProofCorroboration` |
| 6 | **必要scope完全性**: missing-member-scope → false（B14） | `TestRequiredScopeCompleteness` |
| 7 | CDC 単独→relation=[]・CDC+content_hash→segment_identity_candidate のみ・companion ⊆ applied | `TestCDCCapability` |
| 9 | symmetric side-swap → 同一 id / multi-member 先頭でも一意 / directional は別 | `TestSymmetricId` |
| 10 | companion set・field 変化で id 変化 | `TestCompanionAndDrift` |
| 11 | **support_edge_effective**: 空basis/foreign-ref/failed-coverage/wrong-facet → false（B15/B16） | `TestEmptyBasis`, `TestForeignAndFacet` |
| 12 | reviewed=none → positive target で ineligible | `TestReviewedNone` |
| (B17) | v9/v10 → numeric revision で current 決定的・別space非supersede | `TestRevisionOrdering` |
| (gate) | self-loop / 空 side / 非互換 / 空required_ranges / dup basis | `TestSelfLoopGuards` 他 |

## GPT v0.8 必須 negative fixture（全て実行可能・green）

| fixture | finding | テスト |
|---|---|---|
| missing-member-scope | B14 | `test_06_missing_member_scope_false` |
| empty-support-basis | B15 | `test_11a_empty_support_basis_false` |
| foreign-assessment-ref | B16 | `test_11b_foreign_assessment_ref_false` |
| failed-current-coverage | B16 | `test_11c_failed_current_coverage_false` |
| wrong-facet coverage | B16 | `test_11d_wrong_facet_coverage_false` |
| v9/v10 revision ordering | B17 | `test_17_v9_v10_numeric_current` |

## 実行

```bash
python3 tools/conformance/run_conformance.py            # 全テスト + DD別要約
python3 tools/conformance/run_conformance.py --summary  # 要約のみ（実行せず）
python3 tools/conformance/run_conformance.py --json      # 機械可読サマリ
# 直接 unittest でも可:
python3 -m unittest discover -s tools/conformance/tests -p 'test_*.py' -v
```

依存なし（Python 3.9+）。production DB / Box / OCR に触れない（`production_touched: false`）。

## 未実装（次の Phase 0 増分）

- LAYOUT: block_ref stitching（脚注/図表/別紙連結）・STAM 自己修復（NW/SW 整列 + transposition）。
- XDOC 残: use_assessment revision 履歴（append-only/current 導出）・cluster pairwise_support_coverage。
- 合成 fixture を JSON 化し、スキーマ（JSON Schema）と相互検証。
