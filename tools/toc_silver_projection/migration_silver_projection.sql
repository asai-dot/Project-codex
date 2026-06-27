-- migration_silver_projection.sql — Phase 2 Bronze→Silver projection
-- 状態: SCAFFOLD（NOT APPLIED）。CREATE FUNCTION / ALTER TABLE はすべて owner ratify 後の apply gate。
-- v1.2（PASS_WITH_NOTES の 7 notes 反映）に基づく草案。
--
-- 関連:
--   artifacts/phase2_silver_design_20260626/PLAN_PHASE2_BRONZE_TO_SILVER_v1_1.md（本体）
--   artifacts/phase2_silver_design_20260626/PLAN_PHASE2_v1_2_PASS_NOTES_ADDENDUM.md（差分）
--   artifacts/phase2_silver_design_20260626/CHECKSUM_CONTRACT_v1.md（bencom非接触契約）
--
-- 内訳:
--   (A) ALTER TABLE biblio.toc_nodes  -- 列追加（M2/M4/M5）
--   (B) CREATE TABLE biblio.toc_projection_run  -- manifest（M7）
--   (C) CREATE FUNCTION biblio.fn_project_toc_silver(...)  -- 本体（M3, M8, M9）
--   (D) COMMENT ON COLUMN  -- depth=tree_depth 明文化（PASS note #1）

BEGIN;

-- 依存拡張（既存環境で導入済みなら no-op）
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- (A) ALTER TABLE biblio.toc_nodes — v1.2 列追加
-- ----------------------------------------------------------------------------
-- 既存列 (id/toc_node_id/book_id/isbn/title/print_page/depth/path_text/path_id/
--         parent_toc_node_id/toc_source/toc_status/embedding) は温存。
-- v1.2 で追加するのは:
--   source_level_raw / source_level_normalized           （M2）
--   title_raw / normalization_profile_id/version / source_row_hash （M4）
--   embedding_input_hash / embedding_status / _stale_reason / _model_id / _generated_at （M5）
--   projection_run_id                                    （M7）
-- 既存 depth は tree_depth として意味を固定（PASS note #1）。
-- ============================================================================

ALTER TABLE biblio.toc_nodes
  ADD COLUMN IF NOT EXISTS source_level_raw          int,
  ADD COLUMN IF NOT EXISTS source_level_normalized   int,
  ADD COLUMN IF NOT EXISTS title_raw                 text,
  ADD COLUMN IF NOT EXISTS normalization_profile_id      text,
  ADD COLUMN IF NOT EXISTS normalization_profile_version text,
  ADD COLUMN IF NOT EXISTS source_row_hash           text,
  ADD COLUMN IF NOT EXISTS embedding_input_hash      text,
  ADD COLUMN IF NOT EXISTS embedding_status          text,
  ADD COLUMN IF NOT EXISTS embedding_stale_reason    text,
  ADD COLUMN IF NOT EXISTS embedding_model_id        text,
  ADD COLUMN IF NOT EXISTS embedding_generated_at    timestamptz,
  ADD COLUMN IF NOT EXISTS projection_run_id         text;

