### DD-TOCLEGALREF-001: 蔵書目次(bib_toc)からの条文・判例参照を link layer(alo_edges) に commentary→statute/case エッジとして供給する

> **id**: `DD-TOCLEGALREF-001`（ドメイン `TOCLEGALREF`=table-of-contents legal reference, 暫定採番）
> **status**: **candidate / draft v0.1**（草案。**未投函**。gpt_ometsuke ゲート前）
> **recorded_at**: 2026-06-06 / **owner**: 浅井 / **author**: Project-codex Fork 4 (claude-code remote)
> **このDDは書込みを一切伴わない**。`apply_migration` も DB 投入も承認後。

- **depends_on**:
  - 35_link_layer.md v0.1 (active) … `alo_edges` / `alo_edge_evidence` / `alo_pointers` 正本
  - 31_case_layer.md v1.4 (active) … `cases` canonical_uri = `alo:case:jp:{court}:{date}:{case_number_norm}`
  - 30_law_layer.md / DD-LAW-011〜015 … statute URI `egov:{law_id}:art:{article}`
  - DD-LAWTIME-001 (candidate) … 法令参照の as_of(point-in-time)・temporal_status
  - 32_literature_layer.md … 文献(work) URI（src の解決先）
  - control.* governance（source_snapshots / ingest_jobs / releases）

- **§0 self-detect（新設前の既存資産確認）**:
  当初 `legal.statute_law / statute_article / case_citation` の**新スキーマ新設**を検討したが、
  設計図書精読により **link layer(alo_edges) + law layer + case layer が既に設計済**と判明。
  本DDは**新テーブルを一切作らず**、既存 `alo_edges` への供給に徹する。
  （`biblio.bib_toc` 等の実装済スキーマも不変。）

- **decision**:
  `biblio.bib_toc`（蔵書目次、bencom-library 552,544 ノード）のテキストから条文/判例参照を
  ルール抽出し、**文献(commentary)→条文(statute)** を `edge_type=interprets`、
  **文献→判例(case)** を `edge_type=evaluates` として `alo_edges` に供給する。

  - **src**: `src_type=commentary`、`src_uri` = 当該書誌の文献(work) URI（暫定 `alo:work:bencom:{bib_id}`、最終は 32_literature_layer の work URI に解決）。具体ノードは evidence で特定。
  - **dst(条文)**: `dst_type=statute`、`dst_uri = egov:{law_id}[:art:{article}]`（DD-LAW-014 準拠）。
  - **dst(判例)**: cases.canonical_uri は**事件番号(case_number_norm)を要求**するが TOC 文字列に事件番号は無い → **判例は edge 化せず「解決候補」**として court/era/date を保持し、`cases`(court+date+事件番号) への照合で解決後に `evaluates` エッジ化する。
  - **assertion_mode = `vendor_implicit`**（ソースデータからのパイプライン抽出。`llm_inferred` は DB 禁止につき不使用）。
  - **`assertion_confidence` は NULL**（同列は llm_inferred 専用, ck_alo_edges_confidence_only_for_llm）。確信度 tier は `weight`(high=1.0 / medium=0.7) と provenance に格納。**low(複合語誤検出: 医療法人→医療法 等) は edge 化しない**。
  - **Gate-5 遵守**: 全エッジに `alo_edge_evidence`(→`alo_pointers`, role=`source_field`, range=char span) を必ず付す（孤児エッジ 0）。
  - **as_of(DD-LAWTIME 準備)**: 参照元日付 = 書誌 `pub_year`（年粒度）を provenance と `valid_from` proxy に載せる。DD-LAWTIME accept 後、`as_of_date`/`resolved_law_revision_id`/`temporal_status` 列へ正式マップ。

- **why**:
  「Links Are the Core Asset」（35_link_layer §1.1）。実測で bib_toc に条文参照 10,211 / 判例参照 2,042 ノードが実在し、文献→条文/判例の高密度エッジを供給できる。抽出は precision-first（法令名隣接の条のみ・裸の条番号は推測しない）で、誤検出は low tier に隔離され edge から除外される。独自スキーマを作らず既存 link layer に乗せることで相互運用性・監査性・gate 適合を得る。

- **alternatives_rejected**:
  - (a) `legal.*` 新スキーマ新設 → 既設 link/law/case layer と二重化。§0 違反。
  - (b) 判例を court+date だけで canonical case URI 化 → 事件番号欠落で URI 不整合（ck_cases_canonical_uri_consistent 違反）。→ 解決候補に留める。
  - (c) tier を `assertion_confidence` に格納 → 同列は llm_inferred 専用制約に違反。→ weight に格納。
  - (d) 裸の条番号(~9,600ノード)を書誌主題から推測補完 → 誤 law_id 温床。→ 供給対象外。

