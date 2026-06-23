---
request_id: 20260623_lawtime_placement_consult_DDLAWTIME
topic: lawtime / placement (どのproject・どのschemaに何を置くか)
gate: DDLAWTIME
version: placement consultation (v0.2.3a の materialize 前提を訂正)
supersedes_decision_of: 20260623_lawtime_v0.2.3a_notes_closed_DDLAWTIME   # materialize-readiness の判断は本件解決まで HOLD
git_branch: claude/lawsubtrans-production-deploy-b15nmp
git_pr: https://github.com/asai-dot/Project-codex/pull/34
target_mode: placement_consult   # 設計配置の相談。apply/材料化はしない。
status: queued   # owner 指示で gpt_ometsuke/to_gpt/ に投函
materialization_finding_CORRECTION: |
  ⚠️ 前 REQUEST（v0.2.3 / v0.2.3a）の「法令レイヤは未 materialize ＝完全グリーンフィールド、
  alo_edges はどこにも無い」という前提は **実地確認の結果まちがいだった**。本 REQUEST がそれを訂正する。
  v0.2.3a の materialize-readiness 監査は、本 placement が決まるまで保留してほしい。
---

# GPT Pro 相談: DD-LAWTIME を Supabase の「どこに」置くか（置き間違いの確認）

owner（asai）から「Supabase のどこに何を置くのか、置き間違っていないか、監査役とよく相談せよ」との指示。
2026-06-23 に**実 DB を読み取り専用で棚卸し**した結果、前提が崩れたので相談する。apply はしない。

## A. 実地で判明した事実（read-only inventory, 2026-06-23）

### プロジェクトは 2 つ
| project | ref | 実体 |
|---|---|---|
| **asai-dot's Project** | `nixfjmwxmgugiiuqfuym` | 本番ウェアハウス。下記ドメインスキーマ群が稼働中 |
| **alo-connect** | `vlsunmqpjhzbhipiehzs` | **空**（public のみ・オブジェクト 0）。用途未定 |

### asai-dot's Project のスキーマ（非システムのみ）
`d1law_taikei`(11t/2v), `biblio`(13t), `authority`(10t), `dynamic`(14t/2v),
`bookdx`(7t), `control`(6t), `staging_periodical`(6t/7v), `formobj`(5t), `serving`(2v), `public`(0t).

### 核心: `d1law_taikei` は既に存在する ALO/法令体系（D1 KOS）レイヤ
テーブル: `alo_concept_schemes, alo_hubs, alo_hub_memberships, alo_terms, alo_term_labels,
alo_term_relations, alo_term_observation, alo_kos_snapshot, alo_kos_item_extra,
alo_d1law_taikei_extra, **alo_edges**`。
gate view: `v_gate_d1taxo_pending_l3_excluded_from_claim_support_v20260619`,
`v_d1taxo_pending_l3_unresolved_counts_v20260619`。
`alo_concept_schemes.claim_support_eligible boolean` も既存（＝ claim_support 統制が既にこの層にある）。

### 既存 `d1law_taikei.alo_edges` の実体（DD-LAWTIME の想定と別物）
- 列: `edge_id, src_uri, edge_type, dst_uri, source_system, source_version, valid_from(date)`。
- 中身: **10,823 行すべて `edge_type='classified_under'`**（`alo:term:d1law-taikei:…` → `pending:d1law_taikei_l3:…`）。
  ＝ **KOS タクソノミの分類エッジ**。statute citation 用の列
  （as_of_basis / as_of_date / resolved_law_revision_id / temporal_status / temporal_caveat /
   claim_support_eligible / cited_law_*）は**一切持たない**。

### 一方、statute/version/succession/temporal 層は本当に存在しない
`statut|law_work|law_revision|succession|lawtime|temporal|enforce|repeal` に当たる
テーブル/列は**どのスキーマにも 0 件**。ここは真にグリーンフィールド。

## B. これがなぜ「置き間違い」の疑いなのか

PR #34 の再構成（`migrations/lawtime/`）は、上記を知らずに次の前提で作った:
「alo_edges はどこにも無い → lawtime スキーマ内に**最小スタンドインとして alo_edges を自前生成**」。

実際には:
1. `alo_edges` という名前は **d1law_taikei に実在**し、しかも**全く別形・別用途（KOS 分類エッジ・1万行）**。
   → 新スキーマ `lawtime` にもう一つ別形の `alo_edges` を作るのは、**同名・別実体の衝突**で危険。
2. DD-LAWTIME 設計が言う「D2 edge レイヤ alo_edges に temporal 列を足す」相手の実テーブルが、
   この KOS `alo_edges` を指しているのか、**別の未作成テーブル**を指すのかが**未確定**。
3. 既存 D1（d1law_taikei）には claim_support 統制（列 + v_gate_…_claim_support）が**既にある**。
   lawtime/lawsubtrans 側で**並行に別の claim_support 機構**を建てると二重統制になる恐れ。

## C. 監査役に相談したい点（owner の「置き間違い」確認）

1. **どの project か**: 法令時間軸（lawtime）+ lawsubtrans は、`d1law_taikei` のある
   **asai-dot's Project** に同居させるべきで合っているか。空の **alo-connect** は何用か（別用途なら明文化したい）。
2. **どの schema か / alo_edges の正体**: DD-LAWTIME の「D2 alo_edges（temporal 列つき）」は
   - (a) 既存 `d1law_taikei.alo_edges`（KOS 分類エッジ）に edge_type を増やし temporal 列を**ALTER で足す**のが正本か、
   - (b) それとは別の**新テーブル**（例 `alo_law_citation_edge`）を建て、名前衝突を避けるのが正本か、
   - (c) lawtime を **d1law_taikei 内**に置くのか、**別スキーマ（例 d2law / lawref）**で d1law_taikei を参照するのか。
   どれが v0.2.x 正本設計の意図か。**(a) は 1 万行の生 KOS テーブルへの重い変更**になる点も含め判断がほしい。
3. **statute/succession/temporal-eval/resolver の置き場所**: これは真に未作成。
   d1law_taikei に同居か、専用スキーマで d1law_taikei.alo_terms / alo_edges を URI 参照するか。
4. **claim_support の一元化**: 既存 `d1law_taikei` の claim_support_eligible + v_gate_…_claim_support と、
   lawsubtrans/lawtime の claim_support gate を**統合**すべきか、層ごとに分離して良いか。
5. **命名規約**: 既存は `v_gate_<domain>_<predicate>_v<date>`。再構成は `gate_<predicate>`。house style に寄せるべきか。
6. 上記が決まるまで **v0.2.3a の materialize-readiness（GO/HOLD）判断は保留**で良いか。

## D. 添付したい現状（参考）
- 再構成物: `migrations/lawtime/{001_base_v0.2.2,010_patch_v0.2.3,verify_dry_run}.sql` + `COVERAGE.md`（commit c4f4ecb 系）。
  ※これは「グリーンフィールド前提」で書かれており、本相談の結論次第で**配置・名前の作り直し**があり得る。
- 正本 patch doc: `docs/dd/DD-LAWTIME-001_v0.2.3_production_patch.md`。

## 守秘
スキーマ名・状態語彙・件数のみ。実依頼者データ本体は含めない。
