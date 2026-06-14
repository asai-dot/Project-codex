# 3ライブラリー取得データ 再分析 ── 取り漏れ・未活用データの棚卸し

- 作成: 2026-06-14 / Claude（リモートセッション・浅井さん指示）
- 対象: LION BOLT（ライオンボルト）・弁コム法律書カタログ（=「エンコム/ベンコム」）・legal-library（リーガルライブラリー）の取得済みコーパス
- 目的: 「せっかく取ったデータを十分に使い切れているか」「本のジャンル/分類は取れているか・横串にできるか」「他に面白い未活用データはないか」の3点に答える再分析
- 一次資料: Box `事務所内本棚DX化計画/archive/...`・`データ種別分離_20260611/`・`_inventory/`（DATA_INVENTORY v1.1, REPORT.md, e2_results.json, newsources dryrun summary）・`loaders/load_legallib.py` 仕様（legallibbiblio v0.5 INGEST REQUEST）

> **重要な前提（governance）**: 本書は「設計検討・台帳整備」の範囲の*分析のみ*。RAG投入・embedding生成・MCP提供・外部共有はお目付け役レビューにより現在 **HOLD**。本書は実データを動かさない。

---

## 0. 結論（先に3行）

1. **取り漏れはほぼ無い。** 3ソースとも生JSONを `raw`(jsonb) に sha256 付きで完全保全しており、ジャンル/分類を含む全フィールドは*物理的には手元にある*。
2. **使いこなせていないものは多い。** `bib_records` に射影しているのは書誌コア列だけで、各サイトが持つ**分類・ジャンル・OCR品質・要約・外部リンク・引用リンク**は `raw` の中に眠ったまま、構造化・検索可能になっていない。
3. **「本のジャンルを横串」は正しく、かつ実現可能。** ただし**ISBNでの突合は弱い**（ISBNを持つのは LION BOLT の37.6%のみ／弁コム・legallib はISBNゼロ）。既に走っている「書名+出版社+出版年」フィンガープリント突合で**3サイト共通501冊／2サイト共通 約1,500〜1,900冊**が橋渡し済み。ここに各サイトのジャンルを重ねれば「同一書に対する複数サイトの分類ラベル」が取れる。

---

## 1. 何を取得したか（ソース別・フィールドレベル）

DATA_INVENTORY v1.1（2026-06-11）+ 各 REPORT より。

| ソース | 件数 | TOC | 本文 | 一意キー | ISBN |
|---|---|---|---|---|---|
| LION BOLT | 22,844冊（全25,049の91.2%） | 4,433冊・264,555項目 | なし（47条の5準拠） | `isbn` / `book_id` | valid13 **8,582** / invalid 3,664 / 空 10,598 |
| 弁コム | 4,490冊 | **全冊**・709,029ノード | なし | `content_id` | **全件空** |
| legal-library | 4,051（書籍3,629＋雑誌422） | 662,717ノード | なし | 内部 `book_id` | **全件空**（突合でISBN復元中） |
| （参考）LIC 4誌解説 | 7,394 | — | **本文あり** | `data_no` | — |

### 1.1 ソース別の「分類・ジャンル」系フィールド（=今回の主眼）

| ソース | 分類/ジャンルに使える生フィールド | 形式・例 | 現状 |
|---|---|---|---|
| **LION BOLT** | `genre[]` | 配列。例 `["保険法"]` | raw にあり。構造化列へ未射影 |
| **弁コム** | `tags[]`（`category:*`・`series:*`・`単行本`/`雑誌`）、`selection`、`bookshelf`、`content_type` | 例 `category:商法・会社法`, `series:LEGAL QUEST` | raw にあり。`category:`系のみ一度 domain 推定に使用（後述） |
| **legal-library** | `content_type`（書籍/雑誌の別）、責任表示。**サイトUIは分野で棚分けしているため raw に subject/分野キーがある可能性大（要 inspect）** | — | ローダの取込キーに**ジャンル/分類キーが無い**＝射影されていない |

### 1.2 LION BOLT が持つ「他では取れない」付加フィールド

`source_type`(scan/digital)・`accuracy_rank`(OCR精度 A/B/C)・`vertical`(縦書き)・`page_count`・`amazon_url`・`cinii_url`(学術DB)・`calil_url`(図書館蔵書)・`publisher_url`・`asin`/`kindle_asin`。

---

## 2. 「使い切れているか」── 利活用ギャップ

取込先 `biblio.bib_records` が conform している列は書誌コアに限定:

```
title, subtitle, responsibility, edition, publisher, pub_year, series, volume,
isbn, issn, ncid, ndl_bib_id, ndc, ndlc, language, note, source, raw(jsonb),
source_url, source_hash, form_type
```

ここから読み取れるギャップ:

