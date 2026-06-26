-- 0002_prod_schema_and_lockdown.sql  (適用先: codex-prod)
-- prod = 公開リファレンス。直接書き込み経路を塞ぐ（「携帯から OK 連打」で生データが入らない）。

create schema if not exists prod;
comment on schema prod is '公開リファレンス。書込はレビュー済みマイグレーション(service_role)経由のみ。';

-- 読取は許可、書込は剥奪。以後 prod に作る全テーブルへ既定で適用。
grant usage on schema prod to anon, authenticated;

grant select on all tables in schema prod to anon, authenticated;
revoke insert, update, delete, truncate on all tables in schema prod from anon, authenticated;

alter default privileges in schema prod
  grant select on tables to anon, authenticated;
alter default privileges in schema prod
  revoke insert, update, delete on tables from anon, authenticated;
