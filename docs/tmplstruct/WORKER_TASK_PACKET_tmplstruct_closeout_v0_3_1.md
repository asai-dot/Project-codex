# WORKER_TASK_PACKET — tmplstruct closeout v0.3.1（P0×4・原則クォータ0）

```yaml
task_id: WORKER_20260611_TMPLSTRUCT_CLOSEOUT_001
executor: claude-worker   # Mac CC
lifecycle: draft
role: worker_task
permission_tags:
 - no-docx-download          # ★本パケットはクォータ0（取得しない）。batch2取得は別パケット・owner ratify後
 - no-production-db-write
 - no-DDL
 - no-SF-writeback
 - no-Box-delete
max_turns: 80
cost_cap_usd: 6
output_path: _claude_dispatch/from_worker/20260611_tmplstruct_closeout_v0_3_1_RESULT.md
upload_target: Box handoffs/gpt_ometsuke/material_queue/20260611_closeout_v0_3_1
stop_condition: one-pass-complete | needs_decision | blocked
```

## 根拠
GPT お目付け役 `from_gpt/20260611_tmplstruct_v0.3_ROLLOUT_RESULT.md` = **ROLLOUT_MODIFY_REQUIRED**。
batch2 と事務所PDF横展開の前に閉じる **P0×4**（`docs/tmplstruct/structure_profile_v0.3.1.md` §1）。**いずれもクォータ0で実装・実行可**。

## タスク（順に・bounded）

### T1 — P0-2/P0-3: classify v0.3.1 無料再分類＋deduped queue
1. `classify_archetype_v0_3_1.py`（既存・Macローカル）を全3,806件 OCR に適用 → `classification_v0.3.1.jsonl`。
   - **F1 契約title ガード**: title が `契約書|協定書|合意書|Agreement|Contract`（`承諾|同意|誓約|通知|解除|解約|申入|連絡|説明` 除外）∧ archetype=D ∧ clause_count=0 → **A/docx_required**。
   - **F2 近似 title 重複除去**: 同一/近似 title を代表1〜2件に畳む。
2. **deduped `docx_queue.csv`**（representative・docx_priority降順・重複畳み込み済）を出力。
3. `_RECLASSIFY_DIFF.md`: v0.3→v0.3.1 の D→A 移動件数（対象tid列挙）、queue 重複除去で減った件数、deduped top30。

### T2 — P0-4: independent validator 実装＋既取得21profileで実行
4. `validate_restorable_profile.py` を実装（`docs/tmplstruct/VALIDATOR_restorable_profile_spec.md` 準拠・**抽出器とは別実装**）。G1〜G7。
5. batch1 v0.2.1 の **21 profile** に走らせ `<tid>.profile_gate.json` ＋ `_GATE_SUMMARY.md` を出力。
   - G7 は batch1 に content-type 記録が無ければ `unknown` 許容（batch2 から必須）。
   - **profile 側 `restorable_profile_ok` は読まない**。struct/profile/正規化規則から独立再計算。
6. 既存21 profile を v0.3.1 meta/anchor に**最小マイグレーション**（可能な範囲で `fixed_spans.para_i/char_start/char_end/normalized_text_hash` と meta拡張を充填）。充填不能な項目は `null` 明示。

### T3 — P0-1: content-type/zip 検証フェッチャ（実装のみ・取得しない）
7. 既存ダウンロード経路に検証層を**実装**（呼び出しはしない）: ①content-type 記録 ②zip open 可否 ③`[Content_Types].xml`∧`word/document.xml` 存在 ④不正は `bad_downloads.jsonl` へ・内部budget非カウント ⑤公式quota実消費なら内部budgetと分離記録。
8. batch1 の6不正形式（4163,4166,4168,4323,4324,4937）を `bad_downloads.jsonl` の初期エントリに転記（再取得は次月枠・別パケット）。
9. `_FETCHER_NOTES.md`: 実装差分の要点と、batch2 取得時のフロー（取得→検証→不正は再取得キュー）。

### T4 — アップロード＋報告
10. Box `material_queue/20260611_closeout_v0_3_1` へ: `classification_v0.3.1.jsonl` / deduped `docx_queue.csv` / `_RECLASSIFY_DIFF.md` / 21×`profile_gate.json` / `_GATE_SUMMARY.md` / 21×移行後 profile / `bad_downloads.jsonl` / `_FETCHER_NOTES.md` / `_README.md`。
11. `output_path` に §結果schema で報告。

## Forbidden
**docx取得（クォータ0・batch2は別パケット）**・本番DB書込/DDL/SF/Box削除・templates.json改変・設計確定・3852のA→B本反映（owner承認後）・認証情報読取。

## 結果schema
```yaml
result: success | partial | needs_decision | blocked
reclassify: { d_to_a_moved: <n>, moved_tids: [...], queue_dedup_removed: <n>, deduped_queue_top30: [...] }
validator: { profiles_checked: 21, overall_pass: <n>, blocking_tids: [...], g6_warnings: <n> }
fetcher: { implemented: true, bad_downloads_seeded: 6 }
uploaded: [ ... ]
needs_decision: [ ... ]
next_safe_action: 番頭が deduped queue top30 と gate summary を確認 → owner ratify → batch2 取得パケット起票 → 後段で Phase B shadow-run を別ゲートへ
```

## 完了後
番頭（リモートClaude）が deduped queue・gate証跡・fetcher を確認 → owner ratify → batch2 取得パケット（content-type検証フロー込み）→ closeout後に **事務所PDF shadow-run（Phase B）を別ゲート**で起票。
