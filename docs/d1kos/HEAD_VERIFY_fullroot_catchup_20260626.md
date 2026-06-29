# HEAD catch-up 検収: canary2ピボット ＋ resolver runbook ＋ full-root scratch packet（2026-06-26）

> 番頭(head)の catch-up 検収。06-20〜06-22 にループが先行し、私の検収・SoT記録が遅延していた分を遡及照合する。
> **判定: 三件いずれも ACCEPT（設計/governance スコープ）。実行・full batch・production・owner lift は HOLD 継続。**
> 本記録は evidence。apply 認可ではない。

## 0. 経緯（先行したループの再構成）
- 06-20: 番頭が 2本目 rich canary を発注（`WO-CODEX-canary2-rich-root_20260620.md`）。
- 実際の展開（**ピボット・正直記録**）: 単一 rich root の scratch 実行は**単体では行われず**、より有用な
  「全21root pending rollup（read-only 実測）＋ SF-FR closures ＋ pending-L3 resolver runbook ＋ full-root
  scratch execution packet（設計のみ）」に吸収された。**1313 を超える新規 scratch 構造ロードは未実行**＝HOLD と整合。
  発注が要求した「ゲート耐性の荒れデータ実証」は **SF-FR-3 現実ネストJSON G23 negative test**（violation=3＝実term行のみ・
  非配列 taxonomy_paths/term_ids 両方 guard・throw 0・false positive 0・scratch+ROLLBACK schema_remaining=0）で達成。

## 1. 検収対象と監査戻り（三件）

| 対象 | 監査(GPTお目付け) | head 判定 | 主 artifact / id |
|---|---|---|---|
| ① pending-L3 resolver runbook v0.2 = `DD-D1TAXO-002-RUNBOOK-001` | PASS_WITH_NOTES → ACCEPTED_WITH_NOTES（HF-FR-1 satisfied） | **ACCEPT** | result 2300679944735 / closure 2301875798124 / req 2299441926296 |
| ② full-root scratch execution packet v0.1 | PASS_WITH_NOTES（design GO・実行HOLD） | **ACCEPT（設計）** | result 2301873246209 / req 2301225371726 |
| ③ canary2→全root rollup / SF-FR closures | （①②の接地として消費） | **ACCEPT（接地確認）** | per_root_pending_l3_rollup.tsv 等 |

## 2. head 独立 数値接地チェック（再計算で確認）

| 検査 | 値 | 判定 |
|---|---|---|
| terms = v4 patch 行数（grounded） | 49,733（sha256 `2425f8ff…`） | ✓ |
| pending-L3 = bridge staging 行数（grounded） | 10,823（sha256 `13a535a6…`） | ✓ |
| labels = terms × 3（derived） | 149,199 = 49,733 × 3 | ✓ |
| relations = terms − pending（derived） | 38,910 = 49,733 − 10,823 | ✓ |
| 全体 pending 比 | 10,823 / 49,733 = 21.8% | ✓ |
| per-root 戸籍法1313 = canary1 一致（source validity アンカー） | 362 terms / 81 pending / 22.4% | ✓ |
| pending 遍在性（v0.1 比率BLOCK 撤回の根拠） | median 29.5% / 9-of-21 root ≥30%（最大 非訟50.2%・商法2243件） | ✓ |

## 3. 監査の主要ルーリング（head 同意・SoT carry-forward）

**① runbook（HF-FR-1）**
- 新 resolver DD を mint せず**既存 DD-D1TAXO-002 に anchor**（anti-duplication）= 正しい。
- v0.1 の「30% ratio BLOCK」**撤回**は妥当: pending L3 は例外でなく遍在。比率は **resolver_priority_signal**、
  batch 安全は exclusion gate（INV-1 violation=0）で担保。
- `candidate_resolved` は claim_support_eligible=false 維持。`resolved` は law_id＋owner/DBA 承認が前提。

**② full-root packet（HF-FR-2 設計側）**
- derived expected counts は「run を合わせに行く正解値」ではなく**検査仮説**として可。ただし
  **mismatch は自動補正禁止・`invariant_break` で停止**が条件。
- INV-1 単独では実行安全を閉じ切らない → **root単位 SAVEPOINT / root_status[] / per-root rowcount** を追加。
- 隔離は **A案 専用 throwaway DB**（`alo_d1taxo_fullroot_scratch_20260622`）。B案（本番project内schema+即時DROP）は不採用。

## 4. full-root 実行 lease 前 must_fix（監査 ②§4・6件）→ v0.1.1 に反映

1. root単位 SAVEPOINT ＋ `root_status[]` 出力を必須化
2. derived counts mismatch を `invariant_break` として明文化（自動補正禁止）
3. result.json schema 固定（最低: `scratch_scope_only, source_hashes, expected_counts, actual_counts, deltas, root_status, inv1_summary, residue_check, rollback_confirmed, execution_holds`）
4. SQL generator に補正ロジックが無いことを明記（input を忠実展開し検証で停止するのみ）
5. Q-1 = A 専用 throwaway DB 採用（B 不採用）
6. full-root scratch PASS 後も production DDL/load/bridge collapse/canonical/claim-support/MCP は HOLD と再掲

→ 本 must_fix を織り込んだ **`D1TAXO_FULLROOT_SCRATCH_EXECUTION_PACKET_v0.1.1_20260626.md`** を同時起票。

## 5. GO / HOLD（混同禁止）

| 対象 | 判定 |
|---|---|
| runbook v0.2 = DD-D1TAXO-002-RUNBOOK-001（HF-FR-1） | **ACCEPTED_WITH_NOTES** |
| full-root scratch packet（設計/governance） | **GO（設計のみ）** |
| SQL generator 作成（DB write 無し） | **GO**（別 deterministic step） |
| **full-root scratch 実行（HF-FR-2 実測）** | **HOLD**（v0.1.1 must_fix 反映＋controller/owner 受理＋専用DB＋評価責任者明示後） |
| full batch / production DDL apply / production load・write | **HOLD** |
| resolver-based bridge collapse / backfill / canonical promotion | **HOLD** |
| claim-support eligibility（pending / candidate_resolved L3） / embedding / MCP | **HOLD** |
| scratch PASS の production 権限流用（INV-4） | **禁止** |

一行サマリ: **runbook accepted・full-root scratch packet は設計GO。実行/本番は全て HOLD、owner lift 未。**

## 6. 次アクション
1. v0.1.1（must_fix 6件込み）を controller/owner レビューに回す。
2. 受理後の **SQL generator 生成（DB write 無し）** は GO。
3. **full-root scratch 実行と owner lift は owner の明示判断**（head から先行実行しない）。
