# REQUEST — DDLAWREF: statute-citation edge_type vocabulary 照合（lawtime v0.2.4）

> 宛先: **DDLAWREF**（`d1law_taikei.alo_edges` の `edge_type` vocabulary 所有者）
> 発信: DD-LAWTIME-001 v0.2.4（lawtime 配置・ratify 済）
> 種別: **decision_requested**（blocking note #5 の実体）。lawtime からの**照会のみ** — lawtime は edge_type を発明・拡張しない。
> 日付: 2026-06-25 ／ 課金ゼロ（本 REQUEST 作成は read-only 調査に基づく）
> 共有: **2026-06-25 Box `gpt_ometsuke/to_gpt` に送付済**（file_id `2309304297318`）。**DDLAWREF/GPT お目付け役の RESULT 待ち**。

---

## 0. 一行で

lawtime の gate は「statute-citation edge」を `edge_type IN ('cites_statute','statute_ref','applies_statute')` と
**仮置き**しているが、**実 `alo_edges` にこの3つは0件**（実在は `classified_under` のみ）。
**本番で statute-citation edge を何の `edge_type` で表すのか**を DDLAWREF に確定してほしい。

---

## 1. 確認された事実（B′ read-only dry-run, 2026-06-25）

asai-dot's Project (`nixfjmwxmgugiiuqfuym`) の `d1law_taikei.alo_edges` を read-only introspect（SELECT のみ）:

- スキーマ: `edge_id bigint PK / src_uri text / edge_type text / dst_uri text / source_system text /
  source_version text / valid_from date`。
- **`edge_type` の実値は `classified_under` の1種のみ・10,823 行**（`alo:term:…` → `pending:d1law_taikei_l3:…`）
  ＝ KOS タクソノミの分類エッジ。**statute-citation edge は1本も無い。**
- 既存 CHECK `ck_d1taxo_pending_l3_not_claim_support_v20260619` が言及する edge_type は
  `claim_support / claim_proof / casebundle_evidence / legal_reasoning`（claim 系であって statute-citation ではない）。
- `d1law_taikei` 配下に `*citation*` / `*law_citation*` 等の専用テーブルは**無い**
  （alo_concept_schemes / alo_edges / alo_hubs / alo_kos_* / alo_term_* / alo_terms のみ）。

→ つまり「母屋 = canonical citation-edge」という DD-LAWTIME の前提に対し、**実体としての citation edge は未投入**。
lawtime 側の gate / side-table は**器として正しく置けるが（B′ でスキーマ GO 確認済）、中身が来るのは DDLAWREF 次第**。

## 2. lawtime 側の現状（仮置きの所在）

- gate の citation 判定は **1箇所に集約済**: `lawtime.citation_edge_type_v20260624`（view, `200_gates.sql`）。
  現在の値 = `('cites_statute','statute_ref','applies_statute')`（v0.2.3 から踏襲の placeholder）。
- 2 つの integration gate（`v_gate_lawtime_citation_edge_missing_side_table_*` /
  `v_gate_lawtime_side_table_orphan_or_noncitation_*`）はこの view を subquery 参照。
  **DDLAWREF が値を確定したら、この view 1本を書き換えるだけ**で全 gate が追従する。

## 3. DDLAWREF に確定してほしいこと

1. **statute-citation を表す `edge_type` の値**は何か？
   - 例: `cites_statute` を採るのか、別名（`law_citation` / `cites` / `references_statute` …）か、複数か。
   - lawtime は受け取った値を `citation_edge_type_v20260624` に反映するだけ（発明しない）。
2. **citation edge は `alo_edges` に載るのか**、それとも別テーブル（例 `alo_law_citation_edge`）か？
   - `alo_edges` 載せなら lawtime の現 FK（`edge_id bigint`）でそのまま接続可（B′ で型一致確認済）。
   - 別テーブルなら lawtime の FK 接続先を変える設計修正が要る（要 re-audit）。
3. **`dst_uri` の URI 規約**: statute-citation edge の `dst_uri` は `alo:law:jp:…`（lawtime resolver が解決できる形）か？
   resolver `fn_resolve_law_reference_at(work_uri, as_of)` は work_uri を入口にするため、citation edge の
   dst（被参照法令）が work URI 体系に乗っている必要がある。
4. **投入時期**: citation edge の materialize 予定（lawtime apply を先に器として置くか、足並みを揃えるか の判断材料）。

## 4. 含意（回答待ちの間の lawtime の扱い）

- **PHASE D（lawtime 本番 apply）は技術的に安全**（schema 追加のみ・既存に非破壊）だが、citation edge が
  0 の間は `citation_temporal` は空＝**実用上 inert**。「器を先に置く」価値はあるが必須ではない。
- **gate を placeholder のまま本番に出さない**こと（上記1が未確定の gate は「常に空」で誤って green に見える）。
- 有料 branch dry-run は citation edge が入るまで**得る情報が乏しい**（今は課金非推奨）。

---

## 守秘
スキーマ名・状態語彙・件数のみ。実依頼者データ本体は含めない。
