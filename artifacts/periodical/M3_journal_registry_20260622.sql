-- M3: 誌マスタ + 決定的リゾルバ + 常設監査（A+B）
-- generated: 2026-06-22 JST / target: staging_periodical
-- 追加のみ（issue_stage本体への直接DDLなし）。冪等（IF NOT EXISTS / ON CONFLICT）。
-- ※税経通信 crosswalk 281行は artifacts/periodical/crosswalk/zeikei_tsuukan_xwalk.csv
--   および M1 を参照（本ファイルでは構造とロジックを保持）。

-- ============ A: テーブル ============
CREATE TABLE IF NOT EXISTS staging_periodical.journal_registry (
  journal_id text PRIMARY KEY, canonical_name text NOT NULL,
  issn_l text, issn text, ndl_bib_id text, ncid text,
  preferred_key text,                       -- 'issn'|'ncid'|'ndlbibid'|null
  tsuukan_rule text NOT NULL,               -- 'direct'|'formula'|'ndl_actual'|'ym_terminal'
  formula_anchor jsonb,                      -- {"anchor_ym":"YYYY-MM","anchor_tsuukan":N}
  manifestation text NOT NULL DEFAULT 'print',
  parent_journal_id text REFERENCES staging_periodical.journal_registry(journal_id),
  status text NOT NULL, evidence_source text, note text
);
CREATE TABLE IF NOT EXISTS staging_periodical.journal_alias (
  alias text NOT NULL,
  journal_id text NOT NULL REFERENCES staging_periodical.journal_registry(journal_id),
  match_type text NOT NULL, reason text, auto_apply boolean NOT NULL DEFAULT true,
  PRIMARY KEY (alias, journal_id)
);
CREATE TABLE IF NOT EXISTS staging_periodical.tsuukan_crosswalk (
  journal_id text NOT NULL REFERENCES staging_periodical.journal_registry(journal_id),
  year int NOT NULL, month int NOT NULL, tsuukan int NOT NULL, src text,
  PRIMARY KEY (journal_id, year, month)
);

