---
request_id: 20260624_lawtime_supabase_placement_DDLAWTIME
topic: lawtime / lawsubtrans — Supabase 物理配置（どのproject/schemaに何を置くか）
gate: DDLAWTIME
version: placement consultation (pre-materialize)
related:
  - 20260623_lawtime_v0.2.3a_notes_closed_DDLAWTIME (gate/coverage 監査・並行中)
git_branch: claude/lawsubtrans-production-deploy-b15nmp
git_pr: https://github.com/asai-dot/Project-codex/pull/34
target_mode: placement_design   # 本番 apply ではない。配置の妥当性ratify。materialize は HOLD のまま。
box_request_file_id: 2305223370418   # gpt_ometsuke/to_gpt/ に投函済
decision_owner_fixed: |
  owner 決定（2026-06-24）で確定済・再監査不要の点:
   - project は asai-dot's Project（ref nixfjmwxmgugiiuqfuym）。d1law_taikei と同居が正しい。
   - alo-connect（ref vlsunmqpjhzbhipiehzs）は空のまま空けておく（動的DB用に予約。法令層を置かない）。
  ⇒ 相談は「asai-dot's Project の どの schema に・どんな形で lawtime/lawsubtrans を置くか」に限定。
status: answered   # RESULT=DDLAWTIME_PLACEMENT_PASS_WITH_NOTES (file_id 2305621550301, 2026-06-24)。
                   # C-option 採用 + 8 blocking notes。実装は v0.2.4 で着地 → superseded_by:
                   #   docs/dd/20260624_lawtime_v0.2.4_placement_DDLAWTIME_REQUEST.md
                   #   (実装 commit 90f9d8f / migrations/lawtime/placement_v0.2.4/)
---

# GPT Pro 相談: lawtime/lawsubtrans の Supabase 物理配置（schema 設計）

## 0. なぜこの相談か（重大な前提崩れ）
これまでの再構成 REQUEST は「法令層はどこにも未 materialize＝グリーンフィールド」「`alo_edges` は
どこにも無いので最小スタンドインを自前生成」を前提にしていた。**この前提は誤りだった。**
2026-06-24 に asai-dot's Project を実地確認したところ、**`d1law_taikei` schema に既に本物の
`alo_edges` を含む alo_* 一式が存在**する。owner も「置き間違っていないか」を懸念。実態に基づき配置を相談したい。

## 1. asai-dot's Project の実態（read-only 確認 2026-06-24）
domain schema（抜粋・テーブル数）: `d1law_taikei`(11+2view), `biblio`(13), `dynamic`(14),
`authority`(10), `bookdx`(7), `control`(6), `staging_periodical`(6), `formobj`(5),
`serving`(view 2), `public`(view 1)。migration は `supabase_migrations` で timestamp 管理
（`create_dynamic_schema_core` / `create_bookdx_schema` 等、新schema は migration で導入）。

### 1.1 既存 `d1law_taikei`（＝D1 法令体系 KOS）
- tables: `alo_terms, alo_term_labels, alo_term_relations, alo_term_observation,
  alo_concept_schemes, alo_hubs, alo_hub_memberships, alo_kos_snapshot, alo_kos_item_extra,
  alo_d1law_taikei_extra, alo_edges`。
- identity は URI ベース: `alo_terms.term_uri`(text), `notation, scheme_id, source_item_key,
  source_version, status, term_tier, term_id(bigint surrogate)`。
- `d1law_taikei.alo_edges` の実列: `edge_id bigint, src_uri text NOT NULL, edge_type text NOT NULL,
  dst_uri text NOT NULL, source_system text, source_version text, valid_from date`。
  ⇒ URI→URI の汎用 typed-edge グラフ。`cited_law_id / as_of_basis / resolved_law_revision_id /
  temporal_status / claim_support_eligible` 等は持たない。
- 既存の claim_support gate: `v_gate_d1taxo_pending_l3_excluded_from_claim_support_v20260619`
  （`alo_edges→alo_terms→alo_d1law_taikei_extra` を join し、`dst_uri ~ 'pending:d1law_taikei_l3:%'`
  の edge を claim_support から除外）。「gate view + claim_support 除外」「serving schema の _current/_accepted view」
  の流儀が既に確立している。

