# 設計レビュー依頼 v0.2: purchase_recommender の Supabase データソース対応

- **版**: v0.2（v0.1 監査 `DESIGN_MODIFY_REQUIRED` の P0/P1 反映）
- **supersedes**: `20260607_purchaserec_v0.1_DESIGN`
- **依頼日**: 2026-06-07 / 依頼元: Claude Code / Owner: 浅井先生
- **対象**: asai-dot/Project-codex PR #7（購入レコメンド アイデアD / Fork 3）拡張設計
- **ステータス**: 実装未着手（再監査 PASS まで hold）

> お目付け役へ: v0.1 の指摘 F1〜F6・R0 を反映済み。§0 に対応表、§4 に改訂DDL。
> 残論点があれば指摘ください。

---

## 0. v0.1 監査指摘への対応表

| 指摘 | 重大度 | 対応 |
|---|---|---|
| **R0** SoT明記 | — | §4 DDL 冒頭＋README に固定文言バナーを追加（read replica / SoT=books.json / write-back禁止） |
| **F1** RLS/露出面 | P0 | **private `bookdx` schema** を採用（Owner決定）。`public` を使わずPostgREST非露出。SQL直結/service_role/MCP のみ。§4・§9-6 |
| **F2** 重複判定の強弱 | P0 | `isbn`/`bencom_id`＝**強一致=自動ブロック**、`title_norm`(+author/publisher)＝**ソフト=レビュー候補**（自動除外しない）。§6・§9-2 |
| **F3** profile confidence | P0 | 候補に `profile_source`(toc_term_dict/tag_domain_fallback/mixed/unclassified) と `profile_confidence`(high/medium/low) を付与。tagsのみは出力に「tag fallback」明示。§6 |
| **F4** jsonb集計VIEW | P1 | `bookdx.candidate_domain_counts` VIEW 追加。§4 |
| **F5** demand母数分離 | P1 | `demand_share_all` と `demand_share_in_scope` を分離。ランキングは in_scope、出力に使用値を明記。§6 |
| **F6** 投入監査ログ | P1 | `bookdx.load_run`（source_hash/source_files/loaded_at/loader_version）＋各表に `load_run_id`。§4・§5 |

---

## 1. 背景 / 機能（v0.1から不変）

`purchase_recommender.py`（PR #7）は、未所蔵×詳細TOCの書籍（`defer_new` ≈616冊）を
事務所の現業テーマとの関連度でランキングして購入候補を出し、2度買い防止アラートも出す。
```
relevance = Σ_domain ( demand_share_in_scope[domain] ** weight_power ) * candidate_profile[domain]
final     = relevance * flagship_weight(TOCノード数)
```
所蔵と候補を term_dict `domain_l1` 軸（commercial/civil/administrative/labor/procedure/
criminal/ip/tax）に揃えて内積。現状CI緑・合成テスト14件パス。

## 2. なぜ Supabase か（v0.1から不変）

実データ（books.json 33.6MB / bencom_clean.json 67MB）はBox取得50MB上限・文脈溢れ・
セッション切れで実行環境に持ち込めない。Postgresに載せ**SQLでサーバ側集計**すれば数KB返却で回避。
対象: `asai-dot's Project`（`nixfjmwxmgugiiuqfuym` / ap-northeast-1）。

## 3. データ源（実スキーマ確認済み・v0.1から不変）

| 論理 | ファイル | 主フィールド |
|---|---|---|
| 所蔵 | `app/data/books.json` | `id, isbn, bencomId, title, genre(str\|list), ndc, status{...}, hasToc` |
| 候補 | `archive/data_imports/bencom_clean.json` | `id, isbn, title, author, publisher, tags[], toc[].t, bencomUrl` |
| 候補主題 | `term_dict/analysis/book_coverage_by_domain.json` | `book_id, primary_domain, domain_hits{}, total_toc, matched_toc, coverage` |
| tag写像 | `term_dict/analysis/bencom_tag_domain_mapping.json` | `tag -> {domain_l1, count}` |

候補3,802件中1,907件 `unclassified`（照合が疎）→ tags fallback 重要（F3でconfidence化）。

## 4. テーブル設計（**private `bookdx` schema**）

