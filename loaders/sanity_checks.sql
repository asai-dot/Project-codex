-- sanity_checks.sql — legallib biblio 取込後の検証クエリ
-- v0.4 プラン §5 に対応。load_legallib.py 実行後に手動で流す。
-- 対象: Supabase biblio スキーマ（search_path = biblio）

-- ① 件数確認: legallib bib_records が期待件数（書籍のみなら 2751 程度）
SELECT
  source,
  form_type,
  COUNT(*) AS cnt
FROM biblio.bib_records
WHERE source = 'legal-library'
GROUP BY source, form_type
ORDER BY form_type;

-- ② 既存 source が一切改変されていないこと（件数変化なし）
SELECT source, COUNT(*) AS cnt
FROM biblio.bib_records
WHERE source IN ('asai-bookshelf', 'bencom-library')
GROUP BY source;
-- 期待値: asai-bookshelf=6624 / bencom-library=3802

-- ③ bib_toc 孤児チェック（FK 違反 = 0）
SELECT COUNT(*) AS orphan_toc_count
FROM biblio.bib_toc t
WHERE NOT EXISTS (
  SELECT 1 FROM biblio.bib_records b WHERE b.bib_id = t.bib_id
)
AND t.bib_id LIKE 'LEGALLIB:%';

-- ④ ordinal 連番チェック（各 bib_id 内で 0 始まり連番）
SELECT
  bib_id,
  MIN(ordinal) AS min_ord,
  MAX(ordinal) AS max_ord,
  COUNT(*) AS node_cnt,
  -- 連番なら max_ord == cnt - 1
  CASE WHEN MAX(ordinal) = COUNT(*) - 1 THEN 'OK' ELSE 'GAP_DETECTED' END AS ordinal_check
FROM biblio.bib_toc
WHERE bib_id LIKE 'LEGALLIB:%'
GROUP BY bib_id
HAVING MAX(ordinal) != COUNT(*) - 1  -- 連番崩れのある bib_id のみ表示
LIMIT 20;

-- ⑤ author 誤統合チェック: 同じ normalized_key に複数 source の著者 ID が混在しないこと
SELECT normalized_key, COUNT(*) AS dup_count
FROM biblio.authors
WHERE source = 'legal-library'
GROUP BY normalized_key
HAVING COUNT(*) > 1
LIMIT 20;

-- ⑥ 冪等性確認（再実行後に件数が変わらないこと — 実行前後で比較）
SELECT
  'bib_records' AS tbl, COUNT(*) AS cnt FROM biblio.bib_records WHERE source = 'legal-library'
UNION ALL
SELECT
  'bib_toc', COUNT(*) FROM biblio.bib_toc WHERE bib_id LIKE 'LEGALLIB:%'
UNION ALL
SELECT
  'authors', COUNT(*) FROM biblio.authors WHERE source = 'legal-library'
UNION ALL
SELECT
  'bib_authors', COUNT(*) FROM biblio.bib_authors WHERE bib_id LIKE 'LEGALLIB:%';

-- ⑦ TOC 統計（書籍あたりのノード数分布）
SELECT
  percentile_cont(0.50) WITHIN GROUP (ORDER BY cnt) AS median_toc_per_book,
  percentile_cont(0.90) WITHIN GROUP (ORDER BY cnt) AS p90_toc_per_book,
  MAX(cnt) AS max_toc_per_book,
  MIN(cnt) AS min_toc_per_book
FROM (
  SELECT bib_id, COUNT(*) AS cnt
  FROM biblio.bib_toc
  WHERE bib_id LIKE 'LEGALLIB:%'
  GROUP BY bib_id
) sub;

-- ⑧ ISBN 重複（biblio 内で複数 source に同一 ISBN が存在 — 許容、authority で後処理）
SELECT isbn, COUNT(DISTINCT source) AS source_cnt, array_agg(DISTINCT source) AS sources
FROM biblio.bib_records
WHERE isbn IS NOT NULL
  AND 'legal-library' = ANY(
    ARRAY(SELECT source FROM biblio.bib_records b2 WHERE b2.isbn = biblio.bib_records.isbn)
  )
GROUP BY isbn
HAVING COUNT(DISTINCT source) > 1
LIMIT 20;