- **分類列はあるが空。** `ndc`(日本十進分類)・`ndlc`(NDL分類) という分類専用列がスキーマに*ある*のに、3ソースのマッピングはどれもこれを埋めていない（legallib マッピング表は title/publisher/pub_year/responsibility/isbn/raw のみ）。**分類は構造としては用意済みなのに、供給されていない。**
  - **【訂正・2026-06-14】NDC/NDLCの供給元は3サイトではなく NDL（国立国会図書館書誌）。** NDL書誌は NDC・NDLC・件名(BSH/NDLSH)を持つ（NDCは openBD でも取得可、NDLCはNDL固有）。`bib_records.ndl_bib_id` 列と source priority の `ndl`(上位) が示すとおり、設計は最初からNDLを分類の権威として想定済み。
  - **問題は“ソースに無い”ではなく“既存NDL照会で分類を拾っていない”こと。** 実データ `colophon_ndl_results.json` を確認すると、現行のNDL照会は title/author/pubdate/link しか抽出しておらず、**NDC/NDLC が取得対象に入っていない**。穴埋めは新規取得ではなく**既存NDL照会の取得フィールドを増やすだけ**の小拡張。
  - 制約: NDLはISBN/書名で引くため、ISBNゼロの弁コム・legallibは ISBN復元（fingerprint突合・colophonの `recovered`）を経由する必要があるが、その経路も既存。
- **各サイト固有のジャンルは射影されない。** LION BOLT `genre[]`・弁コム `tags/selection/bookshelf`・legallib の分野は `raw` の中。SQLで `where genre = ...` も `group by` もできない＝検索・重み付け・メタタグに使えない。
- **OCR品質シグナルが死蔵。** `accuracy_rank`(A/B/C)・`source_type`(scan/digital) は、横断検索やRAGで「どのソースのTOC/本文を信頼するか」の重み付けに直結する一級メタだが未活用。
- **弁コム `abstract`（出版社あらすじ・数百字）が meta 止まり。** 1冊1要約の自然文は埋め込み・要約検索の最良の素材だが、表示/出力制限の open question（OQ-2）で保留。
- **既存のジャンル作業は弁コム単独・ドメイン8分類どまり。** `_run_util_05_bencom_tags.py` が弁コム `category:`/`series:` → `domain_l1 ∈ {civil, commercial, labor, ip, tax, criminal, procedure, administrative}` を構築（`analysis_genre_results.txt`）。**LION BOLT `genre[]` と legallib 分野は、この taxonomy にまだ接続されていない。**

> まとめ: **取り漏れ（capture loss）はほぼ無い**が、**射影漏れ（projection/usage loss）が大きい**。`raw` から構造化列・タグへ昇格させる工程が、分類・品質・要約・リンク系で軒並み未実装。

---

## 3. 「本のジャンルを複数サイトで横串」── 実現性と設計

浅井さんの「同じ本が各サイトでどのジャンルに分類されているか」を取りたい、は**データ的に成立する**。ただし2つの現実:

### 3.1 突合キーの現実 ── ISBNはあてにできない

- ISBNを持つのは **LION BOLT の 8,582冊（37.6%）のみ**。弁コム・legallib は**ISBNゼロ**。
- そこで既存パイプラインは **「書名+出版社+出版年」フィンガープリント**＋ISBN13チェックディジット＋自動マージ禁止ゲートで突合（`newsources_books_identity_dryrun`）。実績の重なり:

| 重なり | 冊数 | 突合根拠 |
|---|---|---|
| 3サイト共通（弁コム+LION BOLT+legallib） | **501** | title+publisher+year |
| 弁コム + legallib | 1,551 | 〃 |
| 弁コム + LION BOLT | 174 | 〃 |
| LION BOLT + legallib | 128 | 〃 |
| LION BOLT + 所蔵(zosho) | 1,932 | ISBN13完全一致 |

→ つまり「複数サイトのジャンルが*同時に*取れる本」は現状**数百〜千数百冊規模**。全冊ではないが、横串ジャンルの価値検証には十分な母数。

### 3.2 横串ジャンルの作り方（提案・設計のみ）

1. **正準ジャンル軸を1本決める**: 既存の `domain_l1`(8分類) を背骨にしつつ、より細かい第2層（例: 民法/会社法/労働法/知財/租税/刑事/民訴…）を `genre_l2` として定義。
2. **各ソースのラベルを正準軸へマップ**: LION BOLT `genre[]`、弁コム `category:*`/`series:*`、legallib 分野を、それぞれ `genre_l2` への対応表で寄せる（弁コム分は既存 `TAG_DOMAIN_RULES` を流用・拡張）。
3. **本（canonical work）単位で多数決＋出典保持**: フィンガープリント突合済みの本に、各サイトのジャンルラベルを `source_genre`(出典付き) として並べ、合議ジャンル `genre_consensus` と不一致フラグを持たせる。
   - メタタグ用途（本田＝「本だ」アプリ）: `genre_consensus` をそのまま付与。
   - リサーチ重み付け用途: 「3サイト中n社が国際法に分類」を信頼度スコアとして利用。
