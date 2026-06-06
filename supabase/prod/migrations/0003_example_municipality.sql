-- 0003_example_municipality.sql  (適用先: codex-prod)
-- 公開テーブルのサンプル。staging から昇格したものに相当する綺麗なデータのみが入る。
-- RLS を有効化し、書込ポリシーを付けない＝アプリ経由の書込を拒否する。
-- 実データの投入は、レビュー済みの昇格マイグレーション(本ファイル末尾のような INSERT)で行う。

create table if not exists prod.municipality (
  muni_code        text,
  prefecture_code  text,
  prefecture_name  text,
  city_name        text,
  city_kana        text,
  valid_from       date,
  valid_to         date
);
select codex.add_provenance('prod', 'municipality');

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'municipality_prod_pkey') then
    alter table prod.municipality add constraint municipality_prod_pkey primary key (id);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'municipality_prod_code_key') then
    alter table prod.municipality add constraint municipality_prod_code_key unique (muni_code);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'municipality_prod_code_fmt') then
    alter table prod.municipality add constraint municipality_prod_code_fmt
      check (muni_code ~ '^[0-9]{6}$');
  end if;
  if not exists (select 1 from pg_constraint where conname = 'municipality_prod_pref_consistent') then
    alter table prod.municipality add constraint municipality_prod_pref_consistent
      check (prefecture_code = left(muni_code, 2));
  end if;
  -- prod は clean しか入れない（汚い・未検査データの混入を制約で物理的に拒否）
  if not exists (select 1 from pg_constraint where conname = 'municipality_prod_clean_only') then
    alter table prod.municipality add constraint municipality_prod_clean_only
      check (quality_status = 'clean');
  end if;
end $$;

alter table prod.municipality
  alter column muni_code        set not null,
  alter column prefecture_code  set not null,
  alter column prefecture_name  set not null,
  alter column city_name        set not null;

-- 書込ロックダウン: RLS 有効化、読取ポリシーのみ。書込ポリシーなし＝書込拒否。
-- service_role はRLSをバイパスするため、マイグレーション(下記INSERT)は通る。
alter table prod.municipality enable row level security;
do $$
begin
  if not exists (select 1 from pg_policies
                 where schemaname='prod' and tablename='municipality'
                   and policyname='municipality_prod_read') then
    create policy municipality_prod_read on prod.municipality for select using (true);
  end if;
end $$;

grant select on prod.municipality to anon, authenticated;
revoke insert, update, delete on prod.municipality from anon, authenticated;

-- ----------------------------------------------------------------------------
-- 昇格データ（サンプル）: staging から書き出した clean 行のレビュー済みシード。
-- 実運用では staging の内容をこの形で書き出し、PR レビューを経て適用する。
-- ----------------------------------------------------------------------------
insert into prod.municipality
  (muni_code, prefecture_code, prefecture_name, city_name, city_kana,
   valid_from, source, source_ref, validated_at, validated_by, quality_status, version)
values
  ('011002', '01', '北海道', '札幌市', 'サッポロシ', '1947-04-17',
   'e-gov:全国地方公共団体コード', 'sample-seed', now(), 'promotion:sample', 'clean', 1),
  ('131016', '13', '東京都', '千代田区', 'チヨダク', '1947-08-15',
   'e-gov:全国地方公共団体コード', 'sample-seed', now(), 'promotion:sample', 'clean', 1),
  ('271004', '27', '大阪府', '大阪市', 'オオサカシ', '1956-09-01',
   'e-gov:全国地方公共団体コード', 'sample-seed', now(), 'promotion:sample', 'clean', 1)
on conflict (muni_code) do nothing;
