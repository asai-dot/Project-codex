-- 0006_legaldb_staging_and_block.sql  (適用先: codex-staging)
-- legaldb v0.5 の staging「目標形(clean target)」骨格と、昇格を物理ブロックする門番②。
--
-- GPT判定 DESIGN_MODIFY_REQUIRED のため、landing→staging→prod の昇格は不可。
-- ここでは「ratify 後に目指す clean な形」を骨格として置き、昇格関数は例外で止める。
-- 構造が用意されていても、ゲートは閉じている、という状態を表現する。

-------------------------------------------------------------------------------
-- staging 目標形（clean-only。staging には resolve 済み・検査通過のみが入る想定）
-------------------------------------------------------------------------------
create table if not exists staging.legal_work (
  id            uuid primary key default gen_random_uuid(),
  alo_work_uri  text not null,
  work_type     legaldb.work_type not null,
  title         text not null,
  jurisdiction  text not null default 'JP',
  source        text not null,
  validated_at  timestamptz,
  validated_by  text,
  row_hash      text,
  version       integer not null default 1,
  quality_status codex.quality_status not null default 'clean'
    check (quality_status = 'clean'),
  constraint legal_work_uri_key unique (alo_work_uri)
);

create table if not exists staging.citation_edge (
  id                      uuid primary key default gen_random_uuid(),
  citing_work_id          uuid not null,
  cited_authority_work_id uuid not null,   -- staging では resolve 済みのみ（NULL 不可）
  raw_citation_text       text not null,
  pin_cite                text,
  treatment               legaldb.treatment_kind,
  treatment_status        legaldb.treatment_status not null default 'unclassified',
  -- raw/parsed は staging に来ない。resolved 以上のみ。
  parse_status            legaldb.parse_status not null
    check (parse_status in ('resolved','reviewed','promoted')),
  source                  text not null,
  validated_at            timestamptz,
  validated_by            text,
  row_hash                text,
  version                 integer not null default 1,
  quality_status          codex.quality_status not null default 'clean'
    check (quality_status = 'clean')
);

comment on table staging.legal_work is
  'legaldb v0.5 candidate の staging 目標形。昇格はブロック中（landing.promote_legaldb_to_staging 参照）。';

-------------------------------------------------------------------------------
-- 門番②: legaldb v0.5 は DESIGN_MODIFY_REQUIRED。昇格を物理ブロックする。
-- v0.6 必須パッチと owner ratify が済むまで、この関数は必ず例外を投げる。
-------------------------------------------------------------------------------
create or replace function landing.promote_legaldb_to_staging()
returns void
language plpgsql
as $$
begin
  raise exception using
    errcode = 'P0001',
    message = 'BLOCKED: legaldb v0.5 は DESIGN_MODIFY_REQUIRED。',
    detail  = 'owner ratify と v0.6 必須パッチ(DD-LAWTIME v0.2 / 識別子責務表 / anchor lifecycle / citation 状態機械 / treatment 語彙確定 / over-reach ラベル / collision テスト)の完了まで、landing→staging→prod の昇格は不可。',
    hint    = 'docs/data-governance/legaldb-candidate-status.md を参照。パッチ反映・ratify 後にこの関数を本実装へ差し替える。';
end;
$$;

comment on function landing.promote_legaldb_to_staging() is
  '門番②: legaldb v0.5 candidate の昇格ブロック。ratify まで必ず例外を投げる。';
