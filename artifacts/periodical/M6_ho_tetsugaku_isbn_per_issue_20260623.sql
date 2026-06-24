-- M6: 法と哲学を isbn_per_issue 化（ISSN誌ではなく号ごとISBN書籍）
-- generated: 2026-06-23 JST / target: staging_periodical
-- 根拠: 信山社書誌+bib_records で各号が固有ISBNを持ちISSN/NCIDなし。号番と末尾が9860+号で連動。
--   第3-9,11号を実値確認(bib/amazon/hanmoto/shinzansha)。旧候補ISSN 2188-711Xは誤りで破棄。

-- (1) 号→ISBNマップ（resolverが参照＝reconcileで復元可能）
CREATE TABLE IF NOT EXISTS staging_periodical.issue_isbn_map (
  journal_id text NOT NULL REFERENCES staging_periodical.journal_registry(journal_id),
  issue_no   text NOT NULL,
  isbn       text NOT NULL,
  src        text,
  PRIMARY KEY (journal_id, issue_no)
);
INSERT INTO staging_periodical.issue_isbn_map (journal_id, issue_no, isbn, src) VALUES
 ('ho_tetsugaku','2','9784797298628','shinzansha(単行本2016-05-30, 確認済)'),
 ('ho_tetsugaku','3','9784797298635','bib_records'),
 ('ho_tetsugaku','4','9784797298642','bib_records'),
 ('ho_tetsugaku','5','9784797298659','bib_records'),
 ('ho_tetsugaku','6','9784797298666','bib_records'),
 ('ho_tetsugaku','7','9784797298673','bib_records/amazon'),
 ('ho_tetsugaku','8','9784797298680','amazon(ISBN10 4797298685)'),
 ('ho_tetsugaku','9','9784797298697','hanmoto'),
 ('ho_tetsugaku','11','9784797298710','shinzansha')
ON CONFLICT DO NOTHING;

-- (2) registry: 誤候補ISSN破棄、isbn_per_issue、確定
UPDATE staging_periodical.journal_registry
SET issn=null, issn_l=null, preferred_key=null, tsuukan_rule='isbn_per_issue', status='confirmed',
    evidence_source='shinzansha+bib_records',
    note='ISSN無し。号ごと固有ISBNの研究雑誌(信山社)。issue_id=isbn:{ISBN}。旧候補2188-711Xは誤りで破棄'
WHERE journal_id='ho_tetsugaku';

-- (3) resolver に isbn_per_issue 分岐追加 + gate例外化（完全定義は Supabase migration:
--     ho_tetsugaku_isbn_per_issue を参照）。要点:
--     - gate: held = (preferred_key IS NULL AND tsuukan_rule<>'isbn_per_issue') OR status保留
--     - 分岐: WHEN tsuukan_rule='isbn_per_issue' AND im.isbn IS NOT NULL THEN 'isbn:'||im.isbn
--     - JOIN: issue_isbn_map im ON (journal_id, issue_no)

-- (4) 反映: SELECT staging_periodical.reconcile_issue_ids();  → 4行(第2号・第8号×2源)がcanonical化
--     第2号→isbn:9784797298628 / 第8号→isbn:9784797298680（各 bencom+legallib 統合）
