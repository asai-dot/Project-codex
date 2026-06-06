-- supabase_schema.sql
-- 検索/RAG の保存先を将来 Supabase(pgvector) に載せ替えるための DDL。
-- 当面は data/*.json で運用するが、列構成・粒度はこの DDL と1:1対応させてある。
-- 適用先候補: alo-connect / asai-dot's Project（どちらも ap-northeast-1）。
--
-- 設計の要:
--   * toc_nodes 1行 = 目次ノード1個 = 検索/RAGチャンク1個（book_id/isbn + page_start + path をメタに保持）
--   * 着地は (book_id, source_id) ごとの book_links.offset と library_sources.url_template で生成（deeplink.js と同ロジック）
--   * 埋め込みは embedding vector 列（次元はモデルに合わせる。例は 1536）

create extension if not exists vector;

-- 図書館（4つのデータ保存）の正規設定
create table if not exists library_sources (
  id            text primary key,          -- office_pdf / bencom / legal_library / physical_shelf
  label         text not null,
  kind          text not null,             -- self_scan_pdf / digital_library / physical
  tier          text not null,             -- owned / paid
  cost          text,                      -- free / subscription
  page_strategy text not null,             -- offset_url / locate
  needs_auth    boolean not null default false,
  url_template      text,                  -- {viewer_page}=print_page+offset を含む
  book_url_template text,                  -- トップ着地用
  note          text
);

-- 蔵書マスタ（最小限。実体は app/data/books.json と対応）
create table if not exists books (
  book_id    text primary key,             -- 例: isbn_9784641138001
  isbn       text,
  title      text not null,
  author     text,
  publisher  text,
  has_toc    boolean default false,
  created_at timestamptz default now()
);
create index if not exists books_isbn_idx on books (isbn);

-- 本×図書館のリンク（在庫・キー・offset）
create table if not exists book_links (
  book_id   text not null references books(book_id) on delete cascade,
  source_id text not null references library_sources(id) on delete cascade,
  book_key  text,                          -- 有償DL側の識別子
  folder    text,                          -- office_pdf 用
  file      text,                          -- office_pdf 用
  location  text,                          -- physical_shelf 用
  "offset"  integer,                       -- viewer_page = print_page + offset（null=未校正→トップ着地）
  calibrated_at timestamptz,
  primary key (book_id, source_id)
);

-- 目次ノード＝チャンク
create table if not exists toc_nodes (
  id                 bigserial primary key,
  toc_node_id        text unique,          -- alo:book:isbn:...:toc:NNN
  book_id            text not null references books(book_id) on delete cascade,
  isbn               text,
  title              text not null,        -- ノード見出し（= 旧 t）
  print_page         integer,              -- 印刷ページ（= p / page_start）
  depth              integer default 1,
  path_text          text,                 -- 親をたどった章節パス 例: 第3章 消滅時効 > 第2節 時効の起算点
  path_id            text,                 -- toc_path_id
  parent_toc_node_id text,
  toc_source         text,                 -- publisher / openbd / toc_pdf / bencom / ...
  toc_status         text,
  embedding          vector(1536)          -- ③埋め込み+RAG 用。①②段階では null のままでよい
);
create index if not exists toc_nodes_book_idx  on toc_nodes (book_id);
create index if not exists toc_nodes_title_trgm on toc_nodes using gin (title gin_trgm_ops);   -- 要 pg_trgm。②キーワード検索PoC用
-- ③RAG: 近傍探索（コサイン）。データ投入後に作成推奨。
-- create index on toc_nodes using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- pg_trgm（②キーワード検索の部分一致高速化）
create extension if not exists pg_trgm;

-- ============================================================================
-- 将来: 文献→判例リンク（docs/architecture.md §7）。
-- ベンコムの「引用判例リンク」= (書籍, 紙面ページ) → 引用判例 → 判例本文(判例秘書/LIC 等)。
-- ALOでこの遷移を所内側でシームレス化するための土台。今は未使用（コメント）。
-- ============================================================================
-- create table case_sources (               -- 判例の着地先（deeplink.js と同じデータ駆動）
--   id            text primary key,          -- hanrei_hisho / d1_law / courts_go_jp
--   label         text not null,
--   tier          text,                      -- paid / free
--   url_template  text,                      -- {case_key} を埋める
--   needs_auth    boolean default false
-- );
-- create table cases (                       -- 判例の正規レコード
--   case_id     bigserial primary key,
--   court       text,                        -- 東京高等裁判所
--   judged_on   date,                        -- 1969-05-19
--   case_number text,                        -- 昭和41年（ネ）第2780号
--   title       text,                        -- 建物収去、土地明渡請求控訴事件
--   hh_id       text,                        -- 判例秘書ID 例 L02420223
--   unique (court, judged_on, case_number)
-- );
-- create table case_citations (              -- 文献ノード/ページ → 判例 のエッジ（1ページ複数可）
--   id          bigserial primary key,
--   book_id     text references books(book_id) on delete cascade,
--   toc_node_id text references toc_nodes(toc_node_id),
--   print_page  integer,                     -- 引用が載る紙面ページ
--   case_id     bigint references cases(case_id) on delete cascade,
--   source_hint text                         -- どの図書館の引用判例リンク由来か
-- );
