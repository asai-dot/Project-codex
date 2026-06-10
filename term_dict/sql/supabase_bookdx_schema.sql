-- ============================================================================
-- bookdx schema — purchase_recommender 用 private 分析レプリカ
-- ============================================================================
-- bookdx.* は books.json(蔵書SoT) からの一方向リードレプリカ／分析用射影である。
--   * books.json remains the source of truth for holdings.            [監査R0]
--   * bookdx.* is a read replica / analytical projection.
--   * No write-back from bookdx.* to books.json is authorized by this DD.
--
-- 監査 (20260607_purchaserec_v0.2_DESIGN_RESULT = PASS_WITH_NOTES) 反映:
--   F1 private schema + grants/REVOKE 明示、loader/readonly role 分離
--   F3 profile_source / profile_confidence / primary_domain / isbn に CHECK
--   F6 load_run 監査テーブル + load_run_id + source_record_hash
--
-- 適用は Owner の go + ratify 後に MCP apply_migration / service_role で。
-- 通常実行(purchase_recommender --source supabase)は bookdx_readonly で接続する。
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS bookdx;

-- --- 露出面を閉じる（PostgREST/anon/authenticated に出さない） [監査F1] ---
REVOKE ALL ON SCHEMA bookdx FROM PUBLIC;

-- --- ロール（group role）。無ければ作成。LOGIN ロールをこれに GRANT して使う ---
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bookdx_loader') THEN
    CREATE ROLE bookdx_loader NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bookdx_readonly') THEN
    CREATE ROLE bookdx_readonly NOLOGIN;
  END IF;
END $$;

-- ============================================================================
-- 監査ログ: 投入 run [監査F6]
-- ============================================================================
CREATE TABLE IF NOT EXISTS bookdx.load_run (
  load_run_id    text PRIMARY KEY,            -- 例 20260607T1530_books
  source_hash    text NOT NULL,               -- 投入元4ファイルの結合hash
  source_files   jsonb NOT NULL,              -- {path: {sha256,size,mtime}}
  loaded_at      timestamptz NOT NULL DEFAULT now(),
  loader_version text NOT NULL
);

-- ============================================================================
-- 所蔵カタログ（books.json サブセット）
-- ============================================================================
CREATE TABLE IF NOT EXISTS bookdx.holdings (
  internal_id text PRIMARY KEY,               -- books.json "id"
  isbn        text CHECK (isbn IS NULL OR isbn = '' OR isbn ~ '^[0-9]{13}$'),  -- [F4]
  bencom_id   text,                           -- 候補突合キー（強一致）
  title       text,
  title_norm  text,                           -- ソフト一致用
  author      text,
  author_norm text,
  publisher   text,
  publisher_norm text,
  genre       jsonb,
  ndc         jsonb,
  physical    boolean,
  cut         boolean,
  scanned     boolean,
  has_toc     boolean,
  source_record_hash text,                    -- 行単位の再現性 [監査F6]
  load_run_id text REFERENCES bookdx.load_run(load_run_id),
  raw         jsonb
);
CREATE INDEX IF NOT EXISTS ix_h_isbn       ON bookdx.holdings (isbn);
CREATE INDEX IF NOT EXISTS ix_h_bencom_id  ON bookdx.holdings (bencom_id);
CREATE INDEX IF NOT EXISTS ix_h_title_norm ON bookdx.holdings (title_norm);

-- ============================================================================
-- 候補プール（bencom_clean.json × book_coverage_by_domain.json を id でマージ）
-- ============================================================================
CREATE TABLE IF NOT EXISTS bookdx.candidates (
  book_id        text PRIMARY KEY,            -- bencom "id" / coverage "book_id"
  isbn           text CHECK (isbn IS NULL OR isbn = '' OR isbn ~ '^[0-9]{13}$'),  -- [F4]
  title          text,
  title_norm     text,
  author         text,
  author_norm    text,
  publisher      text,
  publisher_norm text,
  tags           jsonb,
  bencom_url     text,
  primary_domain text CHECK (primary_domain IS NULL OR primary_domain IN (   -- [F4]
                   'commercial','civil','administrative','labor',
                   'procedure','criminal','ip','tax','unclassified','unknown')),
  domain_hits    jsonb,
  total_toc      integer,
  matched_toc    integer,
  coverage       numeric,
  profile_source     text CHECK (profile_source IS NULL OR profile_source IN (  -- [F3/F4]
                       'toc_term_dict','tag_domain_fallback','mixed','unclassified')),
  profile_confidence text CHECK (profile_confidence IS NULL OR profile_confidence IN (
                       'high','medium','low')),
  toc            jsonb,                        -- 大。リーダは基本SELECTしない
  source_record_hash text,                    -- [監査F6]
  load_run_id    text REFERENCES bookdx.load_run(load_run_id),
  raw            jsonb
);
CREATE INDEX IF NOT EXISTS ix_c_isbn    ON bookdx.candidates (isbn);
CREATE INDEX IF NOT EXISTS ix_c_primary ON bookdx.candidates (primary_domain);

