# DD-LAWTIME-001 v0.2.4 — materialize runbook（実DB反映 手順書）

> status: **DRAFT runbook（課金ゼロ・実行待ち）**。本書は「確定設計 v0.2.4 を実 Supabase に載せる時の段取り」を
> 文書化したもの。**本書を書いた時点では DB 操作は一切していない**（Supabase 未接触・課金ゼロ）。
> 各 PHASE は **owner の明示 GO がある時だけ**実行する。GO 無しに次の PHASE へ進まない。
>
> - 確定設計: [`DD-LAWTIME-001_v0.2.4_placement.md`](./DD-LAWTIME-001_v0.2.4_placement.md)（RATIFIED 2026-06-25）
> - owner 決裁: [`DD-LAWTIME-001_v0.2.4_owner_ratify_packet.md`](./DD-LAWTIME-001_v0.2.4_owner_ratify_packet.md) §6（A ratify）
> - 対象 SQL: `migrations/lawtime/placement_v0.2.4/`
> - 監査: RESULT `DDLAWTIME_V024_PLACEMENT_PASS_WITH_NOTES`（Box file_id 2306481004211）

---

## 0. このページの読み方（HOLD の地図）

確定したのは「**設計**」だけ。実 DB に触る操作は全部この先で、各々に**別の鍵（owner GO）**が要る。

| PHASE | 何をする | 課金 | 鍵（owner GO） | 取消可否 |
|---|---|---|---|---|
| **A. 事前確認** | 母屋 `d1law_taikei.alo_edges` の現況を read-only 確認 | 無 | 不要（read-only） | — |
| **B′. 課金ゼロ dry-run** | 母屋を read-only introspect → fixture を実物に合わせ → ローカル smoke 再実行 | **無** | read-only 許可のみ（課金 GO 不要） | local（戻す概念なし） |
| **B. branch dry-run（任意）** | Supabase の **preview branch** を作り、そこへ 100/200/300 を apply して gate を回す | **有（branch 課金）** | **要：課金 GO** | branch 削除で戻せる |
| **C. 受入判定** | 8 gate 空 + C-INT-1/2 + golden resolver diff を確認 | 無 | 不要（判定のみ） | — |
| **D. 本番 apply** | 確定設計を **production** に migration 適用 | （branch 課金は無、本番は通常） | **要：本番 apply GO** | rollback SQL 要（§7） |
| **E. 出口接続** | DD-LAWSUBTRANS を serving.* に張り替え | 無〜小 | **要：張り替え GO** | revert 可 |

> ✅ **O1 確定（A 統一RESTRICT, owner 2026-06-25）**: `citation_temporal` / `unresolved_queue` の
> `alo_edges(edge_id)` への FK は **`ON DELETE RESTRICT`**（設計反映済）。母屋 edge は lawtime が参照中は
> 削除できず、**先に lawtime 側を片付ける**運用（§7 D-5 の掃除順）。詳細: [`..._O1_decision.md`](./DD-LAWTIME-001_v0.2.4_O1_decision.md)。

---

## 1. スコープ：何を apply し、何を apply しないか

`placement_v0.2.4/` の中で **本番に apply するのは 3 ファイルだけ**：

| ファイル | 本番 apply | 役割 |
|---|---|---|
| `000_external_dependency_d1law_taikei.sql` | ❌ **しない** | 母屋を**ローカル smoke 用に模す** fixture。本番では母屋は既存。 |
| `100_lawtime_schema.sql` | ✅ する | lawtime 作業棟（works/revisions/succession/mapping/`citation_temporal` サイドテーブル/`temporal_eval_event`/`unresolved_queue`/`fn_resolve_law_reference_at`） |
| `200_gates.sql` | ✅ する | house-style 品質 gate 8 本（`v_gate_lawtime_*_v20260624`） |
| `300_serving.sql` | ✅ する | 出口 view 3 本（`serving.lawtime_formal_status_current` / `lawtime_resolved_ref_current` / `lawtime_claim_support_decision`） |
| `seed_clean.sql` / `sample_resolver.sql` / `violations.sql` / `verify_dry_run.sql` / `smoke_placement.sh` | ❌ 本番では使わない | dry-run/smoke 用。branch では verify に使う（§4）。 |

