# WORKER_TASK_PACKET — tmplstruct: 全3,806件 無料OCR archetype分類＋層化検証セット

```yaml
task_id: WORKER_20260608_TMPLSTRUCT_CLASSIFY3806_001
created_at_jst: 2026-06-08
requested_by: Claude (番頭・リモート)
executor: claude-worker   # Mac CC（templates.json / template_structure_tess.jsonl ローカル保持）
lifecycle: draft
role: worker_task
permission_tags:
 - no-production-db-write
 - no-DDL
 - no-SF-writeback
 - no-Box-delete
 - no-docx-download   # ★本タスクは無料OCRのみ。docx枠は使わない（budget 0）
max_turns: 60
cost_cap_usd: 5
output_path: _claude_dispatch/from_worker/20260608_tmplstruct_classify3806_RESULT.md
upload_target: Box handoffs/gpt_ometsuke/material_queue/20260608_classify3806
stop_condition: one-pass-complete | needs_decision | blocked | max_turns
```

## 根拠
GPT v0.2監査 `DESIGN_PASS_WITH_NOTES`。次アクション=「全3,806件に無料OCRで archetype分類→層化検証、その後に docx枠」。
仕様正本: 本ブランチ `docs/tmplstruct/archetype_classifier_spec_v0.3.md`（＋ `structure_profile_v0.2.md` §1）。

## 前提資産
- `~/alo-ai/work/legallib_dl/template_structure_tess.jsonl`（3,806件OCR・既存）＋ `templates_index.csv`（category_id_lib等）。
- **docx取得は禁止（budget 0）。再fetchなし。** 既存OCRのみ。

## タスク（順に・bounded）
1. 3,806件を読み、`spec_v0.3 §1` の規則で **archetype(A–E)＋E subtype** を**形状シグナルで**判定（title依存にしない）。判定特徴: `第N条/章`数、宛先`御中`、`ラベル：値`箇条、表セル率、ページ数、前文「甲乙…締結」。
2. `clause_count` の**抜け検出**（連番ギャップ）→ `ocr_gap` フラグ。
3. `spec_v0.3 §2` の **source_fidelity 段階値** と §3 の **docx_priority_score** を各件算出。
4. 出力（`spec_v0.3 §6`）:
   - `classification.jsonl`（3,806行・指定12カラム）
   - `confusion_matrix.csv`（category_id_lib × archetype × clause_count_bucket）
   - `ambiguous_top100.csv`（confidence下位/ambiguous上位100）
   - `validation_set.csv`（層化抽出200〜300件・人手検証用。決定論抽出）
5. **Box `material_queue/20260608_classify3806`** に上記4ファイル＋`_README.md`（分布サマリ・分類規則・再現スクリプトパス）をアップロード。
6. `output_path` ＋ Box `CODEX/handoff/` に §7 schema で報告。

## Allowed / Forbidden
- Allowed: 既存OCR/index読取・決定論分類スクリプト実行・Box material_queue へupload・report作成。
- Forbidden: **docx取得**・本番DB書込/DDL・SF書戻・Box削除・templates.json改変・structure_profile設計の確定（解釈確定は番頭/GPT）・認証情報読取。
- 守秘: 実案件個人情報を含む書式があれば該当 `template_id` を除外フラグにして needs_decision 報告。

## 7. Required output schema
```yaml
result: success | partial | needs_decision | blocked | failed
confidence: high | medium | low
records_classified: <n>/3806
archetype_distribution: { A:, B:, C:, D:, E1:, E2:, E3:, E4: }
source_fidelity_distribution: { ocr_shape_ok:, ocr_slot_ok:, ocr_search_only:, docx_required:, human_review_required: }
docx_priority_top: [ {template_id, title, score} ... 上位20 ]
ambiguous_rate: <pct>
uploaded: [ classification.jsonl, confusion_matrix.csv, ambiguous_top100.csv, validation_set.csv, _README.md ]
decision_log: [ {観測, 選択肢, 採択, 理由} ]
needs_decision: [ ... ]
next_safe_action: 番頭が validation_set を人手/高精度レビュー→precision/coverage/ambiguous_rate→docx月30キュー確定
```

## 完了後（HOLD）
docx月30キュー確定・事務所PDF横展開は、`validation_set` の検証数値が出るまで **HOLD**（GPT NOTE5）。番頭が検証 → 基準充足で docx_priority_score 上位から月30枠開始のパケットを起票。
