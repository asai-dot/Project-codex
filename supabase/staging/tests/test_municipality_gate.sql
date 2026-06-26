-- test_municipality_gate.sql
-- 門番①(landing.validate_municipality / promote_municipality_to_staging)の動作テスト。
-- 「わざと汚いデータを入れて、確実に隔離される」ことを検証する。門番の形骸化を防ぐ。
-- トランザクション内で完結し、最後に ROLLBACK するので DB を汚さない。
-- 実行: psql -v ON_ERROR_STOP=1 -f この файл（staging のマイグレーション適用後）

\set ON_ERROR_STOP on
begin;

-- 検査対象を投入（good 2件 / bad 5件）
insert into landing.municipality
  (muni_code, prefecture_code, prefecture_name, city_name, source)
values
  ('011002', '01', '北海道',   '札幌市',   'test'),  -- good
  ('131016', '13', '東京都',   '千代田区', 'test'),  -- good
  ('99999',  '99', 'x',        'y',        'test'),  -- bad: 5桁(書式違反)
  ('270000', '13', '大阪府',   'x',        'test'),  -- bad: 都道府県コード不一致(27≠13)
  ('281000', '28', null,       'x',        'test'),  -- bad: prefecture_name が NULL
  ('231007', '23', '愛知県',   '名古屋市', 'test'),  -- bad: 自然キー重複(下と同じ)
  ('231007', '23', '愛知県',   '名古屋市B','test');  -- bad: 自然キー重複(上と同じ)

-- 門番①: 検査
select * from landing.validate_municipality();

-- 検査結果のアサーション: clean=2, quarantined=5
do $$
declare c_clean int; c_quar int;
begin
  select count(*) filter (where quality_status = 'clean'),
         count(*) filter (where quality_status = 'quarantined')
    into c_clean, c_quar
    from landing.municipality;
  if c_clean <> 2 then
    raise exception 'GATE TEST FAILED: clean は 2 を期待したが % だった', c_clean;
  end if;
  if c_quar <> 5 then
    raise exception 'GATE TEST FAILED: quarantined は 5 を期待したが % だった', c_quar;
  end if;
  raise notice 'gate ok: clean=% quarantined=%', c_clean, c_quar;
end $$;

-- 昇格: clean 行のみが staging へ入る
select landing.promote_municipality_to_staging();

do $$
declare n int;
begin
  select count(*) into n from staging.municipality;
  if n <> 2 then
    raise exception 'PROMOTE TEST FAILED: staging は 2 件を期待したが % 件だった', n;
  end if;
  raise notice 'promote ok: staging=% 件', n;
end $$;

-- row_hash が NULL と空文字を区別できることの確認（衝突しない）
do $$
declare h1 text; h2 text;
begin
  h1 := codex.stable_hash('a', null, 'b');
  h2 := codex.stable_hash('a', '',   'b');
  if h1 = h2 then
    raise exception 'HASH TEST FAILED: NULL と空文字が衝突している';
  end if;
  raise notice 'hash ok: NULL と空文字を区別';
end $$;

rollback;
