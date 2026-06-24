-- 流入経路 未入力アラート (project nixfjmwxmgugiiuqfuym, schema dynamic)
-- 目的: 「継続中(open)なのに流入経路が空」の案件だけを抽出（過去終結案件のノイズを除外）。
-- 使い方: select * from dynamic.v_missing_source_open order by created desc nulls last;
--         sf_url 列のリンクで該当SFレコードを直接開いて入力できる。

create or replace view dynamic.v_missing_source_open as
select
  sf_record_type,
  sf_record_id,
  name,
  status,
  charge_lawyer_id,
  sf_created_date::date as created,
  'https://leala-3392.lightning.force.com/lightning/r/' || sf_record_id || '/view' as sf_url
from dynamic.cases
where source is null and close_date is null;

-- 監視用サマリ（開閉×オブジェクト別の未入力率トレンド確認）
create or replace view dynamic.v_source_fill_summary as
select
  sf_record_type as obj,
  case when close_date is null then 'open' else 'closed' end as state,
  count(*) as cases,
  count(*) filter (where source is null) as missing_source,
  round(100.0*count(*) filter (where source is null)/nullif(count(*),0),1) as missing_pct
from dynamic.cases
group by 1,2;

-- 実測(2026-06-24): open×未入力 計44件 (Business 27 / Consultation 17)。
-- closed は Business 91.5%(649) 未入力だが過去案件主体=低優先。
