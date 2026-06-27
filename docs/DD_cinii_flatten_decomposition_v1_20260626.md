# DD: CiNii 解きほぐし（フラット化・カラム分解）スキーマ v1 (2026-06-26)

- status: 設計のみ（read-only調査に基づく）。実フラット化(63.8万件)はパイプライン処理＝実装。
- 親: `DD_cinii_publication_ingestion_v1` / `DD_eradcode_acquisition_v1` / `データ編成指針`(Adapter→Parser→Merger)
- 目的: CiNii の深いネスト JSON-LD を、authority へ入れる**前に**フラットな2表へ分解（=Parser段の正本化）。
  ネストのまま毎回パースする無駄と、多値NRID/マルチISSNの曖昧さを、**一度きりの列分解で解消**する。

---

## 0. なぜ解きほぐすか

現状の CiNii detail は1ファイル=1論文の JSON-LD で、要素が配列・入れ子：
- `creator[]`（著者複数）→ さらに `creator[].personIdentifier[]`（NRID/researchmap/orcid…が混在）
- `creator[].personIdentifier[@type=NRID]` は **1著者に複数**（最大~35。名寄せ候補が束ねられている＝汚染の元）
- `publication.publicationIdentifier[]`（ISSN/PISSN/LISSN/NCID が並列）

→ このまま authority 突合に使うと毎回ネスト解釈が要り、ISSN絞り・NRID突合・重複検知が重い。
**フラット2表に開けば、以後はSQL一発**。eradCode も列として落ちる。

設計位置づけ: これは **L1 取込層の Parser 出力（derived・冪等・再生成可能）**。raw JSON は L0 に保持（潰さない）。authority へのマップ(`DD_cinii_publication_ingestion`)はこのフラット表を入力にする。

## 1. テーブルA: `cinii_pub_flat`（1行 = 1論文 / CRID）

| 列 | 元フィールド | 備考 |
|---|---|---|
| crid | `@id` | PK。URL接頭辞を除去 |
| resource_type | `resourceType` | 紀要論文/学術雑誌論文 等 |
| title_ja / title_en / title_kana | `dc:title[ja/en/ja-Kana]` | 多言語を列に分離 |
| container_title | `prism:publicationName` | 誌名 |
| issn / pissn / lissn | `publication.publicationIdentifier[ISSN/PISSN/LISSN]` | **マルチISSNを型別に列化** |
| issn_norm | 上記を正規化した代表ISSN | 誌スコープ突合用(単一) |
| ncid | `[NCID]` | NII書誌ID |
| naid / ndl_bib_id / doi | `productIdentifier[NAID/NDL_BIB_ID/DOI]` | DOIは稀 |
| volume / issue | `prism:volume / number` | |
| page_start / page_end | `prism:startingPage / endingPage(pageRange)` | |
| pub_date / pub_year | `prism:publicationDate`(＋年抽出) | |
| publisher | `dc:publisher` | |
| n_authors | `count(creator)` | |
| kaken_project_ids | `project[].projectIdentifier` | jsonb配列(科研費番号) |
| subject_ndc | `dcterms:subject` | jsonb配列 |
| is_legal_journal | 派生(issn_norm ∈ 法律誌ISSNセット) | **スコープflag** |
| raw_ref | 元ファイル/CRID | L0 raw へのポインタ |

## 2. テーブルB: `cinii_author_flat`（1行 = 1著者×1論文 / 解きほぐしの核）

`creator[]` を**縦持ち展開**し、`personIdentifier[]` を**型別カラム**に開く。

