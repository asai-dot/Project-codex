-- DD-FORMOBJ-001 S1: 書式アドレス抽出（本番・biblio.toc_nodes ライブ版 / read-only）
-- toc_nodes(列: toc_node_id, book_id, isbn, title, print_page, depth, parent_toc_node_id …)
-- 出力: 各書式の anchor 確定行（real toc_node_id ＋ 印刷頁範囲）。content は S2(vision)で充填。
-- :book_id を出典本の bib_id に差し替え。複数本は book_id = ANY(:book_ids) に。

with n as (
  select toc_node_id, book_id, depth, print_page, title,
         lead(print_page) over (order by id) as next_page
  from biblio.toc_nodes
  where book_id = :book_id
)
select
  book_id,
  toc_node_id,                                            -- sticky anchor(確定)
  title as form_title,
  print_page as page_start,
  greatest(print_page, coalesce(next_page, print_page) - 1) as page_end,
  case
    when title ~ '^【(文例|書式|記載例|ひな形|雛形|様式|参考例)\s*[0-9０-９]+】' then 'marker'
    else 'leaf_keyword'
  end as match_kind,
  case
    when title ~ '^【(文例|書式|記載例|ひな形|雛形|様式|参考例)\s*[0-9０-９]+】' then 'auto'
    else 'review'
  end as decision_status
from n
where title ~ '^【(文例|書式|記載例|ひな形|雛形|様式|参考例)\s*[0-9０-９]+】'
   or ( title ~ '(契約書|合意書|覚書|念書|誓約書|通知書|請求書|議事録|定款|規程|規則|様式|書式|別紙|別表|条項例|文例|モデル|サンプル|届)'
        and depth >= 3 )
order by page_start;

-- 検証(会社議事録): 期待 321【文例】= 既知テンプレ数と一致
-- where book_id='NOBN_20220609_新・会社法実務問題シリーズ7会社議事録の作り方〈第3版〉_01'
--   and title like '【文例%'  → count = 321
