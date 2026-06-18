# 02_LIT_PHASE0_IDENTITY_DRYRUN_20260617

status: phase0_readonly_dryrun_record
created_at: 2026-06-17 JST
updated_at: 2026-06-17 JST (rev2: authority層・books欠落・3スキーマ重複を追記)
author: Claude (リモートセッション・浅井さん指示)
parent_design: DD-LITID-001 v0.2 + ATTR addendum(20260615) + FP signal strengthening(20260615) + O1 biblio_item_uri(20260613) = 通称 v0.4
gate: **READ-ONLY 棚卸し/dry-runのみ**。DDL / migration / backfill / biblio_item mint / canonical promotion は全て HOLD（owner ratify 待ち）。本記録でDBは一切変更していない（SELECTのみ）。

---

## 0. 目的

DD-LITID-001（文献同一性設計）の実装に先立つ **Phase 0 read-only 棚卸し**（DD-LITID-001 §8 Phase 0 / FP RESULT の proxy dry-run / ATTR RESULT の report-only dry-run に相当）。
狙いは「事務所内の文献データがなぜ不整合に見えるのか」を**実数で局在化**し、設計と実データが噛み合うかを確認すること。

対象DB: Supabase project `asai-dot's Project` (`nixfjmwxmgugiiuqfuym`)
- 関連スキーマ: `bookdx`(holdings/pdf_inventory/candidates/load_run) / `biblio`(books/bib_records/bib_toc/toc_nodes) / `authority`(publication/source_record/person…)
- もう一方の project `alo-connect`(`vlsunmqpjhzbhipiehzs`) は当該スキーマ空。

---

## 1. 棚卸し結果（件数）

| 領域 | 件数 | 備考 |
|---|---:|---|
| **bookdx.holdings 総数** | **6,524** | title_norm 充足 6,524(100%) / publisher_norm 6,521 |
| ├ ISBN付き(ISBN13 valid) | 5,397 | 全件が正規ISBN13 |
| ├ ISBN無し | **1,127** | ← fingerprint対象 |
| ├ has_pdf(自炊) | 611 | |
| ├ **bencom_id 充足** | **0** | 列は存在するが完全未投入 |
| ├ **source_record_hash 充足** | **0** | 同上 |
| └ **scanned=true** | **0** | has_pdf=611 と矛盾（scannedフラグ未設定）|
| bookdx.candidates(弁コム候補) | 3,802 | ISBN付き6 / publisher 3,802(100%) / source_record_hash 3,802(100%) |
| biblio.books | 3,802 | ISBN付き6 / **publisher 0(0%)**（candidatesと1:1の弁コム由来層）|
| biblio.bib_records(NDL/CiNii) | 10,326 | ISBN 5,403 / ndl_bib_id 5,002 / pub_year 10,069 |
| bookdx.pdf_inventory(自炊PDF) | 611 | 全件ISBN付き |
| authority.publication | 7,348 | 著者同定アンカー（book6,690/journal_issue544/other114）|
| authority.source_record | 7,351 | |

## 2. クロス結合の現況（ISBN橋）

正規化ISBN（数字/Xのみ抽出）でのdistinct結合:

| 結合 | 一致件数 | 解釈 |
|---|---:|---|
| holdings(ISBN) ↔ bib_records | **5,397 / 5,397** | ISBN付きholdingsは**100% bib_recordsに結合済み** |
| holdings(ISBN) ↔ pdf_inventory | 611 / 611 | 自炊PDFは100%結合 |
| pdf_inventory ↔ bib_records | 611 / 611 | 自炊も書誌と100%結合 |
| holdings(ISBN) ↔ candidates(弁コム) | **6** | ← 弁コム層との結合がここだけ |
| holdings(ISBN) ↔ biblio.books | 6 | 同上 |

## 3. 重要な訂正（通説の否定）

**「holdings ↔ biblio が0結合」という従来認識は誤り。**
- ISBN付き holdings 5,397件は bib_records と**完全結合**。自炊611件も完全結合。**ISBN中核は事実上の共有キーで既に揃っている。**
- 真の分断は次の2か所に**局在**する:
  1. **弁コム候補 3,802件 ↔ holdings が6件しか繋がっていない。** 意図された橋 `holdings.bencom_id` が**100%空**（設計された接続が一度も投入されていない）。
  2. **ISBN無し holdings 1,127件**（外部ID不在の尾部）。

