# WORKER_TASK_PACKET — docx 抽出器 v0.2.1 再抽出（無料・既取得docx）

```yaml
task_id: WORKER_20260608_TMPLSTRUCT_REEXTRACT_001
executor: claude-worker   # Mac CC
lifecycle: draft
role: worker_task
permission_tags: [no-docx-download, no-production-db-write, no-DDL, no-SF-writeback, no-Box-delete]  # ★クォータ0・既取得docxのみ再処理
max_turns: 60
cost_cap_usd: 4
output_path: _claude_dispatch/from_worker/20260608_tmplstruct_reextract_RESULT.md
upload_target: Box handoffs/gpt_ometsuke/material_queue/20260608_docx_batch1
stop_condition: one-pass-complete | needs_decision | blocked
```

## 根拠
番頭検証 `docs/tmplstruct/VALIDATION_docx_batch1.md` = 復元方式 PASS_WITH_NOTES。欠陥 B/C/D は**既取得の21 docx**で無料修正可（A の再取得は次月枠）。

## 抽出器 v0.2.1 改修（`docx_extract` を最小差分）
- **B slot精度**: slot 候補から **fixed_spans/条キャプションに一致する括弧テキストを除外**。slot は次に限定: party-def `（以下[「『][^」』]+[」』]という）` / blank `[○〇＿_]{2,}|（[\s　]*）|〔[^〕]*〕|【[^】]+】` / money `金[\s〇○0-9,，一-龯]+円` / date `[令平昭]?[\s〇○0-9]+年[\s〇○0-9]+月[\s〇○0-9]+日|年\s*月\s*日` / rate `年[\s〇○0-9.]+[%％分]` / address `〒` 。括弧見出し（条名）は slot にしない。
- **C 英文/表条文**: 条見出し検出に `^Article\s+\d+|^Section\s+\d+|^第\s*\d+\s*条` ＋ **表セル先頭の条文**を追加。11318/11325/11327 の docx_clauses が >0 になることを確認。
- **D F1差し戻し**: docx_clauses==0 ∧ slots<=2 ∧ tables==0 の「契約title」→ archetype を **B（記入フォーム）** に戻し flag `f1_reverted_form`。対象: 3852 雇用契約書。

## タスク
1. 既取得 `docx_batch1/<tid>.docx`（21件・解析OK分）を v0.2.1 で再抽出 → `<tid>.docx_struct.v021.json` / `<tid>.restorable_profile.v021.json`。
2. `_per_template.v021.json`（docx_clauses/slots_extracted/captions/ f1_reverted）と `_DIFF_reextract.md`（v0.1→v0.2.1: slot数の減少、英文条数の回復、F1差し戻し件数）。
3. 6不正形式（4163,4166,4168,4323,4324,4937）は **再取得しない**（次月枠・A修正後）。`_BAD_DOCX` を `_PENDING_REDOWNLOAD.md` に転記。
4. Box `material_queue/20260608_docx_batch1` へ upload＋報告。

## Forbidden
**docx取得（クォータ0）**・本番DB書込/DDL/SF/Box削除・templates.json改変・設計確定・認証読取。

## 完了後
番頭が v0.2.1 プロファイルを確認 → **restorable_profile v0.3 確定** → 事務所PDF横展開を GPT再監査ゲートへ。次月枠で A修正後の再取得＋第2バッチ。