```sql
-- ============================================================
-- bookdx_* は books.json(蔵書SoT) からの一方向リードレプリカ／分析用射影。
-- books.json remains the source of truth for holdings.
-- No write-back from bookdx.* to books.json is authorized by this DD.   [R0]
-- ============================================================
CREATE SCHEMA IF NOT EXISTS bookdx;                       -- [F1] private schema (PostgREST非露出)

-- 投入監査ログ [F6]
CREATE TABLE bookdx.load_run (
  load_run_id    text PRIMARY KEY,        -- 例 20260607T1530_books
  source_hash    text NOT NULL,           -- 投入元ファイルのhash
  source_files   jsonb NOT NULL,          -- {path: {sha256,size,mtime}}
  loaded_at      timestamptz NOT NULL DEFAULT now(),
  loader_version text NOT NULL
);

CREATE TABLE bookdx.holdings (
  internal_id text PRIMARY KEY,           -- books.json "id"
  isbn        text,                       -- 13桁正規化
  bencom_id   text,                       -- 候補突合キー（強一致）
  title       text,
  title_norm  text,                       -- ソフト一致用
  author_norm text,                       -- ソフト一致補助 [F2]
  publisher_norm text,                    -- ソフト一致補助 [F2]
  genre       jsonb,
  ndc         jsonb,
  physical    boolean,
  cut         boolean,
  scanned     boolean,
  has_toc     boolean,
  load_run_id text REFERENCES bookdx.load_run(load_run_id),  -- [F6]
  raw         jsonb
);
CREATE INDEX ix_h_isbn       ON bookdx.holdings (isbn);
CREATE INDEX ix_h_bencom_id  ON bookdx.holdings (bencom_id);
CREATE INDEX ix_h_title_norm ON bookdx.holdings (title_norm);

CREATE TABLE bookdx.candidates (
  book_id        text PRIMARY KEY,        -- bencom "id" / coverage "book_id"
  isbn           text,
  title          text,
  title_norm     text,
  author         text,
  author_norm    text,
  publisher      text,
  publisher_norm text,
  tags           jsonb,
  bencom_url     text,
  primary_domain text,
  domain_hits    jsonb,                   -- {domain:count}
  total_toc      integer,
  matched_toc    integer,
  coverage       numeric,
  profile_source     text,               -- toc_term_dict/tag_domain_fallback/mixed/unclassified [F3]
  profile_confidence text,               -- high/medium/low [F3]
  toc            jsonb,                   -- 大。読取り時は基本SELECTしない
  load_run_id    text REFERENCES bookdx.load_run(load_run_id),
  raw            jsonb
);
CREATE INDEX ix_c_isbn    ON bookdx.candidates (isbn);
CREATE INDEX ix_c_primary ON bookdx.candidates (primary_domain);

CREATE TABLE bookdx.tag_domain (
  tag       text PRIMARY KEY,
  domain_l1 text,
  count     integer
);

-- demand 集計（数十行） [F4]
CREATE VIEW bookdx.holding_genre_counts AS
SELECT g AS genre, count(*) AS n
FROM bookdx.holdings, jsonb_array_elements_text(genre) AS g
GROUP BY g;

-- 候補domain集計 [F4]
CREATE VIEW bookdx.candidate_domain_counts AS
SELECT book_id, key AS domain_l1, value::numeric AS n
FROM bookdx.candidates, jsonb_each_text(domain_hits);
```

> 注: private schema 採用により F1-B（public+RLS revoke）は不要。アクセスは
> Postgres 直結ロール / service_role / MCP `execute_sql` に限定。anon/authenticated には
> `bookdx` への権限を付与しない（`GRANT USAGE ON SCHEMA bookdx` を service ロールのみ）。

## 5. データ投入: `term_dict/scripts/load_to_supabase.py`（お手元PCで実行）

- 入力: 既存4ファイル。candidates は bencom×coverage を `id` で結合し、`profile_source`/
  `profile_confidence` を計算（§6）して格納。
- **load_run を1行作成**（source_hash=4ファイルの結合hash、source_files=各sha256、
  loader_version）。各行に `load_run_id` を付与。[F6]
- 接続: env `BOOKDX_DB_URL`。`psycopg`(v3) 遅延import。`INSERT ... ON CONFLICT DO UPDATE` 冪等。

## 6. リーダ抽象化 & スコアリング改訂

- `SupabaseDataSource(query_runner)` を追加（注入式＝テスト可能）。`bookdx` schema を読む。
  demand は `bookdx.holding_genre_counts`、候補domainは `bookdx.candidate_domain_counts` を利用。
- **F5 demand母数分離**:
  - `demand_share_all` = 全 domain 母数（参考）
  - `demand_share_in_scope` = 候補軸8 domain のみ母数（**ランキング既定**）
  - 出力（txt/csv/json）にどちらを使ったか明記。
- **F3 候補 confidence**:
  - `profile_source`: `toc_term_dict`（matched_toc十分）/ `tag_domain_fallback`（tagsのみ）/
    `mixed` / `unclassified`
  - `profile_confidence`: high（matched_toc≥閾 & coverage≥閾）/ medium（mixed）/ low（tagsのみ）
  - Top-N 出力に列追加。`low` は「tag fallback」と明示。ランキングには使うが過信させない。
- **F2 重複判定の強弱分離**:
  - 強一致（自動「所蔵済み＝買うな」）: 正規化 `isbn` 一致 / `bencom_id` 一致
  - ソフト一致（`dedup_alert` に**レビュー候補**として表示・自動除外しない）:
    `title_norm` 一致 / `title_norm`+`author_norm` / `title_norm`+`publisher_norm`
  - `dedup_alert` 出力に `match_strength`(strong/soft) と `match_reason` を持たせる。

## 7. テスト（合成・実DB不要）: `tests/test_supabase_source.py`

- フェイク query_runner で同一データなら JSON ソースと同一の recommend()/dedup_alert()。
- 追加: confidence 区分（high/medium/low）、dedup の strong/soft 分離、demand all/in_scope の検証。

## 8. 作業順序（再監査 PASS 後）

1. DDL migration（担当が MCP `apply_migration`：`bookdx` schema＋表＋VIEW＋load_run）＋ `term_dict/sql/supabase_bookdx_schema.sql`
2. `load_to_supabase.py`（投入はお手元、load_run記録）
3. リーダ抽象 + `SupabaseDataSource` + スコアリング改訂（F2/F3/F5）+ CLI `--source supabase`
4. `tests/test_supabase_source.py`
5. README（Supabase節・SoT固定文言）
6. PR #7 に積む → CI

## 9. 残監査観点（v0.2で確認したい点）

1. private `bookdx` schema ＋ service ロール限定で F1 露出面はクローズしたか。
2. F2 の強/ソフト分離の鍵（isbn/bencom_id=strong, title_norm系=soft）の線引きで十分か。
3. F3 confidence の閾値（high の matched_toc / coverage 閾）の妥当な初期値の指針。
4. F6 load_run の粒度（run単位＋行参照）で再現性・監査に足るか。
5. その他 regression。

## 10. 確認待ち
- [ ] v0.2 で P0（F1/F2/F3）クローズ＝PASS 可能か、追加修正要か。
