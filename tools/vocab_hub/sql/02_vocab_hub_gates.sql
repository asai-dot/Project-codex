-- 語彙ハブ 物理ゲート (P2 / DD-DICT-008 §2.3.1 改訂版 + 入口品質ゲート)
-- doc: design/vocab_object/03_P2_VOCAB_SCHEMA_DEPLOY_PLAN §2 / 02_P1 §2
-- STATUS: 設計生成物 / 未 apply. 合格条件 = 全 gate の violation_count = 0.
-- CI 化: fn_run_all_gates() を canary/batch 後に実行し 0 を確認.

begin;

-- gate1: canonical 昇格は「昇格可 rank 集合」の anchor のみ
--   昇格可 = 100/100a-100d/101/102 (bedrock) + 200(自身の bibliographic hub のみ).
--   rank103+ (specialty) が canonical hub の anchor なら violation.
create or replace view gate_canonical_promotion as
select h.hub_id, h.anchor_term_id, t.scheme_id, s.authority_rank, h.hub_status
from alo_hubs h
join alo_terms t            on t.term_id = h.anchor_term_id
join alo_concept_schemes s  on s.scheme_id = t.scheme_id
where h.hub_status = 'canonical'
  and not (
        s.authority_rank in ('100','100a','100b','100c','100d','101','102')
        or (s.authority_rank = '200' and s.role = 'bibliographic')
  );

-- gate2: 入口品質ゲート — needs_preprocessing 非空の hub は canonical 不可
--   (空定義/短定義/末尾切れ anchor を canonical 昇格させない. 06/09 findings)
create or replace view gate_quality_canonical as
select h.hub_id, h.anchor_term_id, h.needs_preprocessing, h.hub_status
from alo_hubs h
where h.hub_status = 'canonical'
  and array_length(h.needs_preprocessing, 1) is not null;

-- gate3: specialty(rank>=103) 同士の exact_match を bedrock anchor なしに作らせない
--   specialty term が exact_match なのに、その hub の anchor が bedrock でないなら violation.
create or replace view gate_specialty_exact_match as
select m.hub_id, m.term_id, s.authority_rank
from alo_hub_memberships m
join alo_terms t            on t.term_id = m.term_id
join alo_concept_schemes s  on s.scheme_id = t.scheme_id
join alo_hubs h             on h.hub_id = m.hub_id
join alo_terms at           on at.term_id = h.anchor_term_id
join alo_concept_schemes asch on asch.scheme_id = at.scheme_id
where m.map_type = 'skos_exact_match'
  and s.authority_rank not in ('100','100a','100b','100c','100d','101','102')
  and asch.authority_rank not in ('100','100a','100b','100c','100d','101','102');

-- 全ゲート集計: 各 violation_count を返す. 全て 0 が合格.
create or replace function fn_run_all_gates()
returns table(gate_name text, violation_count bigint) as $$
begin
  return query
    select 'gate_canonical_promotion'::text, count(*)::bigint from gate_canonical_promotion
    union all
    select 'gate_quality_canonical'::text,   count(*)::bigint from gate_quality_canonical
    union all
    select 'gate_specialty_exact_match'::text, count(*)::bigint from gate_specialty_exact_match;
end;
$$ language plpgsql stable;

commit;

-- 使い方(canary/batch 後):
--   select * from fn_run_all_gates();
--   -> 全行 violation_count = 0 で合格. 非0なら apply 中止 + ROLLBACK(doc03 §6).
