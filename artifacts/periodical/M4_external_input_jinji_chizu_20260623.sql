-- M4: 外部入力反映（人事の地図 NDLBibIDキー）+ リゾルバゲート一般化
-- generated: 2026-06-23 JST / target: staging_periodical
-- 「外部入力待ち」3件のうち、Web調査で値が取れた1件を反映。

-- (1) リゾルバのゲートをキー基準に一般化:
--     held = キー無し(preferred_key NULL) or 明示保留(candidate/needs_pull/new_no_issn)。
--     → NDLBibIDキー誌(P5裁可)も解決対象に含まれる。
--     ※ issue_id_resolved の CASE 2分岐を下記に置換（列形状は不変）:
--       旧: WHEN r.status NOT IN ('confirmed','ncid_key') THEN NULL / 'held_'||r.status
--       新: WHEN r.preferred_key IS NULL OR r.status IN ('candidate','needs_pull','new_no_issn')
--            THEN NULL / 'held_'||r.status
--     （完全定義は Supabase migration: jinji_chizu_ndlbibid_key を参照）

-- (2) 人事の地図: ISSN未付番(2022創刊トレード誌)。NDL書誌ID 032430930 をキー化（P5: ISSN-L>ISSN>NDLBibID>NCID）。
UPDATE staging_periodical.journal_registry
SET ndl_bib_id='032430930', preferred_key='ndlbibid', status='ndlbibid_key',
    evidence_source='ndlsearch:R100000002-I032430930',
    note='ISSN未付番。NDL書誌ID 032430930(請求記号Z6-320)をキー化。ISSN判明時はISSN-L優先で差替'
WHERE journal_id='jinji_chizu';

-- (3) リコンサイル: 人事の地図 24行 provisional_ym → canonical_ym（ndlbib:032430930#YYYY-MM）
UPDATE staging_periodical.issue_stage s
SET issue_id=r.issue_id_resolved, issue_id_status=r.status_resolved
FROM staging_periodical.issue_id_resolved r
WHERE s.provisional_book_id=r.provisional_book_id
  AND r.journal_id='jinji_chizu'
  AND r.status_resolved IN ('canonical','canonical_ym')
  AND r.issue_id_resolved IS DISTINCT FROM s.issue_id;

-- 未反映（値未確定・registry据置）:
--   法と哲学: ISSN 2188-711X 未確認（Web調査で確証得られず・桁衝突риск実証）→ ISSN Portal/出版社一次確認待ち。
--   税経通信2026: NDL書誌(403)依存。12行 canonical_ym 据置。実通号取得後 tsuukan_crosswalk に12行追補で canonical化。
