# DD-PERIODICAL-002: 雑誌オブジェクト 記事・本文層 全体設計（v0.1-draft）

```yaml
doc: DD-PERIODICAL-002
title: 雑誌オブジェクトの記事単位・本文・初出・リンク層の設計
status: draft (head提案。owner ratify前)
author: codex(head)
date: 2026-06-24 JST
parent: DD-PERIODICAL-001 (識別子・edge設計, Box) / 04_ALO_雑誌レイヤ技術仕様書 (Box)
extends: WO-PERIODICAL-JOURNAL-REGISTRY / WO-PERIODICAL-ISSN-SEED-EXPANSION (号同定=L3, 実装済)
gate: 設計のみ。生データ取込/OCR/DB投入/accepted edge化/外部公開は owner GO 必須。external_share_allowed=false 不変。
```

## 0. なぜ今これを書くか（位置づけ）
号同定(issue_id, L3)は95%被覆・誤マージ0で実装済み。だが雑誌オブジェクトの価値の大半は**その上**にある:
記事単位への分割、本文(OCR/抽出)、初出メタ、本文からのリンク。現状これらは**設計図が存在しない空白**。
本DDは雑誌オブジェクトを「号同定器」から「**生バイト→記事→本文→リンクされた知識**のパイプライン」へ拡張する全体設計。

**設計原則（DD-001から継承・記事層へ拡張）**
- P1: 誤マージ/誤スプリット厳禁 → 記事層では「異なる作品が同一 article_id を持たない」「作品が誤った号に載らない」。
- P2: 非破壊・append-only・provenance必須。号同定と同じく resolver で決定論的に復元可能に。
- P3: 被覆より精度。曖昧は unresolved/held で残す。
- P4: owner gate（canonical昇格・本文公開・外部処理）。

## 1. 層モデル（雑誌オブジェクトの全体像）
```
L0 物理/生   : PDF(born-digital/scan), DVDイメージ, 生ページ束。source + provenance + ハッシュ
L1 分割      : 多記事PDF/号束 → 記事単位(article)へ。ページ範囲 → 記事境界
L2 本文      : scan→OCR / born-digital→テキスト抽出。記事ごと本文 + 品質スコア + レイアウト
L3 同定(済)  : issue_id(ISSN×通巻) + article_id(号内一意)。誌authority
L4 メタ      : 記事メタ=標題/著者/掲載誌/巻号頁/初出/出典。多ソース統合(D1 RAW, SIGNY, TOC, NDL)
L5 リンク    : article→annotates→判例 / article_published_in→issue / 本文引用抽出→法令・判例・文献
L6 語彙正規化 : vocab_hub 横断（著者名・件名・法令名）
```
各 article は **alo_works の1作品**。issue_id はその container。雑誌オブジェクトは L0–L5 を所有し、
edge は双方向（記事は判例を評釈し=out、号に載る=in）。「記事層は判例/文献の領分」ではない。

## 2. 新規オブジェクト/スキーマ（staging_periodical 拡張案）
| object | 主キー | 主要列 | 由来層 |
|---|---|---|---|
| `article_stage` | article_id | issue_id, seq_in_issue, title, authors[], page_start/end, 初出flag, source_system, work_id(alo_works) | L3/L4 |
| `article_source_blob` | blob_id | article_id, media(pdf/image), uri, sha256, page_range, origin(DVD/born-digital), license | L0 |
| `article_text` | (article_id, text_ver) | body_text, ocr_engine, ocr_conf, layout_json, lang, has_ruby | L2 |
| `article_first_pub` | article_id | first_pub_issue_id, reprints[], evidence(SIGNY/D1/手) | L4 |
| `article_edge` | edge_id | article_id, rel(annotates/cites/reprints), target_kind(hanrei/horei/bunken/article), target_id, extracted_from(title/body), confidence, status(candidate/accepted) | L5 |

- **article_id 規約**: `{issue_id}#a{seq}`（seq=号内通し）。号内順が無いソースは `{issue_id}#p{page_start}`。安定ハッシュ併記。
- すべて append-only + `resolver`/`reconcile` で再構築可能（L3と同じ思想）。

