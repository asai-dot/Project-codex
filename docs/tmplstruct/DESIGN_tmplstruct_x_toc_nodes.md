# 投入後の利用設計 — tmplstruct × toc_nodes（TOC本投入を前提）

date: 2026-06-11 / 前提: Mac側で承認済みapply（bib_toc→新3源）完了後に `toc_nodes` が使える状態になる。
目的: TOC統合（manual>…>lionbolt>…>bencom、D-5 v2）の成果を、tmplstruct（出典本175・式6,976）の
**式境界・頁解決・ポイントOCR**へ直結させる。設計のみ・DB非書込み。

## 0. 前提スキーマ（apply後・確認要）
`toc_nodes`（bib_toc→toc_nodes migration map = 15列+source6列）想定の主キー列：
- `toc_node_id`(正準), `book_id`, `parent_toc_node_id`, `seq/ordinal`, `level`, `title/text`, `page`(print_page)
- source列: `toc_source`(lionbolt/bencom/legallib/…), `source_row_hash`, `provenance_group`, ページ範囲
  （LION BOLT由来は `startHeadlinePage/endHeadlinePage` を無損失保持）, `canonical_confidence`(分解係数)
※ 正確な列名はapply後に `information_schema` で確認してクエリ確定。

## 1. 骨格の供給源が変わる（bib_toc → toc_nodes）
- これまで: 出典本(bencom)の `biblio.bib_toc`（単一`page`・4階層）。
- これから: `toc_nodes`（**ページ範囲付き**・D-5マージ済み・複数源の最良基底）。
  - 出典本はbencom由来だが、同一書がLION BOLTにもあれば**より良い基底**が選ばれる（粒度ガード付き）。
  - LION BOLTの `start/endHeadlinePage` で**式の頁“範囲”**が取れる＝ポイントOCRの頁切りが正確化。

## 2. パイプライン（toc_nodes版・S1→S5）
```
[S1] 書籍identity解決: 出典本175 → biblio_item(正準) → toc_nodes.book_id
     根拠: DD-LITID identity_candidates（isbn13_exact: LB↔蔵書1,932組 等）。ISBN正本で突合
[S2] 式→ノード対応: 各式名 ≈ toc_nodes.title（book内・親パス修飾スコープ, DD-TOCATTACH §1.3のladder）
     → 当該ノードの page / 次同階層ノードの page-1 = 式の頁範囲
[S3] 書式ページ抽出: 自炊600dpi(≤約365MBはBox preview, 超はMac)で頁範囲を画像化
[S4] ポイントOCR(vision): 書式頁 → 式内部構造JSON（条項/空欄/署名/別紙）※パイロット実証済
[S5] 反映: 式境界=①toc_nodes / 中身=④ → tmplstruct構造へ
```
変更点はS1-S2のみ（骨格源がtoc_nodesに）。S3-S5はパイロット(契約解消/業務委託/会社法務書式集)で実証済の方式そのまま。

## 3. apply後すぐ走らせる検証クエリ（雛形・列名は確定後に微修正）
```sql
-- (a) 出典本175のうち toc_nodes に骨格がある冊と、その基底source
select b.isbn, b.title, n.toc_source, count(*) nodes,
       count(*) filter (where n.page is not null) nodes_with_page
from biblio.bib_records b
join <identity_map> m on m.bib_id = b.bib_id          -- DD-LITID解決後
join toc_nodes n on n.book_id = m.canonical_book_id
where b.source='bencom-library' and b.isbn = any(:source_isbns)
group by b.isbn,b.title,n.toc_source;

-- (b) ある出典本の「書式ノード」候補（式名キーワード）＋頁範囲
select toc_node_id, level, page, title
from toc_nodes
where book_id = :book and (title ~ '(契約書|合意書|通知書|議事録|定款|規程|様式|書式|別紙|条項例)')
order by seq;
```

## 4. 頁対応の注意（パイロット知見）
- `toc_nodes.page` は**印刷頁/headline頁**。自炊PDFの物理頁とはオフセット差（実測 `PDF頁 ≒ 印刷頁 + 10` 等、本ごと）。
  → 各本の冒頭1–2頁で校正してから範囲指定（S3）。
- LION BOLTの `start/endHeadlinePage` があれば範囲が直接取れ、校正後の頁切りが安定。

## 5. 版の扱い（D-5/LIONBOLT知見）
- 詳細TOCが揃うのは**新しい版**が多い（LION BOLTはOCR対象が新刊中心）。
- 例: 契約書式実務全書は**第3版がLION BOLT収録**（283/290/542項目）。出典本側の版と差がある場合、
  **TOC・正規化は新版基準**、自炊画像は所蔵版に合わせる（版差は式名で対応付け、頁は校正）。

## 6. 依存・順序
1. （Mac）bib_toc apply → toc_nodes生成（DDL含む, 承認済みRUN_ME）
2. （Mac）新3源map apply（D-6採用後・dry-run再検証・owner承認）→ LION BOLT等が入る
3. （本リポ/この環境）上記(a)(b)クエリで出典本×TOC骨格を確定 → ポイントOCRへ
   ※ toc_nodes投入後は、Supabase MCPで読み取りクエリのみ実行（書込みなし）

## 7. すぐ着手できること（apply前でも）
- 出典本175の **ISBN→identity** 突合準備（DD-LITID candidatesと出典ISBNの照合表）。
- ポイントOCRの **頁校正テーブル**（本ごとの PDF–印刷頁オフセット）を、パイロット済み本から作り始める。
- 式名 正規化（norm_title_v1準拠）で、式↔TOCノードの突合関数を用意（DD-TOCATTACH §1.2に合わせる）。