-- ============ A: registry seed（29誌・最終） ============
INSERT INTO staging_periodical.journal_registry
 (journal_id,canonical_name,issn_l,issn,ncid,preferred_key,tsuukan_rule,formula_anchor,manifestation,parent_journal_id,status,note) VALUES
 ('zeikei','税経通信',null,'0387-2866',null,'issn','ndl_actual',null,'print',null,'confirmed','増刊飛び→NDL実値crosswalk'),
 ('jca','jcaジャーナル','0386-3042','0386-3042',null,'issn','formula','{"anchor_ym":"2016-01","anchor_tsuukan":703}','print',null,'confirmed','NDL27+lionbolt2検証'),
 ('blj','businesslawjournal',null,'1882-7640',null,'issn','formula','{"anchor_ym":"2019-01","anchor_tsuukan":130}','print',null,'confirmed','43通巻行で式100%一致'),
 ('biz_homu','ビジネス法務',null,'1347-4146',null,'issn','ym_terminal',null,'print',null,'confirmed','巻号のみ'),
 ('biz_guide','ビジネスガイド',null,'0387-7035',null,'issn','ym_terminal',null,'print',null,'confirmed',null),
 ('horitsu_hiroba','法律のひろば',null,'0916-9806',null,'issn','ym_terminal',null,'print',null,'confirmed','巻号運用・通巻なし(issue_noは巻内号)'),
 ('jinji_chizu','人事の地図',null,null,null,null,'ym_terminal',null,'print',null,'needs_pull','ISSN/NCID未取得'),
 ('kotsu_minji','交通事故民事裁判例集',null,'0389-6544',null,'issn','direct',null,'print',null,'confirmed',null),
 ('hogaku_kyoshitsu','法学教室',null,'0389-2220',null,'issn','direct',null,'print',null,'confirmed',null),
 ('kinyu_homu','金融法務事情',null,'2185-3223',null,'issn','direct',null,'print',null,'confirmed','旧0451-9787は別'),
 ('rodo_hanrei','労働判例',null,'0387-1878',null,'issn','direct',null,'print',null,'confirmed','労働判例ジャーナルとは別'),
 ('lt','law&technology',null,'1346-812X',null,'issn','direct',null,'print',null,'confirmed',null),
 ('keisatsu_ronshu','警察学論集',null,'0287-6345',null,'issn','direct',null,'print',null,'confirmed','旧字はalias'),
 ('horitsu_jiho','法律時報','0387-3420','0387-3420',null,'issn','direct',null,'print',null,'confirmed',null),
 ('hanrei_jiho','判例時報',null,'0438-5888',null,'issn','direct',null,'print',null,'confirmed','旬刊。判例タイムズとは別'),
 ('hanrei_times','判例タイムズ',null,'0438-5896',null,'issn','direct',null,'print',null,'confirmed',null),
 ('jurist','ジュリスト',null,'0448-0791',null,'issn','direct',null,'print',null,'confirmed',null),
 ('shoji_homu','旬刊商事法務',null,'0289-1107',null,'issn','direct',null,'print',null,'confirmed',null),
 ('kinyu_shoji','金融・商事判例',null,'0287-9956',null,'issn','direct',null,'print',null,'confirmed',null),
 ('nbl','nbl',null,'0287-9670',null,'issn','direct',null,'print',null,'confirmed','staging実値は小文字'),
 ('minsho','民商法雑誌',null,'1342-5056',null,'issn','direct',null,'print',null,'confirmed',null),
 ('katei_saiban','家庭の法と裁判',null,'2189-1702',null,'issn','direct',null,'print',null,'confirmed',null),
 ('rokei_sokuho','労働経済判例速報',null,null,'AN00327835','ncid','direct',null,'print',null,'ncid_key','ISSN判明次第ISSN-L優先で差替'),
 ('koseki','戸籍',null,null,'AN00274615','ncid','direct',null,'print',null,'ncid_key','戸籍時報とは別'),
 ('toki_kenkyu','登記研究',null,null,'AN00157564','ncid','direct',null,'print',null,'ncid_key','登記インターネットとは別'),
 ('keiji_bengo','季刊刑事弁護',null,null,'AN10468265','ncid','direct',null,'print',null,'ncid_key',null),
 ('horitsu_jiho_ebook','法律時報e-book',null,null,null,null,'direct',null,'ebook','horitsu_jiho','candidate','別manifestation'),
 ('ho_tetsugaku','法と哲学',null,'2188-711X',null,'issn','direct',null,'print',null,'candidate','2188-711X未検証'),
 ('jcaa_biz','jcaaビジネスジャーナル',null,null,null,null,'direct',null,'print',null,'new_no_issn','2025創刊・未付番')
ON CONFLICT (journal_id) DO NOTHING;

-- ============ A: alias seed ============
INSERT INTO staging_periodical.journal_alias (alias,journal_id,match_type,reason,auto_apply) VALUES
 ('警察學論集','keisatsu_ronshu','exact','旧字',true),
 ('^jcaジャーナル\[\d{4}\.\d{2}\]号$','jca','regex','号番ノイズ',true),
 ('労働経済判例速報660・','rokei_sokuho','exact','合併号660・661',false)
ON CONFLICT DO NOTHING;

-- ============ A: tsuukan_crosswalk（税経通信 281行：M1 / crosswalk CSV 参照でロード） ============
-- INSERT ... SELECT 'zeikei', y, m, t, 'ndl_tsv:2049089503039' FROM (VALUES ...281行...) v(y,m,t);

