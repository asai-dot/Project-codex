# DD-LAWTIME-001 v0.2.4 — Supabase 物理配置パッチ（C-option 確定形）

> status: **candidate（design）**。production apply / Supabase materialize は **HOLD**（owner ratify 後）。
> 由来: 配置相談 RESULT `DDLAWTIME_PLACEMENT_PASS_WITH_NOTES`（Box file_id 2305621550301, 2026-06-24）。
> supersedes（設計上）: v0.2.3a 再構成 base（`001_base_v0.2.2.sql` / `010_patch_v0.2.3.sql`）の
> 独自 `lawtime.alo_edges` スタンドイン + `search_path` 追記 + text-id identity。

## 0. このパッチが変えること（v0.2.3a → v0.2.4）

監査役の C 案裁定に従い、**法令層の物理配置を作り直す**。SQL は
`migrations/lawtime/placement_v0.2.4/` に新規一式として置く（v0.2.3a の構造スモーク用 DDL は
そのまま残し、本ディレクトリが forward design）。

| 観点 | v0.2.3a（撤回） | v0.2.4（C-option 確定） |
|---|---|---|
| citation edge 本体 | 独自 `lawtime.alo_edges` スタンドイン | **既存 `d1law_taikei.alo_edges`（母屋）** を canonical に使用。lawtime は alo_edges を持たない |
| 時間評価属性 | スタンドイン edge の列 | **`lawtime.citation_temporal`（edge_id keyed 1:1 side-table）** |
| identity | text-id（`LW_minpo`） | **URI**（`alo:law:jp:` / `alo:lawrev:jp:` / `alo:lawprov:jp:`） |
| 名前解決 | DB `search_path` 末尾に `lawtime` 追記 | **追記廃止。全参照を明示 schema 修飾** |
| gate 命名 | `gate_*` | **house style `v_gate_lawtime_<predicate>_v20260624`** |
| 出口 | R-1 view（`v_lawtime_*`、lawtime schema） | **`serving` schema の current/decision view** |
| 二段 CHECK | 既存 edge に NOT VALID→backfill→VALIDATE | side-table は greenfield ゆえ **INLINE CHECK**（+ 完全性は gate） |

## 1. schema 責務（C-option）

- **`d1law_taikei`（母屋）**: URI 語彙・KOS・**canonical `alo_edges`（URI typed-edge）**。
  citation edge は `edge_type ∈ DDLAWREF 語彙` の行（`src_uri`=出典, `dst_uri`=法令URI）として
  **既存 alo_edges に載る**。lawtime は本表に**列を足さない**（narrow のまま）。
- **`lawtime`（作業棟）**: law work/revision/provision の時間軸、succession、revision mapping、
  temporal resolution run/result（eval, append-only）、unresolved queue、
  **edge_id keyed temporal side-table（`citation_temporal`）**、resolver。
- **`serving`（出口）**: LLM/MCP に渡す current/accepted/claim_support 判定済み view。
- **`public`**: 使わない。**`alo-connect`**: 使わない（動的DB予約・owner 確定）。

## 2. URI identity（blocking note #3）

| 対象 | URI 方針 | 例 |
|---|---|---|
| law work | `alo:law:jp:{law_id}` | `alo:law:jp:minpo` |
| law revision | `alo:lawrev:jp:{law_id}:{enforcement_key}` | `alo:lawrev:jp:minpo:2020` |
| provision | `alo:lawprov:jp:{law_id}:art:{article_path}:rev:{revision_key}` | `alo:lawprov:jp:minpo:art:709:rev:2020` |
| citation endpoint | 原則 URI endpoint（`src_uri`/`dst_uri`） | — |

局所 text-id（`LW_minpo`）は **staging/fixture 限定**。canonical/accepted には上げない。
各 URI 列は `CHECK (… LIKE 'alo:…:%')` で接頭辞を強制（`100_lawtime_schema.sql`）。

## 3. citation temporal side-table（C-option core）

`lawtime.citation_temporal`（PK=`edge_id` → `d1law_taikei.alo_edges(edge_id)` ON DELETE CASCADE）。
監査役 §2.3 の保持属性をすべて持つ:
`as_of_basis / as_of_date / source_law_revision_uri / target_law_revision_uri /
resolved_revision_confidence / temporal_status / temporal_caveat / claim_support_eligible /
resolution_method / evidence_pointer / parser_version / created_at`。

