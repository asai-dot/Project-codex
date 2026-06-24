# WORKER_TASK_PACKET — tmplstruct: 出典本175冊 × 蔵書(books.json) 突合＋native直DL検証

```yaml
task_id: WORKER_20260611_TMPLSTRUCT_SRCBOOK_MATCH_001
created_at_jst: 2026-06-11
requested_by: Claude (浅井先生担当・リモートセッション / 番頭)
executor: claude-worker   # Mac CC（books.json ローカル実体・弁コム認証セッションを持つ唯一の実行者）
lifecycle: draft
role: worker_task
permission_tags:
 - no-docx-download           # ★本パケットはクォータ0。native直DLの「検証」はT3で最大3件のみ・明示許可
 - native-dl-PROBE-budget-3   # tmpl_link_url が月30 .docx枠を消費するか確認するための最小プローブ(3件)
 - no-production-db-write
 - no-DDL
 - no-SF-writeback
 - no-Box-delete
 - no-bookjson-write          # books.json は読むだけ・絶対に改変しない
max_turns: 60
cost_cap_usd: 5
output_path: _claude_dispatch/from_worker/20260611_tmplstruct_srcbook_match_RESULT.md
upload_target: Box handoffs/gpt_ometsuke/material_queue/20260611_srcbook_match
stop_condition: one-pass-complete | needs_decision | blocked
```

## 背景（なぜ）
番頭の調査 `docs/tmplstruct/sourcebook_match/FINDINGS_sourcebook_vs_bookjson.md`：
3,806書式（弁コム全体で175冊・6,976書式）は全件「出典本＋ページ＋直DL URL」を持つ。
OCR依存をやめ、(A) native原本直DL／(B) うちの現物本／(C) 自前PDF を生材料にできる可能性がある。
本パケットは **(1) books.json 所蔵突合** と **(2) native直DLが取得枠を消費するかの最小検証** を行う。

## 前提資産（実行前に存在確認）
- 出典本索引: 本ブランチ `docs/tmplstruct/sourcebook_match/source_books_175.csv`（番頭生成・確定）
- マッチャ: 本ブランチ `loaders/match_sourcebooks_to_bookjson.py`（read-only・決定論）
- 蔵書canonical: `~/alo-ai/work/.../app/data/books.json`（=Box `2161143503087` の実体・約33MB）
- カタログ: `~/alo-ai/work/bengo4_dl/templates.csv`（直DL URL 確認用）
- 出力先: Box `material_queue/20260611_srcbook_match`

## タスク（順に・bounded）

### T1 — books.json 所蔵突合（クォータ0・read-only）
1. `python3 loaders/match_sourcebooks_to_bookjson.py --source docs/tmplstruct/sourcebook_match/source_books_175.csv --books <books.json path>`
2. 出力 `sourcebook_holdings_match.csv` ＋ `_HOLDINGS_MATCH_SUMMARY.md` を確認。
   - `match` 列が `none`/`fuzzy_ambiguous` の本は、書名の版次表記揺れが原因か目視し、明らかな取りこぼしのみ
     `source_books_175.csv` の isbn を版元URLから補って再実行（books.json は触らない）。
3. サマリの「現物所蔵 or 自前PDFがある根拠本（書式数降順）」を、復元高価値（docx_priority上位本）と突き合わせる。

### T2 — ISBN欠落74冊の後追い解決（クォータ0・任意）
4. ISBN空欄の出典本のうち、版元URLにISBNが含まれるもの（三修社 `/np/isbn/…`、biz-book `/isbn/…` 等）を
   正規表現で抽出して `source_books_175.csv` の isbn を充填 → T1再実行で突合率を上げる。
   日本加除/新日本法規など社内ID形式URLは fuzzy(書名+出版社) のままでよい。

### T3 — native直DLの取得枠検証（PROBE・最大3件のみ）
5. templates.csv から **Word** 書式を3件選び、`tmpl_link_url` を**3件だけ**取得して
   ①取得可否 ②取得時に月30 .docx枠／公式quota を消費したか（前後でカウンタ確認）を記録。
   - **3件で必ず打ち切る**。枠を消費する挙動なら即停止し `needs_decision`。
   - 取得物は構造の事実確認のみ（paragraphs/tables数）。設計確定はしない。

### T4 — アップロード＋報告
6. Box `material_queue/20260611_srcbook_match` へ:
   `sourcebook_holdings_match.csv` / `_HOLDINGS_MATCH_SUMMARY.md` / `source_books_175.csv`(isbn補填後) /
   `_NATIVE_DL_PROBE.md`（T3結果）/ `_README.md`。
7. `output_path` に §結果schema で報告。

## Forbidden
books.json の改変・本番DB書込/DDL/SF/Box削除・4件目以降のnative取得・templates.csv改変・
構造プロファイルの設計確定・認証情報読取。

## 結果schema
```yaml
result: success | partial | needs_decision | blocked
holdings_match:
  source_books: 175
  matched_isbn: <n>
  matched_fuzzy: <n>
  unmatched: <n>
  owned_physical_books: <n>      # 書式数も: owned_templates: <n>
  pdf_present_books: <n>         # pdf_templates: <n>
  top_clean_material_books: [ {title, publisher, n_templates, channel:[physical|pdf|both]} , ... ]  # 上位10
native_dl_probe:
  fetched: 3
  consumes_docx_quota: true | false | unknown
  formats_ok: [word, ...]
isbn_backfilled: <n>
uploaded: [ ... ]
needs_decision: [ ... ]
next_safe_action: 番頭が holdings_match と probe結果を確認 → owner判断（P1 native主体への切替 / P2 現物・PDF活用 / P3 ISBN補完）
```

## 完了後
番頭(リモートClaude)が突合結果と直DL検証を読み、`to_gpt` に「材料チャネル切替（OCR逆算→native原本主体）」の
設計改訂案を起票。owner ratify 後に tmplstruct の取得設計を改訂する。
