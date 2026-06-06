# legallib/弁コム 書籍データ RDB 構築プラン v0.3

> status: レビュー用ドラフト（DB未適用）。P0=DDL花岡レビュー後に適用。
> 正本(SoT)は Box の ALO 各レイヤ技術仕様書。本書はそれに準拠した **書籍データの実装プラン**。
> 対象DB: Supabase `asai-dot's Project`（`nixfjmwxmgugiiuqfuym`、グリーンフィールド）
> 初回ロード: legallib 書籍2,751冊（弁コムは同一形状で後続。雑誌は巻号正規化未確定のため次フェーズ）

## データ・トポロジ（v0.3 の核）

**メダリオン構成（単一DB・3層）。「由来別に持ってマスターを組む」を物理分割せずスキーマ分割で実現。**

```
bronze（由来別・生・不変）   ← 由来DB＝スキーマ。新ソースは足すだけ
  src_legallib : raw_books / raw_toc
  src_bencom   : raw_books / raw_toc
  src_bookdx / src_ndl / src_d1law / src_cinii …（将来）
        │  ISBNで突合（match_candidates）して「薄く重ねて1work」
        ▼
silver（マスター・正本・1実体）   ← マスター
  alo : works / toc_nodes / work_identifiers / fingerprints
        field_provenance / match_candidates / ingestion_runs
        ▼
gold（派生・配信）
  alo_derived : persons / node_kind / chunks / embeddings
  serving     : v_book_export ほか（由来に依らず同一形状で出力）
```

- **由来別bronze**：弁コム/legallibの生をそれぞれ `src_<source>` に不変保全。source単位で再取得・再構築が完結。
- **単一silverマスター**：両ソースをISBNで突合し**1 work**へoverlay。どのフィールドがどの由来かは `field_provenance`。誤マージ0は fingerprints の active unique で**同一DB内だから物理強制**できる。
- **物理別DB＋参照は不採用**：Postgresは跨DB外部キー不可、跨DB uniqueも不可（＝突合の砦が崩れる）。スキーマ分割で同等の分離を得つつ整合性を守る。

## v0.2→v0.3 変更
- **トポロジ確定**：bronzeを由来別スキーマ化（`src_legallib`/`src_bencom`、将来 `src_bookdx` 等）。`alo.src_legallib_raw`（v0.2）を廃し `src_legallib.raw_books`/`raw_toc` へ。
- **ネイティブID**：`legallib_book_id` と `bencom_book_id` を別 fingerprint（各 active unique）。**ISBNは源横断のマージキー**。
- **TOC源優先（新規）**：1 work のTOCは1源を正本化。既定 legallib＞弁コム（粒度優先・configurable）。負けた源の生はbronze保全、`works.canonical_toc_source` で記録、切替可能。ゲートで「1 workのtoc_nodesは単一source」を強制。
- **export口**：`alo.v_book_export` を予約（由来不問で同一形状出力＝「本が売れた時」対応）。

## v0.1→v0.2（既出・維持）
- C1: 文献URI `alo:book:isbn:{isbn13}`、`toc_node_id=alo:book:isbn:{isbn}:toc:{NNN}`。
- C3: `alo`/`alo_derived` スキーマ。C4: work_identifiers＋fingerprints両立。toc_path_id/toc_status追加。
- provenance: 書誌3項目のみ field_provenance（source別priority）、TOC構造は ingestion_run_id のみ。
- **C2（要承認）**: `alo.toc_nodes` を Canonical relational projection とする（文献§1.1の3層からの拡張）。生は bronze に文献JSON Canonicalとして保全。文献レイヤ仕様オーナー承認待ち。

## DDL（P0+P1）

