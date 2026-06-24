# DD-LAWTIME-001 v0.2.4 — owner ratify packet（C-option / 配置確定）

> 目的: owner（asai）が **v0.2.4 C-option の設計を ratify するか**を、1 枚で判断できるようにまとめた決裁パケット。
> 監査は通過済（PASS_WITH_NOTES, materialize branch dry-run へ GO）。**本番 DB には未着手・課金なし**。
> 検証は**ローカル fixture smoke のみ**（owner 方針: Supabase に触れる前に owner ratify / 課金なし）。

## 0. この ratify が「許可すること / しないこと」

**ratify が許可すること（design 確定）**
- `migrations/lawtime/placement_v0.2.4/` を lawtime 配置の**確定設計**として採用。
- 以降の派生（materialize 手順書・owner-ratify 後の branch 計画）を v0.2.4 を基準に進める。
- v0.2.3a の独自 `lawtime.alo_edges` スタンドイン／search_path 追記／text-id を**正式に廃止**扱いにする。

**ratify が許可しないこと（HOLD 継続・別決裁が要る）**
- ❌ production apply / Supabase 本番反映 / canonical promotion / claim_support serving / MCP publication。
- ❌ 実 Supabase branch での dry-run（**課金あり**。別途 owner の明示 GO が要る）。
- ❌ DDLAWREF edge_type 正本確定 / lawsubtrans 接続張り替え。

## 1. 何を決めたか（C-option 一言）

法令の citation（出典→法令）の**本体は既存 `d1law_taikei.alo_edges`（母屋）**に置き、**時間評価属性だけ**を
`lawtime.citation_temporal`（edge_id 1:1 side-table）に持つ。identity は URI、名前解決は明示 schema 修飾、
出口は `serving` schema、品質は house-style gate 8 本で 0 件保証。詳細は
[`DD-LAWTIME-001_v0.2.4_placement.md`](./DD-LAWTIME-001_v0.2.4_placement.md)。

## 2. 監査トレイル（往復の確定記録）

| 監査 | RESULT label | Box file_id | 要旨 |
|---|---|---|---|
| v0.2.3a notes closed | `DDLAWTIME_PASS_WITH_NOTES` | 2304093933196 | must_fix#1-4 / N-1〜N-4 閉鎖。should_fix #1/#2/#3 提示 |
| 配置相談 | `DDLAWTIME_PLACEMENT_PASS_WITH_NOTES` | 2305621550301 | **C-option 裁定** + 8 blocking notes |
| v0.2.4 実装 | `DDLAWTIME_V024_PLACEMENT_PASS_WITH_NOTES` | 2306481004211 | C-option 採用可・**branch dry-run へ GO**・追加 Notes 3 |

8 blocking notes は全件 PASS / PASS_WITH_NOTES。should_fix #1/#2/#3 反映済（COVERAGE/README/sample_resolver）。

## 3. 受入証跡（ローカル fixture smoke / 課金なし）

実行: `bash migrations/lawtime/placement_v0.2.4/smoke_placement.sh`（throwaway PG16, self-contained）
生ログ: [`evidence/smoke_run.log`](../../migrations/lawtime/placement_v0.2.4/evidence/smoke_run.log)（commit に同梱）。
source_hash(000+100+200+300) = `79f300d60818`。結果 = **STRUCTURAL SMOKE OK**。

**(a) 8 gate 全空（clean seed）— C-INT-1/2 を含む（監査 Note N3 の必須受入条件）**
```
v_gate_lawtime_citation_edge_missing_side_table_v20260624  => 0   ← C-INT-1（必須）
v_gate_lawtime_side_table_orphan_or_noncitation_v20260624  => 0   ← C-INT-2（必須）
v_gate_lawtime_resolved_revision_covers_asof_v20260624     => 0   (P0-2)
v_gate_lawtime_claim_support_requires_resolved_v20260624   => 0   (P0-3)
v_gate_lawtime_succession_no_ambiguous_overlap_v20260624   => 0   (P0-4)
v_gate_lawtime_work_single_fallback_law_id_v20260624       => 0   (N-1)
v_gate_lawtime_statute_revision_no_ambiguous_overlap_v20260624 => 0 (N-2)
v_gate_lawtime_formal_status_inconsistent_v20260624        => 0   (N-3/N-4)
=> ALL LAWTIME v0.2.4 GATES EMPTY — dry-run PASS
```

