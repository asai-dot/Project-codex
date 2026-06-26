-- 0002_landing_schema.sql  (適用先: codex-staging)
-- landing = 検疫区画。生データ・dirty を受け入れる。
-- 重要: landing には自然キー UNIQUE を貼らない。汚い重複も一旦受け入れ、検査で弾くため。

create schema if not exists landing;

comment on schema landing is
  '検疫区画。生データ・未検査・dirty を受け入れる。ここから先へは検査関数を通らないと進めない。';
