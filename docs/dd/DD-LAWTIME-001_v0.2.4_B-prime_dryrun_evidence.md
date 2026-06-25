# DD-LAWTIME-001 v0.2.4 — PHASE B′（課金ゼロ dry-run）証跡

> status: **DONE（課金ゼロ）**。2026-06-25 実施。Supabase は **read-only SELECT のみ**（書込みゼロ・branch 作成ゼロ・課金ゼロ）。
> 方法: 本物の母屋を read-only introspect → fixture 整合確認 → ローカル PG16 smoke 再実行。
> 関連: runbook §4（PHASE B′）/ `introspect_d1law_taikei.sql` / O1=A 確定。

---

## 1. やったこと

有料 branch を作らずに「確定設計 100/200/300 が**本物の母屋**に素直に当たるか」を検証した。
本物の `d1law_taikei.alo_edges` を read-only で introspect し、ローカル smoke の fixture が実物と
一致していることを確認、O1=A（RESTRICT）反映後の smoke を再走させた。

- 対象 project: **asai-dot's Project** (`nixfjmwxmgugiiuqfuym`, ap-northeast-1, pg17)。
- 使用ツール: `list_projects`, `execute_sql`（**SELECT のみ**）。
- 母屋 fixture: `000_external_dependency_d1law_taikei.sql`（本番不適用）。

---

## 2. introspection 結果（本物の母屋）

### 2.1 `d1law_taikei.alo_edges` 実スキーマ
| # | 列 | 型 | NULL | 既定 |
|---|---|---|---|---|
| 1 | `edge_id` | **bigint** | NO | `nextval('…alo_edges_edge_id_seq')` |
| 2 | `src_uri` | text | NO | |
| 3 | `edge_type` | text | NO | |
| 4 | `dst_uri` | text | NO | |
| 5 | `source_system` | text | YES | |
| 6 | `source_version` | text | YES | |
| 7 | `valid_from` | date | YES | |

- **PK = `edge_id` (bigint)** → lawtime の FK（`citation_temporal.edge_id` / `unresolved_queue.edge_id` /
  `temporal_eval_event.edge_id` が `bigint REFERENCES alo_edges(edge_id)`）は**型一致** ✅。
- fixture は列構成を**完全一致**で写している ✅。唯一の差は identity 生成モード（実物=`nextval` 既定 /
  fixture=`GENERATED ALWAYS AS IDENTITY`）。smoke は alo_edges へ**明示 edge_id を INSERT しない**
  （`src_uri,edge_type,dst_uri` で投入し `max(edge_id)` を読む）ため、この差は**挙動に影響しない**。

### 2.2 名前衝突
- `lawtime` スキーマ: **空**（オブジェクト 0）→ 100/200 の新規作成は衝突なし ✅。
- `serving` スキーマ: 実在。既存 view は `publication_author_claim_accepted` / `publication_author_claim_current`
  の2本のみ。300 が作る `lawtime_formal_status_current` / `lawtime_resolved_ref_current` /
  `lawtime_claim_support_decision` とは**非衝突** ✅。旧 v0.2.3a の `v_lawtime_*` view も**残存なし** ✅。
- house-style 既存物（`v_gate_d1taxo_pending_l3_excluded_from_claim_support_v20260619`,
  `ck_d1taxo_pending_l3_not_claim_support_v20260619`）を確認 → 200_gates の命名規則が母屋流儀に一致（blocking note #5 の style 部分は OK）。

### 2.3 ⚠️ citation edge vocabulary（**要対応 / blocking note #5 の具体化**）
- 本物 `alo_edges` の `edge_type` は **`classified_under` 1種のみ（10,823 行）**。
- gate が statute-citation とみなす **`cites_statute` / `statute_ref` / `applies_statute` は母屋に 0 件**。
- 既存 CHECK `ck_d1taxo_pending_l3_not_claim_support_*` が参照する edge_type は
  `claim_support / claim_proof / casebundle_evidence / legal_reasoning`。**statute-citation 系は未定義・未投入**。

→ **発見**: 設計は「母屋 = canonical citation-edge」を前提とするが、**実物の母屋に statute-citation edge は
まだ1本も存在しない**（現状は分類グラフ）。200_gates の citation `edge_type` 集合は
**プレースホルダ**であり（ヘッダで自己申告済）、**実 vocabulary との照合は未了**。これは
**DDLAWREF（edge_type vocabulary の所有者）の決定事項**で、lawtime が勝手に確定してはならない。

---

## 3. ローカル smoke 再実行（O1=A RESTRICT 反映後）

`smoke_placement.sh`（PG16 / 自己完結）を再走 → **STRUCTURAL SMOKE OK**。
- clean seed で 8 gate すべて空。
- golden resolver 出力が `sample_resolver` 期待と一致（C-INT-2 相当）。
- 仕込み違反で 8 gate それぞれ検知（検知力）。
- guards 6件すべて RAISE：eval append-only(UPDATE/DELETE) / two-tier CHECK / FK(no such edge) /
  **母屋 edge DELETE blocked by RESTRICT（O1=A）** / law_work URI CHECK。

---

## 4. B′ 判定

| 観点 | 判定 | 備考 |
|---|---|---|
| FK 型整合（edge_id bigint） | ✅ GO | 100 の FK は本物に当たる |
| 名前衝突（lawtime/serving） | ✅ GO | 衝突なし。旧 view 残存なし |
| house-style 命名 | ✅ GO | 母屋流儀に一致 |
| 構造 smoke（gate/guard/resolver） | ✅ PASS | O1=A 込みで全 green |
| **citation edge vocabulary 照合** | ⚠️ **未了** | 母屋に citation edge 0 / placeholder 未照合 → **DDLAWREF 待ち** |

### 結論
- **スキーマ面の materialize 可否は GO**：100/200/300 は本物の母屋に型・名前とも素直に乗る。
  有料 branch を使わずにここまで確認できた（**課金ゼロ**）。
- ただし **機能面は DDLAWREF 依存**：母屋に statute-citation edge が投入され、その `edge_type`
  vocabulary が確定するまで、lawtime を apply しても `citation_temporal` は空のまま
  （gate は vacuously 空＝PASS だが「中身ゼロ」）。**PHASE D を今やっても実用上は inert**。

### 含意（owner / 次の鍵）
1. **PHASE D（本番 apply）は技術的には安全**だが、**DDLAWREF が citation edge を母屋に入れるまで実利が無い**。
   先に lawtime を“器として”置くか、DDLAWREF と足並みを揃えるかは owner 判断。
2. **200_gates の citation `edge_type` 集合**（`cites_statute`/`statute_ref`/`applies_statute`）は
   **DDLAWREF の実 vocabulary に要差し替え**。これが blocking note #5 / decision_requested の実体。
3. 有料 branch（§4-bis）は「本物の**実データ**に対する gate 結果」を見たい時のみ。現状 citation edge が
   0 なので、branch を作っても得られる追加情報は乏しい（**今は課金する価値が低い**）。
