# DD-LAWTIME-001 — reconstructed base coverage & value-domain rules

> 監査 `DDLAWTIME_MODIFY_REQUIRED` / `..._PASS_WITH_NOTES`（2026-06-23, RESULT id 2302892298128 /
> CURRENT_RESULT id 2303569300724）の must_fix #1/#3/#4 を閉じるための文書。
> 再構成 base（`001_base_v0.2.2.sql`）が**正本欠落からの best-effort 再構成**である境界を明文化する。
> status: **candidate**（owner ratify 前 / production apply は HOLD）。

この表が無いと「どの列が patch doc 由来の確定で、どの列が recon 推定か」が読めず、materialize 後に
正本との差分を潰せない。監査の HOLD（production apply / canonical ratify / claim_support serving）は
本表 + 追加 gate（N-1/N-2/N-3/N-4）が閉じ、owner が ratify するまで維持する。

凡例（provenance）:
- **P** = `docs/dd/DD-LAWTIME-001_v0.2.3_production_patch.md`（承認済 patch doc）が明示的に参照する列。確度高。
- **L** = `migrations/lawsubtrans/*` が消費する列（DD-LAWSUBTRANS 接続点）。確度高。
- **R** = recon 推定（patch/lawsubtrans のどちらにも明示が無く、整合のために再構成が補った）。**要正本照合**。

---

## 1. base object coverage（must_fix #4）

| object | 種別 | provenance | materialize 前の要照合点 |
|---|---|---|---|
| `lawtime.alo_law_work` | table | P,L | FK ターゲット。列は id/title のみ（R: title は推定、欠けても可） |
| `lawtime.alo_statutes` | table | P,L | 版の時間軸。`revision_status` 値域は R（§3） |
| `lawtime.alo_edges` | table | P,L | **D2 層スタンドイン**。generic 列(src/dst)は R。実 D2 設計と要整合 |
| `lawtime.alo_law_succession_edge` | table | P | 二段 resolver tier1。`relation_type`/`confidence` 値域は R |
| `lawtime.alo_law_ref_temporal_eval_event` | table | P | append-only。claim_support gate が存在を要求 |
| `lawtime.fn_resolve_law_reference_at` | function | P,R | tier1→tier2 / LIMIT 1。**fallback は R**（N-1 gate で非決定性を封じる） |
| `trg_lawtime_eval_append_only` | trigger | P | eval ログ append-only |
| `ck_law_ref_two_tier` | constraint | P | patch P0-1 が NOT VALID→backfill→VALIDATE で付与 |
| gate views P0-2/3/4 | view | P | patch doc 明示 |
| gate views N-1/N-2/N-3/N-4 | view | R(audit) | 2026-06-23 監査 notes で追加。LIMIT 1 維持の前提 |
| `v_lawtime_formal_status` / `v_lawtime_resolved_ref` | view | P,L | R-1。lawsubtrans 接続点 |

## 2. 列単位の provenance（抜粋・要照合は R 行）

### alo_statutes
| 列 | provenance | 備考 |
|---|---|---|
| law_revision_id (PK) | P | 版識別 |
| law_work_id (FK) | P,L | |
| law_id | P,L | 版が体現する法令 id |
| valid_from / valid_to | P | 半開区間 [from, to) |
| revision_status | **R** | 値域§3。外部 corpus の状態語と要マッピング |

### alo_edges（D2 列）
| 列 | provenance | 備考 |
|---|---|---|
| edge_type | P | cites_statute / statute_ref / applies_statute を two-tier CHECK が判定 |
| cited_law_work_id / cited_law_id | P | |
| as_of_basis / as_of_date | P | 値域§3 |
| resolved_law_revision_id | P,L | |
| temporal_status | P,L | 値域§3。legacy は NULL→backfill 'unchecked' |
| temporal_caveat | P | 値域§3 |
| claim_support_eligible | P,L | DEFAULT false（安全側） |
| src_id / dst_id | **R** | generic endpoints の最小再構成。実 D2 と要整合 |

