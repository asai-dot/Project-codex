# tools/lionbolt_ingest — LION BOLT カタログ投入ツール

DD-LIONBOLT-INGEST v0.1（`artifacts/lionbolt_ingest_20260622/DD_LIONBOLT_INGEST_v0.1.md`）の実装。
**この時点では未実行**（DB mutation 0 / mint 0 / DDL 適用 0）。owner ratify 後に回す。

## 何をするか
LION BOLT 法律書カタログ（22,844冊 / 目次 264,555項目、Box folder 388659455439 の
`catalog_dedup.jsonl` = file 2274970590283）を Supabase に投入する:
- `biblio.library_sources` に `lionbolt` を 1 行登録
- `biblio.bib_records` に `source='lionbolt'` で 22,844 行
- `biblio.bib_toc` に 264,555 行（`toc.items[]` 展開）

既存 asai/bencom 行は**一切触らない**。重複（lionbolt × asai/bencom の同一 ISBN）は
**レポートのみ**で auto-merge / biblio_item mint はしない（DD §4）。

## ファイル
| ファイル | 役割 |
|---|---|
| `load_lionbolt.py` | ローダ。既定 dry-run（DB 非接触）で正規化・検証・dedup レポート・TSV/SQL 生成 |
| `migration_lionbolt.sql` | library_sources seed + staging + 冪等 upsert 関数（**未適用**） |

## 手順

### 1. dry-run（DB に触れない・推奨の最初の一歩）
```bash
python tools/lionbolt_ingest/load_lionbolt.py \
  --input ~/alo-ai/work/lionbolt_dl/catalog_dedup.jsonl
# → artifacts/lionbolt_ingest_20260622/build/ に
#   bib_records.tsv / bib_toc.tsv / library_source.json / load_report.json
```
`load_report.json` の `books_normalized` ≈ 22,844、`toc_rows` ≈ 264,555 を確認。

### 2. 既存 ISBN との突合レポート（任意）
```sql
-- 既存 isbn を吐く（read-only）
\copy (SELECT isbn FROM biblio.bib_records WHERE isbn IS NOT NULL) TO 'existing_isbns.txt'
```
```bash
python tools/lionbolt_ingest/load_lionbolt.py --input catalog_dedup.jsonl \
  --existing-isbns existing_isbns.txt
# → load_report.json の isbn_collision_with_existing に件数
```

### 3. 実投入（owner ratify 後のみ・READ_ONLY 解除済み前提）
```bash
# (a) マイグレーション適用（library_sources 行 + staging + upsert 関数）
psql "$SUPABASE_DSN" -f tools/lionbolt_ingest/migration_lionbolt.sql
# (b) ローダで投入
python tools/lionbolt_ingest/load_lionbolt.py --input catalog_dedup.jsonl \
  --apply --i-understand-this-writes-prod --dsn "$SUPABASE_DSN"
```

## ゲート（DD §6）
1. owner が DD を ratify（投入先・dedup 非merge・マッピング）
2. `READ_ONLY_STRICT` は本投入には適用しない別ジョブ
3. RLS: `library_sources` は現状 RLS 無効（`RLS_ADVISORY_20260618.md` 参照）。投入と RLS は別判断
4. embedding/RAG 層（`books`/`toc_nodes`）は Phase 2・本ツール非対象

## 入力が手元に無い場合
`catalog_dedup.jsonl` は Mac `~/alo-ai/work/lionbolt_dl/` か Box file `2274970590283`。
このクラウド環境にはダウンロードしていない（64MB）。実行は入力のある環境で。