## 4. FP proxy dry-run（biblio_fingerprint_v1 の部分適用）

正規化キー = `lower(空白除去(title_norm))` ＋ `lower(空白除去(publisher_norm))`（=DD-LITID §6.2 の title_norm+publisher_norm 部分。page_count/pub_year/editionは holdings 側に列が無く今回未使用）

| 測定 | 結果 | 現状ISBN比 |
|---|---:|---|
| 弁コム候補 → holding に title一致 | 1,806 / 3,802 (47.5%) | — |
| 弁コム候補 → holding に title+publisher一致 | **1,761 / 3,802 (46.3%)** | 現状ISBN一致は **6件** のみ |
| ISBN無しholding → 弁コム候補に title+publisher一致 | **784 / 1,127 (69.6%)** | — |
| holdings側 (title,publisher) 衝突グループ | **365** | 自動マージ不可→review必須 |
| candidates側 (title,publisher) 衝突グループ | **0** | クリーン |

**含意:** title+publisher fingerprint だけで、空だった bencom_id 橋の **約1,761本**、無ISBN holdings の **約784件** が read-only で復元可能。
ただし holdings側 **365衝突グループ**は holdings に `page_count`/`pub_year` が無いため曖昧 → FP RESULT(DESIGN_PASS_WITH_NOTES)の規律通り **自動マージ禁止・review行き**。

## 5. DD-LITID-001 への対応づけ（設計と実データの噛み合い）

| 実データ | DD-LITID-001 上の落とし所 |
|---|---|
| ISBN付き holdings 5,397＋bib_records＋自炊611 | `biblio_item`(不透明ULID) `identity_status=resolved`、ISBN/pdf_sha256/box_file_id は `biblio_identifiers` 証拠 |
| 弁コム候補 fingerprint一致 1,761＋無ISBN holding 784 | `identity_status=candidate`（`bencom_cid`/`lionbolt_book_id` を証拠化、`resolution_log`へ）|
| 365衝突グループ | `identity_status=split_required` → review queue（page_count/pub_year/TOC で腑分け）|
| holdings.bencom_id=0 / source_record_hash=0 | 未実装の橋。`biblio_identifiers` 証拠 + projection で恒久化 |

→ 設計（v0.4）と実データは**数値的に噛み合う**ことを確認。

## 6. 査読ガード遵守状況（本dry-runの位置づけ）

- DDL / migration / backfill / biblio_item mint / canonical promotion = **全てHOLD**（owner ratify前）。本記録は読み取りのみで遵守。
- これは O1 RESULT の `alo:lit:item:{UUIDv7}`（案B, ALLOWED_AFTER_OWNER_RATIFY）、ATTR RESULT の report-only dry-run、FP RESULT の proxy dry-run が**揃って次に要求していた唯一のGO**に該当。

## 7. 次工程（gate順守・owner判断待ち）

1. **fingerprint強化dry-run**（read-only）: 弁コム `candidates.raw` jsonb と bib_records から `pub_year`/`page_count` を補い、365衝突を圧縮。resolved/candidate/review の確定見積りを出す。
2. **owner ratify 判断**: `alo:lit:item:{UUIDv7}` 正準mint（O1案B）を owner が ratify するか。ratify後に初めて registry / alias gate / id generator gate の実装 → backfill dry-run。
3. backfill/DDL/本番突合は **owner ratify ＋ お目付け役監査の後**。

---

## 8. authority層は「出版社」ではない（rev2追記）

`authority.publication`(7,348) は出版社マスタではなく、**著者同定(person authority)レイヤの"刊行物"アンカー**。構造:

```
authority.source_record (生の出所/provenance)
 └ authority.publication (刊行物: book/journal_issue)  ← publisher は属性の一列にすぎない
      └ publication_author_claim → authority.person (安定人物)
           └ publication_author_claim_evidence / publication_author_evidence
 serving.publication_author_claim_accepted / _current (採用ビュー)
```

由来(source_system): `bencom-library` 3,802 / `ndl_judge_author_match_20260331` 3,500 / `scholar_candidate_bootstrap` 46。
publisher充足: 全体 5,168/7,348、**弁コム由来は 3,802/3,802(100%)**。container_title は全件空（現状は書籍中心、雑誌記事列は未使用）。