## 2. 再構成案（migrations/lawtime/*）が実態とぶつかる3点
1. 名前衝突: 再構成は新 `lawtime` schema 内に独自の `alo_edges` を作る。本物は `d1law_taikei.alo_edges`。
   同名 2 つ＋`001_base` 末尾の search_path 末尾追記（"$user",public,lawtime）で、非修飾 `alo_edges` の
   解決先が search_path 依存で曖昧化する footgun。
2. identity モデル不一致: 再構成は `law_work_id='LW_minpo'` 等の不透明 text-id。実態は URI
   （`term_uri`, `src_uri/dst_uri`, `pending:...:` 接頭辞）。統合するなら URI 採番に寄せる必要。
3. 既存パターンの再発明: claim_support gate / serving current-view を、再構成は d1law_taikei の既存流儀を
   知らずに別実装した（`gate_*` 命名・`v_gate_..._v<date>`・serving schema を踏襲していない）。

## 3. 配置オプション（recommendation 付き）
- A（推奨: 既存層へ統合）: lawtime/lawsubtrans を d1law_taikei の alo_* モデルに統合。
  statute-citation は既存 `d1law_taikei.alo_edges` の行（`edge_type='cites_statute'`,
  src_uri=出典uri, dst_uri=法令uri）で表し、版解決の temporal/claim_support 属性は
  edge_id をキーにした lawtime 側 side-table に持つ（narrow な共有 alo_edges に列追加しない）。
  statute 時間軸（alo_statutes/succession/eval）は d1law_taikei に alo_* 命名で追加。
  gate/serving は既存流儀（`v_gate_..._v<date>` / serving schema）に合わせる。
  → 利点: 単一 canonical edge 層・URI 一貫・既存 gate と整合。欠点: d1law_taikei に相乗りで隔離性は下がる。
- B（別 schema＋実 edge 参照）: `lawtime`/`lawsubtrans` を別 schema に隔離するが、スタンドイン
  `alo_edges` は廃止し、citation は `d1law_taikei.alo_edges` を跨ぎ参照、temporal 属性のみ別 schema に。
  search_path 追記は廃止し全参照を明示修飾。→ 利点: drop 容易。欠点: 跨ぎ FK/参照運用が増える。
- C（折衷）: statute 時間軸（新規概念）は `lawtime` schema、citation-edge は `d1law_taikei.alo_edges`＋
  lawtime side-table。A と B の中間。

実装側の暫定見解は A or C。理由: 本物の `alo_edges` が URI-edge の単一層として既に機能し、
claim_support gate もそこに集約されているため、citation を別 alo_edges に二重化するのは canonical を割る。

## 4. decision_requested
1. schema 配置: A / B / C のどれで進めるべきか（別案可）。特に「statute-citation を既存 `d1law_taikei.alo_edges`
   の行として持つ」案の是非。
2. alo_edges の扱い: 再構成の独自 `alo_edges` は廃止でよいか（temporal 属性は edge_id keyed side-table へ）。
3. identity: lawtime の work/revision を URI 採番（term_uri 流儀）に寄せるべきか。語彙例の指定があれば欲しい。
4. search_path 追記の廃止: 実 alo_edges がある以上、非修飾解決は危険。明示スキーマ修飾に統一で正しいか。
5. gate/serving 流儀: 既存 `v_gate_..._v<date>` / `serving` schema に合わせるべきか（再構成の `gate_*` は改名するか）。
6. migration 形態: 配置確定後、`supabase_migrations` に乗せる timestamp migration（`create_lawtime_*` 等）として
   出すべきか。materialize 自体は引き続き HOLD（owner ratify 後）でよいか。

## 5. 固定事項（再監査不要）
- project = asai-dot's Project（d1law_taikei 同居）。alo-connect は空のまま（動的DB予約）。
- production apply / materialize / canonical / claim_support serving は HOLD 継続。

## 6. 守秘
schema 名・列名・状態語彙・件数レベルのみ。実依頼者データなし。