-- PASS note #5: embedding_status / stale_reason の語彙固定
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'toc_nodes_embedding_status_chk') THEN
    ALTER TABLE biblio.toc_nodes
      ADD CONSTRAINT toc_nodes_embedding_status_chk
      CHECK (embedding_status IS NULL
             OR embedding_status IN ('missing','active','stale'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'toc_nodes_embedding_stale_reason_chk') THEN
    ALTER TABLE biblio.toc_nodes
      ADD CONSTRAINT toc_nodes_embedding_stale_reason_chk
      CHECK (embedding_stale_reason IS NULL
             OR embedding_stale_reason IN
                ('input_hash_changed','model_id_changed','manual_invalidation'));
  END IF;
END $$;

-- PASS note #1: depth の意味を tree_depth として明文化
COMMENT ON COLUMN biblio.toc_nodes.depth IS
  'tree_depth: 1=root, child=parent.tree_depth+1. NOT the source level. See PHASE2 v1.2.';
COMMENT ON COLUMN biblio.toc_nodes.source_level_raw IS
  'Raw level from biblio.bib_toc.level (no normalization).';
COMMENT ON COLUMN biblio.toc_nodes.source_level_normalized IS
  'per-book (level - min(level)) to start at 0.';

-- 検索性能: projection_run_id でのフィルタが頻出
CREATE INDEX IF NOT EXISTS toc_nodes_projection_run_idx
  ON biblio.toc_nodes (projection_run_id);

-- ============================================================================
-- (B) manifest テーブル（M7 + PASS notes #6 bencom_touched_count gate）
-- ============================================================================

CREATE TABLE IF NOT EXISTS biblio.toc_projection_run (
  projection_run_id      text PRIMARY KEY,
  source                 text NOT NULL,
  p_dry_run              boolean NOT NULL,
  p_limit_books          int,
  plan_version           text NOT NULL DEFAULT 'phase2_v1.2',
  code_version           text,                    -- git commit / loader version
  contract_id            text NOT NULL DEFAULT 'TOC-NODES-CHECKSUM-CONTRACT-v1',
  started_at             timestamptz NOT NULL DEFAULT now(),
  finished_at            timestamptz,
  requested_by           text,
  executed_by            text NOT NULL DEFAULT SESSION_USER,
  status                 text NOT NULL DEFAULT 'running',  -- running/success/failed/rolled_back
  error_summary          text,
  -- メトリクス（M9）
  input_row_count        int,
  projected_row_count    int,
  inserted_count         int,
  updated_count          int,
  unchanged_count        int,
  skipped_count          int,
  duplicate_count        int,
  parent_missing_count   int,
  path_null_count        int,
  orphan_count           int,
  level_gap_count        int,
  root_count_distribution_summary jsonb,         -- {avg, max, p50, p99}
  level_gap_summary      jsonb,                  -- {rows, max_gap}
  -- PASS note #6: bencom_touched_count を gate condition として manifest に
  bencom_touched_count   int NOT NULL DEFAULT 0,
  -- PASS note #4: bencom 非接触は4要素複合
  bencom_check           jsonb,                  -- {before, after, equal} per CHECKSUM_CONTRACT_v1
  -- PASS note #2 / M9: acceptance sample
  sample                 jsonb,                  -- 各クラス5行
  -- 可逆性
  rollback_policy        text NOT NULL DEFAULT 'DELETE WHERE projection_run_id = :id',
  tombstone_policy       text,
  CHECK (status IN ('running','success','failed','rolled_back')),
  CHECK (bencom_touched_count >= 0)
);

CREATE INDEX IF NOT EXISTS toc_projection_run_source_idx
  ON biblio.toc_projection_run (source, started_at DESC);

COMMENT ON COLUMN biblio.toc_projection_run.bencom_touched_count IS
  'PASS note #6 gate: MUST be 0 for non-bencom runs. Function raises and rolls back if != 0.';

-- ============================================================================
-- (C) projection 本体（M3 anomaly決定表 / M8 bencom非接触 / M9 受入メトリクス）
-- ----------------------------------------------------------------------------
-- 設計:
--   - SECURITY INVOKER（DML権限は呼出元に従う）
--   - SET search_path 明示
--   - p_source は必須（PASS M8）
--   - p_dry_run=true なら何も書き込まない（PASS note #7: dry-run は read-only）
--   - p_dry_run=false なら 1トランザクションで manifest + insert/update を一気通貫
--   - bencom_touched_count != 0 で RAISE → ROLLBACK
-- ============================================================================

CREATE OR REPLACE FUNCTION biblio.fn_project_toc_silver(
  p_source       text,
  p_dry_run      boolean DEFAULT true,
  p_limit_books  int     DEFAULT NULL,
  p_norm_profile text    DEFAULT 'nfkc_trim_v1',
  p_code_version text    DEFAULT NULL,
  p_requested_by text    DEFAULT NULL
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, biblio
AS $$
DECLARE
  v_run_id              text;
  v_metrics             jsonb;
  v_bencom_before       jsonb;
  v_bencom_after        jsonb;
  v_inserted            int := 0;
  v_updated             int := 0;
  v_unchanged           int := 0;
  v_touched_bencom      int := 0;
BEGIN
  IF p_source IS NULL OR p_source = '' THEN
    RAISE EXCEPTION 'p_source is required (PASS M8)';
  END IF;
  IF p_source = 'bencom-library' THEN
    RAISE EXCEPTION 'bencom-library projection is Phase 2.5 (separate ratify), not allowed here';
  END IF;

  v_run_id := format('proj:%s:%s:%s',
                     p_source,
                     to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYYMMDDTHH24MISSZ'),
                     substr(md5(random()::text || clock_timestamp()::text), 1, 6));

  ------------------------------------------------------------------------
  -- (1) preflight: ordinal / level
  ------------------------------------------------------------------------
  PERFORM 1 FROM biblio.bib_toc t
    JOIN biblio.bib_records r ON r.bib_id = t.bib_id
   WHERE r.source = p_source AND (t.ordinal IS NULL OR t.level IS NULL)
   LIMIT 1;
  IF FOUND THEN
    RAISE EXCEPTION 'preflight failed: NULL ordinal/level present for source=%', p_source;
  END IF;

  -- duplicate (bib_id, ordinal)
  PERFORM 1 FROM (
    SELECT t.bib_id, t.ordinal
    FROM biblio.bib_toc t JOIN biblio.bib_records r ON r.bib_id = t.bib_id
    WHERE r.source = p_source
    GROUP BY t.bib_id, t.ordinal HAVING count(*) > 1
  ) z LIMIT 1;
  IF FOUND THEN
    RAISE EXCEPTION 'preflight failed: duplicate (bib_id, ordinal) for source=%', p_source;
  END IF;

  ------------------------------------------------------------------------
  -- (2) bencom 非接触 BEFORE 計測（CHECKSUM_CONTRACT_v1）
  ------------------------------------------------------------------------
  SELECT jsonb_build_object(
    'rows',             count(*),
    'key_set_sha256',   encode(digest(string_agg(toc_node_id, ',' ORDER BY toc_node_id), 'sha256'), 'hex'),
    'aggregate_sha256', encode(digest(string_agg(
        encode(digest(
          concat_ws(chr(31),
            n.toc_node_id, n.book_id,
            coalesce(n.source_level_raw::text,'\N'),
            coalesce(n.source_level_normalized::text,'\N'),
            coalesce(n.depth::text,'\N'),                          -- tree_depth
            coalesce(n.parent_toc_node_id,'\N'),
            coalesce(n.path_text,'\N'),
            coalesce(n.title_raw,'\N'),
            coalesce(n.title,'\N'),
            coalesce(n.print_page::text,'\N'),
            coalesce(n.normalization_profile_id,'\N'),
            coalesce(n.normalization_profile_version,'\N'),
            coalesce(n.source_row_hash,'\N'),
            coalesce(n.embedding_input_hash,'\N'),
            coalesce(n.embedding_status,'\N'),
            coalesce(n.embedding_stale_reason,'\N'),
            coalesce(n.embedding_model_id,'\N'),
            coalesce(to_char(n.embedding_generated_at AT TIME ZONE 'UTC',
                             'YYYY-MM-DD HH24:MI:SS.US'),'\N')
          ), 'sha256'), 'hex'),
        ',' ORDER BY toc_node_id), 'sha256'), 'hex'),
    'touched_count',    0
  ) INTO v_bencom_before
  FROM biblio.toc_nodes n
  JOIN biblio.bib_records r ON r.bib_id = n.book_id
  WHERE r.source = 'bencom-library';

  ------------------------------------------------------------------------
  -- (3) 親決定 + tree_depth 構築（CTE; per-source）
  ------------------------------------------------------------------------
  CREATE TEMP TABLE _silver_tmp ON COMMIT DROP AS
  WITH src AS (
    SELECT r.source, t.bib_id, t.ordinal, t.level, t.text, t.page
    FROM biblio.bib_toc t JOIN biblio.bib_records r ON r.bib_id=t.bib_id
    WHERE r.source = p_source
      AND (p_limit_books IS NULL OR t.bib_id IN (
          SELECT bib_id FROM biblio.bib_records
          WHERE source = p_source LIMIT p_limit_books))
  ),
  bk AS (SELECT bib_id, min(level) AS mn FROM src GROUP BY bib_id),
  with_parent AS (
    SELECT s.bib_id, s.ordinal, s.level AS source_level_raw,
           (s.level - bk.mn) AS source_level_normalized,
           s.text, s.page,
           (SELECT s2.ordinal FROM src s2
             WHERE s2.bib_id = s.bib_id
               AND s2.ordinal < s.ordinal
               AND s2.level   < s.level
             ORDER BY s2.ordinal DESC LIMIT 1) AS parent_ordinal
    FROM src s JOIN bk USING (bib_id)
  )
  SELECT
    'tn:' || p_source || ':' || bib_id || ':' || ordinal::text AS toc_node_id,
    bib_id AS book_id,
    source_level_raw, source_level_normalized,
    parent_ordinal,
    CASE WHEN parent_ordinal IS NULL THEN NULL
         ELSE 'tn:' || p_source || ':' || bib_id || ':' || parent_ordinal::text END
      AS parent_toc_node_id,
    text AS title_raw,
    -- title_norm = trim + NFKC（pg では unaccent/translation 簡略形）
    nullif(btrim(text), '') AS title,
    page AS print_page,
    ordinal
  FROM with_parent;

  -- tree_depth は recursive 構築
  CREATE TEMP TABLE _silver_with_depth ON COMMIT DROP AS
  WITH RECURSIVE r AS (
    SELECT t.*, 1 AS tree_depth FROM _silver_tmp t WHERE parent_toc_node_id IS NULL
    UNION ALL
    SELECT c.*, p.tree_depth + 1
    FROM _silver_tmp c JOIN r p ON c.parent_toc_node_id = p.toc_node_id
  )
  SELECT * FROM r;

  -- path_text 構築（祖先たどり、 > は ＞ にエスケープ）
  CREATE TEMP TABLE _silver_final ON COMMIT DROP AS
  WITH RECURSIVE p AS (
    SELECT toc_node_id, book_id,
           array[replace(coalesce(title,''),'>','＞')] AS path_arr,
           parent_toc_node_id, tree_depth,
           source_level_raw, source_level_normalized, title_raw, title,
           print_page, ordinal
    FROM _silver_with_depth WHERE parent_toc_node_id IS NULL
    UNION ALL
    SELECT c.toc_node_id, c.book_id,
           p.path_arr || replace(coalesce(c.title,''),'>','＞'),
           c.parent_toc_node_id, c.tree_depth,
           c.source_level_raw, c.source_level_normalized, c.title_raw, c.title,
           c.print_page, c.ordinal
    FROM _silver_with_depth c JOIN p ON c.parent_toc_node_id = p.toc_node_id
  )
  SELECT toc_node_id, book_id, source_level_raw, source_level_normalized,
         tree_depth, parent_toc_node_id,
         array_to_string(path_arr, ' > ') AS path_text,
         title_raw, title, print_page, ordinal
  FROM p;

  ------------------------------------------------------------------------
  -- (4) p_dry_run=true → 何も書かずに戻る（PASS note #7）
  ------------------------------------------------------------------------
  IF p_dry_run THEN
    SELECT jsonb_build_object(
      'projection_run_id', v_run_id,
      'p_source',          p_source,
      'p_dry_run',         true,
      'plan_version',      'phase2_v1.2',
      'contract_id',       'TOC-NODES-CHECKSUM-CONTRACT-v1',
      'input_row_count',   (SELECT count(*) FROM _silver_final),
      'sample_rows',       (SELECT jsonb_agg(to_jsonb(s)) FROM (
                              SELECT * FROM _silver_final ORDER BY toc_node_id LIMIT 20) s)
    ) INTO v_metrics;
    RETURN v_metrics;
  END IF;

  ------------------------------------------------------------------------
  -- (5) 実投入（INSERT only on new toc_node_id; UPDATE on hash diff）
  ------------------------------------------------------------------------
  WITH src AS (
    SELECT f.*, encode(digest(
        concat_ws(chr(31),
          coalesce(f.path_text,''), coalesce(f.title,'')),
        'sha256'), 'hex') AS embedding_input_hash
    FROM _silver_final f
  ),
  ins AS (
    INSERT INTO biblio.toc_nodes
      (toc_node_id, book_id, source_level_raw, source_level_normalized, depth,
       parent_toc_node_id, path_text, title_raw, title, print_page,
       normalization_profile_id, normalization_profile_version, source_row_hash,
       embedding_input_hash, embedding_status, projection_run_id)
    SELECT s.toc_node_id, s.book_id, s.source_level_raw, s.source_level_normalized,
           s.tree_depth, s.parent_toc_node_id, s.path_text, s.title_raw, s.title,
           s.print_page, p_norm_profile, '1', null,
           s.embedding_input_hash, 'missing', v_run_id
    FROM src s
    ON CONFLICT (toc_node_id) DO UPDATE SET
      path_text                = EXCLUDED.path_text,
      title                    = EXCLUDED.title,
      title_raw                = EXCLUDED.title_raw,
      depth                    = EXCLUDED.depth,                 -- tree_depth
      source_level_raw         = EXCLUDED.source_level_raw,
      source_level_normalized  = EXCLUDED.source_level_normalized,
      parent_toc_node_id       = EXCLUDED.parent_toc_node_id,
      embedding_input_hash     = EXCLUDED.embedding_input_hash,
      embedding_status         = CASE
        WHEN biblio.toc_nodes.embedding IS NULL THEN 'missing'
        WHEN biblio.toc_nodes.embedding_input_hash IS DISTINCT FROM EXCLUDED.embedding_input_hash
          THEN 'stale'
        ELSE biblio.toc_nodes.embedding_status
      END,
      embedding_stale_reason   = CASE
        WHEN biblio.toc_nodes.embedding IS NOT NULL
         AND biblio.toc_nodes.embedding_input_hash IS DISTINCT FROM EXCLUDED.embedding_input_hash
          THEN 'input_hash_changed'
        ELSE biblio.toc_nodes.embedding_stale_reason
      END,
      projection_run_id        = v_run_id
    WHERE
      -- 既存と差分があるときだけ UPDATE（unchanged は skip）
      biblio.toc_nodes.path_text             IS DISTINCT FROM EXCLUDED.path_text
      OR biblio.toc_nodes.title              IS DISTINCT FROM EXCLUDED.title
      OR biblio.toc_nodes.depth              IS DISTINCT FROM EXCLUDED.depth
      OR biblio.toc_nodes.parent_toc_node_id IS DISTINCT FROM EXCLUDED.parent_toc_node_id
    RETURNING (xmax = 0) AS was_insert
  )
  SELECT count(*) FILTER (WHERE was_insert),
         count(*) FILTER (WHERE NOT was_insert)
    INTO v_inserted, v_updated
    FROM ins;

  v_unchanged := (SELECT count(*) FROM _silver_final) - v_inserted - v_updated;

  ------------------------------------------------------------------------
  -- (6) bencom 非接触 AFTER 計測
  ------------------------------------------------------------------------
  SELECT jsonb_build_object(
    'rows',             count(*),
    'key_set_sha256',   encode(digest(string_agg(toc_node_id, ',' ORDER BY toc_node_id), 'sha256'), 'hex'),
    'aggregate_sha256', encode(digest(string_agg(
        encode(digest(
          concat_ws(chr(31),
            n.toc_node_id, n.book_id,
            coalesce(n.source_level_raw::text,'\N'),
            coalesce(n.source_level_normalized::text,'\N'),
            coalesce(n.depth::text,'\N'),
            coalesce(n.parent_toc_node_id,'\N'),
            coalesce(n.path_text,'\N'),
            coalesce(n.title_raw,'\N'),
            coalesce(n.title,'\N'),
            coalesce(n.print_page::text,'\N'),
            coalesce(n.normalization_profile_id,'\N'),
            coalesce(n.normalization_profile_version,'\N'),
            coalesce(n.source_row_hash,'\N'),
            coalesce(n.embedding_input_hash,'\N'),
            coalesce(n.embedding_status,'\N'),
            coalesce(n.embedding_stale_reason,'\N'),
            coalesce(n.embedding_model_id,'\N'),
            coalesce(to_char(n.embedding_generated_at AT TIME ZONE 'UTC',
                             'YYYY-MM-DD HH24:MI:SS.US'),'\N')
          ), 'sha256'), 'hex'),
        ',' ORDER BY toc_node_id), 'sha256'), 'hex'),
    'touched_count',    v_touched_bencom
  ) INTO v_bencom_after
  FROM biblio.toc_nodes n
  JOIN biblio.bib_records r ON r.bib_id = n.book_id
  WHERE r.source = 'bencom-library';

  IF v_bencom_after IS DISTINCT FROM v_bencom_before
     OR v_touched_bencom <> 0 THEN
    RAISE EXCEPTION 'bencom non-touch invariant violated. before=% after=% touched=%',
                    v_bencom_before, v_bencom_after, v_touched_bencom;
  END IF;

  ------------------------------------------------------------------------
  -- (7) manifest INSERT（成功記録）
  ------------------------------------------------------------------------
  INSERT INTO biblio.toc_projection_run (
    projection_run_id, source, p_dry_run, p_limit_books,
    plan_version, code_version, contract_id,
    finished_at, requested_by, executed_by, status,
    input_row_count, projected_row_count,
    inserted_count, updated_count, unchanged_count,
    bencom_touched_count, bencom_check
  ) VALUES (
    v_run_id, p_source, false, p_limit_books,
    'phase2_v1.2', p_code_version, 'TOC-NODES-CHECKSUM-CONTRACT-v1',
    clock_timestamp(), p_requested_by, SESSION_USER, 'success',
    (SELECT count(*) FROM _silver_final),
    v_inserted + v_updated + v_unchanged,
    v_inserted, v_updated, v_unchanged,
    v_touched_bencom,
    jsonb_build_object('before', v_bencom_before, 'after', v_bencom_after, 'equal', true)
  );

  RETURN jsonb_build_object(
    'projection_run_id', v_run_id,
    'inserted', v_inserted, 'updated', v_updated, 'unchanged', v_unchanged,
    'bencom_touched_count', v_touched_bencom,
    'status', 'success'
  );
END;
$$;

COMMENT ON FUNCTION biblio.fn_project_toc_silver(text, boolean, int, text, text, text) IS
  'Phase 2 v1.2 bronze-to-silver projection. p_source required (M8). dry-run is read-only (PASS #7). '
  'bencom non-touch via CHECKSUM_CONTRACT_v1 with auto-rollback on diff (PASS #4/#6).';

COMMIT;

-- ============================================================================
-- ロールバック（適用後に撤去したい場合の参考）
-- ----------------------------------------------------------------------------
--   DROP FUNCTION IF EXISTS biblio.fn_project_toc_silver(text, boolean, int, text, text, text);
--   DROP TABLE IF EXISTS biblio.toc_projection_run;
--   ALTER TABLE biblio.toc_nodes
--     DROP CONSTRAINT IF EXISTS toc_nodes_embedding_status_chk,
--     DROP CONSTRAINT IF EXISTS toc_nodes_embedding_stale_reason_chk,
--     DROP COLUMN IF EXISTS projection_run_id,
--     DROP COLUMN IF EXISTS embedding_generated_at,
--     DROP COLUMN IF EXISTS embedding_model_id,
--     DROP COLUMN IF EXISTS embedding_stale_reason,
--     DROP COLUMN IF EXISTS embedding_status,
--     DROP COLUMN IF EXISTS embedding_input_hash,
--     DROP COLUMN IF EXISTS source_row_hash,
--     DROP COLUMN IF EXISTS normalization_profile_version,
--     DROP COLUMN IF EXISTS normalization_profile_id,
--     DROP COLUMN IF EXISTS title_raw,
--     DROP COLUMN IF EXISTS source_level_normalized,
--     DROP COLUMN IF EXISTS source_level_raw;
-- ============================================================================