-- ============================================================================
-- tag → domain_l1
-- ============================================================================
CREATE TABLE IF NOT EXISTS bookdx.tag_domain (
  tag       text PRIMARY KEY,
  domain_l1 text,
  count     integer
);

-- ============================================================================
-- 集計 VIEW（サーバ側集計・返却は小） [監査F4]
-- ============================================================================
CREATE OR REPLACE VIEW bookdx.holding_genre_counts AS
SELECT g AS genre, count(*) AS n
FROM bookdx.holdings, jsonb_array_elements_text(genre) AS g
GROUP BY g;

CREATE OR REPLACE VIEW bookdx.candidate_domain_counts AS
SELECT book_id, key AS domain_l1, value::numeric AS n
FROM bookdx.candidates, jsonb_each_text(domain_hits);

-- ============================================================================
-- 権限 [監査F1/F2 of result] — loader=RW / readonly=RO。anon/authenticated は不可。
-- ============================================================================
-- 念のため明示的に剥奪（PostgREST 既定ロール）
REVOKE ALL ON ALL TABLES    IN SCHEMA bookdx FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA bookdx FROM anon, authenticated;

-- readonly: 通常実行（purchase_recommender --source supabase）用
GRANT USAGE ON SCHEMA bookdx TO bookdx_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA bookdx TO bookdx_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA bookdx GRANT SELECT ON TABLES TO bookdx_readonly;

-- loader: 投入（load_to_supabase.py）用
GRANT USAGE ON SCHEMA bookdx TO bookdx_loader;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA bookdx TO bookdx_loader;
ALTER DEFAULT PRIVILEGES IN SCHEMA bookdx
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO bookdx_loader;

-- 検証クエリ（migration後に手動確認推奨）:
--   SELECT has_schema_privilege('anon','bookdx','USAGE');          -- false 期待
--   SELECT has_schema_privilege('authenticated','bookdx','USAGE'); -- false 期待

-- ============================================================================
-- 多層防御: RLS（grant隔離に加えた第2層）。Owner 判断で適用済み 2026-06-10。
-- ポリシーは bookdx_readonly(SELECT) / bookdx_loader(ALL) のみ。anon/authenticated は
-- ポリシー無し＝遮断（かつ schema usage も無し）。所有者/postgres/service_role は
-- RLS をバイパスするため migration・管理は通る。
-- ============================================================================
ALTER TABLE bookdx.load_run   ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookdx.holdings   ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookdx.candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookdx.tag_domain ENABLE ROW LEVEL SECURITY;

CREATE POLICY ro_select ON bookdx.load_run   FOR SELECT TO bookdx_readonly USING (true);
CREATE POLICY ro_select ON bookdx.holdings   FOR SELECT TO bookdx_readonly USING (true);
CREATE POLICY ro_select ON bookdx.candidates FOR SELECT TO bookdx_readonly USING (true);
CREATE POLICY ro_select ON bookdx.tag_domain FOR SELECT TO bookdx_readonly USING (true);

CREATE POLICY loader_all ON bookdx.load_run   FOR ALL TO bookdx_loader USING (true) WITH CHECK (true);
CREATE POLICY loader_all ON bookdx.holdings   FOR ALL TO bookdx_loader USING (true) WITH CHECK (true);
CREATE POLICY loader_all ON bookdx.candidates FOR ALL TO bookdx_loader USING (true) WITH CHECK (true);
CREATE POLICY loader_all ON bookdx.tag_domain FOR ALL TO bookdx_loader USING (true) WITH CHECK (true);