```sql
-- ===== P0: 基盤 =====
CREATE SCHEMA IF NOT EXISTS alo;          -- silver(マスター)
CREATE SCHEMA IF NOT EXISTS alo_derived;  -- gold(派生)
CREATE SCHEMA IF NOT EXISTS src_legallib; -- bronze(由来別)
CREATE SCHEMA IF NOT EXISTS src_bencom;   -- bronze(由来別)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE OR REPLACE FUNCTION alo.fn_book_uri(p_isbn text, p_src text, p_src_id text)
RETURNS text LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE WHEN coalesce(p_isbn,'') <> '' THEN 'alo:book:isbn:'||p_isbn
              ELSE 'alo:book:'||p_src||':'||p_src_id END   -- ISBN無し本は由来採番
$$;
CREATE OR REPLACE FUNCTION alo.fn_toc_node_id(p_book_uri text, p_ordinal int)
RETURNS text LANGUAGE sql IMMUTABLE AS $$
  SELECT p_book_uri||':toc:'||lpad(p_ordinal::text,3,'0') $$;
CREATE OR REPLACE FUNCTION alo.fn_touch_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at:=now(); RETURN NEW; END $$;

-- ===== bronze: 由来別・生・不変（各source同一形状）=====
CREATE TABLE src_legallib.raw_books (
    book_id text PRIMARY KEY, isbn text,
    raw_json jsonb NOT NULL, raw_sha256 text NOT NULL,
    snapshot_id text NOT NULL, fetched_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE src_bencom.raw_books (LIKE src_legallib.raw_books INCLUDING ALL);
-- raw_toc も同様に各srcへ（生TOCを保全。再導出の起点）

-- ===== silver: マスター =====
CREATE TABLE alo.ingestion_runs (
    run_id text PRIMARY KEY, source_system text NOT NULL, source_snapshot text NOT NULL,
    pipeline_script text NOT NULL, pipeline_version text NOT NULL,
    run_mode text NOT NULL DEFAULT 'full' CHECK (run_mode IN ('full','delta','reprocess')),
    started_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz,
    status text NOT NULL DEFAULT 'running' CHECK (status IN ('running','completed','failed','cancelled')),
    records_input int, records_created int, records_updated int, records_unchanged int, records_error int,
    config_snapshot jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE alo.works (
    work_id bigserial PRIMARY KEY,
    canonical_uri text UNIQUE NOT NULL,            -- alo:book:isbn:{isbn13} | alo:book:{src}:{id}
    work_type text NOT NULL DEFAULT 'book' CHECK (work_type IN ('book','serial','article')),
    title text, title_norm text, publisher text, publication_date date,
    external_id text,                              -- D1-Law文献番号用に予約
    canonical_toc_source text,                     -- TOC正本の由来（legallib/bencom…）
    ingestion_run_id text NOT NULL REFERENCES alo.ingestion_runs(run_id),
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT works_uri_nfc CHECK (canonical_uri IS NFC NORMALIZED)
);
CREATE TRIGGER trg_works_touch BEFORE UPDATE ON alo.works
    FOR EACH ROW EXECUTE FUNCTION alo.fn_touch_updated_at();

CREATE TABLE alo.work_identifiers (
    identifier_id bigserial PRIMARY KEY,
    work_id bigint NOT NULL REFERENCES alo.works(work_id),
    id_type text NOT NULL CHECK (id_type IN
        ('isbn','legallib_book_id','bencom_book_id','issn','ndl_bib_id','doi')),
    id_value text NOT NULL,
    ingestion_run_id text NOT NULL REFERENCES alo.ingestion_runs(run_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT wid_value_nfc CHECK (id_value IS NFC NORMALIZED),
    UNIQUE (work_id, id_type, id_value)            -- レイヤ内はuniqueを“広く”張らない
);

CREATE TABLE alo.fingerprints (
    fp_id bigserial PRIMARY KEY,
    entity_type text NOT NULL DEFAULT 'work' CHECK (entity_type IN ('work','case','statute','person')),
    entity_id text NOT NULL,
    fp_type text NOT NULL CHECK (fp_type IN
        ('isbn','legallib_book_id','bencom_book_id','issn','ndl_bib_id','doi')),
    fp_value text NOT NULL, is_active boolean NOT NULL DEFAULT true,
    source_system text NOT NULL,
    ingestion_run_id text NOT NULL REFERENCES alo.ingestion_runs(run_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT fp_value_nfc CHECK (fp_value IS NFC NORMALIZED)
);
CREATE UNIQUE INDEX uq_fp_isbn_active     ON alo.fingerprints(fp_value) WHERE fp_type='isbn'            AND is_active;
CREATE UNIQUE INDEX uq_fp_legallib_active ON alo.fingerprints(fp_value) WHERE fp_type='legallib_book_id' AND is_active;
CREATE UNIQUE INDEX uq_fp_bencom_active   ON alo.fingerprints(fp_value) WHERE fp_type='bencom_book_id'   AND is_active;
-- NOTE: issn には UNIQUE を張らない（1 ISSN = 複数work, 雑誌§6）

CREATE TABLE alo.toc_nodes (                        -- ★C2要承認: Canonical relational projection
    toc_node_id text PRIMARY KEY,                  -- alo:book:isbn:{isbn}:toc:{NNN}
    work_id bigint NOT NULL REFERENCES alo.works(work_id),
    parent_toc_node_id text REFERENCES alo.toc_nodes(toc_node_id),
    depth int NOT NULL, ordinal int NOT NULL CHECK (ordinal >= 1),
    label_raw text NOT NULL, label_norm text,
    page_start int, page_end int,
    toc_path_id text, toc_status text DEFAULT 'rich',
    toc_source text NOT NULL,                       -- legallib | bencom …（1 work内は単一）
    node_kind text,                                 -- 当面NULL。P3でDerived分類
    ingestion_run_id text NOT NULL REFERENCES alo.ingestion_runs(run_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT toc_label_nfc CHECK (label_raw IS NFC NORMALIZED),
    CONSTRAINT toc_no_self_parent CHECK (parent_toc_node_id <> toc_node_id)
);
CREATE INDEX idx_toc_work ON alo.toc_nodes(work_id, ordinal);
CREATE INDEX idx_toc_parent ON alo.toc_nodes(parent_toc_node_id);
CREATE INDEX idx_toc_norm_trgm ON alo.toc_nodes USING gin (label_norm gin_trgm_ops);

CREATE TABLE alo.field_provenance (
    provenance_id bigserial PRIMARY KEY,
    entity_type text NOT NULL CHECK (entity_type IN ('work','person','case','term','edge')),
    entity_id text NOT NULL, field_path text NOT NULL,
    source_system text NOT NULL, source_record_id text NOT NULL, source_snapshot text NOT NULL,
    ingestion_run_id text NOT NULL REFERENCES alo.ingestion_runs(run_id),
    priority int NOT NULL, is_adopted boolean NOT NULL DEFAULT true,
    field_value_hash text, created_at timestamptz NOT NULL DEFAULT now(), superseded_at timestamptz
);
CREATE UNIQUE INDEX uq_fp2_one_adopted ON alo.field_provenance(entity_type, entity_id, field_path)
    WHERE is_adopted AND superseded_at IS NULL;

-- ===== gold: export口（予約・由来不問で同一形状）=====
CREATE OR REPLACE VIEW alo.v_book_export AS
SELECT w.canonical_uri, w.work_type, w.title, w.publisher, w.publication_date,
       w.canonical_toc_source,
       (SELECT id_value FROM alo.work_identifiers wi
         WHERE wi.work_id=w.work_id AND wi.id_type='isbn' LIMIT 1) AS isbn
FROM alo.works w;
```