-- ============ A: 決定的リゾルバ ============
CREATE OR REPLACE VIEW staging_periodical.issue_id_resolved AS
WITH s AS (
  SELECT provisional_book_id, journal_norm, source_system, NULLIF(issue_no,'') AS issue_no,
         CASE WHEN issue_year ~ '^\d+$' THEN issue_year::int END AS y,
         CASE WHEN issue_month ~ '^\d+$' THEN issue_month::int END AS m,
         issue_id AS issue_id_current, issue_id_status AS status_current
  FROM staging_periodical.issue_stage
),
mapped AS (
  SELECT s.*, COALESCE(rd.journal_id, ra.journal_id) AS journal_id
  FROM s
  LEFT JOIN staging_periodical.journal_registry rd ON rd.canonical_name = s.journal_norm
  LEFT JOIN staging_periodical.journal_alias a ON a.auto_apply AND (
       (a.match_type='exact' AND a.alias=s.journal_norm) OR
       (a.match_type='regex' AND s.journal_norm ~ a.alias) OR
       (a.match_type='prefix' AND s.journal_norm LIKE a.alias||'%'))
  LEFT JOIN staging_periodical.journal_registry ra ON ra.journal_id = a.journal_id
)
SELECT m.provisional_book_id, m.journal_norm, m.source_system, m.journal_id,
  m.issue_id_current, m.status_current, r.tsuukan_rule, r.manifestation, r.status AS journal_status, kp.key_prefix,
  CASE
    WHEN r.journal_id IS NULL THEN NULL
    WHEN r.status NOT IN ('confirmed','ncid_key') THEN NULL
    WHEN r.manifestation <> 'print' THEN NULL
    WHEN r.tsuukan_rule='direct'  AND m.issue_no IS NOT NULL THEN kp.key_prefix||'#'||m.issue_no
    WHEN r.tsuukan_rule='formula' AND m.y IS NOT NULL AND m.m IS NOT NULL
      THEN kp.key_prefix||'#'||((r.formula_anchor->>'anchor_tsuukan')::int + (m.y*12+m.m)
           - ((substr(r.formula_anchor->>'anchor_ym',1,4))::int*12 + (substr(r.formula_anchor->>'anchor_ym',6,2))::int))::text
    WHEN r.tsuukan_rule='ndl_actual' AND x.tsuukan IS NOT NULL THEN kp.key_prefix||'#'||x.tsuukan::text
    WHEN r.tsuukan_rule IN ('ndl_actual','ym_terminal') AND m.y IS NOT NULL AND m.m IS NOT NULL
      THEN kp.key_prefix||'#'||m.y||'-'||lpad(m.m::text,2,'0')
    ELSE NULL
  END AS issue_id_resolved,
  CASE
    WHEN r.journal_id IS NULL THEN 'unregistered'
    WHEN r.status NOT IN ('confirmed','ncid_key') THEN 'held_'||r.status
    WHEN r.manifestation <> 'print' THEN 'separate'
    WHEN r.tsuukan_rule='direct'  AND m.issue_no IS NOT NULL THEN 'canonical'
    WHEN r.tsuukan_rule='formula' AND m.y IS NOT NULL AND m.m IS NOT NULL THEN 'canonical'
    WHEN r.tsuukan_rule='ndl_actual' AND x.tsuukan IS NOT NULL THEN 'canonical'
    WHEN r.tsuukan_rule IN ('ndl_actual','ym_terminal') AND m.y IS NOT NULL AND m.m IS NOT NULL THEN 'canonical_ym'
    ELSE 'unresolved'
  END AS status_resolved
FROM mapped m
LEFT JOIN staging_periodical.journal_registry r ON r.journal_id=m.journal_id
LEFT JOIN LATERAL (SELECT CASE r.preferred_key
    WHEN 'issn' THEN 'issn:'||r.issn WHEN 'ncid' THEN 'ncid:'||r.ncid
    WHEN 'ndlbibid' THEN 'ndlbib:'||r.ndl_bib_id END AS key_prefix) kp ON true
LEFT JOIN staging_periodical.tsuukan_crosswalk x ON x.journal_id=m.journal_id AND x.year=m.y AND x.month=m.m;

-- ============ B: 常設監査ビュー ============
CREATE OR REPLACE VIEW staging_periodical.audit_false_merge AS
SELECT issue_id, COUNT(*) AS rows,
  COUNT(DISTINCT issue_year||'-'||issue_month) FILTER (WHERE issue_year IS NOT NULL AND issue_month IS NOT NULL) AS distinct_ym,
  array_agg(DISTINCT issue_year||'-'||issue_month) AS ym_list
