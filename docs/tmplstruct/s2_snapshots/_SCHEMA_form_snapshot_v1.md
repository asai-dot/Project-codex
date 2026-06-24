# form_snapshot.v1 — S2出力の正準スキーマ（書式オブジェクト）

DD-FORMOBJ-001 の **S2（源別snapshot）** 出力標準。1ファイル = **1書式 × 1源** の構造化抽出（merge前）。
canonical（S3）はこれらを源優先policy＋crosswalkで合成して作る。本フォルダの3本が参照実装。

## トップレベル
| key | 型 | 説明 |
|---|---|---|
| `schema` | str | 固定 `"form_snapshot.v1"` |
| `form_uid` | str/null | sticky不変ID（S5確立時に発番 `alo:form:{ULID}`）。**未確立はnull** |
| `provisional_key` | str | `{book/toc参照}:{ノード}` の暫定キー。form_uidへ resolution_log で対応 |
| `anchor` | obj | **住所**（下記）。OCRでなくTOC/紙面で決める |
| `source` | obj | 源・provenance・スキャン・OCRエンジン |
| `form_title` / `form_no?` | str | 式名（正準・norm_title_v1で誤謬クラス吸収）／書式番号 |
| `form_kind` | enum | `contract\|agreement\|notice\|minutes\|decision\|application\|bylaw\|clause_set\|other` |
| `language` | enum | `ja\|en\|…` |
| `content` | obj | `blocks[]` ＋ 集計（下記） |
| `quality` | obj | `notes` ＋ `ocr_error_classes[]`（廷→延 等。吸収せず層で保持） |
| `confidence` | obj | `source_authority × merge × quality_adjustment`（係数列、finalは導出） |
| `form_group_uid` | str/null | 版跨ぎ「同一抽象書式」束ね（候補のみ・自動禁止）。v0.1は予約=null |
| `resolution_log_ref` | str/null | 確立・改訂の監査ログ参照 |

## anchor（住所）
| key | 説明 |
|---|---|
| `canonical_book_id` | DD-LITID解決後の正準書籍ID。**未解決はnull** |
| `book_ref` | `bencom_bib_id / isbn / title`（＋版違い時は `source_book_isbn`） |
| `toc_node_id` | toc_nodes投入後のノードID。**未投入はnull** |
| `toc_ref` | 暫定アンカー：`source(bencom_bib_toc\|image_label) / ordinal / level / text` |
| `page_span_print` | 印刷頁 `[start,end]` |
| `page_span_pdf` | 源スキャンの物理頁 `[start,end]`（校正後） |
| `page_offset_pdf_minus_print` | 本ごとのオフセット実測（`gate_page_calibration_recorded`） |
| `span_kind` | `single_node`（独立書式）/`subtree`（小節点群）/`embedded`（解説埋込）/`multi_node` |
| `edition_mismatch?` | スキャン版とTOC版が違う場合 true |

## content.blocks[]（block型は9種に固定）
`heading` / `party` / `recital` / `clause` / `item` / `signature` / `date` / `attachment` / `note`

| field | 説明 |
|---|---|
| `type` | 上記9種 |
| `no?` | 採番（`第1条`/`第1章`/`RE`/`TO`/`FROM`/`CC`/`注1` 等） |
| `title?` | 条見出し（`目的` 等） |
| `text?` | 本文（OCR忠実。プレースホルダ `XX`/`【 】`/`[ ]`/`___` は保持） |
| `items?` | 項・号の配列（clause/item内） |
| `blanks?` | 空欄ラベル配列（**源に在る空欄のみ。創作禁止** `gate_no_blank_invention`） |
| `ref?` | 別紙・別表参照（attachment時） |

### content 集計（自動導出）
`block_count` / `clause_count`（clause型数）/ `item_count`（item型数）/ `blanks_total`（全blanksの和）

## 規約・ゲート（このスキーマが満たすもの）
- **発明禁止**: blanks/clauses/署名欄は紙面に在るものだけ。
- **anchor必須**: 住所のないsnapshotを作らない（pending可、ただしキーは保持）。
- **源別1 active**: `(form_uid, source_system)` に1スナップショット。
- **品質非吸収**: 意味のあるOCR誤りは `ocr_error_classes` に記録（norm検索吸収とは別）。
- **頁校正記録**: `page_offset_pdf_minus_print` を本ごとに保持。

## 参照実装（本フォルダ）
| file | 書式 | 型 | block/clause/item/blanks | span |
|---|---|---|---|---|
| `keiyakukaisho_kaijo_tsuchi.s2.json` | 解除通知書(英文文例) | notice | 10/2/0/21 | embedded |
| `gyomu_seizo_kihon_keiyaku.s2.json` | 製造委託基本契約書(サンプル) | contract | 7/3/0/2 | subtree |
| `kaishahoumu_shoshiki1-8.s2.json` | 発起人決定書(書式1-8) | decision | 10/0/4/11 | single_node |

3型（埋込/巻末書式/書式集）を一形式で表現できることを確認。生のパイロットJSON
（`../pilot_keiyakukaisho/out_*.json`）はraw記録、本フォルダがS2標準。