**FK / reference policy（blocking note #6）**:
- side-table 行は **statute-citation edge にのみ 1:1** で存在する（不変条件）。
- edge が canonical fact、side-table は time-evaluation。edge を消すと評価も消える（CASCADE）。
- `target_law_revision_uri` / `source_law_revision_uri` は `lawtime.law_revision(revision_uri)` 参照。
- 二段ルールは **INLINE CHECK `ck_ct_two_tier`**（全行が citation ゆえ edge_type 参照不要）。
- 横断完全性（citation edge ↔ side-table 1:1、非 citation edge への混入禁止）は
  `v_gate_lawtime_citation_edge_missing_side_table_*` / `..._side_table_orphan_or_noncitation_*` が 0 件保証。

## 4. gate（house style, `200_gates.sql`）

| gate | 由来 | 検出する異常 | 失敗時の owner action |
|---|---|---|---|
| `v_gate_lawtime_citation_edge_missing_side_table_v20260624` | C-INT | citation edge に side-table 行が無い | resolver 再走 or unresolved_queue 投入 |
| `v_gate_lawtime_side_table_orphan_or_noncitation_v20260624` | C-INT | side-table 行が孤児 / 非 citation edge を指す | 行削除 or edge_type 是正 |
| `v_gate_lawtime_resolved_revision_covers_asof_v20260624` | P0-2 | as_of が解決版の区間外 | 版再解決（resolution_method 見直し） |
| `v_gate_lawtime_claim_support_requires_resolved_v20260624` | P0-3 | claim_support=true が条件未充足 | eligible を false に戻す/条件充足 |
| `v_gate_lawtime_succession_no_ambiguous_overlap_v20260624` | P0-4 | tier1 多重マッチ（曖昧 succession） | lineage_event_id 付与 or confidence 降格 |
| `v_gate_lawtime_work_single_fallback_law_id_v20260624` | N-1 | succession 不在 work が複数 law_id | succession 明示 or 版整理 |
| `v_gate_lawtime_statute_revision_no_ambiguous_overlap_v20260624` | N-2 | 同一 law_id 版区間の重なり | 区間是正 |
| `v_gate_lawtime_formal_status_inconsistent_v20260624` | N-3/N-4 | CurrentEnforced 重複 / Repeal 同居 | corpus 状態語の再マップ |

全 8 gate を `verify_dry_run.sql` が 0 件 assert。`violations.sql` が各 1 件検知を確認
（スモーク 1/1/1…）。

## 5. serving 出口 + claim_support 統合（truth table, blocking note #7）

`300_serving.sql`:
- `serving.lawtime_formal_status_current(law_id, formal_status, current_from)` — `v_lawtime_formal_status` 互換列。
- `serving.lawtime_resolved_ref_current(edge_id, citing_uri, cited_law_work_uri, as_of_basis,
  as_of_date, target_law_revision_uri, temporal_status, temporal_caveat, lawtime_resolved)`
  — 母屋 edge ⨝ side-table。`v_lawtime_resolved_ref` 互換（endpoint は URI）。
- `serving.lawtime_claim_support_decision` — lawtime 寄与分の **truth table**:

| resolved | status_ok | caveat_ok | eval_present | **lawtime_serve** |
|:--:|:--:|:--:|:--:|:--:|
| F | * | * | * | **F** |
| T | F | * | * | **F** |
| T | T | F | * | **F** |
| T | T | T | F | **F** |
| T | T | T | T | **T** |

最終 claim_support = `lawtime_serve` ∧ **d1law_taikei pending 除外**
（`v_gate_d1taxo_pending_l3_excluded_from_claim_support_v20260619` 空）∧
**DD-LAWSUBTRANS**（accepted ∧ ¬disputed ∧ evidence_pointer 在）。後二者は各層所有で重複実装しない。

## 6. search_path 廃止と DD-LAWSUBTRANS 接続契約（blocking note #2）

`ALTER DATABASE … SET search_path` は**廃止**。全参照を明示修飾。これに伴い lawsubtrans の
非修飾参照は新しい接続契約へ張り替える:

| lawsubtrans 旧（非修飾） | v0.2.4 新（明示修飾） |
|---|---|
| `v_lawtime_formal_status` | `serving.lawtime_formal_status_current` |
| `v_lawtime_resolved_ref` | `serving.lawtime_resolved_ref_current` |
| `alo_statutes` | `lawtime.law_revision`（law_id 経由で突合） |

⚠️ lawsubtrans gate の張り替えは **DD-LAWSUBTRANS 側の後続変更**で、lawtime placement ratify を
trigger に行う（本 lawtime-scoped パッチでは行わない）。identity 整合（lawsubtrans の text
`law_work_id` ↔ canonical URI）も同後続で扱う。

## 7. edge_type 語彙と DDLAWREF（blocking note #5）

