-- 0004_example_municipality.sql  (適用先: codex-staging)
-- 参照テーブルの「型」を示すサンプル: 全国地方公共団体コード(市区町村)。
-- landing(検疫) と staging(検証済) の2段、門番①の検査関数と昇格関数を定義する。
-- 新しい参照テーブルを足すときは、この構造を踏襲する。

-------------------------------------------------------------------------------
-- landing.municipality : 検疫区画。自然キー UNIQUE は貼らない（重複も受け入れて検査で弾く）。
-------------------------------------------------------------------------------
create table if not exists landing.municipality (
  muni_code        text,   -- 6桁の全国地方公共団体コード（自然キー）
  prefecture_code  text,   -- 都道府県コード（muni_code の先頭2桁と一致すべき）
  prefecture_name  text,
  city_name        text,
  city_kana        text,
  valid_from       date,
  valid_to         date
);
select codex.add_provenance('landing', 'municipality');
create index if not exists municipality_landing_code_idx on landing.municipality (muni_code);

-------------------------------------------------------------------------------
-- staging.municipality : 昇格候補。制約で綺麗さを保証する。
-------------------------------------------------------------------------------
create table if not exists staging.municipality
  (like landing.municipality including defaults);

do $$
begin
  -- 主キー・自然キー・値域・clean-only を強制（既に在れば握り潰す）
  if not exists (select 1 from pg_constraint where conname = 'municipality_staging_pkey') then
    alter table staging.municipality add constraint municipality_staging_pkey primary key (id);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'municipality_staging_code_key') then
    alter table staging.municipality add constraint municipality_staging_code_key unique (muni_code);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'municipality_staging_code_fmt') then
    alter table staging.municipality add constraint municipality_staging_code_fmt
      check (muni_code ~ '^[0-9]{6}$');
  end if;
  if not exists (select 1 from pg_constraint where conname = 'municipality_staging_pref_consistent') then
    alter table staging.municipality add constraint municipality_staging_pref_consistent
      check (prefecture_code = left(muni_code, 2));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'municipality_staging_clean_only') then
    alter table staging.municipality add constraint municipality_staging_clean_only
      check (quality_status = 'clean');
  end if;
end $$;

alter table staging.municipality
  alter column muni_code        set not null,
  alter column prefecture_code  set not null,
  alter column prefecture_name  set not null,
  alter column city_name        set not null;

-------------------------------------------------------------------------------
-- 門番①: 検査関数。landing の unverified 行を検査し、clean / quarantined を付ける。
--   dirty 行には触れない（人が意図的にラベルしたものは尊重する）。
-------------------------------------------------------------------------------
create or replace function landing.validate_municipality()
returns table(checked integer, clean integer, quarantined integer, dirty integer)
language plpgsql
as $$
begin
  -- 業務列から row_hash を計算（二重投入・改竄の識別に使う）
  update landing.municipality
     set row_hash = md5(concat_ws('|',
           coalesce(muni_code, ''), coalesce(prefecture_code, ''),
           coalesce(prefecture_name, ''), coalesce(city_name, ''),
           coalesce(city_kana, ''), coalesce(valid_from::text, ''),
           coalesce(valid_to::text, '')))
   where quality_status = 'unverified';

  -- 検査NGを quarantined にする
  update landing.municipality m
     set quality_status = 'quarantined'
   where m.quality_status = 'unverified'
     and (
          m.muni_code is null
       or m.muni_code !~ '^[0-9]{6}$'
       or m.prefecture_code is distinct from left(m.muni_code, 2)
       or m.prefecture_name is null
       or m.city_name is null
       or exists (   -- 自然キー重複は両方とも隔離し、人に判断させる
            select 1 from landing.municipality d
             where d.muni_code = m.muni_code
               and d.id <> m.id
               and d.quality_status in ('unverified', 'clean')
          )
     );

  -- 生き残りを clean にする
  update landing.municipality
     set quality_status = 'clean',
         validated_at   = now(),
         validated_by   = 'landing.validate_municipality'
   where quality_status = 'unverified';

  return query
    select count(*)::int,
           count(*) filter (where quality_status = 'clean')::int,
           count(*) filter (where quality_status = 'quarantined')::int,
           count(*) filter (where quality_status = 'dirty')::int
      from landing.municipality;
end;
$$;

-------------------------------------------------------------------------------
-- 門番①の出口: clean 行のみを staging へ反映。
--   同一自然キーで内容が変わっていれば version を上げる。同一なら何もしない（冪等）。
-------------------------------------------------------------------------------
create or replace function landing.promote_municipality_to_staging()
returns integer
language plpgsql
as $$
declare
  affected integer;
begin
  insert into staging.municipality (
    id, muni_code, prefecture_code, prefecture_name, city_name, city_kana,
    valid_from, valid_to, source, source_ref, ingested_at, ingested_by,
    validated_at, validated_by, quality_status, row_hash, version, notes)
  select
    id, muni_code, prefecture_code, prefecture_name, city_name, city_kana,
    valid_from, valid_to, source, source_ref, ingested_at, ingested_by,
    validated_at, validated_by, 'clean', row_hash, version, notes
  from landing.municipality
  where quality_status = 'clean'
  on conflict (muni_code) do update set
    prefecture_code = excluded.prefecture_code,
    prefecture_name = excluded.prefecture_name,
    city_name       = excluded.city_name,
    city_kana       = excluded.city_kana,
    valid_from      = excluded.valid_from,
    valid_to        = excluded.valid_to,
    row_hash        = excluded.row_hash,
    validated_at    = excluded.validated_at,
    validated_by    = excluded.validated_by,
    version         = staging.municipality.version + 1
  where staging.municipality.row_hash is distinct from excluded.row_hash;

  get diagnostics affected = row_count;
  return affected;
end;
$$;

comment on function landing.validate_municipality() is
  '門番①: landing.municipality の未検査行を検査し clean/quarantined を付与。dirty は不可侵。';
comment on function landing.promote_municipality_to_staging() is
  'clean 行を staging へ反映。内容変更時のみ version を上げる冪等な昇格。';
