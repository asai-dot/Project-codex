-- Runbook: SF/LEALA -> dynamic.cases ETL (project nixfjmwxmgugiiuqfuym)
-- 本番DB変更/SF起動はセーフティ上 human 実行（Supabase SQL Editor で実行）。
-- <ANON_KEY> は当該プロジェクトの anon publishable key に置換。

-- 0) 前提拡張（ダッシュボード Database > Extensions で ON 済み）: pg_net, pg_cron, http

-- 1) Vault にSF認証情報を格納（初回のみ。値は実値に置換、リポジトリには残さない）
--    select vault.create_secret('<PEM>',  'sf_jwt_private_key', '...');
--    select vault.create_secret('<CKEY>', 'sf_consumer_key',    '...');
--    select vault.create_secret('asai@asai-lo.com', 'sf_username', '...');
--    select vault.create_secret('https://login.salesforce.com', 'sf_login_url', '...');

-- 2) cases スキーマ拡張（KPI用の型付き列 + 全項目保持 sf_raw）
alter table dynamic.cases
  add column if not exists name text,
  add column if not exists charge_lawyer_id text,
  add column if not exists clerk_id text,
  add column if not exists team_id text,
  add column if not exists source text,
  add column if not exists source_middle text,
  add column if not exists source_partner_id text,
  add column if not exists case_category text,
  add column if not exists reception_date date,
  add column if not exists consulted_date date,
  add column if not exists mandatory_date date,
  add column if not exists close_date date,
  add column if not exists expected_close_date date,
  add column if not exists reason_for_failure text,
  add column if not exists reason_not_reach text,
  add column if not exists detailed_reason_closing text,
  add column if not exists next_deadline_at timestamptz,
  add column if not exists waiting_on text,
  add column if not exists outcome text,
  add column if not exists probability numeric,
  add column if not exists consultation_converted boolean,
  add column if not exists consultation_ref text,
  add column if not exists box_folder_url text,
  add column if not exists account_name text,
  add column if not exists earnings numeric,
  add column if not exists sf_created_date timestamptz,
  add column if not exists sf_last_modified timestamptz,
  add column if not exists sf_raw jsonb;

-- 3) 初回同期を起動（pg_net 非同期）
select net.http_post(
  url := 'https://nixfjmwxmgugiiuqfuym.supabase.co/functions/v1/sf-sync',
  headers := jsonb_build_object('Authorization','Bearer <ANON_KEY>','Content-Type','application/json'),
  body := jsonb_build_object('action','sync')
);

-- 4) 定期自動実行（毎日 18:00 UTC = 03:00 JST）
select cron.schedule('sf-sync-nightly', '0 18 * * *', $$
  select net.http_post(
    url := 'https://nixfjmwxmgugiiuqfuym.supabase.co/functions/v1/sf-sync',
    headers := jsonb_build_object('Authorization','Bearer <ANON_KEY>','Content-Type','application/json'),
    body := jsonb_build_object('action','sync')
  );
$$);

-- 検証: 投入件数・背骨ID解決率
-- select sf_record_type, count(*) from dynamic.cases group by 1;
-- select count(*) filter (where exists (select 1 from dynamic.cases c where left(c.sf_record_id,15)=left(m.sf_record_id,15)))::float
--        /count(*) as resolved_pct from dynamic.comms m;
