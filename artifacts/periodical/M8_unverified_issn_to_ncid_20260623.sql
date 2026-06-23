-- M8: 未登録ISSN3件をNCIDキーへ訂正（ISSN突合スイープの結果）
-- generated: 2026-06-23 JST / target: staging_periodical
-- 全registry ISSNをISSN Portal等で突合した結果、内部DB由来の3件が未登録（該当誌なし）と判明。
-- いずれもチェックデジットは有効だが登録実体が3レジストリ(Portal/WorldCat/miar)に無く、
-- 各誌は雑誌コード運用（税経の0387-2866=法学論叢と同一の誤付与プロファイル）。

UPDATE staging_periodical.journal_registry
SET issn=null, issn_l=null, ncid='AA11504883', preferred_key='ncid', status='ncid_key',
    evidence_source='cinii:AA11504883',
    note='旧seed 1347-4146は未登録の誤付与。NCIDキー。月刊巻号→ym終端'
WHERE journal_id='biz_homu';

UPDATE staging_periodical.journal_registry
SET issn=null, issn_l=null, ncid='AN0026915X', preferred_key='ncid', status='ncid_key',
    evidence_source='cinii:AN0026915X',
    note='旧seed 0387-7035は未登録の誤付与。CiNii NCID AN0026915X。月刊→ym終端'
WHERE journal_id='biz_guide';

UPDATE staging_periodical.journal_registry
SET issn=null, issn_l=null, ncid='BN14939714', preferred_key='ncid', tsuukan_rule='vol_issue', status='ncid_key',
    evidence_source='cinii:BN14939714',
    note='旧seed 0389-6544は未登録の誤付与。第N巻第M号→ncid#{巻}-{号}。号単独は巻跨ぎ誤マージ(50行→6id)のため巻号複合キー'
WHERE journal_id='kotsu_minji';

-- resolver: vol列追加 + vol_issue分岐（key_prefix||'#'||vol||'-'||issue_no）を追加。
--   完全定義は Supabase migration: fix_three_unverified_issn_to_ncid 参照。

-- 反映: SELECT staging_periodical.reconcile_issue_ids();
--   ビジネス法務66→ncid:AA11504883#YYYY-MM / ビジネスガイド10→ncid:AN0026915X#YYYY-MM
--   交通事故民事50→ncid:BN14939714#{巻}-{号}（6id誤マージ→25正規号に分離）
