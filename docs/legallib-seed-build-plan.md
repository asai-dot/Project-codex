# legallib → biblio 取込プラン v0.4（ライブスキーマ準拠）

> status: レビュー用。**v0.1〜v0.3（alo.works/toc_nodes/fingerprints/メダリオン）は撤回・superseded。**
> 正本(SoT)は Box の ALO 仕様書＋CODEX設計＋**ライブ `biblio` スキーマ**。
> 対象DB: Supabase `asai-dot's Project`（`nixfjmwxmgugiiuqfuym`）の **既存 `biblio` スキーマ**。

## 0. 状況（ライブ確認済み 2026-06-06）
`biblio` は稼働中。bib_records 10,326 / bib_toc 552,544 / authors 2,200 / terms 554 / bib_terms 0。

| source | 件数 | 備考 |
|---|---|---|
| asai-bookshelf | 6,624 | 事務所所蔵(BookDX)。form_type細分類・ISBN高率 |
| bencom-library | 3,802 | BOOK/PERIODICAL/WEB。ISBNほぼ無し |
| **legal-library** | **0** | **未投入＝本タスク** |

ローダ正本: `github.com/asai-dot/asai-biblio-ingest`（private）の `load_bencom.py` / `ingest.py`。
取込3層方針: コード=GitHub正本 / ドキュメント=Box正本 / 構造化データ=Supabase正本。

## 1. 結論
**legallib は既存 `biblio` への source 追加**。bencom・asai-bookshelf と同じテーブル形状に載せ、`load_bencom.py` に倣った `load_legallib.py` を書くだけ。スキーマ変更なし（＝Data API再公開も不要）。

## 2. conform先（既存スキーマ・変更しない）
ライブ確認済みの列：
- `biblio.bib_records`(PK bib_id text): title, title_yomi, subtitle, responsibility, edition, publisher, pub_place, pub_year(int), series, volume, physical, isbn, issn, ncid, ndl_bib_id, ndc, ndlc, language, note, **source**, raw(jsonb), imported_at, updated_at, source_url, source_hash, form_type
- `biblio.authors`(PK author_id text): name, name_yomi, name_roman, alt_names(text[]), birth/death_year, dates_note, ndl_auth_id, viaf_id, source, raw, updated_at, **normalized_key**
- `biblio.bib_authors`(PK bib_id,author_id,role,ordinal): role default 'creator'
- `biblio.bib_toc`(PK bib_id,ordinal): **ordinal(0始まり) / level(int) / page(int,null可) / text** — フラット構造
- `biblio.terms`(PK term_id): term, term_yomi, scheme, broader_id(self FK), scope_note, source, raw / `bib_terms`(PK bib_id,term_id)

## 3. マッピング（legallib → biblio）
| legallib | → biblio | 規則 |
|---|---|---|
| 内部book_id | `bib_records.bib_id` = `LEGALLIB:{book_id}` | 決定論的・source-local |
| isbn | `isbn` | あれば。**マージキーにはしない**（同定はauthorityで後） |
| 書名/出版社/出版年/責任表示 | title/publisher/pub_year/responsibility | source-thinはauthority層で解決、biblioは忠実保全 |
| 生JSON | `raw` (jsonb) | 全保全。`source_hash`=sha256, `source_url`=legallib URL |
| — | `source` = `'legal-library'` / `form_type`='BOOK' | |
| 著者 | `authors` + `bib_authors` | `LEGALLIB-AUTH:{md5(normalized)}`、`normalized_key`でdedup、**複合著者は分割しない**(bencom方針)、role='creator' |
| `{l,p,t,level}` | `bib_toc` | ordinal=配列位置(0始まり)、level=level、page=p、text=t。**parent/toc_node_id等は不要**（bib_tocはフラット） |
| 巻末索引 | terms/bib_terms | scheme='LEGALLIB'。**後フェーズ**（bencom同様まず空でも可） |

## 4. ローダ手順（load_bencom踏襲・冪等）
取込順（FK厳守）: `authors → bib_records → bib_authors → bib_toc`（→ terms/bib_terms 後）。
- 500/1000件バッチ upsert、決定論ID（再実行で同一）、`--dry-run`、`--limit`、`SUPABASE_SCHEMA=biblio`、service_role key。
- 実測（bencom 55万TOC）約3分 → legallib 2,751冊も同程度。

## 5. ゲート/検証（sanity_checks.sql 流用 + 追加）
- `source='legal-library'` の bib_records が legallib件数(2,751)と一致
- bib_toc 孤児 0（FK）/ ordinal が book内 0始まり連番
- 既存 source（asai-bookshelf/bencom）が**一切改変されない**
- 再実行 diff 0（冪等）
- normalized_key 衝突で別人を統合していない（誤統合0）

## 6. 後続（biblioの外・別フェーズ）
- **横断同定（マスター）**: `authority.publication/source_record/publication_author_evidence/publication_author_claim`（未構築）。ISBNで asai-bookshelf(所蔵)↔legallib↔bencom を **promotion制で**突合、**版は束ねない**(DDL-20260428-01)、誤マージ0。
- **control lineage**: snapshot/ingest_job/batch（bencom契約どおり薄く追加）。
- **catalog/serving/telemetry**: アプリ投影は後。
- **雑誌**: legallib PERIODICAL 422号は次スコープ（巻号正規化未確定）。

## 7. 要決定／ブロッカー
- `bib_id` 採番 = `LEGALLIB:{legallib_book_id}` で良いか（ISBN基準にしない方針でOKか）
- `form_type` = 'BOOK' 統一か、asai-bookshelf式の細分類（treatise/qa…）を付与するか
- 巻末索引 terms を今やるか後か
- **コード置き場**: `load_legallib.py` は private repo `asai-biblio-ingest` に置くのが筋（私の現GitHubスコープは `project-codex` のみ＝直接pushは別途権限/手段が要る）。当面このrepoにドラフトを置き、後で移送も可
- **legallib生JSONの実トップレベル列**（書名/著者/出版社等のキー名）確認 → マッピング確定（1冊実物が要る）
