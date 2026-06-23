# DD-CASEBIND-001 — false-merge 防止ガード **accepted v1.0_with_notes**

- accept(ratify)日時: **2026-06-23 JST（浅井さん「5本まとめてアクセプト」）**
- lifecycle: draft v0.1 → **`accepted_v1.0_with_notes`**（design accept・production HOLD）
- 監査: **`DDCASE_PASS_WITH_NOTES`**（2026-06-23, result 2303193170327 / queue_drain 2303200695802）
- 設計本体: `DD-CASEBIND-001_..._draft_v0.1_20260622.md`(Box 2302912765498)
- 実装: `scripts/case_bind_guard.py` / `test_case_bind_guard.py`
- 役割: 精度ロードマップ②（誤統合を防ぐ）

> **accepted 正本**。設計本体は v0.1。accept-notes を本文則化。design accept。

## 0. 確定（accept 済の中核）
決定的 blocking ＋ 多シグナル合意 ＋ fail-closed で false-merge を構造的に防ぐ（split 寄り）。gold テンプレ（ハード負例4型）で **false_merge=0 / precision=1.0** を実証。

## 1.5 Accept-notes（拘束）
- **AC-1（G1-G5 fail-closed）**: forum 跨ぎ比較禁止 / norm null・era未解決は provisional（自動bind禁止）/ 同source外部ID衝突→review / 別norm→別case_key（併合はedge, AN-2）/ Tier A のみ auto。
- **AC-2（split寄り）**: 自動bind は Tier A（決定キー合意）のみ。B/C/prov は merge しない。recall 犠牲でも false_merge を出さない。
- **AC-3（回帰ゲート）**: bind 変更で gold の false_merge_rate が悪化したら **fail**（CASEEVAL AC-1 と一致）。
- **AC-4（監査 note）**: **conflict チェックを source 横断へ拡張**（③CORROB と結線）を v0.2 で。
- **AC-5（HOLD）**: 実 gold 閾値確定・auto-bind 本番適用は Mac CC / HOLD。

## 2. verification
- self = `test_case_bind_guard.py` green（exit 0、gold false_merge=0＋G1-G5）。
- audit = PASS_WITH_NOTES。owner = ratified（2026-06-23）。

## 3. 残務
- Mac CC: 実 observation で false_merge_rate / Tier A precision 計測・閾値確定。台帳登録。