**(b) golden resolver 6 行（should_fix #3。半開区間と施行前 null を確認）**
```
alo:law:jp:minpo   | 1900-01-01 | alo:lawrev:jp:minpo:1898
alo:law:jp:minpo   | 2019-12-31 | alo:lawrev:jp:minpo:1898
alo:law:jp:minpo   | 2020-04-01 | alo:lawrev:jp:minpo:2020   ← [from,to) 境界 = 新版
alo:law:jp:minpo   | 2025-01-01 | alo:lawrev:jp:minpo:2020
alo:law:jp:shotaku | 1990-01-01 | <null>                     ← 施行前 = 解決なし
alo:law:jp:shotaku | 2000-01-01 | alo:lawrev:jp:shotaku:1991
```

**(c) serving claim_support truth table（責務分離: lawtime は lawtime_serve まで）**
```
edge_id | resolved | status_ok | caveat_ok | eval_present | lawtime_serve
   1    |   t      |   t       |   t       |   t          |   t
   2    |   t      |   t       |   t       |   t          |   t
   3    |   f      |   f       |   t       |   f          |   f   ← unknown-basis citation は serve 不可
```

**(d) 仕込み違反 8 件 → 各 gate が 1 件検知（検出力）**: citation_edge_missing_side_table / side_table_orphan_or_noncitation /
resolved_revision_covers_asof / claim_support_requires_resolved / succession_no_ambiguous_overlap /
work_single_fallback_law_id / statute_revision_no_ambiguous_overlap / formal_status_inconsistent = 各 1。

**(e) guard 5 件すべて RAISE**: eval append-only(UPDATE/DELETE) / 二段 INLINE CHECK(ck_ct_two_tier) /
母屋 FK(citation_temporal_edge_id_fkey) / URI CHECK(ck_law_work_uri)。

## 4. 既存本番データへの影響（materialize 前提・今は未実行）

- `d1law_taikei.alo_edges` に**列を足さない・触らない**（side-table + FK 参照のみ）。既存行への DDL 影響ゼロ。
- 新規 FK は `citation_temporal.edge_id` / `temporal_eval_event.edge_id` / `unresolved_queue.edge_id`
  → `alo_edges.edge_id`（参照のみ）。
- `alo-connect`（空）は不使用のまま（動的DB予約）。`public` 不使用。

## 5. ratify 後に残る OPEN 項目（materialize gate / 別決裁）

| # | 項目 | 由来 | 扱い |
|---|---|---|---|
| O1 | 母屋 edge 削除時の `ON DELETE CASCADE` 運用（RESTRICT＋archive か CASCADE＋append-only 保全か） | Note N2 / blocking #4 | production DDL 確定時に判断。smoke は CASCADE 据え置き |
| O2 | production FK の負荷・権限・削除方針の再確認 | blocking #4 | materialize 別 gate |
| O3 | DDLAWREF edge_type 正本確定後の語彙同期（現状 3 値暫定） | Note / blocking #5 | DDLAWREF 確定待ち |
| O4 | `lawref` が上位正本化する場合の lawtime(作業棟)/lawref(正本) 分離 | Note N1 | 将来オプション |
| O5 | DD-LAWSUBTRANS の接続張り替え（`v_lawtime_*`→`serving.lawtime_*_current`）+ identity URI 整合 | 設計書 §6 | lawtime ratify を trigger に DD-LAWSUBTRANS 側で |
| O6 | 実 corpus での `revision_status` 状態機械の最終照合（N-3 強化） | v0.2.3a 残 | materialize dry-run |

## 6. owner 決裁欄

- [ ] **A. v0.2.4 C-option 設計を ratify する**（design 確定。HOLD ラインは §0 のまま維持）。
- [ ] **B. 修正を要する**（指摘 → design スコープで対応し再提出）。
- [ ] **C. 保留**（このまま据え置き）。

> ratify されても、§0 の HOLD（production apply / Supabase 本番反映 / branch 課金 dry-run / canonical /
> claim_support / DDLAWREF / lawsubtrans 張り替え）には**進みません**。それぞれ別途あなたの明示 GO が要ります。

---
記録: 監査 RESULT 2306481004211 / 実装 commit `90f9d8f` / 証跡 commit は本パケット同梱コミット。
