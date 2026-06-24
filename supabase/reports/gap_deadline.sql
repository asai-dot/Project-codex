-- GAP-DEADLINE: 係属中なのに有効期限が無い受任案件＝弁護過誤(懈怠)リスクの自動検知
-- 重大度 🔴。owner裁定「徒過防止=人・SF・AIの多重チェック(D-033/G-20)」のAI担当部分。
-- 権威ソース: SF leala__IsDeadlineActive__c(期限有効) / leala__Deadline__c(期限参照)。
--   ※これらは sf-sync 関数 v4 で sf_raw に取り込む。再同期後に正確化。
-- 使い方: select * from dynamic.v_gap_deadline order by sf_last_modified desc;

create or replace view dynamic.v_gap_deadline as
select
  sf_record_id,
  name,
  status,
  charge_lawyer_id,
  (sf_raw->>'leala__IsDeadlineActive__c')::boolean as deadline_active,
  sf_raw->>'leala__Deadline__c' as deadline_ref,
  next_deadline_at,
  sf_last_modified,
  'https://leala-3392.lightning.force.com/lightning/r/' || sf_record_id || '/view' as sf_url
from dynamic.cases
where sf_record_type='leala__Business__c'
  and status in ('交渉中','裁判中','申立等準備','調停等')   -- 係属中(active)
  and coalesce((sf_raw->>'leala__IsDeadlineActive__c')::boolean, false) = false
  and (sf_raw->>'leala__Deadline__c') is null;
