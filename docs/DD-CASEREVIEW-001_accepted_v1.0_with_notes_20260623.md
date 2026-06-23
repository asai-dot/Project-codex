# DD-CASEREVIEW-001 — サンプル監査 frame **accepted v1.0_with_notes**

- accept(ratify)日時: **2026-06-23 JST（浅井さん「5本まとめてアクセプト」）**
- lifecycle: draft v0.1 → **`accepted_v1.0_with_notes`**（design accept・production HOLD）
- 監査: **`DDCASE_PASS_WITH_NOTES`**（2026-06-23, result 2303194171044 / queue_drain 2303200695802）
- 設計本体: `DD-CASEREVIEW-001_..._draft_v0.1_20260622.md`(Box 2303069990215)
- 実装: `scripts/case_review_sample.py` / `test_case_review_sample.py`
- 役割: 精度ロードマップ⑤（実精度監視・drift→gold 還流）

> **accepted 正本**。設計本体は v0.1。accept-notes を本文則化。design accept。

## 0. 確定（accept 済の中核）
bind を層化抽出（tier×corroboration）して人手監査し、実 precision を推定・drift 検知。`CASE_HUMAN_REVIEW_SAMPLE_FRAME` の本体。

## 1.5 Accept-notes（拘束）
- **AC-1（層化）**: stratum = tier(A/B/C/prov) × corroboration。決定的（seed）抽出。worksheet は人手最小項目（CASEID-001 should_fix①）。
- **AC-2（層別目標）**: precision=correct/(correct+false_merge)。Tier A 0.99 / B 0.95 / C 0.90、未達で **drift_detected**。
- **AC-3（閉ループ）**: drift 原因 observation を ①gold の**新ハード負例**へ還流 → ②ガード強化 → 再計測。
- **AC-4（監査 note・運用前必須）**: **サンプルサイズ・信頼区間・unsure率 KPI を運用開始前に確定**（owner：許容誤差）。
- **AC-5（HOLD）**: 実運用サンプリング・人手レビューは Mac CC / HOLD。

## 2. verification
- self = `test_case_review_sample.py` green（exit 0、層化数・決定性・precision推定・drift検知）。
- audit = PASS_WITH_NOTES。owner = ratified（2026-06-23）。

## 3. 残務
- Mac CC: 実 bind の層化抽出→人手レビュー→実 precision・drift。サンプルサイズ/CI/unsure率 確定（AC-4）。worksheet を ②Tier B / ③conflict review と統合。台帳登録。
