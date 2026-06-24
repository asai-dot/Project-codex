# WO-SILVER-WRITE-001（草案）: silver candidate → staging への確定書き込み（P1）

> doc_kind: WORK ORDER 草案 / **設計のみ・owner ratify 前は実書込み禁止** / status: DRAFT
> author: Claude / date: 2026-06-19 / owner: 浅井
> 親: design/vocab_bottleneck/01_BOTTLENECK_RESOLUTION_PLAN_20260618.md（P1）/ DD-DATAARCH-001 v0.2（build側②silver）
> 前提: P0 dry-run（WORKER_TASK_PACKET_P0_SILVER_DRYRUN）の report が出ていること
> tool: tools/silver_resolve/silver_stage_write.py（既定 dry-run・`--apply` で append-only 書込み）
> gate: **append-only JSONL staging のみ**。DDL / DB / canonical graph / 外部取得 / embedding は HOLD。

## 0. 一行
P0 で出た candidate のうち owner が承認した閾値・ポリシーに合致するものだけを、**build側② silver の
append-only staging（JSONL）**へ確定書き込みする。canonical graph には触れない。

## 1. 位置づけ（DD-DATAARCH-001 整合）
- 書込み先は **build側② クレンジング(silver)** = 「掲載位置→判例ID 解決済」「論点section 解決済」の中間成果。
- **論理分離で足りる**（INVARIANT1）。物理スキーマ・DDL は実需着弾まで HOLD ⇒ 本 WO は **JSONL append-only** に留める。
- canonical 化（③curated / 概念層 / claim_support serve）は本 WO の範囲外（後続ゲート）。

## 2. owner ratify ゲート（書込み前に必須）
owner は P0 report を見て次を確定する。これが揃うまで `--apply` しない。
```text
- accept_status   : ["strong"]（推奨・D2） / ["strong","review"]（評釈付き等の例外時のみ）
- min_confidence  : 例 0.90（strong 閾値）
- source_scheme_version : 雑誌レーン版（journal_issn_map / edges_20260611 の版）
- reviewed_by     : owner / 監査主体
- scope           : canary（賃料不払解除）か全量か
```

## 3. 書込み対象と除外
| candidate | 採択（accepted staging へ） | 退避（review_queue へ・常に保存） | 除外 |
|---|---|---|---|
| silver-1 cite | `decision_status` ∈ accept_status かつ `confidence`≥min かつ resolved 単一 | review / 多候補 | `honest_empty` 行 |
| silver-2 section | 評釈密度>0（strong） | review（trace_absent） | member 0 |
| silver-2 cooccurrence | importance>0 かつ pair_weight≥1 | importance=0 | weight 0 |

- **flag-first**: review は捨てず `*_review_queue.jsonl` へ保存（自動確定しない）。
- **strong-only 既定**: accepted staging に入るのは原則 strong のみ（D2）。

## 4. staging レコード（append-only・provenance 必須）
各 accepted 行に最低限:
```text
silver_id（安定キー）/ kind（cite_resolved|issue_section|issue_cooccurrence）/
payload（resolved_hanrei_id / issue_id / section_heading 等）/ decision_status /
confidence / match_method / source_scheme_version / reviewed_by / reviewed_at /
parser_version / policy_hash / assertion_kind="derived_match" / honest_empty=null
```
- `assertion_kind=derived_match`（雑誌レーン periodical_edges_normalize と同語彙。canonical 確定は受理層で別途）。
- **冪等**: `silver_id`（cite=lic_edge_id+target / section=issue_section_id / cooc=a|b）で重複書込みを抑止。
- **append-only ledger**: 書込みイベントを `_SILVER_WRITE_LEDGER.jsonl` に1行追記（gpt_audit 台帳に倣う）。

## 5. 実行（tool）
```bash
# 既定 dry-run（何も書かない・書込み予定を表示）
python3 tools/silver_resolve/silver_stage_write.py \
  --cite-candidates    out/silver1_*/silver_cite_resolution_candidates.jsonl \
  --section-candidates out/silver2_*/silver_toc_section_candidates.jsonl \
  --cooc-candidates    out/silver2_*/silver_issue_cooccurrence_candidates.jsonl \
  --policy policy.json --staging-dir build/silver_staging

# owner ratify 後にのみ:
python3 ... --policy policy.json --staging-dir build/silver_staging --apply
```

## 6. ACCEPTANCE
- dry-run が「採択/退避/除外」件数と書込み予定を出す。
- `--apply` で accepted staging・review_queue・ledger が append-only で増える。
- 再実行で二重書込みが起きない（冪等）。
- accepted staging に honest_empty 行・auto review が混入しない。

## 7. FORBIDDEN（逸脱）
- DDL / DB write / canonical graph / 概念層 mint / serve / embedding（すべて後続ゲート）。
- owner ratify 前の `--apply`。
- review / 多候補 / honest_empty を accepted staging へ入れること。
- 論点section を accepted 論点として下流へ（DD-LRINDEX v0.4 GPT確認パス前）。

## 8. ROLLBACK
- staging は append-only。誤書込みは ledger の event を辿り、`superseded` イベントを追記して無効化（物理削除しない）。
- DD-CSI-AUDIT-001（rollback audit ledger）流儀に合わせる。