**前提**：本番には `d1law_taikei.alo_edges`（canonical citation-edge / 母屋）が既存。
100 の `citation_temporal` / `unresolved_queue` はその `edge_id` を FK 参照する。母屋が無い環境に 100 を当ててはいけない。

---

## 2. PHASE A — 事前確認（read-only・課金なし）

owner GO 不要。Supabase MCP の read 系のみ。

1. プロジェクト確認: `list_projects` → 対象 project_id を控える（本書では `<PROJECT_ID>`）。
2. 母屋の存在: `list_tables`（schema=`d1law_taikei`）で `alo_edges` があること、`edge_id` 主キーの型を確認。
3. 衝突確認: `list_tables`（schema=`lawtime` / `serving`）。
   - `lawtime` スキーマ・本書が作る table 名が**既存でないこと**。
   - `serving` に同名 view（旧 v0.2.3a の `v_lawtime_formal_status` 等）が**残っていないこと**。残っていれば §6 の置換メモへ。
4. advisor: `get_advisors`（security / performance）で既存の未対応指摘を控える（apply 後の差分判定の基準線）。

**A 終了条件**：母屋あり／lawtime・serving に名前衝突なし／基準線 advisor を記録。1つでも崩れたら停止して owner に報告。

---

## 3. 母屋ファースト原則（apply 順の絶対則）

apply は必ずこの順。**100 の前に母屋が無いと FK が張れない**。

```
（母屋 d1law_taikei.alo_edges：既存・触らない）
  └─ 100_lawtime_schema.sql      … 作業棟 + FK(edge_id) ON DELETE CASCADE
       └─ 200_gates.sql          … gate view（100 のオブジェクトに依存）
            └─ 300_serving.sql   … 出口 view（100/200 に依存）
```

`apply_migration` は1ファイル=1 migration で、上から順に。途中失敗したら**その時点で停止**（後続を当てない）。

---

## 4. PHASE B′ — 課金ゼロ dry-run（**推奨・read-only・branch 不要**）

> 💡 **branch を作らずに「100/200/300 が本物の母屋に当たるか」を検証する。** 課金ゼロ。
> 有料 branch（§4-bis）が足すのは「本物の**実データ**に対する gate 結果」だけ。
> スキーマ不一致という主リスクは本 PHASE で潰せる。

考え方: ローカル smoke は母屋を fixture（`000_*`）で模している。その fixture を**本物の
`d1law_taikei.alo_edges` に 1:1 で合わせ**れば、ローカル PG16 での再 smoke が「本物スキーマに対する
dry-run」と等価になる（FK 型整合・citation 種別・PK 型・RESTRICT ガードまで確認できる）。

### B′-1. 母屋を read-only で introspect（書込みゼロ・課金ゼロ）
`execute_sql` で `introspect_d1law_taikei.sql` の SELECT 群を流す（**SELECT のみ／branch 作らない**）：
- alo_edges の列・型・NULL・既定値／PK の実型（`edge_id`）／citation 種別カラム／CHECK 制約／
  既存被参照 FK／lawtime・serving の名前衝突。
> read-only でも本番 project を「触る」ので、owner の read-only 許可だけは要る（課金は発生しない）。

### B′-2. fixture を実物に合わせる
取得結果で `000_external_dependency_d1law_taikei.sql` の `alo_edges` 定義を**実物と一致**させる
（列名・型・PK・種別カラム・関連 CHECK）。差分があれば 100 側の FK/two-tier 前提と突き合わせ、
不整合は**この時点で**修正（PHASE D 前に潰す）。

### B′-3. ローカル smoke 再実行（無料）
`smoke_placement.sh`（PG16）を実物そっくりの母屋で再走：
1. 100→200→300 が当たる（FK 型一致）。
2. `seed_clean` → `verify_dry_run` で 8 gate 空。
3. `sample_resolver` が `evidence/` golden と一致（C-INT-2）。
4. RESTRICT ガード（母屋 edge DELETE blocked）が効く。

**B′ 終了条件**: 実物整合の fixture で smoke 全 PASS。これで「本物スキーマに対する dry-run」は完了。
ここまで**課金ゼロ**。実データに対する確認まで要る場合のみ §4-bis（有料 branch）へ。

