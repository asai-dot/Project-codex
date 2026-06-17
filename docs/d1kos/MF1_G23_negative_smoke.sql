-- MF-1 G23 negative smoke (scratch only / read-only to production)
-- 目的: 非配列 term_ids でも (a) エラーで落ちない (b) violation を誤検出しない ことを示す。
-- 実行: scratch/local Postgres。production テーブルには一切触れない。
-- 期待: 「OLD」はエラー、「NEW(guard)」はエラーなし・配列行のみ展開・誤検出0。

BEGIN;

CREATE TEMP TABLE g23_smoke(id int, term_ids jsonb) ON COMMIT DROP;
INSERT INTO g23_smoke VALUES
  (1, '[1,2,3]'::jsonb),   -- good array            -> 1,2,3
  (2, '"123"'::jsonb),     -- string (非配列)        -> 0件
  (3, 'null'::jsonb),      -- json null             -> 0件
  (4, '{"a":1}'::jsonb),   -- object                -> 0件
  (5, '123'::jsonb),       -- number                -> 0件
  (6, 'true'::jsonb),      -- boolean               -> 0件
  (7, '["1","x","2"]'::jsonb); -- 配列だが "x" 混在  -> 1,2 (regex で x 除外)

-- OLD（COALESCE のみ・非array で落ちる）: 検証用に明示エラーを観察したい場合だけコメント解除
-- SELECT id, jsonb_array_elements_text(COALESCE(term_ids,'[]'::jsonb)) AS t
-- FROM g23_smoke;   -- => ERROR: cannot extract elements from a scalar (id=2,5,6 等)

-- NEW（MF-1 P1 guard）: エラーなし
SELECT id, jsonb_typeof(term_ids) AS kind, count(*) AS extracted
FROM g23_smoke
CROSS JOIN LATERAL jsonb_array_elements_text(
  CASE WHEN jsonb_typeof(term_ids) = 'array' THEN term_ids ELSE '[]'::jsonb END
) AS term_id_text
WHERE term_id_text ~ '^[0-9]+$'
GROUP BY id, jsonb_typeof(term_ids)
ORDER BY id;
-- 期待: id=1 -> 3 / id=7 -> 2 のみ。id=2..6 は行が出ない（=0件・エラーなし）。

-- 受入アサーション: NEW guard で「非array が violation 化しない」= 全件エラーなく完走し、
-- id 2..6 は extracted 行が 0 であること。id=1,7 のみ数値要素を持つ。

ROLLBACK;
