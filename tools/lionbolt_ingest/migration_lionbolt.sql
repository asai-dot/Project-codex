-- migration_lionbolt.sql — DD-LIONBOLT-INGEST v0.1 の DDL/seed
-- 状態: NOT APPLIED（owner ratify 後に適用。READ_ONLY 解除済み前提）
-- 対象: Supabase nixfjmwxmgugiiuqfuym / schema biblio
--
-- 構成:
--   (1) library_sources に lionbolt 行を seed（既存 0 行）
--   (2) staging テーブル 2 つ（\copy 受け）
--   (3) fn_lionbolt_upsert(): staging → bib_records / bib_toc へ冪等 upsert
--       既存行は触らない。lionbolt 行のみ ON CONFLICT (bib_id) で更新。
--
-- ローダ load_lionbolt.py --apply はこの fn を呼ぶ。手動でも実行可。

BEGIN;

-- (1) ソース登録 -----------------------------------------------------------
INSERT INTO biblio.library_sources
  (id, label, kind, tier, cost, page_strategy, needs_auth,
   url_template, book_url_template, note)
VALUES
  ('lionbolt', 'LION BOLT 法律書カタログ', 'commercial_catalog',
   'subscription', '3278yen/month', 'print_page', true,
   'https://api.lionbolt.jp/v2/std/books/search/initial',
   'https://law-books.lionbolt.jp/books/{book_id}',
   '著作権法47-5。書誌+構造化目次のみ、本文不取得。取得2026-06-09/10。external_share=false')
ON CONFLICT (id) DO UPDATE
  SET label = EXCLUDED.label, note = EXCLUDED.note;

-- (2) staging（ローダの TSV を \copy で流し込む。列順は load_lionbolt.py と一致） -----
DROP TABLE IF EXISTS biblio._stg_lionbolt_bib;
CREATE TABLE biblio._stg_lionbolt_bib (
  bib_id         text,
  title          text,
  responsibility text,
  publisher      text,
  pub_year       integer,
  physical       text,
  isbn           text,
  note           text,
  source         text,
  source_url     text,
  source_hash    text,
  form_type      text,
  raw            jsonb
);

DROP TABLE IF EXISTS biblio._stg_lionbolt_toc;
CREATE TABLE biblio._stg_lionbolt_toc (
  bib_id  text,
  ordinal integer,
  level   integer,
  page    integer,
  text    text
);

-- (3) 冪等 upsert 関数 ------------------------------------------------------
-- 既存 asai/bencom 行は一切触らない（WHERE source='lionbolt' 限定の delete+insert で
-- toc を作り直し、bib_records は ON CONFLICT 更新）。biblio_item mint は行わない。
CREATE OR REPLACE FUNCTION biblio.fn_lionbolt_upsert(
  p_loader_version text,
  p_source_hash    text
) RETURNS TABLE(bib_upserted bigint, toc_inserted bigint)
LANGUAGE plpgsql AS $$
DECLARE
  v_run text := 'lionbolt:' || p_source_hash;
  v_bib bigint;
  v_toc bigint;
BEGIN
  -- provenance: load_run（bencom と同じ様式）
  INSERT INTO bookdx.load_run (load_run_id, source_hash, source_files, loader_version)
  VALUES (v_run, p_source_hash,
          jsonb_build_object('catalog', 'catalog_dedup.jsonl',
                             'box_file_id', '2274970590283'),
          p_loader_version)
  ON CONFLICT (load_run_id) DO UPDATE SET loaded_at = now();

  -- bib_records: lionbolt 行のみ upsert（source_hash 不変なら実質 no-op）
  INSERT INTO biblio.bib_records
    (bib_id, title, responsibility, publisher, pub_year, physical, isbn,
     note, source, source_url, source_hash, form_type, raw)
  SELECT bib_id, title, responsibility, publisher, pub_year, physical,
         nullif(isbn, ''), note, 'lionbolt', source_url, source_hash,
         form_type, raw
  FROM biblio._stg_lionbolt_bib
  ON CONFLICT (bib_id) DO UPDATE SET
    title = EXCLUDED.title, responsibility = EXCLUDED.responsibility,
    publisher = EXCLUDED.publisher, pub_year = EXCLUDED.pub_year,
    physical = EXCLUDED.physical, isbn = EXCLUDED.isbn, note = EXCLUDED.note,
    source_url = EXCLUDED.source_url, source_hash = EXCLUDED.source_hash,
    form_type = EXCLUDED.form_type, raw = EXCLUDED.raw, updated_at = now()
  WHERE biblio.bib_records.source = 'lionbolt'        -- 既存他ソースは保護
    AND biblio.bib_records.source_hash IS DISTINCT FROM EXCLUDED.source_hash;
  GET DIAGNOSTICS v_bib = ROW_COUNT;

  -- bib_toc: lionbolt 配下を作り直し（FK 順: bib_records 投入後）
  DELETE FROM biblio.bib_toc t
   USING biblio.bib_records r
   WHERE t.bib_id = r.bib_id AND r.source = 'lionbolt';
  INSERT INTO biblio.bib_toc (bib_id, ordinal, level, page, text)
  SELECT s.bib_id, s.ordinal, s.level, s.page, s.text
  FROM biblio._stg_lionbolt_toc s
  JOIN biblio.bib_records r ON r.bib_id = s.bib_id AND r.source = 'lionbolt';
  GET DIAGNOSTICS v_toc = ROW_COUNT;

  RETURN QUERY SELECT v_bib, v_toc;
END;
$$;

-- 適用後の検証クエリ（参考。COMMIT 前に手で確認可）:
--   SELECT count(*) FROM biblio.bib_records WHERE source='lionbolt';  -- ~22,844
--   SELECT count(*) FROM biblio.bib_toc t JOIN biblio.bib_records r
--     ON r.bib_id=t.bib_id WHERE r.source='lionbolt';                 -- ~264,555
--   -- 既存件数が不変であること:
--   SELECT source, count(*) FROM biblio.bib_records GROUP BY source;
--   --   asai-bookshelf 6,524 / bencom-library 3,802 / lionbolt ~22,844

-- 注意: 確認するまで COMMIT しない運用も可。ここでは関数定義+seed+staging までを確定。
COMMIT;

-- 後始末（任意・投入確認後）:
--   DROP TABLE IF EXISTS biblio._stg_lionbolt_bib;
--   DROP TABLE IF EXISTS biblio._stg_lionbolt_toc;
