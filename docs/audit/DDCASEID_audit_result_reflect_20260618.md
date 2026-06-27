# DDCASEID 監査結果 reflect + accept package (ループ返り便処理)

- date: 2026-06-19 JST（監査返却） / 処理 2026-06-18 セッション
- loop: GPT Pro 監査ループ（`gpt_ometsuke`）の返り便を Claude 側で処理
- REQUEST: `20260618_DD-CASEID-001_meaning_audit_DDCASEID_REQUEST.md`（Box 2294732774081）
- RESULT: `20260618_DD-CASEID-001_meaning_audit_DDCASEID_RESULT.md`（Box 2294753110991, reviewed 2026-06-19）

---

## 1. verdict と routing

| 項目 | 値 |
|---|---|
| verdict | **`DDCASEID_PASS_WITH_NOTES`** |
| blocking must_fix | **なし**（"blocking must_fix はない"） |
| loop_state | returned → **ratify**（LOOP_RULE: PASS_WITH_NOTES/blocking無 → approval_queue → ratify_wait） |
| 次アクション | **owner ratify**（`_accepted_v1.0_with_notes` 昇格は owner-gated） |
| HOLD | DDL/DB write/canonical mint/alo_edges/reviewed=true/claim_support/MCP/vector serve/source mutation/**jufu出口利用** |

GPT総合判定（原文要旨）: 「中核判断（特定＝自然キー と ID確定＝case_key を分ける）は正しい。むしろ分けない方が危険。design accept 可。ただし accept-notes を必ず付すこと。」

---

## 2. accept-notes（`_accepted_v1.0_with_notes` に必ず明記する5点）

監査の must_fix（=blocking ではないが accept note 必須）:

1. **`case_key ≠ canonical_uri ≠ natural_key`** をDD本文に明記（case_key=内部surrogate不変anchor / canonical_uri=外部表示・解決名 / natural_key=観測属性。三者は別責務）。
2. **merge禁止原則**を「別判断＝別case_key、関係は edge」と明文化（審級・原処分・取消訴訟・答申・ADRは同一事件性があっても別case_key）。
3. **jufu（受任手元判決）**は identity evidence には使えるが、**claim_support / MCP / export は不可**を明記。
4. **DD-CASE-001 reconcile メモを `_accepted_v1.0` の前提資料**にする（→ 本セッションで起票: `DD-CASE-001_DDCASEID_reconcile_20260618.md`）。
5. **DDL/DB/canonical mint は本監査では許可されない**と明記。

## 3. should_fix（accept後に反映する改善5点）

1. Tier B/C 人手レビュー項目に「裁判所表記・日付・事件番号・外部ID・source_system・content_grade」を最低表示（→ S5 レビュー枠 `CASE_HUMAN_REVIEW_SAMPLE_FRAME` に反映済の方向）。
2. `resolution_log` に `decision_basis / evidence_observation_ids / decided_by / decided_at / supersedes_resolution_id` を追加。
3. split/merge 再審査に備え、case_key 廃止ではなく **tombstone / superseded_by**（DD-CASEID の `merged_into_case_key` を superseded系へ一般化）。
4. `forum_code` registry に `forum_type / jurisdiction_scope / source_basis / valid_from/to` を追加（→ 31d forum registry spec 側）。
5. fuzzy は自動merge禁止＝**review queue 生成に限定**（既存設計と整合、明文化のみ）。

## 4. 監査の重要補強（finding H）

- NII∩D1 norm一致 12,661件を**「正解」と過信しない**。初回投入では非一致・片側のみ・番号崩れ・裁判所表記揺れを **Tier B/C に逃がす**。
- **false merge の方が false split より危険** → 初期は **split 寄り**でよい。
- → G2ゲート §1 の「canonical名寄せ確定は少量・高信頼サブセットから」と整合。初回 Tier A 自動bind は高信頼の一部に限定する方針を確定。

## 5. ループ・ハイジーン（残務）

- REQUEST の Box description は既に `processed_by_gpt; result=...; label=DDCASEID_PASS_WITH_NOTES` に更新済。
- 物理的な `to_gpt/processed/` 退避・`_AUDIT_LEDGER.jsonl` 追記・approval_queue カード作成は、`alo_gpt_audit.py close-all --apply`（Box Drive マウントのある Mac CC 単一書き手）で実行する（本リモート環境はマウント無のため未実行）。**承認不要の事務**。
- 反映（reflect）= 本書 + reconcile メモ + ratification 更新で完了。

---

## 6. owner digest（5行）

```
監査: DD-CASEID-001 独立意味監査（GPT Pro, gate=DDCASEID）
結論: DDCASEID_PASS_WITH_NOTES / blocking無 → design accept 可、ratify待ち
条件: accept-notes 5点明記 ＋ DD-CASE-001 reconcile（本セッション起票）
注意: false merge > false split。初回は split寄り・高信頼少量から（HOLD: DDL/canonical/jufu出口）
次手: 浅井ratify → _accepted_v1.0_with_notes 昇格 → 下位DD(CASEID-002/forum seed)
```

→ **オーナーへの依頼**: 上記 accept-notes 5点込みで DD-CASEID-001 を `_accepted_v1.0_with_notes` に ratify してよいか。OKなら Box DD正本の昇格（owner-gated）を正式経路で行う。
