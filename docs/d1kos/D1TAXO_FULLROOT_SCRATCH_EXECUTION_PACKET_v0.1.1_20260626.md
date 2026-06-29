# D1TAXO full-root scratch execution packet v0.1.1（2026-06-26）

> from: 番頭(head) / to: Codex 5.5 controller / 浅井(owner)
> kind: **design + generation spec only. No DDL apply / no DB write / no psql / no execution.**
> supersedes: v0.1（2026-06-22, GPT監査 PASS_WITH_NOTES, result 2301873246209）。本 v0.1.1 は監査 §4 must_fix 6件を反映。
> precedent: 戸籍法1313 single-root scratch canary（CLOSED 2026-06-20, owner-accepted 2026-06-22）
> gate authority: DD-D1TAXO-002-RUNBOOK-001 v0.2（ACCEPTED_WITH_NOTES, closure 2301875798124）
> **実行・full batch・production・owner lift はすべて HOLD。本 packet は受理対象であって実行指示ではない。**

## 1. purpose
1313 single-root scratch canary を全21法編（full-root）へ scale する scratch/rollback 実行の**設計**を確定し、
HF-FR-2（全 root で INV-1 gate violation=0 を実測）を充足するための実行計画を v0.1.1 として締め直す。
本 packet 自体は実行しない。scratch load・psql・SQL 生成の実走は受理後の別 lease。

## 2. scope & scale（実測接地）
- scheme: d1law-taikei（external_kos satellite KOS — backbone にしない）
- root 21法編 / terms 49,733（=v4 patch 行数 grounded）/ pending-L3 edges 10,823（=bridge staging grounded）
- non-scope: L2.5_topic / B4※ 先頭 = out_of_scope
- per-root rollup（実測・抜粋）: 非訟1317 50.2% | 経済法1321 49.1% | 破産等1319 48.1% | 労働1320 45.2% |
  民訴1309 32.7% | 商法1307 32.3%（pending 2,243）| 債権Ⅰ1304 32.0% | … | 戸籍1313 22.4%(=canary一致) |
  借地借家1314 8.1% | 債権Ⅱ1305 1.0% | TOTAL 21.8%
- per-root rollup は **`resolver_priority_signal`**（商法・債権Ⅰ・民訴を先に解決）であって
  **batch を止める閾値ではない**（runbook v0.2 §4 / RDB-055 key ruling）。

## 3. input_artifacts（実在・sha256 固定）
- v4 patch（terms 源 49,733）: `…/d1taxo_v06_r4_patch_proposed_49733.jsonl` sha256 `2425f8ff…`
- bridge staging（pending-L3 源 10,823）: `…_bridge_staging_for_table_load.jsonl` sha256 `13a535a6…`
- Phase0 DDL（245行）: `…_v0_4_DDL_07_tables_alterations.sql` sha256 `39e5093a…`
- resolver runbook v0.2（id=DD-D1TAXO-002-RUNBOOK-001）: sha256 `d5b0a2ff…`
- INV-1 gate SQL: `MF_D_pending_l3_exclusion_gate.sql`（gate `gate_d1taxo_pending_l3_excluded_from_claim_support_v20260619`）
- per-root rollup: `per_root_pending_l3_rollup.tsv`

## 4. execution model（scratch 隔離 — must_fix #5: A案固定）
- target DB（**専用 throwaway, A案固定**）: `alo_d1taxo_fullroot_scratch_20260622`
  / role: `alo_d1taxo_fullroot_scratch_role`（非 superuser/createdb/createrole）/ schema: `scratch_d1taxo_fullroot`
- **B案（本番 alo-connect project 内 schema＋即時DROP）は不採用**（49,733件規模で blast radius 過大）。
- 単一 `BEGIN` … 最終 `ROLLBACK`、**root単位 + phase区切り SAVEPOINT**、`COMMIT=0`、
  `search_path = scratch_d1taxo_fullroot, pg_temp`（public fallback 不使用）。
- ROLLBACK 後 scratch schema/table 残存 0 を確認。本番 alo-connect には触れない。

