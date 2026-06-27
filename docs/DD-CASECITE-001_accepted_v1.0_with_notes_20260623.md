# DD-CASECITE-001 — 引用検証ゲート **accepted v1.0_with_notes**

- accept(ratify)日時: **2026-06-23 JST（浅井さん「5本まとめてアクセプト」）**
- lifecycle: draft v0.1 → **`accepted_v1.0_with_notes`**（design accept・production HOLD）
- 監査: **`DDCASE_PASS_WITH_NOTES`**（2026-06-23, result 2303193172349 / queue_drain 2303200695802）
- 設計本体: `DD-CASECITE-001_..._draft_v0.1_20260622.md`(Box 2303062955103)
- 実装: `scripts/case_cite_gate.py` / `test_case_cite_gate.py`
- 役割: 精度ロードマップ④（出力 L4・誤引用 0）

> **accepted 正本**。設計本体は v0.1。accept-notes を本文則化。design accept。

## 0. 確定（accept 済の中核）
CaseBundle を serve 前に fail-closed 検証し、根拠が解決しない引用・無根拠 claim を **0** に。31層 §6.3 guards を実行時ゲート化。

## 1.5 Accept-notes（拘束）
- **AC-1（V1-V7 fail-closed）**: must_cite / cite解決 / evidence必須 / pointer_case_match / range_inbounds / annotation canonical / egress。いずれか違反で **serve しない（部分配信もしない）**。
- **AC-2（ハルシネーション 0）**: cite_resolution_rate=100% / unsupported_claim=0 / egress_violation=0 を **回帰ゲート**化。
- **AC-3（V7 egress 二重化）**: global serve は `open∧public`（can_global_index）のみ引用（AC-3 守秘を出力段でも強制）。
- **AC-4（known_cases 限定）**: authoritative cite は ②BIND の **confirmed 集合のみ**。provisional / `pending_source_fixation` は使わない（CASEID-002 AC-2 と一致）。
- **AC-5（監査 note）**: **matter scope の認可チェック（authorization）を別途追加**を v0.2 で（当該 matter 関係者のみ閲覧）。
- **AC-6（HOLD）**: runtime 統合・実 cases ゲートは Mac CC / HOLD。

## 2. verification
- self = `test_case_cite_gate.py` green（exit 0、正常通過＋V1-V7 各違反を遮断）。
- audit = PASS_WITH_NOTES。owner = ratified（2026-06-23）。

## 3. 残務
- Mac CC: runtime 統合、known_cases を BIND confirmed に結線、matter 認可（v0.2）。台帳登録。
