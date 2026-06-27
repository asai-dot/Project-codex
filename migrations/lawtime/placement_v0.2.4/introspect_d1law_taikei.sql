-- DD-LAWTIME-001 v0.2.4 — 母屋 introspection（READ-ONLY / 課金ゼロ / branch 不要）
-- ============================================================================
-- 目的: 本物の d1law_taikei.alo_edges の「実スキーマ」を read-only で取得し、
--   ローカル smoke の fixture (000_external_dependency_d1law_taikei.sql) を実物に
--   1:1 で合わせるための材料にする。これにより branch を作らず（＝課金ゼロ）に
--   「100/200/300 が本物の母屋に当たるか」のスキーマ整合を検証できる（PHASE B'）。
--
-- ⚠️ SELECT のみ。INSERT/UPDATE/DELETE/DDL は一切含まない。書込みゼロ・課金ゼロ。
--   Supabase MCP では execute_sql でそのまま流せる（read-only）。
-- ============================================================================

-- (1) alo_edges の列・型・NULL 可否・既定値 ----------------------------------
SELECT ordinal_position, column_name, data_type, udt_name,
       is_nullable, column_default, character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'd1law_taikei' AND table_name = 'alo_edges'
ORDER BY ordinal_position;

-- (2) 主キー（edge_id の実型を FK 側と突き合わせる肝）------------------------
SELECT kcu.column_name, c.data_type, c.udt_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON kcu.constraint_name = tc.constraint_name AND kcu.table_schema = tc.table_schema
JOIN information_schema.columns c
  ON c.table_schema = kcu.table_schema AND c.table_name = kcu.table_name
 AND c.column_name = kcu.column_name
WHERE tc.table_schema = 'd1law_taikei' AND tc.table_name = 'alo_edges'
  AND tc.constraint_type = 'PRIMARY KEY';

-- (3) citation 種別を見分けるカラム（side-table の two-tier 前提の検証用）-----
--    edge の「種別」を持つ列（type/kind/relation/predicate 等）を洗い出す。
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_schema = 'd1law_taikei' AND table_name = 'alo_edges'
  AND (column_name ILIKE '%type%' OR column_name ILIKE '%kind%'
       OR column_name ILIKE '%relation%' OR column_name ILIKE '%predicate%'
       OR column_name ILIKE '%edge%')
ORDER BY column_name;

-- (4) CHECK 制約（種別の取りうる値＝enum 的制約があれば拾う）-----------------
SELECT con.conname, pg_get_constraintdef(con.oid) AS definition
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
JOIN pg_namespace ns ON ns.oid = rel.relnamespace
WHERE ns.nspname = 'd1law_taikei' AND rel.relname = 'alo_edges'
  AND con.contype = 'c'
ORDER BY con.conname;

-- (5) 既存の被参照 FK（他テーブルが既に alo_edges.edge_id を参照しているか）---
--    lawtime の FK と衝突／前例がないか確認。
SELECT ns.nspname AS child_schema, rel.relname AS child_table,
       con.conname, pg_get_constraintdef(con.oid) AS definition
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
JOIN pg_namespace ns ON ns.oid = rel.relnamespace
JOIN pg_class frel ON frel.oid = con.confrelid
JOIN pg_namespace fns ON fns.oid = frel.relnamespace
WHERE con.contype = 'f'
  AND fns.nspname = 'd1law_taikei' AND frel.relname = 'alo_edges'
ORDER BY child_schema, child_table;

-- (6) lawtime / serving の名前衝突チェック（既に存在しないこと）---------------
SELECT n.nspname AS schema, c.relname AS object, c.relkind
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname IN ('lawtime','serving')
ORDER BY n.nspname, c.relname;

-- (7) 行数の桁感（任意・SELECT のみ。重ければ省略可）------------------------
-- SELECT count(*) AS alo_edges_rows FROM d1law_taikei.alo_edges;
