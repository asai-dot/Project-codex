# 設計レビュー依頼: purchase_recommender の Supabase データソース対応

- **依頼日**: 2026-06-06
- **依頼元**: 浅井 / Claude Code（実装担当）
- **レビュー種別**: 監査役レビュー（実装着手前の設計監査）
- **対象PR**: asai-dot/Project-codex #7（購入レコメンド アイデアD / Fork 3）
- **ステータス**: 設計のみ。**実装未着手**。本資料の承認後に着手予定。

> 監査役へ: 本資料は単体で精査できるよう自己完結で書いています。末尾
> 「§9 監査観点」に、特に見てほしい論点を列挙しています。

---

## 1. 背景 / 何の機能か

`purchase_recommender.py`（PR #7）は、**未所蔵で詳細TOCを持つ書籍**（`defer_new`
≈616冊）を、事務所の**現業テーマとの関連度**でランキングして購入候補を出す
スタンドアロン・ツール。あわせて「2度買い防止」アラートを出す。

スコアの核:
```
relevance = Σ_domain ( demand_share[domain] ** weight_power ) * candidate_profile[domain]
final     = relevance * flagship_weight(TOCノード数)
```
- `demand_share` = 所蔵の主題分布（= 現業テーマの強さ）
- `candidate_profile` = 未所蔵候補のTOC主題分布
- 所蔵と候補を **term_dict の `domain_l1` 軸**（commercial/civil/administrative/
  labor/procedure/criminal/ip/tax）に揃えて内積。

現状は CI 緑・合成テスト14件パス。**未検証なのは実データでの実走**のみ。

## 2. 解きたい問題（なぜ Supabase か）

実データは Box/PC 側にあり、実行環境（クラウドのコンテナ）に持ち込めない:

| 壁 | 詳細 |
|---|---|
| サイズ上限 | Box の取得APIは50MB上限。`bencom_clean.json` が **67MB** で取得不可 |
| コンテキスト溢れ | 取得＝全文が文脈に乗る。`books.json` **33.6MB** は溢れる |
| セッション期限 | 大ファイルで転送中にセッション切れ（実測で2回失敗） |

→ Postgres（Supabase）に載せ、**SQLでサーバ側集計**すれば、返却は数KBで済み
3つの壁を同時に回避できる。所蔵分布・重複検出・ランキングを実行環境から実走可能。

**対象**: Supabase `asai-dot's Project`（project_id `nixfjmwxmgugiiuqfuym` /
ap-northeast-1 / 現在 public テーブル 0）。

## 3. データ源（実スキーマ確認済み）

| 論理 | ファイル | サイズ | 主フィールド |
|---|---|---|---|
| 所蔵カタログ | `app/data/books.json` | 33.6MB | `id, isbn, bencomId, title, genre(str\|list), ndc, status{physical,cut,scanned}, hasToc` |
| 候補プール | `archive/data_imports/bencom_clean.json` | 67MB | `id, isbn, title, author, publisher, tags[], toc[].t, bencomUrl` |
| 候補主題 | `term_dict/analysis/book_coverage_by_domain.json` | 1.4MB | `book_id, primary_domain, domain_hits{domain:n}, total_toc, matched_toc, coverage` |
| tag写像 | `term_dict/analysis/bencom_tag_domain_mapping.json` | 小 | `tag -> {domain_l1, count}` |

実データ実測の留意点:
- 候補3,802件中 **1,907件が `primary_domain=unclassified`**（term_dict照合が疎・
  `matched_toc` が小さい）。→ `tags`→domain フォールバックが実務上重要。
- 所蔵 genre は2系統の和集合: keyword分類（`GENRE_RULES`）＋ NDCバックフィル
  （`ndc_genre_mapping.json`、2026-05-13）。写像辞書 `GENRE_TO_DOMAIN` は両系統を網羅済み。

## 4. テーブル設計（prefix `bookdx_` / public）

配列は `jsonb`、全体は `raw jsonb` で温存（監査・将来フィールド耐性）。

```sql
CREATE TABLE bookdx_holdings (
  internal_id text PRIMARY KEY,         -- books.json "id"
  isbn        text,                     -- 13桁正規化して投入
  bencom_id   text,                     -- 候補との突合キー
  title       text,
  title_norm  text,                     -- 正規化タイトル（重複判定）
  genre       jsonb,                    -- str|list -> 配列
  ndc         jsonb,
  physical    boolean,
  cut         boolean,
  scanned     boolean,
  has_toc     boolean,
  raw         jsonb                     -- 全フィールド温存
);
CREATE INDEX ix_holdings_isbn      ON bookdx_holdings (isbn);
CREATE INDEX ix_holdings_bencom_id ON bookdx_holdings (bencom_id);
CREATE INDEX ix_holdings_title_norm ON bookdx_holdings (title_norm);

CREATE TABLE bookdx_candidates (
  book_id        text PRIMARY KEY,      -- bencom "id" / coverage "book_id"
  isbn           text,
  title          text,
  title_norm     text,
  author         text,
  publisher      text,
  tags           jsonb,
  bencom_url     text,
  primary_domain text,                  -- coverage
  domain_hits    jsonb,                 -- coverage {domain:count}
  total_toc      integer,
  matched_toc    integer,
  coverage       numeric,
  toc            jsonb,                 -- 大。読取り時は基本SELECTしない
  raw            jsonb
);
CREATE INDEX ix_cand_isbn    ON bookdx_candidates (isbn);
CREATE INDEX ix_cand_primary ON bookdx_candidates (primary_domain);

CREATE TABLE bookdx_tag_domain (
  tag       text PRIMARY KEY,
  domain_l1 text,
  count     integer
);

-- demand をサーバ側集計（返却は数十行）。domain写像はコード側 GENRE_TO_DOMAIN で実施。
CREATE VIEW bookdx_holding_genre_counts AS
SELECT g AS genre, count(*) AS n
FROM bookdx_holdings, jsonb_array_elements_text(genre) AS g
GROUP BY g;
```