> ✅ **B′ 実施済（2026-06-25, 課金ゼロ）**: 結果は [`..._v0.2.4_B-prime_dryrun_evidence.md`](./DD-LAWTIME-001_v0.2.4_B-prime_dryrun_evidence.md)。
> スキーマ面は GO（FK 型一致／名前衝突なし／smoke 全 PASS）。ただし母屋に statute-citation edge が
> **0 件**＝gate の citation `edge_type` は placeholder 未照合（DDLAWREF 待ち / blocking note #5）。
> → PHASE D を今やっても `citation_temporal` は空のまま（実用上 inert）。有料 branch も現状は得る情報が乏しい。

---

## 4-bis. PHASE B — branch dry-run（**課金あり・owner GO 必須／任意**）

> 🔴 **この PHASE は Supabase の preview branch を作る＝課金が発生する。** owner の「課金 GO」無しに `create_branch` を呼ばない。
> B′ でスキーマ整合は取れているので、これは「**本物の実データに対する gate 結果まで見たい時だけ**」の任意ステップ。

### B-0. 課金の事前提示（owner 承認の materialize）
1. `get_cost`（type=`branch`, project_id=`<PROJECT_ID>`）で見積りを取得 → owner に金額提示。
2. owner が金額に GO → `confirm_cost` で確認トークンを得る。
3. そのトークンで `create_branch`（name 例: `lawtime-v024-dryrun`）。

### B-1. branch へ apply（母屋ファースト順）
branch の接続先に対し `apply_migration` を §3 の順で：
1. `100_lawtime_schema.sql`
2. `200_gates.sql`
3. `300_serving.sql`

> branch には母屋 `d1law_taikei.alo_edges` が production から引き継がれている前提。
> 引き継がれていなければ（空 branch 等）、母屋が無い＝FK 不成立なので**停止**し owner に報告（branch は削除）。

### B-2. seed + verify（gate を実際に回す）
`execute_sql` で順に流す（branch 上なので安全）：
1. `seed_clean.sql` … URI identity のクリーンデータ投入。
2. `verify_dry_run.sql` … **8 gate すべて 0 行**を assert（非0なら `RAISE EXCEPTION`）。
3. `sample_resolver.sql` … golden resolver 出力を取得 → リポジトリの `evidence/` 期待値と **diff**（§5 C-INT-2）。
4. （任意）`violations.sql` … 仕込み違反で各 gate が**検知できる**ことを確認（検知力テスト）。clean に戻すなら branch を作り直すか seed をロールバック。

### B-3. 後始末
- 判定に必要な出力（gate notice / resolver diff / advisor）を控える。
- **branch はそのまま放置しない**：判定が済んだら `delete_branch`（課金停止）。本番反映は branch merge ではなく PHASE D の本番 migration で行う（branch merge を使うかは owner 判断）。

---

## 5. PHASE C — 受入判定（owner GO 不要・判定のみ）

下記**全部 green** で初めて PHASE D に進める。1つでも欠けたら停止。

| # | 受入条件 | 根拠 |
|---|---|---|
| G-1..8 | `verify_dry_run.sql` の 8 gate が**全て 0 行**（`ALL LAWTIME v0.2.4 GATES EMPTY — dry-run PASS`） | 200_gates |
| **C-INT-1** | `citation_temporal` の各行が母屋 `alo_edges(edge_id)` に**実在**し、かつ citation 種別の edge にのみ紐づく（`v_gate_lawtime_citation_edge_missing_side_table` / `_side_table_orphan_or_noncitation` が 0） | 監査 Notes 必須受入 |
| **C-INT-2** | golden resolver 出力が `evidence/` の期待値と**完全一致**（`fn_resolve_law_reference_at` の as-of 解決が回帰していない） | should_fix #3 / 監査 Notes |
| C-adv | apply 後 `get_advisors` が PHASE A 基準線から**新規 critical を増やしていない** | 運用 |

> **C-INT-1/C-INT-2 は監査が「必須受入」と名指しした2点**。gate 数だけ見て通すのではなく、
> 母屋整合（C-INT-1）と resolver 回帰（C-INT-2）を**個別に**確認すること。

---

## 6. 旧 v0.2.3a / 旧 serving の置換メモ

- 本番 `serving` に旧 R-1 view（`v_lawtime_formal_status` / `v_lawtime_resolved_ref`）が残っていれば、
  300_serving の新 view（`serving.lawtime_formal_status_current` 他）が**置換**する。`CREATE OR REPLACE` で名前が違うため、
  旧 view は別途 `DROP VIEW` が要る（PHASE D の最後、出口を切り替えてから）。
