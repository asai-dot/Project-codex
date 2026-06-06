-- 0001_codex_common.sql  (適用先: codex-staging)
-- 共通スキーマ codex: 品質ステータス enum と、来歴メタ列を付与するヘルパ。
-- このファイルは codex-prod 側の 0001 と同一内容（別DBのため各々に適用する）。

create schema if not exists codex;

-- 品質ステータス: データが「綺麗か汚いか・どの段階か」を表す。
do $$
begin
  if not exists (select 1 from pg_type where typname = 'quality_status'
                 and typnamespace = 'codex'::regnamespace) then
    create type codex.quality_status as enum
      ('unverified', 'clean', 'dirty', 'quarantined');
  end if;
end $$;

-- 来歴メタ列を対象テーブルに付与する。全テーブル共通の縛りをDRYに強制するための関数。
-- 空テーブルに対して呼ぶ前提（NOT NULL 列を後付けするため）。
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
      add column if not exists quality_status codex.quality_status not null default 'unverified',
      add column if not exists row_hash      text,
      add column if not exists version       integer            not null default 1,
      add column if not exists notes         text
  $f$, p_schema, p_table);
end;
$$;

comment on function codex.add_provenance(text, text) is
  '対象テーブルに来歴メタ列(source, ingested_*, validated_*, quality_status, row_hash, version, notes)を付与する。空テーブルに対して使う。';