| 列 | 元フィールド | 備考 |
|---|---|---|
| crid | 親 | FK → cinii_pub_flat |
| ordinal | creator 順 | 著者順(筆頭=1) |
| name_ja / name_en / name_kana | `foaf:name[...]` | |
| affiliation | `jpcoar:affiliationName` | あれば |
| creator_crid | `creator.@id` | 研究者CRID(代表ID候補) |
| nrid_all | `personIdentifier[@type=NRID][]` | **多値をそのまま配列保持**(監査・名寄せ用) |
| nrid_count | `len(nrid_all)` | **汚染検知**(>1で多重) |
| nrid_1000 | nrid_all のうち `1000`系 | e-Rad由来 |
| **erad_from_nrid** | `right(nrid_1000, 8)` | ★解きほぐしの成果＝eradCode列(導出) |
| kaken_researcher_id | `personIdentifier[@type=KAKEN_RESEARCHERS]` | eradCode直書きがある場合 |
| researchmap_id | `personIdentifier[@type=RESEARCHMAP]` | |
| orcid | `personIdentifier[@type=ORCID]` | |
| cinii_author_id | `personIdentifier[@type=CINII_AUTHOR_ID]` | |
| viaf | `personIdentifier[@type=VIAF]` | biblio↔authority供給源候補 |
| nrid_primary | 代表ID選別後の1件 | creator_crid優先で決定(下記) |

## 3. 解きほぐしの3原則（曖昧さをここで殺す）

1. **配列は縦持ち or 型別列に開く**：`creator[]`→B表の行、`personIdentifier[]`→型別カラム、`publicationIdentifier[]`→ISSN型別カラム。
2. **多値NRIDは「全保持＋代表選別」の二本立て**：`nrid_all`(全部) と `nrid_primary`(代表1件)を両方持つ。代表は creator_crid(研究者CRID)優先 → 1000系優先 → 単一なら自明。`nrid_count>1` を汚染フラグに。
3. **eradCode は列として導出**：`erad_from_nrid = right(nrid_1000,8)`（規則確定済, DD_eradcode §3）。`kaken_researcher_id` 直書きがあれば優先。

## 4. これで何が一発になるか

- **誌スコープ件数**: `SELECT count(*) FROM cinii_pub_flat WHERE is_legal_journal`（dry-run対象がSQLで出る）
  - **スコープ二重性（2026-06-27 実測で確定）**: 「誌レベル(法律誌に載る全記事)」＝数十万オーダー（過大。法律誌の紀要・非法学記事を含む）vs「内容レベル(DD-CINII-001の3軸=法律論考判定)」＝**約2〜3万件**。**dry-run実投入対象は内容レベル≈2〜3万**が妥当。`is_legal_journal` は前者(誌絞り)なので、DD-CINII-001の3軸スコアと合わせて二段で絞る。
  - 補足: 既存集計(`cinii_batch/issn_summary.tsv`=175誌)からは誌レベルの概数しか出ず、`legal_journal_issn_filter.jsonl` はBoxテキスト抽出不可(500)で**正確な誌数・件数はjsonl直パースが必要**。この `cinii_pub_flat` を作れば正確値が初めて確定する。
- **NRID突合**: `cinii_author_flat.nrid_primary = authority.person_history.history_value`（B表とJOIN一回）
- **eradCode供給**: `cinii_author_flat.erad_from_nrid` / `kaken_researcher_id` をそのまま person_identifier へ
- **重複検知**: crid一意・nrid_count分布で汚染可視化
- **biblio供給**: `cinii_author_id / viaf` を biblio.authors の権威ID補填に回せる(現状 ndl/viaf=0)

## 5. 形式・置き場所

- 中間フラットは **derived staging**：`staging_cinii.cinii_pub_flat` / `cinii_author_flat`（または parquet/duckdb）。raw(L0)とは別、canonical(authority)とも別。
- **冪等**：crid をキーに再生成可能（Parser版・生成日時を付す）。raw更新時のみ再パース(ハッシュ差分)。
- パイプライン: L0 raw JSON → **Parser(本DDの分解)** → flat 2表 → Merger(`DD_cinii_publication_ingestion`が authority へ)。

## 6. 実装メモ / 残課題

- 実フラット化(63.8万件走査)は実装環境のバッチ。MCP read の範囲外。
- `pageRange` の開始/終了分割、`publicationDate` の年抽出など正規化規則は実装時に確定。
- 著者ID欠落レコード(古い法律記事)は name_* のみ→ B表は作るが nrid_primary=NULL（candidate止まり）。
- このフラット表は ISSN絞り・eradCode・NRID突合・biblio補填の共通入力になるので、**先に作ると下流が全部軽くなる**（Owner指摘の通り）。
