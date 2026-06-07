### DD-TOCLEGALREF-001 v0.2: 蔵書目次(bib_toc)由来の条文・判例参照を link layer(alo_edges) に **candidate signal** として供給する

> **id**: `DD-TOCLEGALREF-001` / **version**: v0.2 / **status**: candidate
> **supersedes_review**: v0.1 (gate DDTOCLEGALREF → `DDTOCLEGALREF_MODIFY_REQUIRED`, 2026-06-07)
> **recorded_at**: 2026-06-07 / **owner**: 浅井 / **author**: Project-codex Fork 4 (claude-code remote)
> v0.1 の方向性（新スキーマを作らず alo_edges に供給）は GPT お目付け役に**支持**された。
> 本 v0.2 は required_patches 1–9 と proposed gates を反映し、TOC 由来リンクを
> **弱い candidate signal** として明文化、DD-LAWTIME 未accept 部分と canonical work/case
> URI 解決を遮断する。**DB 書込みは依然ゼロ**（accept + 層実装後）。

- **depends_on**: 35_link_layer v0.1 / 31_case_layer v1.4 / 30_law_layer・DD-LAW-011〜015 /
  DD-LAWTIME-001 (candidate, **MODIFY_REQUIRED**) / 32_literature_layer / control.*

---

## §1 GPT お目付け役 指摘の解決（required_patches 1–9）

| # | 指摘 | v0.2 解決 | 実装(producer) |
|---|---|---|---|
| 1 (R-01) | `interprets`/`evaluates` が TOC の弱い証拠に強すぎ | 既存型を維持しつつ **`edge_semantics_status=candidate`** で隔離。link layer 本体(10値CHECK)は無改変。`evaluates`(判例)は**そもそも edge 化しない**（§3 解決候補）ので強すぎる評価を出さない | `edge_semantics_status:"candidate"` 付与 |
| 2 (R-02) | `vendor_implicit` が active CHECK に無い／`weight` が confidence と混同 | **`assertion_mode="implicit"`（既存値）+ `extraction_method="vendor_rule"`** に変更。`vendor_implicit` は新設しない。`weight_basis="relevance_strength_not_truth_confidence"` を明記、`assertion_confidence=NULL` | 反映済 |
| 3 (R-03) | pub_year を as_of に流用すると旧法誤接続。DD-LAWTIME は MODIFY_REQUIRED | pub_year は **`as_of_status="coarse_proxy"`/`as_of_precision="year"`/`as_of_basis="pub_year"`**。`valid_from`に流用せず**null**。`resolved_law_revision_id`/`temporal_status`は**書かない**、`claim_support_eligible=false` | 反映済 |
| 4 (R-04) | 暫定 `alo:work:bencom:{bib_id}` の canonical 混入 | `src_uri_status="provisional"`/`source_record_key=bib_id`/`canonical_work_uri=NULL`/`src_resolution_status="unresolved"`。**canonical と呼ばない**。解決後に alias/redirect で束ねる | 反映済 |
| 5 (A-01) | medium をいきなり本番 edge に入れるとノイズ | **初回 backfill は high(initial) のみ**。medium は `rollout_status="quarantine_sample_required"`。medium 供給は 100件以上の層化サンプルで precision 測定・閾値明記後 | `rollout_status` 付与 |
| 6 (A-02) | source_priority=50 の根拠不足 | `is_canonical=false`/`conflict_policy=append`/**`source_role="toc_signal"`**/`claim_support_eligible=false_by_default` をセットに。priority 数値は alo_source_priority 全体表で相対確認後に確定（producer は `source_role` を付与、数値確定は SE） | `source_role="toc_signal"` |
| 7 (A-03) | external pointer の再現性 | pointer に **`bib_toc_node_key`(bib_id:ordinal) + `payload_hash`(node text sha1) + `parser_version` + char span** | 反映済 |
| 8 (A-04) | case 候補が積み上がるだけ | candidate に **`candidate_status`/`resolution_basis`/`matched_case_uri`/`ambiguity_count`/`review_required`/`source_text`**。事件番号なしは edge 化しない gate | 反映済 |
| 9 | 冪等 dedup | **`dedup_key = sha1(source_record_key | dst_uri | edge_type | node_key | source_span_hash | extractor_version)`** | 反映済 |

## §2 proposed gates（producer 自己検査で実装・全 PASS）

`scripts/run_alo_edges_export.py` が下記を assert（実データ 600 ノードで全 PASS）:
`gate_toc_edges_have_evidence_pointer` / `gate_toc_low_tier_not_exported` /
`gate_toc_no_case_edge_without_canonical_case_uri` / `gate_toc_pub_year_not_used_as_exact_asof` /
`gate_toc_no_temporal_resolution_before_lawtime_accept` /
`gate_toc_src_uri_not_marked_canonical_until_resolved` / `gate_toc_edge_semantics_quarantined` /
`gate_toc_assertion_mode_no_vendor_implicit` / `gate_toc_medium_quarantined` /
`gate_toc_case_candidate_review_required`。

## §3 確定スキーマ（v0.2 出力契約）

- **statute edge（commentary→statute, candidate）**:
  `src_uri`(provisional)/`src_uri_status`/`source_record_key`/`canonical_work_uri=NULL`、
  `dst_uri=egov:{law_id}[:art:{article}]`/`dst_type=statute`、
  `edge_type=interprets`/`edge_semantics_status=candidate`、
  `assertion_mode=implicit`/`extraction_method=vendor_rule`/`assertion_confidence=NULL`、
  `weight`(high1.0/med0.7)/`weight_basis`/`rollout_status`、
  `valid_from=NULL`/`as_of_*`(coarse_proxy)/`resolved_law_revision_id=NULL`/`temporal_status=NULL`/`claim_support_eligible=false`、
  `source_system=bencom-library`/`source_role=toc_signal`/`dedup_key`/`provenance`。
- **evidence**: `(edge dedup_key) → pointer_uri`, `role=source_field`。
- **pointer**: `entity_type=work`/`entity_uri=src_uri`/`storage_type=external`/`bib_toc_node_key`/`payload_hash`/`parser_version`/char span。
- **case candidate（edge 化しない）**: §1 #8 のフィールド一式。

## §4 据え置き（owner/SE 判断・accept 条件）

- medium 供給の precision ゲート閾値（A-01）／ source priority 数値の全体表確認（A-02）。
- DD-LAWTIME-001 accept が**本 DD の temporal backfill 前提**（R-03）。それまで法令版解決は禁止。
- canonical work URI（32_literature_layer）/ canonical case URI（31_case_layer 事件番号解決）への
  resolution は別タスク（producer は provisional/candidate のまま供給）。

## §5 artifacts（本 PR, 書込みなし・全 gate PASS）

`out_real/alo_edges_export.jsonl`(interprets 49: initial43/quarantine6) /
`alo_edge_evidence_export.jsonl` / `alo_pointers_export.jsonl`(再現性フィールド付) /
`alo_case_ref_candidates.jsonl`(25, review_required) / `alo_edges_export_summary.json`(all_gates_pass=true)。

## §6 changelog
- v0.2 (2026-06-07): GPT お目付け役 `DDTOCLEGALREF_MODIFY_REQUIRED` の required_patches 1–9 +
  proposed gates を反映。edge を candidate signal 化、assertion_mode=implicit+extraction_method、
  temporal 遮断、src/case を provisional/解決候補に格下げ、再現性・dedup・rollout を明文化。
- v0.1 (2026-06-06): 初版。方向性レビュー合格（新スキーマ棄却・alo_edges 供給）。
