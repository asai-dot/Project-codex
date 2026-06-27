# DD-LIONBOLT-INGEST v0.1 — lionbolt 法律書カタログ 本投入設計（実行前・要 ratify）

```yaml
doc_id: DD-LIONBOLT-INGEST-001
version: v0.1
status: design_for_review (NOT EXECUTED / DB mutation 0 / mint 0)
created_at: 2026-06-22 JST
author: Claude (claude.ai head) — 浅井さん指示「lionbolt/legal-library の本投入を進めて」
decision_by_owner: 「設計+ローダを PR で提出（実行はしない）」（2026-06-22）
supabase_project: nixfjmwxmgugiiuqfuym  # asai-dot's Project
gate: NO_WRITE (本DDの作成時点で DB への書き込みは一切なし。実行は owner ratify 後)
parent:
  - LIT_SOURCE_GAP_20260618.md (Box 2292462074338) — 4ソース設計 vs 2ソース実投入のギャップ記録
  - 法律情報コーパス データインベントリ台帳 v1.1 (Box 2276950720705 §2)
  - LION BOLT REPORT.md (Box folder 388659455439 / file 2274975450659)
```

> **このDDの性格**: lionbolt を Supabase に本投入するための**実行可能な設計図 + ローダ + マイグレーションSQL**。
> owner 選択により**この時点では実行しない**。ratify 後に `tools/lionbolt_ingest/` を回せば投入できる状態まで用意する。
> legal-library は source が Mac ローカルのみ（Box 未配置）でこのクラウド環境からは到達不能のため、**別紙 `LEGALLIB_HANDOFF_20260622.md` で Mac 側手順を引き継ぐ**。

---

## 1. ソース実体（Box 確認済み）

LION BOLT 法律書カタログ（株式会社サピエンス、著作権法47条の5 ベース、書誌+目次のみ・**本文不取得**）。
Box folder `388659455439`（`LIONBOLT_法律書カタログ_20260610`）に配置済み:

| ファイル | id | サイズ | 用途 |
|---|---|---:|---|
| `catalog_dedup.jsonl` | 2274970590283 | 64MB | **投入元**（ISBN dedup 済み・全フィールド+目次本体） |
| `catalog.jsonl` | 2274968884429 | 75MB | dedup 前（重複含む・使わない） |
| `INDEX.jsonl` / `INDEX.csv` | 2274974075505 / 2274975824906 | 11.5MB / 5.4MB | メタのみ（TOC本体除く・検証用） |
| `REPORT.md` | 2274975450659 | 11KB | データ契約（本DDの§3スキーマの一次ソース） |

**規模**: 22,844冊 / 目次あり 4,433冊(19.4%) / 目次項目 264,555 / 出版社 258社。
台帳v1.1 §2 の lionbolt 行（264,555項目）と一致。

---

## 2. 投入先の決定（新テーブルは作らない）

既存DBには lionbolt を受け入れる**空の器がすでに用意されている**。新規テーブルは作らず、以下に投入する:

### 採用（Phase 1）— canonical 層 + ソース登録
| 投入先テーブル | 現状 | lionbolt 投入後 | 役割 |
|---|---:|---|---|
| `biblio.library_sources` | 0 行（空） | **+1 行**（`id='lionbolt'`） | ソース定義レジストリ。`needs_auth/tier/cost/url_template/book_url_template/page_strategy` が lionbolt の profile（商用・JWT・URLテンプレ・月額）に一致 |
| `biblio.bib_records` | 10,326（asai 6,524 + bencom 3,802） | **+22,844**（`source='lionbolt'`） | 統合書誌カタログ。bencom-library と同じ器。a1–a3 の fingerprint/dedup 機構がそのまま lionbolt にも効く |
| `biblio.bib_toc` | 552,544（100% bencom） | **+264,555**（lionbolt 由来） | 書誌ごと目次。逆引き索引・網羅性チェックの土台 |

