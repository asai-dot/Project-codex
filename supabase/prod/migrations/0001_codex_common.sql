-- 0001_codex_common.sql  (適用先: codex-prod)
-- codex-staging 側の 0001 と同一内容。別DBのため各々に適用する。

create schema if not exists codex;

do $$
begin
  if not exists (select 1 from pg_type where typname = 'quality_status'
                 and typnamespace = 'codex'::regnamespace) then
    create type codex.quality_status as enum
      ('unverified', 'clean', 'dirty', 'quarantined');
  end if;
end $$;

create or replace function codex.add_provenance(p_schema text, p_table text)
returns void
language plpgsql
as $$
begin
  execute format($f$
    alter table %I.%I
      add column if not exists id            uuid               not null default gen_random_uuid(),
      add column if not exists source        text               not null default 'unspecified',
      add column if not exists source_ref    text,
      add column if not exists ingested_at   timestamptz        not null default now(),
      add column if not exists ingested_by   text               not null default current_user,
      add column if not exists validated_at  timestamptz,
      add column if not exists validated_by  text,
      add column if not exists gate_run_id   text,
      add column if not exists quality_status codex.quality_status not null default 'unverified',
      add column if not exists row_hash      text,
      add column if not exists version       integer            not null default 1,
      add column if not exists notes         text
  $f$, p_schema, p_table);
end;
$$;

comment on function codex.add_provenance(text, text) is
  '対象テーブルに来歴メタ列を付与する。空テーブルに対して使う。';

-- 業務列から安定した row_hash を作る。NULL と空文字を区別し、列の順序を保持する。
create or replace function codex.stable_hash(variadic vals text[])
returns text
language sql
immutable
as $$
  select md5(string_agg(coalesce(v, chr(1)), chr(31) order by ord))
  from unnest(vals) with ordinality as t(v, ord);
$$;

comment on function codex.stable_hash(text[]) is
  '列値から row_hash を生成。NULL(chr1)と空文字を区別し列順を保持する。';