## ゲートVIEW（全0件で合格）
- `gate_book_uri_drift`（URI決定性）
- `gate_toc_orphan_parent` / `gate_toc_ordinal_dup` / `gate_toc_depth_inconsistent`
- `gate_toc_mixed_source`（1 workのtoc_nodesが複数sourceに割れていない＝TOC源優先の単一性）
- `gate_fp_isbn_collision` / `gate_provenance_multi_adopted`
- 冪等：同一snapshot再実行で差分0

```sql
CREATE OR REPLACE VIEW alo.gate_toc_mixed_source AS
SELECT work_id, count(DISTINCT toc_source) AS src_count
FROM alo.toc_nodes GROUP BY work_id HAVING count(DISTINCT toc_source) > 1;
```

## P1 ロード手順（冪等・legallib先行）
1. legallib生JSON → `src_legallib.raw_books`（+raw_toc）、`ingestion_runs` 起票
2. `works`（canonical_uri=`fn_book_uri`）＋`work_identifiers`(isbn, legallib_book_id)＋`fingerprints`(同)
3. 書誌3項目を `field_provenance`（source=legallib, priority=50）
4. `{l,p,t,level}` → `toc_nodes`（parent再構築, toc_source='legallib'）、`works.canonical_toc_source='legallib'`
5. 全ゲート0件 → `ingestion_runs.status='completed'`
6. **弁コムは同手順を `src_bencom` で繰り返す**：ISBN一致は既存workにoverlay（fingerprint=bencom_book_id追加、書誌はprovenance競合解決、TOCは源優先で判定）。ISBN新規はwork新設。

## 後続（接続点のみ）
P2 突合（match_candidates・誤マージ0）／P3 Derived（persons・node_kind）／P4 語彙（TOC見出し・巻末索引→term候補, term_dict接続）／P5 リンク（edges, llm_inferred禁止）。

## 要承認・要決定
- **C2（本質）**：toc_nodes を Canonical relational projection とする → 文献レイヤ仕様オーナー承認
- TOC源優先の既定（legallib＞弁コム）で良いか
- スキーマ命名（`alo`/`alo_derived`/`src_*`）確定
- page_start の pdf_page/print_page 優先
- legallib・弁コム 生JSONの実フィールド名（parent再構築の確定）
