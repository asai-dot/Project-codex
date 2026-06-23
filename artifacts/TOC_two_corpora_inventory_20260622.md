# 文献オブジェクト TOC 2コーパス統合棚卸し（実測ギャップ表）

> ⚠️ 帰属注記（2026-06-23 追記）: 本書の**構造論点（canonical一本化・最精度選択・source/status）は
> 既存の監査済み設計 DD-TOCATTACH / DD-TOCADOPT / DD-TOCNODES に帰属**する（再発明だった）。
> 詳細は `dd/DD-LITID_TOC_RECONCILIATION_20260623.md`。
> 本書で**新規に効く実測**は §2 のルート横断重なり（1,509 / 810）＝既存設計が待つ cross-source gold 候補のみ。

- 作成日: 2026-06-22
- 目的: マスター契約（golden/silver・最精度選択規則）設計の**前提実測**。設計語彙を実データの形に根ざす。
- 方法: DB read-only（Supabase nixfjmwxmgugiiuqfuym）＋ Box read-only（folder 観測のみ）。**書込・DDL・egress なし**。
- 監査拘束（不変）: candidate≠confirmed / coverage≠correctness / title一致は候補（別版・同名衝突あり）。

---

## 0. 結論サマリ（3行）

1. TOC は実は**3表現**: ①bencom DB(toc_nodes) ②bencom DB(bib_toc) ③self-scan Box(per-title JSON)。①②は**同一corpusの2形**、③だけが別corpusで**DB未投入**。
2. self(ISBN/NDL強・TOC=Box) と bencom(ISBN/NDL無・TOC=DB) は**識別子が真逆に相補的**。
3. **タイトル一致が1,509冊**。うち**810冊は self側がISBN+NDL保持**＝bencom同定欠落をTOC経由で埋められる金鉱。

---

## 1. コーパス別プロファイル

| 項目 | Corpus-BENCOM（DB） | Corpus-SELF（Box・未投入） |
|---|---|---|
| 格納 | `biblio.toc_nodes`(階層) ＋ `biblio.bib_toc`(flat) | Box `事務所内本棚DX化計画/app/data/toc/`（folder 370441454337） |
| 形式 | DB行（toc_node_id, parent, path, depth, print_page, title） | per-book JSON（`isbn_*.json` / `title_*.json`） |
| 冊数 | **3,802**（bib_records bencom 全件 100%） | **5,206ファイル**（self 6,524 の約80%） |
| ノード/エントリ総数 | **552,544**ノード | **≈776,999**エントリ（release計） |
| 粒度（/冊） | 平均145・中央値110・最大1,409 | 平均≈149（776,999/5,206） |
| 階層 | **depth最大4・92%がdepth≥2**（深い） | JSON構造（要パース確認） |
| 品質 | **空title 0・page欠落 0**（高品質） | 未測（348MB・要ローカル走査） |
| 識別子 | **ISBN 6件・NDL 0件**（同定弱） | **ISBN-keyed中心**（同定強） |
| provenance | `toc_source=unknown` 全件 | bookshelf_dx app/data（出所明確） |
| 品質階層 | `toc_status=unknown` 全件 | 無（DB外） |
| embedding | カラム有・**0件** | 無 |
| DB投入 | **済** | **未**（release滞留） |

※ `toc_nodes` と `bib_toc` は **book_id 完全一致（3,802/3,802）・件数一致（552,544）**＝同一 bencom TOC の「階層版」と「flat版」。toc_nodes が上位（hierarchy・embedding枠・source/status枠を持つ）＝**canonical候補**、bib_toc は派生flat。

---

## 2. ルート横断オーバーラップ（接続可能性の核）

self(asai-bookshelf) と bencom のタイトル正規化一致:

| 指標 | 値 |
|---|---|
| self タイトル（正規化distinct） | 5,836 |
| bencom タイトル（正規化distinct） | 3,802 |
| **正規化完全一致** | **1,509**（bencom の 40% / self の 26%） |
| └ うち self側が ISBN 保持 | 835 |
| └ うち self側が NDL 保持 | 813 |
| └ うち self側が ISBN+NDL 両持ち | **810** |

> 注: 正規化一致は**候補**。別版・同名異書・合冊の混入あり → DD-LITID 確定ゲート必須。
> ただし「両ルートにTOCがある」ので、**TOC内容の一致度そのものが確定の独立証拠**になりうる（後述）。

