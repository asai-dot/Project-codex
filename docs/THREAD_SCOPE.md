# THREAD SCOPE — 知識グラフ（文献↔判例↔法令 / RAG）

このブランチ／スレッドの担当範囲。ビューワー（4図書館横断検索・ジャンプ）は別スレ
（branch `claude/toc-search-rag-tLcyb` / PR #6）。**互いのファイルは触らない。**

## ミッション
ALOが自前で握る**引用グラフ**を作る。商用2サービス（リーガル=文献→法令 / ベンコム=文献→判例）の
強みを吸い、着地は**ALOが構築できる公開アンカー**（e-Gov法令 / 裁判所HTML）＋内部PD。
商用の壁庭（判例秘書の暗号化URL等）には最後にオンランプのみ。最終的に③RAG「事務所ライブラリに聞く」
が、文献パッセージ＋根拠判例＋根拠法令の3レーン出典で答える。

## このスレが所有するファイル
- `src/case_identity.py` — 判例の正本キー（和暦/事件番号/裁判所、略記`最大判`/leala`令和４年（ワ）`、
  `extract_case_refs`でraw_textから地名込み再抽出）
- `src/case_deeplink.py` + `config/case_sources.json` — 判例の3層着地（内部PD→裁判所HTML→ベンコムオンランプ）
- `scripts/harvest_precedents.py` — ベンコムprecedentsページ→引用レコード
- `scripts/validate_case_refs.py` — 実OPACへの一括適用で被覆率/衝突（`--from-raw`）
- `tests/test_case_lane.py` — 56チェック
- `docs/literature_precedent_graph.md` — 本設計の主資料（§1-11）
- 共有参照: `docs/link_structures.md`（e-Gov/裁判所アンカー）/ `docs/architecture.md §7` / `schema/supabase_schema.sql`（case_citations/law_citations）

## 既に作った到達点（fork時点）
- 判例の**正本キー**は ALO未整備だったので本スレが提供（case_spineは案件＝別物、と確認済）。
- 既存資産に接続: OPAC/CiNii の case_citations 17,259件・`docket_raw`、D1KOS `article_cites_case` レビューレーン、
  `opac_parse.py` の `case_ref_text`。規律一致（claim_scope=cites / pending_review）。
- 被覆率実証: 旧case_ref_text=40% → `--from-raw`（raw_text地名込み再抽出）=100%（代表サンプル）。

## 次の一手（推奨順）
1. **フル17,259件の `--from-raw` 実走**（本番env: `validate_case_refs.py opac_parsed/ext_opac_articles.jsonl --from-raw`）→ 本番被覆率/衝突を確定。
2. ベンコム precedents 実ページの採取で harvest を実物固め。
3. OPAC `docket_raw` × 本スレ正本キーの突合（既存17,259件の名寄せ）。
4. e-Gov法令着地（alo-kg resolver/temporalを流用）・裁判所HTML着地（court_id既存メタデータ接続）。
5. 時点警告バッジ（temporal、データが溜まってから精度が出る）。
6. ③RAG（pgvector文献ノード＋エッジ同梱回答）。

## 触らない（ビューワースレの所有）
`src/deeplink.js` / `server/` / `public/` / `config/library_sources.json` / `data/` /
`scripts/build_toc_search_index.py` / `calibrate.js` / `generate_book_links.py` / `tests/deeplink.test.js`