## 5. phase plan + expected_counts（grounded / derived / target 分離）
Phase 0 DDL（11表+8gate view）/ 1 scheme+snapshot 1/1 / 2 terms 49,733(grounded) / 3 labels 149,199(derived=×3) /
4 relations 38,910(derived=terms−pending) / 5 kos_item_extra 49,733(derived) / 6 d1law_taikei_extra 49,733(derived) /
7 observation 49,733(derived; matched/false run-emitted) / 8 pending-L3 10,823(grounded) / 9 検証 / ROLLBACK 残存0。
- 不変条件: 各 term は skos_broader 1本 **XOR** statute-layer L3 pending edge 1本（1313 実証: 362 = 281 + 81）。
- target: INV-1 全root violation=0 / cycle 0 / hub 0 / hub_membership 0 / term_tier!=2 0 / orphan 0。

## 6. must_fix 反映（監査 v0.1 §4・6件）— **本 v0.1.1 の核**

### MF-FR-1 root単位 SAVEPOINT ＋ root_status[]（#1）
- 各 root を独立 `SAVEPOINT` で分離。root load 中の error は当該 root を fail マークし、**run 全体を failed として最終 ROLLBACK**。
- 出力 `root_status[]`（root_id ごと）: `{root_id, terms_expected, terms_actual, delta, inv1_subset_violation, savepoint, status}`。
- load order は **deterministic root order**（root_id 昇順）とし、順序を artifact に記録。

### MF-FR-2 derived mismatch = invariant_break（#2）
- derived count（labels/relations/kos_item_extra/d1law_taikei_extra/observation）の expected≠actual は
  **`invariant_break` として即停止**。**generator/loader 側で actual を expected に寄せる自動補正は禁止**。
- result.json に `expected / actual / delta / classification(grounded|derived|target)` を必ず出す。

### MF-FR-3 result.json schema 固定（#3）
必須キー: `scratch_scope_only(=true)`, `source_hashes`, `expected_counts`, `actual_counts`, `deltas`,
`root_status[]`, `inv1_summary`, `residue_check`, `rollback_confirmed`, `execution_holds[]`。

### MF-FR-4 generator に補正ロジック無し（#4）
- SQL generator は input artifact を**忠実に展開**するのみ。actual を expected に合わせる補正・穴埋め・推測補完を持たない。
- generator 仕様書と生成物 header に「no correction logic」を明記し、generator ソース sha256 を result.json に刻む。

### MF-FR-5 隔離 A案固定（#5）
- §4 のとおり専用 throwaway DB（A）固定。B不採用を packet 内に明記。scratch role 権限一覧を packet に添付（should_fix #6）。

### MF-FR-6 production HOLD 再掲（#6）
- full-root scratch PASS は **構造ロード予行の成功にすぎず**、production DDL/load/bridge collapse/canonical/
  claim-support/embedding/MCP の認可には**一切ならない**（INV-4: scratch PASS 本番流用禁止）。

## 7. verification additions
(m) INV-1 全root gate violation=0 必須（HF-FR-2）＋ SF-FR-3 現実ネスト negative test 再走 /
(n) per-root rollup を `resolver_priority_signal` として emit（`batch_block_threshold` 表記禁止）＋ §2 表と cross-check /
(o) candidate_resolved も claim_support_eligible=false 維持 /
(p) result.json `scratch_scope_only=true` /
(q) 生成 SQL ＋ result.json header に runbook v0.2 を id/version/hash（`d5b0a2ff…`）刻印 /
(r/新) root_status[] と invariant_break 停止条件の単体テスト（故意 mismatch を 1 root に注入し停止を確認）。

## 8. should_fix（監査 §5・次反映）
per-root rollup に pending_ratio bucket＋resolver priority queue 初期順 / root別 `terms = broader + pending` 表示 /
1313 との root family 偏り commentary / observation matched=0 許容条件を result.json で分離記録 /
生成 SQL artifact の sha256 を result.json と review packet に記載 / scratch role 権限一覧を packet に添付。

## 9. GO / HOLD
- **GO**: 本 packet v0.1.1 起案 DONE / SQL generator 作成・生成（DB write 無し）は受理後 GO。
- **HOLD**: scratch 実行そのもの / psql 接続 / DB write / full batch / production DDL apply / production load・write /
  resolver-based bridge collapse / backfill / canonical promotion / claim-support eligibility /
  embedding / MCP serving / scratch PASS の production 権限流用。
- **owner lift（full-root scratch 実行 lease の発火）は owner の明示判断**。head から先行実行しない。

## 10. done_definition
must_fix 6件（MF-FR-1〜6）反映 / result.json schema 固定 / 隔離 A案固定 / invariant_break 停止明文化 /
generator 無補正明記 / production HOLD 再掲 ── 済。残: controller/owner 受理 → 受理後 SQL 生成 → 実行 lease で HF-FR-2 実測。
