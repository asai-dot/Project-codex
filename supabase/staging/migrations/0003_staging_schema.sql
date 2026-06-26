-- 0003_staging_schema.sql  (適用先: codex-staging)
-- staging = 検査通過した昇格候補。制約で綺麗さを保証する。

create schema if not exists staging;

comment on schema staging is
  '検査通過した昇格候補。自然キー UNIQUE・値域 CHECK・clean-only を制約で強制する。';