- **downstream_effect**:
  - `alo_source_priority` に **`bencom-library`** ソース登録が必要（fk_ae_source_system / gate_orphan_source_system）。priority/conflict_policy は要決定（提案: priority=後位, conflict_policy=append, is_canonical=false）。
  - `interprets`/`evaluates` の evidence pointer は storage_type=`external`（TOC は full_text ではない）。31_case_layer の pointer 帰属検証(fn_check_pointer_belongs_to_case)は case 用途であり、本 commentary→statute では entity_type=`work` を使用。
  - 判例解決候補は `cases`(D1-Law 249,863件 / 将来 saikousai-db 年20万件)への突合タスク（別 DD: 判例名寄せ）に渡す。
  - DD-LAWTIME accept 時、本エッジ群に as_of/temporal_status を backfill。

- **open_issues（accepted 前）**:
  1. `src_uri` の文献(work) URI 正準化（`alo:work:bencom:{bib_id}` 暫定 → 32_literature_layer の work 同定）。
  2. `bencom-library` の `alo_source_priority` 登録値（priority / conflict_policy / is_canonical）。
  3. `interprets`/`evaluates` の `weight` 自動算出ルール（現状 tier 固定。35_link_layer §11 未解決の weight ロジックと整合）。
  4. medium tier(裸の法令名)を供給に含めるか、high(条番号あり)のみに絞るか（初回は high+medium 供給・low 除外を提案）。
  5. as_of 年粒度（pub_year）の妥当性。月日まで取れない書誌の扱い（DD-LAWTIME open_issue#2 と統合）。
  6. 判例解決の同定規則（court_code 正規化・元号→西暦・同日複数事件の曖昧性）。
  7. GPT Pro お目付け役クロスレビュー（gate=要 `DDTOCLEGALREF`）。

- **enforcement_by_guarantee_level**:
  - enforced (Claude Code / producer): edge_type∈{interprets,evaluates} / assertion_mode=vendor_implicit / assertion_confidence=NULL / Gate-5 evidence 必須 / NFC URI / low 除外 / 冪等 dedup(uq_alo_edges_vendor_dedup 同形キー)。本 PR の `scripts/run_alo_edges_export.py` が自己検査(Gate-5 PASS)込みで実装。
  - partial (Codex/SE): alo_source_priority 登録・実投入 migration・cases 突合。
  - advisory (GPT Pro): DD クロスレビュー。

- **review_required（accepted 昇格条件）**: 浅井先生本文レビュー / GPT Pro クロスレビュー(gpt_ometsuke gate) / open_issues 解消 / 法令・リンク層の実 DB 実装 / accept 時 Generated Index backfill。

- **artifacts（本 PR, 書込みなしのエクスポート）**:
  - `out_real/alo_edges_export.jsonl`（commentary→statute interprets, 実データ 49 本）
  - `out_real/alo_edge_evidence_export.jsonl` / `out_real/alo_pointers_export.jsonl`
  - `out_real/alo_case_ref_candidates.jsonl`（判例解決候補 25 本）
  - `out_real/alo_edges_export_summary.json`（Gate-5 PASS）

- **changelog**:
  - v0.1 (2026-06-06): 初版草案。35_link_layer/31_case_layer/30_law_layer/DD-LAWTIME 精読後。新スキーマ新設を棄却し alo_edges 供給に確定。**未投函（承認後に gpt_ometsuke へ）**。

---

## 付録A. 推奨決定（producer 側の既定値 / owner ratify 待ち）

open_issues のうち producer 側で既定にできるものを以下に確定（DB 反映は承認後）:

| # | 論点 | **推奨既定** | 根拠 |
|---|---|---|---|
| 4 | 供給 tier | **high + medium を供給**（weight 1.0 / 0.7 で区別）、low は除外 | low に誤検出が集中（医療法人→医療法 等）。high=条番号あり・medium=語境界ありは実害なし。serving 側で weight≥1.0 に絞る運用は別途可 |
| 2 | `bencom-library` の alo_source_priority | **priority=50（後位）/ conflict_policy=`append` / is_canonical=false** | D1-Law(1)等の一次ソースを上書きしない。文献由来の補助エッジは追記型が安全 |
| 1 | `src_uri` | **`alo:work:bencom:{bib_id}` を暫定採用**、32_literature_layer の work URI への解決は backfill タスク | work 同定は文献層の責務。producer は安定 ID で先行し後解決 |
| 5 | as_of 粒度 | **`pub_year`（年）を as_of_date proxy** | bib_records に月日が無い。DD-LAWTIME accept 後に精緻化 |

owner/SE 判断が必須で producer 既定にしない項目: #3 weight 自動算出ルール, #6 判例同定規則, #7 GPT クロスレビュー gate。

## 付録B. 投函ステータス（gpt_ometsuke）

- 本 DD は **未投函**。投函レディの REQUEST は `reports/gpt_ometsuke/20260606_toclegalref_v0.1_DDTOCLEGALREF_REQUEST.md`（リポジトリ内・**Box 未配置**）。
- 投函の前提条件（推奨・順序）:
  1. 親 **DD-LAWTIME-001 が accepted** になる（本 DD は depends_on）。
  2. 本 DD 現物を Box `docs/alo/` にアップロード（DDCASESOURCE が「現物 Box 不在」で blocked になった轍を踏まない）。
  3. REQUEST front-matter の `status: draft → queued`、`source_hash` を実 sha256 で確定。
  4. `to_gpt/` に重複が無いか確認（PROTOCOL v0.2 重複投函禁止）してから配置。