`edge_type` の**最終語彙は DDLAWREF 所有**。lawtime は勝手に増やさない。本パッチの citation 述語は
v0.2.3 から持ち越した `('cites_statute','statute_ref','applies_statute')` のみ（200_gates 冒頭で集中定義）。
production 前に DDLAWREF taxonomy と reconcile すること（監査役 §3.1 候補
`cites_statute / delegates_to / implements / references / authority_basis` は**未採用＝要 DDLAWREF 確定**）。

## 8. migration 形態（blocking note #8）

配置 ratify 後、`supabase_migrations` の timestamp migration（`create_lawtime_schema` /
`create_lawtime_serving` 等）として出す。**ただし materialize / production apply は別ゲート（HOLD）**。
既存 `d1law_taikei.alo_edges` への影響範囲 inventory（blocking note #4）は materialize 前に固定:
本パッチは alo_edges に**列を足さず・触らない**（side-table と FK 参照のみ）ので、既存行への
DDL 影響はゼロ。唯一の結合は新規 FK（`citation_temporal.edge_id`, `temporal_eval_event.edge_id`,
`unresolved_queue.edge_id` → `alo_edges.edge_id`）で、これは参照のみ。

## 9. ローカル構造スモーク（課金なし）

`migrations/lawtime/placement_v0.2.4/smoke_placement.sh`（throwaway PG16, self-contained）:
母屋 fixture → lawtime → gates → serving → clean seed → verify(8 gate 空) →
golden resolver sample（should_fix #3）→ serving sanity → planted violations(各 1 検知) →
guards(eval append-only ×2 / 二段 CHECK / 母屋 FK / URI CHECK = 全 RAISE)。
結果: **STRUCTURAL SMOKE OK**。source_hash(000+100+200+300) = `79f300d60818`。

## 10. 残 HOLD（ratify 後 / 別ゲート）

- production apply / Supabase materialize / canonical / claim_support serving。
- DD-LAWSUBTRANS の接続張り替え + identity URI 整合。
- DDLAWREF edge_type 語彙の確定と reconcile。
- 既存 `d1law_taikei.alo_edges` 実データへの side-table backfill 手順（materialize dry-run）。

## 11. 監査 v0.2.4 RESULT の Notes 反映（DDLAWTIME_V024_PLACEMENT_PASS_WITH_NOTES, 2026-06-25, file_id 2306481004211）

判定 **PASS_WITH_NOTES / materialize branch dry-run へ GO**（branch/local/fixture/smoke 範囲限定。
実 Supabase apply は HOLD）。8 blocking notes は全て PASS / PASS_WITH_NOTES。追加 Notes 3 件を以下に反映:

- **N1（schema 名 lawtime / lawref 分離）**: schema 名 `lawtime` は当面許容。将来 `lawref` が**上位正本語彙**として
  正本化する場合は、`lawtime`=作業棟（時間軸評価）、`lawref`=正本語彙、に**分離**する。
  ⇒ 本パッチは `lawtime` 単一で進めるが、URI 語彙正本（§2/§7）は DDLAWREF/`lawref` 確定で再同期する余地を残す。
- **N2（ON DELETE CASCADE の削除運用）**: 母屋 edge 削除時に `citation_temporal` の時間評価も消える。
  local smoke は CASCADE で可。**production の削除運用は別途確定が必要**（候補: ①`ON DELETE RESTRICT`＋明示アーカイブ、
  ②CASCADE 継続＋eval は append-only ログで履歴保全）。**materialize-gate 項目**として保留（blocking note #4 の
  「production FK は別 gate で負荷・権限・削除方針を再確認」と統合）。本パッチでは smoke の CASCADE を据え置き、
  production DDL 確定時に判断する。
- **N3（C-INT-1/2 を必須受入条件に）**: `v_gate_lawtime_citation_edge_missing_side_table_*` と
  `v_gate_lawtime_side_table_orphan_or_noncitation_*` が **0 件であることを materialize branch dry-run の
  必須受入条件**とする（INLINE 二段 CHECK が「全 side-table 行 = citation edge」前提に依存するため）。
  ⇒ `verify_dry_run.sql` は既に 8 gate を assert 済。README / owner-ratify packet に「C-INT-1/2 = 必須」を明記。

### materialize branch dry-run の受入条件（GO 範囲・課金は owner 判断）
1. 8 gate（C-INT-1/2 必須含む）全空。 2. golden resolver 6 行一致（`sample_resolver.sql`）。
3. serving truth table の fixture validation。 4. guard 5 件 RAISE。
※ 実 Supabase **branch** での dry-run は課金が伴うため、owner の明示 GO まで**ローカル fixture smoke で代替**。
