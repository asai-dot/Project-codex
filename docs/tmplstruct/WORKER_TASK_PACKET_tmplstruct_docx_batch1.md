# WORKER_TASK_PACKET — tmplstruct docx batch1（月30枠・owner ratify済）

```yaml
task_id: WORKER_20260608_TMPLSTRUCT_DOCX_BATCH1_001
created_at_jst: 2026-06-08
requested_by: Claude (番頭・リモート)
executor: claude-worker   # Mac CC（リーガルライブラリー .docx エクスポート権・月30枠を持つ唯一の実行者）
lifecycle: draft
role: worker_task
permission_tags:
 - docx-download-AUTHORIZED-budget-30   # ★owner ratify済（2026-06-08）。30件ちょうど。31件目以降禁止
 - no-production-db-write
 - no-DDL
 - no-SF-writeback
 - no-Box-delete
max_turns: 90
cost_cap_usd: 8
output_path: _claude_dispatch/from_worker/20260608_tmplstruct_docx_batch1_RESULT.md
upload_target: Box handoffs/gpt_ometsuke/material_queue/20260608_docx_batch1
stop_condition: one-pass-complete | needs_decision | blocked | budget_exhausted | max_turns
```

## 根拠
番頭検証 PASS_WITH_NOTES → v0.3.1 → docx_queue 精査 → **owner ratify（分散版30件）**。
本タスクで初めて月30 docx枠を消費し、**restorable_profile を実docxで充填→復元品質を検証**する。
正本: `docs/tmplstruct/docx_queue_review_batch1.md`（30件表）＋ `structure_profile_v0.2.md` §2 ＋ `archetype_classifier_spec_v0.3.md` §8。

## 対象30件（tid・budget30厳守・除外: 帰化申請のてびき等の手引書）
```
3249 5211 14950 15055 4937 11318 11325 11327 11331 1859
4262 9395 9400 2354 1988 9414 2369 9338 4323 4324
4119 2349 4168 4656 4166 14970 4163 3852 14281 14490
```

## タスク（順に・bounded）
1. **取得**: 各 tid を templates_index の `source_book_url`(legal-library.jp/r/{book}?page=N) から **.docx エクスポート（30件ちょうど）** → `~/alo-ai/work/legallib_dl/docx_batch1/<tid>.docx`。**30で打ち切り**。枠が尽きたら取得済分で `budget_exhausted` 報告。
2. **忠実構造抽出**（python-docx 等・解釈は最小、事実中心）→ `<tid>.docx_struct.json`:
   - paragraphs[{text, style_name, outline_level, numbering(ilvl/numId), is_heading}]
   - **headings_full**: 条/項/号 を**キャプション込み**で（例「第1条（目的）」）← OCRが落とした見出し文をdocxで回収
   - tables[{rows,cols,cell_texts}] / placeholders[〔〕()下線/甲乙/年月日] / signature_block
3. **restorable_profile 充填**（`structure_profile_v0.2.md §2` ＋ spec §8 メタ）→ `<tid>.restorable_profile.json`:
   fixed_spans / slots[{name,kind,pattern,required,normalization,display_format}] / repeat_groups / signature_block /
   meta{canonical_image_ref, ocr_text_hash, docx_hash, ocr_parser_version, profile_version, confidence, slot_evidence, layout_profile, validation_status:"candidate", sample_bucket}。
4. **OCR↔docx 差分**（復元価値の定量化）→ `_OCR_VS_DOCX.md`:
   各 tid で「OCR検出条数 vs docx実条数」「OCRが落とした見出しキャプション数」「OCR誤字率の目安」。← v0.2「OCRは条/文面を落とす」を実測で確証。
5. **アップロード**: Box `material_queue/20260608_docx_batch1` に 30×(.docx + .docx_struct.json + .restorable_profile.json) ＋ `_OCR_VS_DOCX.md` ＋ `_README.md`。
6. **報告**: `output_path` ＋ Box `CODEX/handoff/` に §7 schema。

## Allowed / Forbidden
- Allowed: 対象30件の .docx エクスポート（**budget 30**）、構造抽出、Box upload、report。
- Forbidden: **31件目以降の取得**・本番DB書込/DDL/SF/Box削除・templates.json改変・structure_profile 設計の確定（最終設計は番頭/GPT）・認証情報読取。
- 守秘: 実案件個人情報を含む書式は除外フラグ＋needs_decision（本30件は商用書式集由来の汎用テンプレ）。

## 7. Required output schema
```yaml
result: success | partial | needs_decision | blocked | budget_exhausted | failed
downloaded: <n>/30
docx_quota_used: <n>   # 月枠消費（30以下）
per_template: [ {tid, title, archetype, docx_clauses, ocr_clauses, captions_recovered, tables, slots_extracted, restorable_profile_ok} ]
ocr_vs_docx_summary: { avg_clause_recovery, avg_captions_recovered, notes }
uploaded: [ ... ]
needs_decision: [ ... ]
next_safe_action: 番頭が restorable_profile と OCR↔docx差分をレビュー→復元方式v0.3確定→残バッチ/事務所PDF横展開
```

## 完了後
番頭(リモートClaude)が restorable_profile 30件＋OCR↔docx差分をレビューし、**復元方式（restorable_profile）の最終形を確定**。良ければ次月枠で第2バッチ＋**事務所スキャンPDFへ横展開**のパケットを起票。