## 9. 「弁コム＝出所」の検証と biblio.books の publisher 欠落（rev2追記・本節が核心）

owner指摘:「弁コムは出版社ではない。出版社欄に出所(弁コム)が紛れているのはおかしい。元の本の実出版社へ遡って埋めるべき」。

### 9.1 検証: 出版社欄に弁コムは紛れていない
publisher欄が `bencom|弁護士|弁コム|ベンコム` を含む件数:

| 層 | publisher充足 | 弁コム汚染 |
|---|---:|---:|
| authority.publication(弁コム由来) | 3,802 / 3,802 (100%) | 4 |
| bookdx.candidates | 3,802 / 3,802 (100%) | 4 |
| bookdx.holdings | 6,521 / 6,524 (99.95%) | 23 |
| **biblio.books** | **0 / 3,802 (0%)** | 0 |

弁コム由来の実出版社 上位: 日本評論社577 / 中央経済社315 / 日本加除出版283 / 三修社280 / 新日本法規出版237 / 日本法令218 / 有斐閣195 / 法律文化社162 / 労働新聞社161 / 日本商事仲裁協会147 / 税務経理協会143 / 青林書院125。
→ **実出版社は正しく入っており、「弁コム」は `source_system` 列に分離されている**（汚染は4〜23件のみ）。設計上の source≠publisher 分離は概ね守られている。

### 9.2 真の欠陥: biblio.books だけ publisher を捨てている
- `biblio.books`(3,802) は `bookdx.candidates`(3,802) と **`book_id` で 3,802/3,802 (100%) 完全1:1**。同一弁コム集合・ISBN無し(6件)。
- books.publisher は **0%** だが、candidates(publisher 100%, 同一book_id)から **3,802件すべて決定的にbackfill可能**。
- books ↔ authority.publication は id 結合 **0**（authpub は publication_id の別体系）。

### 9.3 同一弁コム3,802が3スキーマに重複転記
同じ弁コムカタログが別キーで3か所に存在:

| スキーマ.テーブル | 役割 | キー | publisher |
|---|---|---|---|
| bookdx.candidates | 棚DX候補 | book_id | 100% |
| biblio.books | 書誌(痩せコピー) | book_id(candidatesと100%一致) | **0%** |
| authority.publication | 著者アンカー | publication_id(別体系) | 100% |

→ DD-LITID/ATTR 的には、これらは**1つの biblio_item に収斂すべき同一観測群**。publisher は観測(値=実出版社, 出所=bencom)。books は publisher を独立保存せず観測から射影すべき層であり、現状は「採用値=観測接地」の違反例。

### 9.4 books と holdings の関係
- books をタイトルキーで holding に一致: **1,170 / 3,802 (31%)**（うち ISBN付きholding 618 / ISBN無しholding 555）。
- 残り 約2,632件は holding に出てこない＝**蔵書ではない弁コムカタログ本**。
- すなわち books/candidates ≈ 弁コムカタログ宇宙、holdings ≈ 実蔵書。両者は title で約1,170件重なる。

### 9.5 是正の方向（gate遵守・owner判断待ち）
- **即時の低リスク補完**: `biblio.books.publisher` ← `bookdx.candidates.publisher`（exact book_id, 3,802件, 決定的）。データ作成でなく欠落補完。owner ratify で実行可、未承認なら本記録に留置。
- **恒久解**: 3スキーマの弁コム重複を `biblio_item`(不透明ULID)に収斂し、publisher等は ATTR観測層→projection で一元化。books/candidates/authority.publication は同一itemへの観測/別名に降格。

---

## 付録: 実行クエリの要点（再現性）

- 全数: `bookdx.holdings`=6524, `bookdx.candidates`=3802, `biblio.books`=3802, `biblio.bib_records`=10326, `bookdx.pdf_inventory`=611, `authority.publication`=7348。
- ISBN正規化: `regexp_replace(isbn,'[^0-9Xx]','','g')`、ISBN13判定 `~ '^97[89][0-9]{10}$'`。
- fingerprint key: `lower(regexp_replace(coalesce(*_norm | title,''),'[[:space:]　]','','g'))`。
- books↔candidates: `biblio.books.book_id = bookdx.candidates.book_id`（3,802/3,802）。
- 弁コム汚染検出: `publisher ~* 'bencom|弁護士|弁コム|ベンコム'`。
- 本記録の数値は 2026-06-17 時点のスナップショット。load_run 更新で変動しうる。

