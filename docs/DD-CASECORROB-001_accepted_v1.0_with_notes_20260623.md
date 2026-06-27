# DD-CASECORROB-001 — 多源コロボレーション **accepted v1.0_with_notes**

- accept(ratify)日時: **2026-06-23 JST（浅井さん「5本まとめてアクセプト」）**
- lifecycle: draft v0.1 → **`accepted_v1.0_with_notes`**（design accept・production HOLD）
- 監査: **`DDCASE_PASS_WITH_NOTES`**（2026-06-23, result 2303195665962 / queue_drain 2303200695802）
- 設計本体: `DD-CASECORROB-001_..._draft_v0.1_20260622.md`(Box 2303000584085)
- 実装: `scripts/case_corroborate.py` / `test_case_corroborate.py`
- 役割: 精度ロードマップ③（取りこぼしを安全回収）

> **accepted 正本**。設計本体は v0.1。accept-notes を本文則化。design accept。

## 0. 確定（accept 済の中核）
独立源の一致で confidence を上げ不一致を review に出す。源の種類で L1 identity / L2 annotation / L3 relation を分離。

## 1.5 Accept-notes（拘束）
- **AC-1（源種別分離・非merge）**: L1（判例DB間 自然キー一致）のみ identity 補強。**L2（解説誌 crosswalk）・L3（引用）は永久に非merge**（CASE-001 AN-2、reuse reality_check 禁止）。コロボは assignment を書き換えない。
- **AC-2（conflict は recall 回収）**: `caselaw_same_case` 主張で採番割れ＝`conflict_review` を人手回収。precision（false_merge=0）を守ったまま recall を底上げ。
- **AC-3（監査 note 確認）**: **annotation/relation の証拠は非merge を維持**（既定方針の恒久化）。
- **AC-4（reality_check 厳守）**: LIC data_no を canonical case にしない。OPAC accepted edge は review-first（現状 0）。
- **AC-5（HOLD）**: 実 link 化（D1-LIC 5,475 / OPAC）・recall 計測は Mac CC。canonical 昇格・accepted edge は HOLD。

## 2. verification
- self = `test_case_corroborate.py` green（exit 0、L1/L2/L3 分離・conflict検出・非merge）。
- audit = PASS_WITH_NOTES。owner = ratified（2026-06-23）。

## 3. 残務
- Mac CC: D1-LIC/OPAC を実 link 化、CASEEVAL で recall改善 vs false_merge を計測。台帳登録。
