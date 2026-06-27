-- migration_toc_path_text_trgm.sql — TOC検索精度レバー#2: path_text の trgm GIN索引
-- 状態: NOT APPLIED（owner ratify 後に適用）
-- 対象: Supabase nixfjmwxmgugiiuqfuym / biblio.toc_nodes（552,544行）
-- gate: 本ファイルは DDL の提示のみ。適用していない。可逆（DROP INDEX で完全撤去可）。
--
-- 背景（read-only 実測 2026-06-25）:
--   biblio.toc_nodes は構造完備（page 100% / path_text 100% / 階層整合100%）だが、
--   既存 trgm 索引は `title`（葉ノードのベタ見出し）のみ。トピック語は親階層
--   path_text 側にしか無いため、title 索引では取りこぼす。
--     例: title="§§329-332(西原道雄)" / path_text="第8章 先取特権 > 第3節 先取特権の順位 > ..."
--   → 「先取特権」検索は title 索引では当たらない。
--
-- 実測した recall 改善（title ILIKE のみ vs path_text ILIKE）:
--   先取特権   : 313 → 483 (+170, +54%)
--   債権者代位 : 235 → 476 (+241, +103%)
--   path_text は葉 title を末尾に含むため、title 索引の上位互換（recall 落ちなし）。

-- ============================================================================
-- 適用方法（どちらか一方）
-- ----------------------------------------------------------------------------
-- 【推奨】無停止: CONCURRENTLY はトランザクション外で実行すること。
--   apply_migration（暗黙トランザクション）ではなく execute_sql（autocommit）で:
--
--   CREATE INDEX CONCURRENTLY IF NOT EXISTS toc_nodes_path_text_trgm
--     ON biblio.toc_nodes USING gin (path_text gin_trgm_ops);
--
-- 【代替】通常: 下の BEGIN/COMMIT ブロック。構築中は書き込みを短時間ロック
--   （現状 toc_nodes は in-DB projection で常時書き込み無しのため実用上問題なし）。
-- ============================================================================

BEGIN;

-- pg_trgm は導入済み（v1.6 確認済）だが冪等のため明示
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- path_text への trgm GIN 索引（ILIKE '%...%' と類似度 % / <-> を高速化）
CREATE INDEX IF NOT EXISTS toc_nodes_path_text_trgm
  ON biblio.toc_nodes USING gin (path_text gin_trgm_ops);

COMMIT;

-- ============================================================================
-- 適用後の検証（参考）
-- ----------------------------------------------------------------------------
--   -- 索引が使われること（Bitmap Index Scan on toc_nodes_path_text_trgm を確認）:
--   EXPLAIN ANALYZE
--   SELECT book_id, path_text FROM biblio.toc_nodes
--   WHERE path_text ILIKE '%先取特権%' LIMIT 50;
--
--   -- recall 比較（適用前後で path_text 側が title 側を上回ること）:
--   SELECT
--     (SELECT count(*) FROM biblio.toc_nodes WHERE title     ILIKE '%先取特権%') title_only,
--     (SELECT count(*) FROM biblio.toc_nodes WHERE path_text ILIKE '%先取特権%') path_text;
--
-- 推奨検索クエリ形（リテラル/トピック）:
--   -- 部分一致（確実・全件）:
--   SELECT book_id, print_page, path_text FROM biblio.toc_nodes
--   WHERE path_text ILIKE '%' || :q || '%';
--   -- 類似度ランキング（曖昧入力に強い。閾値は set pg_trgm.similarity_threshold で調整）:
--   SELECT book_id, print_page, path_text, similarity(path_text, :q) AS sim
--   FROM biblio.toc_nodes
--   WHERE path_text % :q
--   ORDER BY path_text <-> :q LIMIT 50;
--
-- 任意のクリーンアップ（path_text が title の上位互換のため、title 索引は概ね冗長。
-- 即時に消す必要はないが、容量最適化時の候補）:
--   -- DROP INDEX IF EXISTS biblio.toc_nodes_title_trgm;
--
-- ロールバック:
--   DROP INDEX IF EXISTS biblio.toc_nodes_path_text_trgm;
