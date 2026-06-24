-- M2: 誤スプリット回収（正規化ノイズで切り離された行を本来の通巻idへ合流）
-- generated: 2026-06-22 JST
-- target: staging_periodical.issue_stage
-- idempotent: status='provisional_no_issn' 条件が再実行時に空マッチを保証

-- jcaジャーナル[2025.11]号（lionbolt, 正規化ノイズ）→ issn:0386-3042#821
-- bencom/legallib の 2025-11号(既canonical) と 3ソース統合（クロスソースdedup）
-- 通号821 = 703 + (2025-2016)*12 + (11-1)
UPDATE staging_periodical.issue_stage
SET
  journal_norm    = 'jcaジャーナル',
  issue_id        = 'issn:0386-3042#821',
  issue_id_status = 'canonical'
WHERE journal_norm    = 'jcaジャーナル[2025.11]号'
  AND issue_id_status = 'provisional_no_issn';

-- 非回収（精度上あえて据置）:
--  労働経済判例速報 660・661号 = 合併号。単独通巻id化は将来の660/661分離ソースと
--   誤マージする潜在リスク + dedup利得ゼロ → provisional隔離が正。合併号採番規約は別途。
--  XXXX年版重要労働判例総覧 / 労働判例読本 / 精選労働判例集 = 書籍（誌でない）→ 対象外。
--  law&technology「…」特別公開版 / 戸籍特別版 = 別manifestation（P5準拠）→ 対象外。