**なぜ bib_records 層か**: bencom-library が既にこの層に居る（catalog ソースの定位置）。lionbolt も catalog なので同層に置くと、本WO の dry-run（a1–a4）が回している同一性・dedup の機械をそのまま再利用できる（lionbolt × asai × bencom の跨ぎ重複が自動で triage 対象になる）。

### 保留（Phase 2・本DD非対象）— embedding/RAG 層
`biblio.books` / `biblio.toc_nodes`(embedding vector 列) / `biblio.book_links` は bencom の RAG 射影層。lionbolt の embedding 生成は別コスト・別ゲート（RAG投入は WO §6 禁止事項）。**Phase 1 では触らない**。必要になれば bib_records→books 射影として後続 DD で起こす。

---

## 3. フィールドマッピング（lionbolt JSON → bib_records / bib_toc）

REPORT.md §5 のスキーマを一次ソースとする。ローダは全フィールド `.get()` 防御アクセス。

### 3.1 `bib_records`（1冊 = 1行）
| bib_records 列 | lionbolt フィールド | 変換ルール |
|---|---|---|
| `bib_id` (PK) | `book_id` | `'lionbolt:' || book_id`（例 `lionbolt:YHK0000041`）。book_id 欠落時は `'lionbolt:isbn:' || isbn` にフォールバック |
| `source` | — | 固定 `'lionbolt'` |
| `isbn` | `isbn13`→`isbn` | 13桁数字のみ採用（`^[0-9]{13}$`）。不一致は NULL（holdings の check 制約に合わせる） |
| `title` | `title` | trim |
| `responsibility` | `author` | そのまま（正規化は dedup 段で） |
| `publisher` | `publisher` | trim（表記揺れは正規化せず raw 保持。dedup 段で吸収） |
| `pub_year` | `pub_date` | ISO8601 から年を抽出（`pub_date[:4]`、UTC でも年はズレない範囲） |
| `physical` | `page_count` | `page_count::text || 'p'`（既存 physical は text 形式） |
| `note` | `genre` / `accuracy_rank` / `source_type` | `genre` 配列 + OCR メタを 1 行 note に要約（例 `genre=[保険法]; ocr=scan/B`） |
| `source_url` | `book_id` | `'https://law-books.lionbolt.jp/books/' || book_id`（book_url_template） |
| `source_hash` | レコード全体 | `sha256(canonical_json(record))`（idempotency キー） |
| `raw` | レコード全体 | **元 JSON を jsonb で保持**（lionbolt は raw を埋められる。既存 asai/bencom は raw=NULL だったが lionbolt は provenance を残す） |
| `form_type` | — | `'monograph'`（暫定） |
| `ncid`/`ndl_bib_id`/`ndc`/`issn` 等 | — | NULL（lionbolt は NDL/CiNii enrich を持たない。外部リンク url は raw 内に保持） |

### 3.2 `bib_toc`（toc.items[] を展開）
`toc.items[]` を出現順に展開。`(bib_id, ordinal)` が PK。

| bib_toc 列 | lionbolt | ルール |
|---|---|---|
| `bib_id` | — | 親の bib_id |
| `ordinal` | items index | 0 始まりの連番（disabled を除外した後の連番） |
| `level` | `item.level` | 0=部,1=章,2=節… をそのまま |
| `page` | `item.startHeadlinePage` | int。欠落/0 は NULL |
| `text` | `item.text` | trim。空 or `disabled=true` の項目はスキップ |

> **検証**: 投入後 `count(bib_toc where source経由 lionbolt)` ≈ 264,555（disabled/空除外で多少減る）。±数%以内を期待。

### 3.3 `library_sources`（1 行）
```
id='lionbolt', label='LION BOLT 法律書カタログ', kind='commercial_catalog',
tier='subscription', cost='3278yen/month',
page_strategy='print_page',  -- toc は startHeadlinePage = 印刷ページ
needs_auth=true,
url_template='https://api.lionbolt.jp/v2/std/books/search/initial',
book_url_template='https://law-books.lionbolt.jp/books/{book_id}',
note='著作権法47-5。書誌+構造化目次のみ、本文不取得。取得2026-06-09/10。external_share=false'
```