FROM staging_periodical.issue_stage WHERE issue_id_status='canonical'
GROUP BY issue_id
HAVING COUNT(DISTINCT issue_year||'-'||issue_month) FILTER (WHERE issue_year IS NOT NULL AND issue_month IS NOT NULL) > 1;

-- false_split: 同一(誌,年,月)に ym形と通巻形が混在（旬刊の正常な月複数通巻は偽陽性にしない）
CREATE OR REPLACE VIEW staging_periodical.audit_false_split AS
SELECT r.journal_id, s.issue_year, s.issue_month, array_agg(DISTINCT s.issue_id ORDER BY s.issue_id) AS ids
FROM staging_periodical.issue_stage s
JOIN staging_periodical.issue_id_resolved r USING (provisional_book_id)
WHERE s.issue_id_status IN ('canonical','canonical_ym')
  AND s.issue_year IS NOT NULL AND s.issue_month IS NOT NULL AND r.journal_id IS NOT NULL
GROUP BY r.journal_id, s.issue_year, s.issue_month
HAVING bool_or(s.issue_id ~ '#\d{4}-\d{2}$')
   AND bool_or(s.issue_id !~ '#\d{4}-\d{2}$' AND s.issue_id ~ '#\d+$');

CREATE OR REPLACE VIEW staging_periodical.audit_key_collision AS
SELECT r.journal_id, COUNT(DISTINCT split_part(s.issue_id,':',1)) AS key_schemes,
       array_agg(DISTINCT split_part(s.issue_id,':',1)) AS schemes
FROM staging_periodical.issue_stage s
JOIN staging_periodical.issue_id_resolved r USING (provisional_book_id)
WHERE s.issue_id_status IN ('canonical','canonical_ym') AND r.journal_id IS NOT NULL
GROUP BY r.journal_id HAVING COUNT(DISTINCT split_part(s.issue_id,':',1)) > 1;

CREATE OR REPLACE VIEW staging_periodical.audit_tsuukan_monotonic AS
WITH t AS (
  SELECT DISTINCT r.journal_id, s.issue_year::int AS y, s.issue_month::int AS m, split_part(s.issue_id,'#',2)::int AS tsuukan
  FROM staging_periodical.issue_stage s
  JOIN staging_periodical.issue_id_resolved r USING (provisional_book_id)
  JOIN staging_periodical.journal_registry jr ON jr.journal_id=r.journal_id AND jr.tsuukan_rule IN ('formula','ndl_actual')
  WHERE s.issue_id_status='canonical' AND s.issue_year ~ '^\d+$' AND s.issue_month ~ '^\d+$' AND split_part(s.issue_id,'#',2) ~ '^\d+$'
), o AS (SELECT journal_id,y,m,tsuukan, lag(tsuukan) OVER (PARTITION BY journal_id ORDER BY y,m) AS prev_t FROM t)
SELECT * FROM o WHERE prev_t IS NOT NULL AND tsuukan <= prev_t;

CREATE OR REPLACE VIEW staging_periodical.audit_unregistered AS
SELECT journal_norm, COUNT(*) AS cnt, array_agg(DISTINCT status_current) AS statuses
FROM staging_periodical.issue_id_resolved WHERE journal_id IS NULL GROUP BY journal_norm;

CREATE OR REPLACE VIEW staging_periodical.audit_resolver_drift AS
SELECT provisional_book_id, journal_id, journal_norm, source_system,
       issue_id_current, status_current, issue_id_resolved, status_resolved
FROM staging_periodical.issue_id_resolved
WHERE status_resolved IN ('canonical','canonical_ym') AND issue_id_resolved IS DISTINCT FROM issue_id_current;

-- ============ リコンサイル（冪等・backfillの一般形） ============
-- UPDATE staging_periodical.issue_stage s
-- SET issue_id=r.issue_id_resolved, issue_id_status=r.status_resolved
-- FROM staging_periodical.issue_id_resolved r
-- WHERE s.provisional_book_id=r.provisional_book_id
--   AND r.status_resolved IN ('canonical','canonical_ym')
--   AND r.issue_id_resolved IS DISTINCT FROM s.issue_id;
-- ※適用済: 法律のひろば(3行 ym統合) / businesslawjournal(18行 通巻昇格統合)
