# DD-CASEEVAL-001 — 判例同一性の精度評価 **accepted v1.0_with_notes**

- accept(ratify)日時: **2026-06-23 JST（浅井さん「5本まとめてアクセプト」）**
- lifecycle: draft v0.1 → **`accepted_v1.0_with_notes`**（design accept・production HOLD）
- 監査: **`DDCASE_PASS_WITH_NOTES`**（2026-06-23, GPT-5.5, queue_drain result 2303200695802 / 個別 2302895922985）
- 設計本体: `DD-CASEEVAL-001_..._draft_v0.1_20260622.md`(Box 2302683608870)
- 実装: `scripts/case_eval.py` / `test_case_eval.py` / `app/data/case_identity/case_eval_gold_template.jsonl`
- 役割: 精度ロードマップ①（計測基盤）。②③④⑤の効果判定の土台

> **accepted 正本**。設計本体は v0.1。本書は ratify を記録し accept-notes を本文則化。design accept であり production acceptance ではない。

## 0. 確定（accept 済の中核）
判例同一性（L1）の精度を **false_merge 中心**で計測。主指標 `false_merge_rate`、precision 優先・初回 split 寄り（AN-4 数値化）、ハード負例4型を内蔵。

## 1.5 Accept-notes（拘束）
- **AC-1**: 主 KPI は `false_merge_rate`。bind ロジック変更で false_merge が悪化したら **回帰 fail**。
- **AC-2**: gold は正例（NII∩D1 12,661）＋**ハード負例**（same_number_diff_forum / merged_sibling_docket / provisional / era_mismatch）を必須混入。
- **AC-3（監査 note）**: cluster-level 補助指標（B-cubed 等）を **v0.2 で追加**（pairwise と併用）。
- **AC-4（HOLD）**: corpus-level 実行（実 gold）は Mac CC。DDL/DB/serving は HOLD。

## 2. verification
- self = `test_case_eval.py` green（exit 0、false_merge/false_split/per-tier precision 検出）。
- audit = PASS_WITH_NOTES（2026-06-23）。owner = ratified（2026-06-23）。

## 3. 残務
- Mac CC: 実 gold 構築（NII∩D1＋ハード負例マイニング）、corpus 計測、Tier A precision 閾値（owner）。
- Mac CC 単一書き手: DD_REGISTRY / _AUDIT_LEDGER 登録、approval_queue clear。