候補は **bencom と coverage を `id` でマージして1テーブル**に格納（リーダが両方
必要なため）。

## 5. データ投入（file→Postgres）: `term_dict/scripts/load_to_supabase.py`

- **お手元PC/Box同期環境で実行**（実行環境からは投入不可＝同じサイズ壁）。
- 入力: 既存4ファイル（`REL` パス流用）。candidates は bencom×coverage を `id` で結合。
- 接続: env `BOOKDX_DB_URL`（Supabase の Postgres 接続文字列）。`psycopg`(v3) を
  **遅延import**、未導入なら明確なエラー。
- `INSERT ... ON CONFLICT DO UPDATE`（冪等）。`--truncate` 任意。バッチ500件。

## 6. リーダ抽象化（`purchase_recommender.py`）

- 既存 `load()`（JSON直読み）は温存。`SupabaseDataSource(query_runner)` を追加
  （`query_runner(sql)->list[dict]` を**注入**＝テスト可能）。
  - holdings: 必要列のみ（toc/raw を取らない）。dedup 用に `isbn,bencom_id,title_norm`。
  - candidates: 必要列のみ。`toc` は既定で取得しない（ペイロード最小、total_toc は列から）。
  - demand: ビュー `bookdx_holding_genre_counts` から取得し Python で `GENRE_TO_DOMAIN` 写像。
  - `query_runner` 実装: **本番**=psycopg+`BOOKDX_DB_URL`／**テスト**=フェイク／
    **実行環境での検証**=MCP `execute_sql`（スクリプト経由でなく担当が直接）。
- CLI: `--source {json,supabase}`（既定 json）。スコアリング/出力は共通。

## 7. テスト（合成・実DB不要）: `tests/test_supabase_source.py`

- フェイク query_runner にカンドrowsを返させ、**同一データなら JSON ソースと
  同一の recommend()/dedup_alert() 結果**になることを確認。既存14テストは不変。

## 8. 作業順序

1. DDL migration（担当が MCP `apply_migration`、承認後）＋ `term_dict/sql/supabase_bookdx_schema.sql`
2. `load_to_supabase.py`（投入はお手元）
3. リーダ抽象 + `SupabaseDataSource` + CLI
4. `tests/test_supabase_source.py`
5. README（Supabase節）
6. PR #7 に積む → CI

## 9. 監査観点（特に見てほしい）

1. **テーブル正規化 vs jsonb**: genre/ndc/tags/domain_hits を `jsonb` 配列で持つ方針。
   集計は `jsonb_array_elements_text` で対応。これで十分か、別正規化テーブル
   （holding_genre 等）にすべきか。
2. **重複判定の信頼性**: dedup を `isbn` / `bencom_id` / `title_norm` の一致で行う。
   `title_norm`（NFKC・記号除去）での誤検出/取りこぼしリスク。別版の扱い。
3. **demand の希釈**: 軸外ドメイン（other/information/international/medical）も
   所蔵分布の母数に入る→ 整合スコアが相対的に薄まる。正規化で順位は不変との理解で可か。
4. **疎な term_dict 照合**: 候補の半数が unclassified。`tags`→domain 依存度が高い。
   この設計上の前提でランキング品質が担保できるか（番頭目検前提で許容か）。
5. **依存追加**: 本番のみ `psycopg`(v3) を遅延import。stdlib縛りを本番だけ緩める方針で可か。
6. **Supabase セキュリティ（RLS）**: `public` に新テーブル。アクセスは Postgres 直結
   （接続文字列）想定だが、PostgREST/anon キーが有効なら public テーブルは露出しうる。
   RLS 有効化 + ポリシー（service_role のみ）を入れるべきか。**要判断**。
7. **命名/配置**: prefix `bookdx_`、project=asai-dot's Project、PR #7 集約で良いか。
8. **冪等性/監査**: `ON CONFLICT DO UPDATE` ＋ `raw jsonb` 温存で再投入安全か。

## 10. 確認待ち事項（実装可否の前提）

- [ ] prefix `bookdx_` / 1候補テーブル統合 / `psycopg` 追加 / PR #7 集約 / 担当が apply_migration 実施 — の可否
- [ ] §9-6 RLS をどうするか
