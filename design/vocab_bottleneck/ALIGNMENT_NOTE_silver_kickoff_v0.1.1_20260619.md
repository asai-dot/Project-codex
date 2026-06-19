# ALIGNMENT NOTE: リポジトリ silver 実装 → 監査済み SILVER-RESOLUTION-KICKOFF v0.1.1 整合

> doc_kind: 整合記録 / date: 2026-06-19 / owner: 浅井 / author: Claude
> 決定: owner 指示「リポジトリ実装を監査版へ整合」(2026-06-19)
> 監査正本: `SILVER-RESOLUTION-KICKOFF v0.1.1`（Codex著・Box）/ 監査結果 `SILVERKICKOFF_ADOPT_AS_PLAN`（GPT-5.5, 2026-06-17）
> 併せて: `DD-DATAARCH-001 v0.2` → `ADOPT_AS_DESIGN`（2026-06-17）/ `WO-PERIODICAL-ISSN-SEED-EXPANSION` → DESIGN_PASS_WITH_NOTES

## 0. なぜ整合したか

silver-1（掲載位置→判例ID）は Mac/Codex レーンで先行し、**監査済みプラン v0.1.1 ＋ 既存 crosswalk v0**
（`d1lic_case_source_crosswalk_v0_20260611`：5,475 解決リンク・invariant failure 0・非canonical）が既に存在した。
私のリポジトリ実装は用語と同一性境界が食い違っており、放置すると二重発明になる。owner 判断で**監査版へ寄せた**。

## 1. 監査が要求し、本リポジトリに反映した点

| 監査要求（v0.1.1） | 旧実装 | 整合後 |
|---|---|---|
| status 命名から resolved/accepted/strong を排除 | `decision_status: strong/review` | `suggestion_status: machine_suggested_*_unreviewed / needs_human_review / ambiguous_or_unresolved / blocked_*` |
| 解決先は source-record URI（canonical case でない） | `resolved_hanrei_id` | `target_source_record_uri:["d1hanrei:…"]` ＋ `identity_scope=source_record_crosswalk_not_canonical_case` |
| 非選択 sibling を理由付き保存 | 多候補は review に丸める | 全 sibling を target に保存＋`non_selection_reason` |
| blocker_code 拡充 | db_unbuilt / locator_unresolvable | db_unbuilt / index_absent / policy_blocked / insufficient_signal / authority_snapshot_missing / source_registry_unratified |
| authority snapshot 必須（gate8） | なし | `--authority-snapshot` 必須。無いと全行 `blocked_by_policy_or_provenance` |
| tier A/B も未レビュー候補（reviewed/canonical 化しない） | P1 が "accepted" lane へ書込み | P1 lane を `candidate` / `ambiguity_queue` に改名・`reviewed=false` 固定 |
| 商用本文を出さない | locator 文字列を出力 | ID/hash(`source_ref_hash`)/正規化キー(`normalized_position_key`)/短ラベルのみ |
| QA を層化・negative control・freeze | canary のみ | worker packet に QA strata / negative control / sample-freeze を追加 |

## 2. tier 対応（kickoff v0.1.1 §6）

| tier | 条件 | status |
|---|---|---|
| A | 正規化 誌+号+頁 exact・単一 | `machine_suggested_source_record_match_unreviewed` |
| B | 誌名 alias 経由の exact 等（要高密度QA） | `machine_suggested_source_record_match_high_density_qa_required` |
| C | 号レベル一意（頁欠）/ court+date 手掛り | `needs_human_review` |
| D | 多候補・衝突・index 無 | `ambiguous_or_unresolved` |
| X | authority 欠 / ポリシー / provenance | `blocked_by_policy_or_provenance` |

## 3. 同一性 4 層（kickoff §4・厳守）

```
source record    d1hanrei:{id} / lic:case_text:{data_no}   ← 本ツールの解決先
occurrence link  resolved_link_key / source_pair_fingerprint
grouping fp      case_fingerprint_v0_noncanonical          ← key にしない
canonical case   future ALO case URI                       ← 別ゲート・自動昇格禁止
```

本ツールは **source-record 候補リンクのみ**生成する。canonical case 行を作らず、source-record 等価＝法的同一性とも主張しない。

## 4. 既存 crosswalk v0 を起点にする（再発明しない）

- 実データ実行時は **`build/d1_lic_reference_staging_20260611.../` の crosswalk v0（5,475 links）を起点**にする。
  本ツールは「未解決 B-tier（lic via_journal 23,914 / by_date 5,571）の追加解決」を担い、v0 を上書きしない。
- 誌名正規化は雑誌レーン正本（`periodical_edges_normalize.py` の `ALIAS` ＋ `journal_issn_map.jsonl`）から
  `--norm-dict` を生成（WORKER_TASK_PACKET §1.5）。

## 5. HOLD（監査 §10 を継承）

production 実装 / DDL / DB write / canonical case 化 / `alo_edges` 昇格 / `reviewed=true` / claim_support /
MCP・vector serve / 商用本文の GPT 送出 / source mutation / 新規 D1 取得。**`ADOPT_AS_PLAN` は実装許可ではない。**

## 6. 反映済みファイル（本 PR）

- `tools/silver_resolve/silver_cite_id.py` … tier status / source-record URI / blocker codes / authority snapshot
- `tools/silver_resolve/silver_toc_section.py` … status 命名整合（grouping_noncanonical）
- `tools/silver_resolve/silver_stage_write.py` … candidate/ambiguity_queue・reviewed=false
- `tools/silver_resolve/tests/*` … 31 tests（新語彙・authority gate・source-record 境界・reviewed=false）
- docs: README / RUNBOOK / WORKER_TASK_PACKET / 本ノート

## 7. 残課題（pending）

- `DD-LRINDEX-001 v0.4`（harvest 訂正 G_HARVEST_NOT_MANUFACTURE）の GPT 確認パス RESULT は未確認 → silver-2 論点の accepted 化はそれまで保留。
- `DD-CITE-TREATMENT` は `CITETREAT_MODIFY_REQUIRED`（treatment 付与は別ゲート・本ツールは付けない）。
