# カーネル選定 & 本番データ接地メモ（実装ロードマップ補遺）

> **date**: 2026-06-22 JST / **author**: 番頭(リモートClaude) / **status**: research record（DD-IMPL-ROADMAP-001 v0.1 を実データで接地）
> **依拠**: Supabase `nixfjmwxmgugiiuqfuym`（asai-dot's Project）本番実査。read-only。

## 1. カーネル候補（賃貸借終了/明渡＋要件事実・TOC 実測）
`toc_nodes` で「賃貸借 AND (終了|解除|明渡)」を含む章を持つ本のうち、論点ヒット上位：

| 書名 | topic_hits | toc_n | 標的シリーズ |
|---|---|---|---|
| Q&A 借地借家の法律と実務 第3版 | 71 | 276 | 実務解説 |
| 完全講義 民事裁判実務［要件事実編］ | 41 | 322 | **民事裁判実務（標的）** |
| 実務裁判例 借地借家契約における原状回復義務 | 41 | 158 | 裁判例 |
| 契約違反と信頼関係の破壊による 建物賃貸借契約の解除 | 39 | 99 | 実務解説 |
| 要件事実マニュアル 第5版 第2巻 民法2 | (7 in 終了系) | — | **要件事実** |
| 要件事実入門 紛争類型別編 第2版 | (3) | — | **要件事実** |

→ **table facet（要件事実表）比較**が成立する母集団が存在。カーネル＝「**建物賃貸借・信頼関係破壊による解除の要件事実**」を軸に、要件事実系2冊＋実務/裁判例1冊の計3冊で縦貫通させるのが有力。最終確定は Phase 1 着手時（PDF 突合後）。

## 2. ★重要発見：biblio↔bookdx の asset 同定ギャップ（Phase 1 前提条件）
「TOC→PDF」数珠繋ぎの前提として、**TOC コーパスと PDF 在庫が直接結合できない**：

| 事実 | 値 |
|---|---|
| `biblio.books` 総数 | 3,802 |
| うち `isbn` 非NULL | **6 のみ**（book_id=NOBN_… が主キー） |
| `bookdx.holdings` で pdf_folder_id 有 | **611**（isbn keyed） |
| `holdings.internal_id` が NOBN_ 形式 | **0** |
| `biblio.book_publication_link` | 3,798（book_id → authority.publication, match_basis/confidence 付） |
| `bookdx.candidates` | 3,802（= books 総数。holdings 側の橋渡し候補） |

含意：
- TOC（biblio, book_id）↔ PDF（bookdx, isbn/pdf_folder_id）の**直接 join キーが無い**。
- 橋渡しは `book_publication_link`（books→publication）と `bookdx.candidates`/`holding_bencom_link` の二段で、**asset 同定（DD-LITID 級）が未完**。
- **ロードマップ Phase 1 に「kernel 3冊の biblio↔bookdx asset 同定」を前提タスクとして追加**。スケール時は同定の機械化が必須（611冊）。カーネル段階では人手 3冊で解消可能。

## 3. 既存資産の確認（再発見しない）
- `toc_nodes`: `print_page`(552,544 投入)・`embedding`(pgvector・**0行**＝本文埋め込み未生成)・path_id/parent で木構造済。
- `control.releases`/`source_snapshots`/`active_release_pointer`: DD の `corpus_snapshot_id`/`release_id` の実体。release 1件・pointer 未設定＝**機構有・未稼働**。
- `formobj.{form_object,form_variant,requisite}`: 要件事実層（`grounded_in_law`/`favors_role`/`requisite_class`/`defect_kind`）。空＝**XDOC table facet の出力先**。
- 拡張: pgvector 0.8.0 / pg_trgm 1.6 / pgcrypto。
- `authority.ocr_extract`(bbox_json 付) は著者同定用の狭い OCR。**書籍本文 OCR 層は別途必要**。

## 4. ロードマップへの反映事項
1. Phase 1 に「kernel asset 同定（biblio↔bookdx）」を前提タスク追加。
2. カーネル＝建物賃貸借・信頼関係破壊解除の要件事実（要件事実2冊＋裁判例/実務1冊）を第一候補として固定（PDF 突合で最終確定）。
3. `toc_nodes.embedding` 0行＝T軸検索は Phase 2 で kernel subset から生成（本番 backfill は Phase 5）。
