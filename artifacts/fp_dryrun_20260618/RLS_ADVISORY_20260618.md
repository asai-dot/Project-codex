# RLS_ADVISORY_20260618 — RLS無効テーブルの指摘（報告のみ・未適用）

```yaml
doc_id: RLS-ADVISORY-20260618
status: report_only (NOT APPLIED)
created_at: 2026-06-18 JST
author: Claude (WO-BIBREC-FPDRYRUN-RECFIX-20260618 セッション中に検出した別件)
supabase_project: nixfjmwxmgugiiuqfuym  # asai-dot's Project
gate: READ_ONLY_STRICT (検出は SELECT のみ。remediation SQL は提示のみで未実行)
```

> **本WO（fingerprint dry-run + 記録整備）の対象外の別件**。Supabase MCP `list_tables` の critical advisory
> および `pg_class`/`pg_policy` の read-only 確認で検出。**自動適用していない**（空ポリシーで RLS を有効化すると
> 全アクセスが遮断されるため、ポリシー設計を伴う owner 判断事項）。

## 1. 検出（2026-06-18, SET TRANSACTION READ ONLY）

`biblio` / `bookdx` スキーマで **RLS 無効かつポリシー 0 件**のテーブル = **6件**:

| schema.table | 行数(概算) | rls_enabled | policy_count | 中身 |
|---|---:|---|---:|---|
| biblio.book_links | 0 | false | 0 | 書籍↔ソースリンク（未投入） |
| biblio.books | 3,802 | false | 0 | 弁コム書誌（痩せコピー） |
| biblio.books_load_log | 3,803 | false | 0 | books ロードログ |
| biblio.library_sources | 0 | false | 0 | ソース定義（未投入） |
| biblio.toc_nodes | 552,596 | false | 0 | **TOCノード全量** |
| bookdx.purchase_wishlist | 6 | false | 0 | 手動購入ウィッシュリスト |

（参考: `biblio.bib_records` / `bookdx.holdings` / `bookdx.candidates` / `biblio.bib_toc` 等は RLS 有効。）

## 2. リスクと但し書き（過大評価しないための条件）

- Supabase の anon/authenticated ロールは **PostgREST 経由**でテーブルに到達する。RLS 無効テーブルは、**そのスキーマが API 公開スキーマ(`PGRST db_schemas`, 既定は `public`)に含まれている場合に限り**、anon キーで全行 read/write 可能になる。
- 本件の対象は `biblio` / `bookdx` スキーマ。**これらが API 公開スキーマに含まれていなければ、anon からは到達不能**（RLS 無効でも REST 露出なし）。→ **まず公開スキーマ設定の確認が先**。
- 公開スキーマに含まれる場合は実害（特に `toc_nodes` 55万行・`books` 3,802 が anon 読み書き可能）。台帳の `external_share_allowed=false` 方針とも矛盾するため要対処。

## 3. remediation 案（未適用・owner 判断後に実行）

空ポリシーで有効化すると全遮断になる。**有効化とポリシー付与はセット**で行うこと。

```sql
-- (a) まず公開スキーマを確認（露出有無の判定）
--     Supabase ダッシュボード > Project Settings > API > Exposed schemas、
--     または: SHOW pgrst.db_schemas; （環境により取得方法が異なる）

-- (b) 露出している場合の最小対処: RLS 有効化 + service_role 以外を拒否（読み取りも止める）
ALTER TABLE biblio.book_links       ENABLE ROW LEVEL SECURITY;
ALTER TABLE biblio.books            ENABLE ROW LEVEL SECURITY;
ALTER TABLE biblio.books_load_log   ENABLE ROW LEVEL SECURITY;
ALTER TABLE biblio.library_sources  ENABLE ROW LEVEL SECURITY;
ALTER TABLE biblio.toc_nodes        ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookdx.purchase_wishlist ENABLE ROW LEVEL SECURITY;
-- ↑ ポリシー未定義なら anon/authenticated は全行アクセス不可になる（service_role は RLS バイパス）。
--   アプリが anon/authenticated で読む必要があるテーブルには、別途 SELECT ポリシーを設計して付与する。
```

## 4. 推奨アクション順

1. **owner 確認**: `biblio`/`bookdx` が API 公開スキーマか。非公開なら緊急度低（設定で十分）。
2. 公開なら上記 (b) を適用し、必要なテーブルにのみ最小権限ポリシーを設計。
3. いずれも本WOの gate 外。**本記録は提示のみ。DDL は未実行**。
