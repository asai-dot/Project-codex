-- M5: reconcile_issue_ids() — 本流反映を1関数に集約
-- generated: 2026-06-23 JST / target: staging_periodical
-- issue_stage が再生成/再ロードされても、これを1回呼べば registry/resolver から
-- 全昇格が冪等に復元する（「再ロードで戻る」問題の構造的解決）。
CREATE OR REPLACE FUNCTION staging_periodical.reconcile_issue_ids()
RETURNS TABLE(updated_rows integer) LANGUAGE plpgsql AS $$
DECLARE n integer;
BEGIN
  UPDATE staging_periodical.issue_stage s
  SET issue_id        = r.issue_id_resolved,
      issue_id_status = r.status_resolved
  FROM staging_periodical.issue_id_resolved r
  WHERE s.provisional_book_id = r.provisional_book_id
    AND r.status_resolved IN ('canonical','canonical_ym')
    AND r.issue_id_resolved IS DISTINCT FROM s.issue_id;
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN QUERY SELECT n;
END $$;
-- 運用: 再ロード後に  SELECT staging_periodical.reconcile_issue_ids();  → 0=既に整合。
