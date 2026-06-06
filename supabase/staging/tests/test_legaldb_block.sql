-- test_legaldb_block.sql
-- 門番②の検証: legaldb v0.5 candidate の昇格が物理的にブロックされていること。
-- ratify 前に staging/prod へ legaldb が漏れないことを保証する。

\set ON_ERROR_STOP on

do $$
begin
  begin
    perform landing.promote_legaldb_to_staging();
    -- ここに到達したらブロックされていない＝テスト失敗
    raise exception 'BLOCK TEST FAILED: legaldb 昇格がブロックされていない';
  exception
    when others then
      if position('BLOCKED' in sqlerrm) > 0 then
        raise notice 'block ok: legaldb 昇格は正しくブロックされている (%)', sqlerrm;
      else
        raise;  -- 想定外のエラーはそのまま失敗させる
      end if;
  end;
end $$;

-- landing に candidate を入れても staging が空のままであること（昇格していない証跡）
do $$
declare n integer;
begin
  insert into landing.legal_work (alo_work_uri, work_type, title, source)
  values ('alo:work:test-0001', 'case', 'テスト判例', 'test');

  select count(*) into n from staging.legal_work;
  if n <> 0 then
    raise exception 'LEAK TEST FAILED: staging.legal_work に % 件あり（昇格漏れ）', n;
  end if;
  raise notice 'leak ok: landing 投入後も staging.legal_work は空';

  delete from landing.legal_work where alo_work_uri = 'alo:work:test-0001';
end $$;