- リポジトリの `migrations/lawtime/001_base_v0.2.2.sql` / `010_patch_v0.2.3.sql` は **SUPERSEDED**。
  本番には当てない（v0.2.3a の構造 smoke 専用）。

---

## 7. PHASE D — 本番 apply（**owner GO 必須**）と rollback

> 🔴 owner の「本番 apply GO」無しに production へ `apply_migration` しない。**O1 は確定済（A 統一RESTRICT）**（§0）。

### D-1. 直前チェック
1. PHASE C 全 green が出ていること。
2. **O1 = A 統一RESTRICT 確定済**（2026-06-25）。`citation_temporal` / `unresolved_queue` の FK は
   `ON DELETE RESTRICT`（`100_lawtime_schema.sql` 反映済・smoke ガード PASS）。apply 時は現行の 100 をそのまま使う。
3. backup/PITR 確認（本番 schema 追加なので影響は加算的だが、念のため復帰点を確認）。

### D-5. 母屋 edge 削除時の掃除順（O1-A 運用）
RESTRICT のため、本番で母屋 `alo_edges` の特定 edge を消す必要が出たら、**lawtime 側を先に**片付ける：
1. その `edge_id` の `unresolved_queue` 行を削除（あれば）。
2. その `edge_id` の `citation_temporal` 行を削除。
3. `temporal_eval_event` は append-only。**履歴は消さない**（必要なら別表へアーカイブしてから扱う。通常は残す）。
4. 上記後に母屋 edge を削除。RESTRICT が外れて成功する。
> この順を踏まない削除は RESTRICT で**意図的にブロック**される（smoke ガード「母屋 edge DELETE blocked by RESTRICT」で確認済）。

### D-2. apply（母屋ファースト順）
production 接続で `apply_migration` を §3 の順（100 → 200 → 300）。途中失敗で停止。

### D-3. 直後 verify
production で `verify_dry_run.sql` の gate 部分（seed は入れない＝既存データに対して）を回し、8 gate が 0 行であることを確認。0 でなければ §7 rollback。

### D-4. rollback（apply を戻す手順）
schema 追加型なので、戻すのは作った順の**逆順 DROP**：
```sql
-- 逆順。view → gate → table の順で落とす（依存の葉から）。
DROP VIEW IF EXISTS serving.lawtime_claim_support_decision;
DROP VIEW IF EXISTS serving.lawtime_resolved_ref_current;
DROP VIEW IF EXISTS serving.lawtime_formal_status_current;
-- 200 の gate view 8本を DROP（v_gate_lawtime_*_v20260624）
-- 100 の lawtime.* table / function を DROP（FK 葉から：unresolved_queue, citation_temporal,
--   temporal_eval_event, revision_mapping, law_succession_edge, law_provision,
--   law_revision, law_work, fn_resolve_law_reference_at, trg_eval_append_only）
-- ※ 母屋 d1law_taikei.alo_edges は絶対に触らない。
```
> rollback SQL の確定版は PHASE D 実行時に 100/200/300 の最終形から機械生成して別ファイルに置く。
> 本 runbook はその**段取り**のみ規定する（実 DROP 文は実行時に owner 確認の上で確定）。

---

## 8. PHASE E — 出口接続（DD-LAWSUBTRANS 張り替え・**owner GO 必須**）

1. DD-LAWSUBTRANS が読む参照点を、`serving.lawtime_*_current` / `lawtime_claim_support_decision` に張り替え（**explicit schema-qualified、search_path 非依存**）。
2. 旧 R-1 view を参照していた箇所を切り替え後、§6 の旧 view を `DROP`。
3. 必要なら `generate_typescript_types` で型を再生成し、クライアント側に反映。
4. `get_advisors` 最終確認。

---

## 9. owner が押す鍵の一覧（このページのまとめ）

実行に進むには、以下を**それぞれ別個に**もらう：

1. **課金 GO**（PHASE B：branch dry-run の費用承認）
2. **O1 決裁**（CASCADE のまま / RESTRICT へ）— PHASE D 前
3. **本番 apply GO**（PHASE D）
4. **張り替え GO**（PHASE E：lawsubtrans を serving へ）

> 本 runbook は段取りの確定のみ。上記いずれの鍵も、本書作成時点では**もらっていない**。
> 次にどれを押すか指示があれば、その PHASE だけを実行する。
