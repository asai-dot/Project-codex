# WORKER_TASK_PACKET — tmplstruct classify v0.3.1 再分類＋docx_queue（無料）

```yaml
task_id: WORKER_20260608_TMPLSTRUCT_CLASSIFY_V031_001
created_at_jst: 2026-06-08
requested_by: Claude (番頭・リモート)
executor: claude-worker   # Mac CC
lifecycle: draft
role: worker_task
permission_tags: [no-production-db-write, no-DDL, no-SF-writeback, no-Box-delete, no-docx-download]  # ★クォータ0・無料OCRのみ
max_turns: 40
cost_cap_usd: 3
output_path: _claude_dispatch/from_worker/20260608_tmplstruct_classify_v031_RESULT.md
upload_target: Box handoffs/gpt_ometsuke/material_queue/20260608_classify3806
stop_condition: one-pass-complete | needs_decision | blocked
```

## 根拠
番頭独立検証 `docs/tmplstruct/VALIDATION_classify3806_v0.3.md` = **VALIDATION PASS_WITH_NOTES**。
v0.3.1 パッチ（spec §8 の F1/F2）を当てて無料再分類し、横展開ゲートを開ける。

## タスク（既存 `loaders/classify_archetype_v0_3.py` を最小差分改修）
1. **F1 契約title ガード**を分類後段に追加（spec §8）: `契約書|協定書|合意書|Agreement|Contract` ∧ not `承諾|同意|誓約|通知|解除|解約|申入|連絡|説明` ∧ archetype==D ∧ clause_count==0 → archetype=A / source_fidelity=docx_required / flag `contract_zero_clause_needs_docx`。再計算: docx_priority_score。
2. 全3,806件を再分類 → `classification_v0.3.1.jsonl`（v0.3と同カラム＋flag列）。
3. **F2 docx_queue 生成**: source_fidelity∈{docx_required} を対象に、title正規化（空白/括弧/版表記除去）→ 同一/先頭8字一致で `dup_group` 化 → 各groupの最高score 1件を `representative_flag=1`。`docx_queue.csv`（tid,title,category_id_lib,archetype,score,ocr_gap,is_english,dup_group,representative_flag）を出力、representative を score 降順で並べる。
4. **差分レポート**: v0.3→v0.3.1 で archetype が変わった件数・一覧（特に D→A の12件前後）、docx_queue の representative 件数（=実際に月30で狙う母数）。
5. Box `material_queue/20260608_classify3806` に `classification_v0.3.1.jsonl` ＋ `docx_queue.csv` ＋ `_DIFF_v031.md` をアップロード。
6. `output_path` ＋ Box `CODEX/handoff/` に §7 schema で報告。

## Allowed / Forbidden
- Allowed: 既存OCR/分類スクリプト改修・実行、Box material_queue へupload、report。
- Forbidden: **docx取得（クォータ0）**・本番DB書込/DDL/SF/Box削除・templates.json改変・設計確定・認証読取。

## 7. Required output schema
```yaml
result: success | partial | needs_decision | blocked | failed
reclassified: <n>/3806
changed_v03_to_v031: { D_to_A: <n>, other: <n> }
changed_list_D_to_A: [ {tid,title} ... ]
docx_queue_representatives: <n>   # 重複除去後の実母数
docx_queue_top20: [ {tid,title,score} ... ]
uploaded: [ classification_v0.3.1.jsonl, docx_queue.csv, _DIFF_v031.md ]
needs_decision: [ ... ]
next_safe_action: 番頭が docx_queue 確認 → owner ratify → docx月30枠を representative 上位から開始
```

## 完了後
番頭が `docx_queue.csv` の representative 上位を確認 → owner ratify → **docx月30枠を上位から開始**（別パケット）。それまで docx取得・横展開は HOLD。
