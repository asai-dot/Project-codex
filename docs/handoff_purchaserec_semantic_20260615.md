# Handoff — 購入レコメンド v2（content/semantic へ転換）/ 2026-06-15

新セッションはこれを最初に読む。長い試行錯誤の確定事項だけ凝縮。**同じ轍を踏まないこと。**

## 0. 目的
弁コムライブラリ(bencom)の未所有本から、事務所が「本当に欲しい本」を推薦する。基盤は Supabase `bookdx` schema。

## 1. 確定した結論（繰り返さない）
- **購入歴/作業状況ベースの推薦＝「枯れ」**（commodity collaborative filtering）→却下。
- **regexキーワードで8 domain分類＝「雑」**→却下。手作りの title 正規化も破棄方針。
- **ISBN単独同定＝不可**：(a)ISBN無し (b)シリーズ全部同一ISBN (c)版違いでも同一ISBN (d)読み違い/登録ミス。
  → 同定は**複合キー（書名＋著者＋ISBN＋ページ数＋出版日）**。文献DDに論考あり。
- **本筋＝中身の意味空間での content 推薦**。ただし**セマンティックデータは未構築＝それを作るのが技術仕事**。
  pgvector(vector 0.8.0) は当該Supabaseに**インストール済み**。
- 推薦は **need/gap-driven**（①空白起点＝薄い主題を埋める ②引用・権威起点＝判例/論文が引く未所有定番 ③先回り＝法改正/新論点）。**history-driven ではない。**

## 2. 必読設計（新セッション冒頭で読む）
- **`docs/alo/32_literature_layer.md`（Box file_id=2173755733934）= 文献オブジェクトの canonical 設計**。推薦も同定もこの上に乗せる。今回読めずに終わった。
- 関連: `33_magazine_layer.md`(2173747518039) / `DD-VOCAB-000_meaning_backbone`(2276848606937 意味背骨) /
  `DD-TOCLEGALREF-001`(2269729051059) / `bibnorm_offload_assessment_20260603`(2262755204409) /
  `isbn_inventory_architecture`(2183672055716) / `SOTSYNC_..._3layer_divergence`(2259797483217=SOT-001) /
  `HANDOFF_phaseA_bookshelf_pdf_match_v2`(2259709275751) / `bookshelf_pdf_match.py`(2226180887285=正準normalize).

## 3. 現状の実体（Supabase project `nixfjmwxmgugiiuqfuym` / schema `bookdx`）
- `holdings` 6,524（=asai-bookshelf 所蔵。`has_pdf`/`pdf_folder_id` 列を追加済）
- `candidates` 3,802（=bencom-library 候補）
- `buy_candidates`(view) 1,894（未所有BOOK。title/isbn dedup。**まだ既所有が漏れる**＝SOT-001の天井）
- `pdf_inventory` 611（自炊page1のISBN突合で `has_pdf` 実体化＝Phase A 第1波）
- `tag_domain` 空 / `load_run` あり / RLS・grants 設定済（anon/authenticated 遮断）
- 元データ: `biblio.bib_records`(title, responsibility=著者, publisher, pub_year, physical=頁, isbn, ndc, raw),
  `bib_toc`(約56万行=TOC), `bib_terms`, `terms`(554 法令定義語). `authority.publication`(7348, container_title/volume/issue=雑誌号の素).

## 4. SOT-001（最重要の制約）
裁断/自炊/PDF状態の「単一の正本」が無い。4層が件数も表記も乖離: 自炊フォルダ1,115 / books.json 6,528 /
Sheet 6,407 / bib_records。**dedup（既所有判定）の天井はここ**。実務寄り推薦に振るほど既所有の漏れが目立つ
（実証: 「M&Aを成功に導く法務DDの実務〈第4版〉」「企業法務1年目の教科書」等は既所有疑い）。
Phase A（(c)自炊フォルダ × (d)books.json 突合 → `has_pdf` 実体化）を閉じるのが前提。
自炊フォルダ名にISBN埋込多数。611は第1波（page1のみ/ISBNのみ/fuzzy未適用）。

## 5. 次の一手（順番）
1. `32_literature_layer.md` を読み、文献オブジェクトの正準モデル（lit_id/alo_uri/同定キー）を把握。
2. 同定を**複合キー**化（ISBN脱却）。`bookshelf_pdf_match.py` の正準normalize＋fuzzyを再利用。
3. **semantic 層構築**: `bib_toc`＋title＋`bib_terms` を embedding（Supabase Edge `gte-small` 等→pgvector格納）。
   PoC 数百冊 → 全件。これが「技術仕事」の本体。
4. need/gap-driven 推薦: 所蔵の意味カバレッジが薄い領域 × 重要新刊、を距離/密度で。
5. Phase A 残: 自炊page2(153)＋fuzzy(0.85)＋(d)を `bookshelf_master_latest.csv`(file_id=2187212488151, 2.98MB,
   取得時に表現生成pending→再取得要)に差替えて全1,115再測定。

## 6. 環境メモ（ハマり所）
- 直結 Postgres(5432/6543) は network policy で**遮断**。`bookdx` 書込は MCP `execute_sql` のみ。HTTPS(443)は通る。
- Box `get_file_content` は **~1.5MB まで安全**、33MB+ は**セッション落ち**。大物は (d) に使わない。
- execute_sql のクエリ本文は生成トークン＝**MB級の転記は不可**。ISBN等の数字列なら可（611投入はこれで実施）。
- branch `claude/purchase-recommendations-topic-bXfvG` / PR #7。
