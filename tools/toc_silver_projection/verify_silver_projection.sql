-- verify_silver_projection.sql — Phase 2 適用後検証クエリ集（read-only）
-- 状態: SCAFFOLD（NOT APPLIED の前後で手動実行する想定。本ファイル自体は何も書かない）

-- 1) 親欠落（非rootで parent_toc_node_id IS NULL）はゼロであること
SELECT count(*) AS parent_missing
FROM biblio.toc_nodes n
WHERE n.projection_run_id IS NOT NULL                    -- 今回 run 由来のみ
  AND n.depth > 1
  AND n.parent_toc_node_id IS NULL;
-- 期待: 0

-- 2) path_text 100% 充足
SELECT count(*) FILTER (WHERE path_text IS NULL OR path_text = '') AS path_null,
       count(*) AS total
FROM biblio.toc_nodes
WHERE projection_run_id IS NOT NULL;
-- 期待: path_null = 0

-- 3) tree_depth 整合性（child.depth = parent.depth + 1）
WITH issue AS (
  SELECT c.toc_node_id, c.depth AS c_depth, p.depth AS p_depth
  FROM biblio.toc_nodes c
  JOIN biblio.toc_nodes p ON p.toc_node_id = c.parent_toc_node_id
  WHERE c.projection_run_id IS NOT NULL
    AND c.depth <> p.depth + 1
)
SELECT count(*) AS depth_mismatch FROM issue;
-- 期待: 0

-- 4) bencom 非接触の最終 cross check（CHECKSUM_CONTRACT_v1 と独立に簡易確認）
SELECT count(*) AS bencom_touched_by_run
FROM biblio.toc_nodes n
JOIN biblio.bib_records r ON r.bib_id = n.book_id
WHERE r.source = 'bencom-library'
  AND n.projection_run_id IS NOT NULL;                    -- 今回 run で触れた行
-- 期待: 0

-- 5) embedding_status 分布
SELECT embedding_status, count(*)
FROM biblio.toc_nodes
WHERE projection_run_id IS NOT NULL
GROUP BY embedding_status;
-- 期待（新規 lionbolt 等）: missing がほぼ全数、active/stale は 0

-- 6) acceptance sample（クラス別 5行）
-- 6a) root
SELECT * FROM biblio.toc_nodes
WHERE projection_run_id IS NOT NULL AND depth = 1
ORDER BY book_id LIMIT 5;
-- 6b) depth=2
SELECT * FROM biblio.toc_nodes
WHERE projection_run_id IS NOT NULL AND depth = 2
ORDER BY book_id LIMIT 5;
-- 6c) depth>=3
SELECT * FROM biblio.toc_nodes
WHERE projection_run_id IS NOT NULL AND depth >= 3
ORDER BY book_id LIMIT 5;
-- 6d) level_gap（source_level_raw が parent と 2以上差）
SELECT c.toc_node_id, c.source_level_raw, p.source_level_raw AS parent_source_level
FROM biblio.toc_nodes c
JOIN biblio.toc_nodes p ON p.toc_node_id = c.parent_toc_node_id
WHERE c.projection_run_id IS NOT NULL
  AND c.source_level_raw - p.source_level_raw >= 2
ORDER BY c.book_id LIMIT 5;
-- 6e) multi_root book の root行
WITH mr AS (
  SELECT book_id, count(*) c FROM biblio.toc_nodes
  WHERE projection_run_id IS NOT NULL AND depth = 1
  GROUP BY book_id HAVING count(*) >= 10
)
SELECT n.* FROM biblio.toc_nodes n JOIN mr USING (book_id)
WHERE n.depth = 1 ORDER BY n.book_id, n.toc_node_id LIMIT 5;
-- 6f) high_root book（per-book root_count 上位5冊の root行、PASS note #2）
WITH ranked AS (
  SELECT book_id, count(*) c FROM biblio.toc_nodes
  WHERE projection_run_id IS NOT NULL AND depth = 1
  GROUP BY book_id ORDER BY c DESC LIMIT 5
)
SELECT n.* FROM biblio.toc_nodes n JOIN ranked USING (book_id)
WHERE n.depth = 1 ORDER BY n.book_id, n.toc_node_id;
-- 6g) long_title
SELECT * FROM biblio.toc_nodes
WHERE projection_run_id IS NOT NULL AND length(title_raw) > 120
ORDER BY book_id LIMIT 5;
-- 6h) page_null
SELECT * FROM biblio.toc_nodes
WHERE projection_run_id IS NOT NULL AND print_page IS NULL
ORDER BY book_id LIMIT 5;
-- 6i) bencom_negative（同一行が前後で変化していないことのスポット）
SELECT n.toc_node_id, n.path_text
FROM biblio.toc_nodes n JOIN biblio.bib_records r ON r.bib_id = n.book_id
WHERE r.source = 'bencom-library'
ORDER BY n.toc_node_id LIMIT 5;