## 3. ソース別取込アダプタ（L0→L1→L2 はソースで分岐）
| ソース | 形態 | 必要処理 | 備考 |
|---|---|---|---|
| **DVD由来 生記事**(金融・商事判例/金融法務事情 等) | 画像系PDF/TIFF | L1分割→**OCR必須**→L2。ルビ/縦書き/二段組対応 | 精度の主戦場。OCR conf を必ず保持 |
| **born-digital PDF** | テキスト埋込PDF | L1分割→テキスト抽出(OCR不要)→L2 | ページ境界=記事境界の検出が要 |
| **D1 RAW(文献編)** | 構造化メタ | L4メタ直結（標題/掲載誌/巻号頁/著者）。本文は無 | 既に931誌labeled。記事↔issue_idの接合は済み土台 |
| **SIGNY 論考** | 論考メタ | **初出(L4 first_pub)特化**ソース | 再録判定の権威 |
| **TOC/目次** | 号目次 | seq_in_issue・ページ範囲の確定、評釈対象判例の取得 | L1境界とL5辺の両方に効く |

## 4. 高レバレッジ順（ヘッドの優先判断）
精度を下流に一番効かせる順に:
1. **L1×L3 の積を固める**（記事を正しい号に・号を正しいISSNに）。号同定(済)の上に**記事↔issue_id接合**を最初に敷く。ここが崩れると本文も評釈リンクも全部ズレる。D1 RAWは記事↔誌が既にあるので最短。
2. **L4 初出(first_pub)**。同一論考が初出誌→単行本→判例集と再録される雑誌特有の重複。初出を押さえると**重複排除と引用の権威付け**が一気に効く。SIGNY/D1がソース。
3. **L2 本文 + L5 本文リンク**。本文があって初めて「この評釈は最判平成Xを論じる」を**本文から抽出**でき判例オブジェクトと双方向に繋がる。タイトルマッチでは取りこぼす。DVDのOCRが律速。
4. L6 語彙正規化は L4/L5 の上に被せる（著者・件名・法令名）。

## 5. 分担（重複解消・実証済みモデル）
| 層 | producer | 監査/設計(私=head) | owner gate |
|---|---|---|---|
| L0/L1/L2 取込・OCR・分割 | Mac(生データ・計算資源が手元) | パイプライン設計・抽出精度の回帰監査(誤分割/低OCR検出) | 本文取込・公開 |
| L3 号同定 | Mac(NDL/記事データ) | ISSN衝突回帰検査(継続) | canonical昇格 |
| L4 メタ/初出 | Mac(D1/SIGNY) | 初出衝突・再録誤判定の監査 | — |
| L5 リンク辺 | Mac(本文抽出) | candidate辺の精度監査(誤リンク=誤マージの記事版) | accepted edge化 |
**head(私)の本務**: 全体設計の維持、各層の**精度監査の規格化**（号でやったISSN衝突検査を記事/辺へ一般化）、誤接合の指摘。
個別誌のWebSearch解決のような local でできる作業はやらない。

## 6. 精度監査の一般化（号→記事/辺）
DD-001の監査ビュー(false_merge/split/key_collision)を記事層へ拡張:
- `article_collision`: 同一 article_id に異なる本文/標題（=誤統合）
- `article_orphan`: issue_id 未解決の article、または存在しない号への接合
- `firstpub_conflict`: 1論考に複数の初出主張
- `edge_falselink`: 本文抽出辺で対象判例/法令IDが実在しない or 信頼度低
authority更新・取込のたびに回す回帰チェックとして常設。

## 7. 未確定（owner判断・次段で詰める）
- L0生データの所在/ライセンス（DVD原盤の取込可否、external_share=falseとの整合）。
- 初出(L4)優先 vs 本文連結(L5)優先 の重み（実務価値で owner 判断）。本DDは「L1接合→初出→本文」を推奨。
- DD-PERIODICAL-001(Box)の edge定義との整合確認（article_published_in/hanrei_published_in の正式スキーマ）。
- alo_works との article_id↔work_id 対応規約の最終化。

## 8. 次アクション（設計→着手の最小ステップ）
1. 本DDを owner レビュー（層立て・優先順・分担の承認）。
2. 承認後 **WO-PERIODICAL-ARTICLE-JOIN_v0.1**: D1 RAW記事↔issue_id 接合(L1×L3, 最短・最高レバレッジ)を起票。Mac=producer / 私=接合精度監査。
3. 並行 **初出スキーマ(article_first_pub)** dry-run を SIGNY/D1 で設計。
4. DVD/OCRパイプライン(L0-L2)は別WOで、ソース所在とライセンスの owner GO 後。
```
本DDは read-only 設計。生データ取込・OCR・DB投入・edge化・外部公開はすべて owner GO 待ち（DD-PERIODICAL-001 gate 準拠）。
```