---

## 3. 識別子の相補性（なぜ統合が効くか）

```
self-scan : ISBN 5,397 / NDL 5,002  かつ  TOC 5,206冊(Box)   → 同定◎ 内容◎（但しDB外）
bencom    : ISBN 6     / NDL 0      かつ  TOC 3,802冊(DB)    → 同定✗ 内容◎（DB内）
```

- bencom は**内容(TOC)は完備だが同定子が無い**＝「中身は分かるがどの版か分からない本」。
- self は**同定子完備**。1,509の重なりで **self→bencom に ISBN/NDL を貸与**できる。
- 最大ペイオフ: **約810件の bencom 本**が、title+TOC一致経由で ISBN+NDL 候補を得る（candidate-grade）。

---

## 4. ギャップ＝マスター契約で埋めるべき項目（実データ由来）

| # | ギャップ | 実測根拠 | 契約で定義すべきもの |
|---|---|---|---|
| G1 | TOC出所が全件 `unknown` | toc_source 552,544件 unknown | `toc_source` 語彙（bencom_import / bookshelf_self / ndl_toc …） |
| G2 | 品質階層が全件 `unknown` | toc_status 552,544件 unknown | `toc_status` の golden/silver/bronze 定義 |
| G3 | self TOC が DB 未投入 | Box 5,206ファイル滞留 | bookshelf TOC の ingest 契約（read-only export→staging） |
| G4 | 同一版に複数TOC（最大2: self+bencom） | 1,509重なり | **最精度選択規則**（どちらのTOCを正にするか） |
| G5 | embedding 0件 | toc_nodes embedding null | 内容類似（dedup・ルート横断同一性）の embedding 方針 |
| G6 | flat(bib_toc)と階層(toc_nodes)の二重 | 同一corpus2形 | canonical を toc_nodes に一本化、bib_toc を派生明示 |
| G7 | bencom 同定欠落 | bencom ISBN6/NDL0 | TOC経由 identity 貸与の candidate ルール（810件） |

---

## 5. 設計への含意（マスター契約v0.1 に直接渡す論点）

1. **canonical TOC は `toc_nodes` に一本化**（hierarchy/source/status/embedding 枠を既に持つ）。bib_toc は flat 派生として retain。
2. **`toc_source` 初期語彙（実測ベース）**: `bencom_import`（DB既存552k）/ `bookshelf_self`（Box 777k・未投入）/ 将来 `ndl_toc` `ocr_colophon`。
3. **`toc_status` 階層**:
   - `golden` = 人手検証 or 単一高信頼源で確定
   - `silver` = 単一源・未検証だが構造健全（bencom現状＝page/title完備はここ）
   - `bronze` = 機械抽出のみ・要検証（OCR由来など）
4. **最精度選択規則（G4）**: 同一editionに self+bencom 両TOCがある1,509件で、(a)ノード数 (b)depth網羅 (c)page単調性 (d)空率 をスコア化し高い方を primary、他を alternate として保持（捨てない）。
5. **1,509は「評価の金鉱」**: 両TOCの内容一致度が高い→ DD-LITID edition確定の**NDL非依存な独立証拠**。低い→ same_work_diff_edition / 別版の検出器。**Q評価のgold seed候補**。
6. **OCRの位置づけ確定**: bencom TOCが既にsilver品質(page/title完備)で揃う以上、OCRは**全件前提でなく** G7残差（同定貸与で埋まらない bencom）と版/刷曖昧例に限定投下。611PDF→難所専用。

---

## 6. 次アクション（最効率順）

1. 本棚卸しを GPT 監査レーンへ（実測の独立確認）。
2. **マスター契約 v0.1 起草**（§5 を骨子: canonical一本化／source・status語彙／最精度選択スコア／1,509 gold seed／OCR残差化）。
3. （契約承認後）self TOC 5,206 を staging へ read-only ingest → 1,509 で内容一致スコア試走。

---

## 付記: 観測クエリ・出所
- DB: `biblio.bib_records / toc_nodes / bib_toc`（read-only 集計）。snapshot 2026-06-22。
- Box: folder 370441454337（`app/data/toc`）item数・size のみ観測。ファイル内容は未取得（egress回避）。
- 全数値は集計値。原本・索引の外部搬出なし（external_egress=prohibited 準拠）。