4. **legallib の raw を1冊 inspect**して subject/分野キーの有無を確定（v0.5時点で legallib 生JSONトップレベル列は "design-synthesis（未検証）" 扱い。ここを潰せば3点目が3社そろう）。

---

## 4. 他に眠っている「面白いデータ」（未活用の上位候補）

ジャンルは一例。同じく `raw` に入っていて、構造化すれば効く素材:

1. **TOC（詳細目次）の超大規模ストック** ── 弁コム709,029＋legallib662,717＋LION BOLT264,555ノード。**階層レベル＋ページ範囲付き**。
   - 「公序良俗を扱う章・節を持つ本とその頁」のような**節レベル検索**が可能。
   - 横断TOC突合も実証済み（bencom↔legallib **74%**一致、LION BOLT↔各社 **73〜78%**）。同一書のTOCを相互補完／OCR欠損補修に使える。
2. **OCR品質メタ（LION BOLT）** ── `accuracy_rank`(A/B/C)・`source_type`(scan/digital)・`vertical`。検索/RAGの**ソース信頼度の重み付け**にそのまま使える。
3. **弁コム abstract（あらすじ）** ── 1冊1要約の自然文。埋め込み・類書推薦・要約検索の最良素材。
   - **【訂正・2026-06-14】これは“取り漏れ”ではない。** abstractは弁コムmetaに**取得済み**（出版社提供の数百字・裏表紙的、種別分離READMEで「metaに含めた」と明記）。論点は capture でなく **usage**＝検索/埋め込みに回せていない（OQ-2でmeta_only据え置き＝HOLD側）。
   - **射程の限界: abstractは弁コム固有。** LION BOLT・legal-library・LIC には同等のあらすじが無い。「あらすじ要約検索」は弁コム約4,490冊には効くが、残り約27,000冊(LION BOLT/legallib)には素材が無い＝横断利用時は弁コム以外をTOC見出し＋将来の本文で代替する前提。
   - 付与率（非null率）の実測は未計上。必要なら弁コム4,490件で1回カウントして確定する。
4. **外部オーソリティ・リンク（LION BOLT）** ── `cinii_url`(学術DB)・`calil_url`(図書館蔵書)・`amazon_url`。ISBN欠損本でも、これらをたどって **NDC/NDLC・分類を外部から補完**できる経路。
5. **引用・参照リンク（弁コム）** ── with_external_url に**判例引用リファレンス 428,217件**。本→判例の**引用グラフ**を構成できる（gated・再配布NGに注意）。
6. **書式テンプレート（弁コム）** ── 175冊・6,976個の書式DLリンク。法律書式の構造化カタログ（gated・pointer only）。
7. **出版社・出版年の分布** ── LION BOLT で算出済み（有斐閣2,992／商事法務系3,000+、2010年代以降が過半）。蔵書方針・購入推薦の基礎統計に。

---

## 5. 推奨アクション（governance HOLD と整合する“設計のみ”）

> いずれも実DB書込・embedding・外部共有を伴わない。HOLD範囲内で着手可。

- **A. legallib raw を1冊 inspect** し、subject/分野キーの有無を確定（3.2-④）。所要数分、ゲート不要。
- **B. 正準ジャンル軸 `genre_l2` の対応表ドラフト** を作る（LION BOLT genre[]・弁コム tags・legallib 分野 → 共通軸）。既存 `TAG_DOMAIN_RULES` を起点に。
- **C. `raw`→構造化列の“昇格候補”台帳** を起票（genre/accuracy_rank/source_type/abstract/external_urls/citation_links を、それぞれ用途＝メタタグ／重み付け／検索 と紐付け）。
- **D. 横串ジャンルの価値検証 PoC を“紙の上で”設計**: 3サイト共通501冊で「サイト間ジャンル一致率」を出す dry-run 仕様だけ先に固める（実行は別途承認）。
- **E. NDC/NDLC 列の供給経路を決める**: 自前ジャンルとは別に、CiNii/図書館リンク or NDL 突合で標準分類を埋める設計を検討。

---

## 付録: 参照した一次資料（Box file id）

- DATA_INVENTORY v1.1 … `2276950720705`
- LION BOLT REPORT.md（スキーマ・genre[]・統計） … `2274975450659`
- データ種別分離 README（class別フィールド一覧） … `2276924870041`
- newsources identity dryrun summary（ISBN統計・overlap matrix） … `2277187057925`
- e2_results.json（TOC横断突合 match率・サンプル） … `2278293571061`
- legallibbiblio v0.5 INGEST REQUEST（bib_records列・legallibマッピング） … `2269094301007`
- bib_toc→toc_nodes schema差分 … `2278358764765`
- 弁コム tags→domain_l1 enrichment スクリプト … `2176179687748`
