# toc_nodes ライブ化の確認と S1 本番接続（2026-06-11）

## 入った範囲（実測）
`biblio.toc_nodes` がライブ。ただし**現状は弁コム(step1)のみ**：
- **552,544行 / 3,802冊 / toc_source 実質 'unknown' / toc_status 'unknown'**。
- 列: `id, toc_node_id, book_id, isbn, title, print_page, depth, path_text, path_id, parent_toc_node_id, toc_source, toc_status, embedding`。
- **sticky toc_node_id** 形式: `<bib_id>:toc:<seq>`（例 `NOBN_20220609_…会社議事録…_01:toc:287`）。
- 互換ビュー `biblio.v_bib_toc_compat` も新設。

## ⚠ LIONBOLT は toc_nodes に未投入
- LIONBOLT固有ISBN（全書第3版 9784324107508/515/522）= **0件**。
- `toc_source='lionbolt'` のノード = **0**。`book_id like 'LB%'` = **0**。別schema/別テーブルにもlionbolt無し。
- → 投入されたのは **step1（弁コム bib_toc→toc_nodes・承認済みRUN_ME）** で、**step2（新3源 LIONBOLT/legallib map apply）は未反映**と判断。
- **要確認**: LIONBOLT本投入(step2)が別env/別ターゲットに行ったか、未実行か。

## S1 本番接続（今できること・read-only）
- 本番抽出SQL: `tools/sql/form_addresses_from_toc_nodes.sql`（toc_nodesから real toc_node_id＋印刷頁範囲で書式アドレス）。
- **会社議事録〈第3版〉= 321【文例】**（toc_nodesでも完全一致）→ 321式すべてに **確定 toc_node_id ＋頁範囲** が付く（anchor確定）。

## 重要な実測: 書式ノードの粒度は本ごとに不均一（弁コムTOC）
| 出典本 | toc nodes | 【…N】marker | keyword書式 |
|---|--:|--:|--:|
| 会社議事録〈第3版〉 | 456 | **321** | 382 |
| 企業労働法実務入門【書式編】 | 519 | 0 | 77 |
| 会社法務書式集〈第3版〉(238式) | **150** | 0 | 11 |
| 契約書作成の実務と書式〔第2版〕 | 521 | 0 | 10 |
| 情状弁護アドバンス | 758 | 0 | 1 |

- 会社議事録は【文例N】で式が個別に立つ→**自動で全式アドレス化**。
- 会社法務書式集は **238式なのにtoc 150ノード**＝弁コム目次が粗く、**式が個別に立っていない**。
  → こういう本は **LIONBOLTの細目次（page範囲付き）** か **自炊02_目次のOCR** で粒度を補う必要（＝LIONBOLT投入の実益）。
- マーカー流儀（【文例】/【書式】/無印）も出版社ごとに違う → 書式検出は**源/シリーズ別に調整**（S1のladderは対応済、marker語彙を拡張）。

## 次アクション
1. **会社議事録**: 321式の anchor確定アドレスを確定（自炊が揃えばS2量産。本丸再自炊の最優先）。
2. **LIONBOLT step2 の所在確認/実行**（owner/Mac側）。粒度の粗い本（会社法務書式集等）はこれで救われる。
3. marker語彙の源別拡張（【書式】無番号・章内 書式 等）で keyword依存を減らす。
