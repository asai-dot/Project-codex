-- M7: 税経通信 ISSN誤付与の訂正（0387-2866=法学論叢 → NCID AN00390536）
-- generated: 2026-06-23 JST / target: staging_periodical
-- owner指摘「ないんちゃうか」を契機に検証:
--   ISSN Portal: 0387-2866 = 「法学論叢(京都)」。税経通信ではない（内部bib_recordsの誤付与）。
--   税経通信の正ISSNはCiNii/NDL/ISSN Portalいずれにも無し（実務月刊誌・雑誌コード/JAN運用）。
--   → CiNii NCID AN00390536 をキーに（P5: ISSN無→NCID）。通号crosswalkはキー非依存で有効。
UPDATE staging_periodical.journal_registry
SET issn=null, issn_l=null, ncid='AN00390536', preferred_key='ncid', status='ncid_key',
    evidence_source='cinii:AN00390536',
    note='ISSN無し。旧seed 0387-2866はISSN Portalで法学論叢(京都)=誤付与のため破棄。通号はNDL実値crosswalk'
WHERE journal_id='zeikei';

-- 再キー: issn:0387-2866#{通号} → ncid:AN00390536#{通号}（2026の年月もncid:へ）
SELECT staging_periodical.reconcile_issue_ids();
-- 確認: leftover issn:0387-2866 = 0、全監査クリーン、件数不変。