---

## 4. 既存 10,326 行との dedup 方針（mint は HOLD）

lionbolt はほぼ全冊 ISBN-13 を持つ → **ISBN 完全一致**が最強の重複シグナル。

1. **ISBN 一致**: `lionbolt.isbn ∩ bib_records.isbn`（asai 5,397 / bencom 6 が isbn 保持）。一致は**版・実体が同一の強証拠**だが、**auto-merge しない**（本WO 方針: 衝突は review queue へ）。ローダは dedup レポート（一致 isbn 一覧）を出力するのみ。
2. **fingerprint 一致**: ISBN 無し同士は `title_norm|publisher_norm|page_count|pub_year` の full fingerprint v1（a2 と同一定義）で突合。
3. **投入の独立性**: lionbolt 行は `source='lionbolt'` として**独立に着地**する（既存行を一切 UPDATE しない）。重複の収斂（biblio_item mint / merge）は a1–a4 の triage に合流させ、**owner ratify 後**に別途実施。本投入では `minted_biblio_items=0`。
4. **再見積りの必要**: 投入後は bib_records が 33,170 行（10,326+22,844）になり、a1–a3 の identity 見積りは lionbolt を含めて再実行が必要（DD に明記）。

---

## 5. 冪等性・トランザクション・provenance

- **staging → upsert**: `catalog_dedup.jsonl` を一時 staging テーブルに `\copy` → `INSERT ... SELECT ... ON CONFLICT (bib_id) DO UPDATE`（source_hash 不変なら no-op）。再実行しても重複行を作らない。
- **load_run**: `bookdx.load_run` に lionbolt の run を 1 行記録（loader_version, source_hash=catalog_dedup.jsonl の sha256, source_files）。bencom と同じ provenance 様式。
- **source_hash**: bib_records.source_hash にレコード単位 sha256。差分再投入時に変化行だけ更新。
- **トランザクション**: 全 INSERT を 1 トランザクション（失敗時ロールバック）。bib_toc は bib_records 投入後（FK 順序）。

---

## 6. 実行ゲート（owner ratify 後の手順）

本DD時点では**未実行**。実行する場合のみ、以下を満たすこと:

1. owner が本DD（特に §2 投入先・§4 dedup 非merge・§3 マッピング）を ratify。
2. `READ_ONLY_STRICT` を解除（本投入は INSERT を伴う。WO-BIBREC の read-only gate とは別ジョブ）。
3. `tools/lionbolt_ingest/load_lionbolt.py --apply` を Mac（`~/alo-ai/work/lionbolt_dl/catalog_dedup.jsonl` がある環境）で実行、または Box から取得して実行。
4. `tools/lionbolt_ingest/migration_lionbolt.sql`（library_sources 行 + staging + idempotent upsert）を先に適用。
5. RLS: `biblio.library_sources` / `toc_nodes` は現状 RLS 無効（RLS_ADVISORY_20260618 参照）。投入と RLS 整備は別判断。

---

## 7. 成果物（この PR）

| パス | 内容 |
|---|---|
| `artifacts/lionbolt_ingest_20260622/DD_LIONBOLT_INGEST_v0.1.md` | 本DD |
| `tools/lionbolt_ingest/load_lionbolt.py` | ローダ（既定 dry-run。--apply は明示ガード） |
| `tools/lionbolt_ingest/migration_lionbolt.sql` | library_sources seed + staging + idempotent upsert（未適用） |
| `tools/lionbolt_ingest/README.md` | 実行手順・ゲート |
| `artifacts/lionbolt_ingest_20260622/LEGALLIB_HANDOFF_20260622.md` | legal-library（Mac ローカルのみ・Box未配置）の引き継ぎ |

**この PR の時点で**: DB mutation 0 / mint 0 / DDL 適用 0 / Box への lionbolt 投入 0。設計と道具のみ。