### alo_law_succession_edge
| 列 | provenance | 備考 |
|---|---|---|
| law_work_id / law_id | P | |
| relation_type | **R** | 値域§3 |
| valid_from / valid_to | P | |
| confidence | **R**(P0-4 由来) | 値域§3。gate は reviewed/confirmed のみ ambiguous 判定 |
| lineage_event_id | P | merge/split を束ねる |

## 3. enum 値域と丸め規則（must_fix #3）

すべての `(recon)` enum は **安全側に狭く**取り、**外部 corpus の未知語は捨てずに unknown 系に丸める**。
unknown 系は **claim_support に流れない**ことを gate / CHECK で保証する。

| enum | 許容値 | unknown 系 | 外部値の丸め規則 |
|---|---|---|---|
| `alo_statutes.revision_status` | CurrentEnforced / PreviousEnforced / Repeal / UnEnforced | （明示 unknown 無し） | 4 値に**確実に**写せない外部状態は **materialize しない**（捨てる）。曖昧を CurrentEnforced に丸めない。N-3/N-4 gate が CurrentEnforced 重複・Repeal 同居を検出 |
| `alo_edges.temporal_status` | unchecked / current / superseded / pre_enactment / unenforced / repealed / not_yet_in_force | **unchecked** | 判定不能・未評価は `unchecked`。NULL(legacy) は backfill で `unchecked` |
| `alo_edges.as_of_basis` | explicit / document_date / event_date / **unknown** | **unknown** | 基準時点が取れない場合 `unknown`＋as_of_date NULL（two-tier CHECK の unknown branch） |
| `alo_edges.temporal_caveat` | none / approximate / ambiguous / **unknown** | **unknown** | 既定 `none`。曖昧さは approximate/ambiguous、判定不能は unknown。claim_support は `none` のみ許容 |
| `succession.relation_type` | renamed / merged / split / absorbed / reorganized / continues / **unknown** | **unknown** | 系譜関係が確定しないものは `unknown`。resolver tier1 は `<> 'unknown'` のみ採用 |
| `succession.confidence` | candidate / reviewed / confirmed / **unknown** | **unknown** | 既定 `candidate`。P0-4 ambiguous gate は reviewed/confirmed のみ対象 |

### unknown 系の扱い（不変条件）
1. `as_of_basis='unknown'` の edge は two-tier CHECK の unknown branch に閉じ込められ、
   `resolved_law_revision_id IS NULL / temporal_status='unchecked' / claim_support_eligible=false` を強制。
2. `temporal_status='unchecked'`（および NULL）は `gate_unknown_or_unchecked_blocked`（lawsubtrans 側）で
   claim_support から遮断。
3. `relation_type='unknown'` は resolver tier1 と P0-4 gate の双方で除外され、版解決に寄与しない。

## 4. resolver の非決定性に対する保証（must_fix #2 / 監査 N-1・N-2）

`fn_resolve_law_reference_at` は v0.2.2 互換のため **LIMIT 1 を維持**する。監査推奨（option A）に従い、
LIMIT 1 が一意に定まる前提を **gate で 0 件保証**する（`verify_dry_run.sql` が assert）:

- `gate_law_work_single_fallback_law_id` … succession 不在の law_work が複数 law_id を持たない（tier2 fallback の一意性）。
- `gate_statute_revision_no_ambiguous_overlap` … 同一 law_id の版区間が重ならない（tier2 ORDER BY LIMIT 1 の一意性）。
- `gate_succession_no_ambiguous_overlap`（P0-4 既存） … tier1 の一意性。

これら + `gate_formal_status_inconsistent_revision_status`（N-3/N-4）が全空であることが、
materialize branch dry-run → owner ratify への次段階品質ゲート（RESULT §6）。

## 5. 残 HOLD（本表で閉じない・ratify 後）

- 実 D2 edge レイヤとの整合（`alo_edges` スタンドインの移設/接続）。
- 正本 v0.2.x 設計との `revision_status` 状態機械の最終照合（corpus 実態での N-3 強化）。
- production apply / Supabase materialize / canonical / claim_support serving。