---

## rev3 訂正 (2026-06-18): bib_records のソース帰属を実測訂正（append-only）

訂正元WO: `WO-BIBREC-FPDRYRUN-RECFIX-20260618`（read-only dry-run + 記録整備, gate=READ_ONLY_STRICT）。
本節は **append-only**。上記 §0〜付録の本文は一切削除・改変していない（Box 版管理で旧版 file_version 2537141514017 も保持）。
実行: 全SQLを `SET TRANSACTION READ ONLY;` 下で実行（`current_setting('transaction_read_only')='on'` 確認）。DB mutation 0 / biblio_item mint 0。

### rev3.1 訂正対象
§1 棚卸し表の行「**biblio.bib_records(NDL/CiNii)**」および本文中で bib_records を「NDL/CiNii 由来」とした帰属。**これは事実誤認。**

### rev3.2 実測（2026-06-18, source 列の実値）
bib_records.source は **2値のみ**:

| source | 行数 | isbn | ndl_bib_id | ncid(CiNii) | pub_year | ndc |
|---|---:|---:|---:|---:|---:|---:|
| asai-bookshelf | 6,524 | 5,397 | 5,002 | **0** | 6,267 | 5,503 |
| bencom-library | 3,802 | 6 | **0** | **0** | 3,802 | 0 |
| **合計** | **10,326** | 5,403 | 5,002 | **0** | 10,069 | 5,503 |

（合計 isbn 5,403・ndl_bib_id 5,002・pub_year 10,069 は §1 表の数値と一致。差は source 帰属ラベルのみ。）

### rev3.3 誤記の原因と正しい理解
- bib_records の **provenance（source 列）は asai-bookshelf（実蔵書）/ bencom-library（弁コムカタログ）の2ソース**。NDL も CiNii も source ではない。
- 「NDL/CiNii 由来」と見えたのは `ndl_bib_id` が 5,002 件埋まっていたため。だが ndl_bib_id は **asai-bookshelf 行のみ**(5,002/6,524) に付く **NDL 由来の同定補強（enrichment）**であり、provenance ではない。
- **`ncid`（CiNii ID）は全 10,326 行で 0 件** → CiNii 帰属は完全に無根拠。
- bencom-library 行は ndl_bib_id=0 / ncid=0（弁コムカタログ由来。NDL補強なし）。

### rev3.4 含意
§2〜§9 の結論（ISBN中核=resolved / 弁コムfingerprint=candidate / 365衝突=split_required / books.publisher欠落 / 3スキーマ重複）は**不変**。
変わるのはラベルのみ：bib_records は「NDL/CiNii 由来テーブル」ではなく、**「asai-bookshelf + bencom-library の2ソース縦積み（asai 側に NDL enrichment が乗ったもの）」**。
従って「bib_records 10,326 > 6,528 は異常」も誤り（→ `LIT_SOURCE_GAP_20260618.md` §B3 で決着）。

### rev3.5 実測クエリ
```sql
SET TRANSACTION READ ONLY;
SELECT source, count(*) AS total,
  count(*) FILTER (WHERE isbn IS NOT NULL AND isbn<>'')       AS isbn,
  count(*) FILTER (WHERE ndl_bib_id IS NOT NULL AND ndl_bib_id<>'') AS ndl_bib_id,
  count(*) FILTER (WHERE ncid IS NOT NULL AND ncid<>'')       AS ncid,
  count(*) FILTER (WHERE pub_year IS NOT NULL)                AS pub_year,
  count(*) FILTER (WHERE ndc IS NOT NULL AND ndc<>'')         AS ndc
FROM biblio.bib_records GROUP BY source ORDER BY source;
```

参照成果物（Box `_inventory` 388953248767 にミラー）: `a1_fanout_breakdown.json` / `a2_collision_compressed.json` / `a3_identity_status_estimate.json` / `SESSION_LOG_readonly_proof.json` / `SHA256SUMS.txt`。
