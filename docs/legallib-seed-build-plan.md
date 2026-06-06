# legallib 詳細TOC 起点 RDB 構築プラン v0.2

> status: レビュー用ドラフト（DB未適用）。P0=DDL花岡レビュー後に適用。
> 正本(SoT)は Box の ALO 各レイヤ技術仕様書。本書はそれに準拠した **legallibシードの実装プラン**。
> 対象DB: Supabase `asai-dot's Project`（`nixfjmwxmgugiiuqfuym`、グリーンフィールド）
> スコープ: 書籍2,751冊（雑誌は次フェーズ＝巻号正規化未確定のため除外）

## v0.1→v0.2 変更（設計資料突合の反映）
- **C1（必須・反映済）**: 文献URI名前空間を `alo:work:` → **`alo:book:isbn:{isbn13}`**（全体§5／実BookDXデータ一致）。`toc_node_id = alo:book:isbn:{isbn}:toc:{NNN}`。
- **C3（命名）**: スキーマ `alo`(Canonical)/`alo_derived`(派生)。`alo.works ≡ 資料の alo_works` とマッピング固定。
- **C4（同一性）**: 資料どおり `work_identifiers`（レイヤ内・unique張らない）＋ `fingerprints`（横断・active unique で誤マージ0）の**両方**を持つ。`works.external_id` はD1-Law文献番号用に予約（legallibはNULL、legallib_book_idはidentifier/fingerprintへ）。
- **toc列追加**: 既存BookDX TOCに合わせ `toc_path_id`・`toc_status` を追加。
- **provenance方針**: 多源候補の書誌フィールド（title/publisher/publication_date）は `field_provenance`（legallib=priority 50→NDL/CiNiiが後で自動上書き）。単源自明のTOC構造は field_provenance に入れず `ingestion_run_id` のみ保持（lineage §3.4準拠）。
- **C2（要承認・未確定）**: 文献§1.1では Canonical=文献JSON文書、relational TOCはDerived。本プランは **`alo.toc_nodes` を Canonical relational projection** として新設する（RDB必須要件が根拠）。生JSONは `src_legallib_raw` に文献JSON Canonicalとして保全。**この1点だけ文献レイヤ仕様オーナー承認待ち**。

## 不変条件（手戻り防止）
1. 決定的URI＋NFCを初日から　2. Canonical/Derived物理分離　3. provenance/ingestion_run初回から
4. 同一性=surrogate＋fingerprints、突合=match_candidates、誤マージ0をゲート強制　5. 書誌は値を焼かず採用値をprovenanceで算出

## DDL（P0+P1）

```sql
-- ============ P0: 基盤 ============
CREATE SCHEMA IF NOT EXISTS alo;
CREATE SCHEMA IF NOT EXISTS alo_derived;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 決定的URI（dump/restore安全のためIMMUTABLE）
CREATE OR REPLACE FUNCTION alo.fn_book_uri(p_isbn text, p_legallib_id text)
RETURNS text LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE WHEN coalesce(p_isbn,'') <> '' THEN 'alo:book:isbn:'||p_isbn
              ELSE 'alo:book:legallib:'||p_legallib_id END
$$;

CREATE OR REPLACE FUNCTION alo.fn_toc_node_id(p_book_uri text, p_ordinal int)
RETURNS text LANGUAGE sql IMMUTABLE AS $$
  SELECT p_book_uri||':toc:'||lpad(p_ordinal::text, 3, '0')
$$;

CREATE OR REPLACE FUNCTION alo.fn_touch_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at := now(); RETURN NEW; END $$;

-- ============ P1: Canonicalシード ============

-- 生スナップショット（不変・冪等再生成の起点＝文献JSON Canonical保管庫）
CREATE TABLE alo.src_legallib_raw (
    legallib_book_id text PRIMARY KEY,
    raw_json    jsonb       NOT NULL,
    raw_sha256  text        NOT NULL,
    snapshot_id text        NOT NULL,
    fetched_at  timestamptz NOT NULL DEFAULT now()
);

-- 取込実行記録（lineage）
CREATE TABLE alo.ingestion_runs (
    run_id           text PRIMARY KEY,
    source_system    text NOT NULL DEFAULT 'legallib',
    source_snapshot  text NOT NULL,
    pipeline_script  text NOT NULL,
    pipeline_version text NOT NULL,
    run_mode  text NOT NULL DEFAULT 'full'
              CHECK (run_mode IN ('full','delta','reprocess')),
    started_at   timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    status text NOT NULL DEFAULT 'running'
           CHECK (status IN ('running','completed','failed','cancelled')),
    records_input integer, records_created integer, records_updated integer,
    records_unchanged integer, records_error integer,
    config_snapshot jsonb NOT NULL DEFAULT '{}'
);

-- 文献の同一性（Canonical・書誌はsource-thin）  ≡ 資料 alo_works
CREATE TABLE alo.works (
    work_id          bigserial PRIMARY KEY,
    canonical_uri    text UNIQUE NOT NULL,        -- alo:book:isbn:{isbn13} | alo:book:legallib:{id}
    work_type        text NOT NULL DEFAULT 'book'
                     CHECK (work_type IN ('book','serial','article')),
    title            text,
    title_norm       text,
    publisher        text,
    publication_date date,
    external_id      text,                        -- D1-Law文献番号用に予約（legallibはNULL）
    legallib_present boolean NOT NULL DEFAULT true,
    ingestion_run_id text NOT NULL REFERENCES alo.ingestion_runs(run_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT works_uri_nfc CHECK (canonical_uri IS NFC NORMALIZED)
);
CREATE TRIGGER trg_works_touch BEFORE UPDATE ON alo.works
    FOR EACH ROW EXECUTE FUNCTION alo.fn_touch_updated_at();

-- レイヤ内識別子（uniqueを張らない＝将来ISSN多重性を許容）
CREATE TABLE alo.work_identifiers (
    identifier_id bigserial PRIMARY KEY,
    work_id  bigint NOT NULL REFERENCES alo.works(work_id),
    id_type  text NOT NULL CHECK (id_type IN ('isbn','legallib_book_id','issn','ndl_bib_id','doi')),
    id_value text NOT NULL,
    ingestion_run_id text NOT NULL REFERENCES alo.ingestion_runs(run_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT wid_value_nfc CHECK (id_value IS NFC NORMALIZED),
    UNIQUE (work_id, id_type, id_value)
);

-- 横断的同一性解決（誤マージ0の砦）  ※ISSNには active unique を張らない（雑誌§6）
CREATE TABLE alo.fingerprints (
    fp_id        bigserial PRIMARY KEY,
    entity_type  text NOT NULL DEFAULT 'work' CHECK (entity_type IN ('work','case','statute','person')),
    entity_id    text NOT NULL,                  -- works.canonical_uri
    fp_type      text NOT NULL CHECK (fp_type IN ('isbn','legallib_book_id','issn','ndl_bib_id','doi')),
    fp_value     text NOT NULL,
    is_active    boolean NOT NULL DEFAULT true,
    source_system text NOT NULL DEFAULT 'legallib',
    ingestion_run_id text NOT NULL REFERENCES alo.ingestion_runs(run_id),
    created_at   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT fp_value_nfc CHECK (fp_value IS NFC NORMALIZED)
);
CREATE UNIQUE INDEX uq_fp_isbn_active     ON alo.fingerprints(fp_value)
    WHERE fp_type='isbn'             AND is_active;
CREATE UNIQUE INDEX uq_fp_legallib_active ON alo.fingerprints(fp_value)
    WHERE fp_type='legallib_book_id' AND is_active;
-- NOTE: issn には UNIQUE を張らない（1 ISSN = 複数work）

-- 詳細TOC（★起点・Canonical relational projection ※C2要承認）
CREATE TABLE alo.toc_nodes (
    toc_node_id        text PRIMARY KEY,          -- alo:book:isbn:{isbn}:toc:{NNN}
    work_id            bigint NOT NULL REFERENCES alo.works(work_id),
    parent_toc_node_id text REFERENCES alo.toc_nodes(toc_node_id),
    depth              int  NOT NULL,
    ordinal            int  NOT NULL CHECK (ordinal >= 1),
    label_raw          text NOT NULL,             -- legallib原文(NFC) ← {t}
    label_norm         text,                      -- 検索正規化(cheap)
    page_start         int,
    page_end           int,
    toc_path_id        text,                      -- 既存BookDX互換（安定パスキー）
    toc_status         text DEFAULT 'rich',       -- simple | rich
    toc_source         text NOT NULL DEFAULT 'legallib',
    node_kind          text,                      -- 当面NULL。P3でDerived分類(section/article/other)
    ingestion_run_id   text NOT NULL REFERENCES alo.ingestion_runs(run_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT toc_label_nfc CHECK (label_raw IS NFC NORMALIZED),
    CONSTRAINT toc_no_self_parent CHECK (parent_toc_node_id <> toc_node_id)
);
CREATE INDEX idx_toc_work   ON alo.toc_nodes(work_id, ordinal);
CREATE INDEX idx_toc_parent ON alo.toc_nodes(parent_toc_node_id);
CREATE INDEX idx_toc_norm_trgm ON alo.toc_nodes USING gin (label_norm gin_trgm_ops);

-- フィールドプロヴナンス（source-thinの実装・多源候補フィールドのみ）
CREATE TABLE alo.field_provenance (
    provenance_id bigserial PRIMARY KEY,
    entity_type text NOT NULL CHECK (entity_type IN ('work','person','case','term','edge')),
    entity_id   text NOT NULL,
    field_path  text NOT NULL,                    -- 'title','publisher','publication_date'
    source_system text NOT NULL,
    source_record_id text NOT NULL,
    source_snapshot  text NOT NULL,
    ingestion_run_id text NOT NULL REFERENCES alo.ingestion_runs(run_id),
    priority   int NOT NULL,                      -- 小さいほど優先（legallib=50）
    is_adopted boolean NOT NULL DEFAULT true,
    field_value_hash text,
    created_at timestamptz NOT NULL DEFAULT now(),
    superseded_at timestamptz
);
CREATE UNIQUE INDEX uq_fp2_one_adopted
    ON alo.field_provenance(entity_type, entity_id, field_path)
    WHERE is_adopted AND superseded_at IS NULL;
CREATE INDEX idx_fp2_lookup
    ON alo.field_provenance(entity_type, entity_id, field_path)
    WHERE superseded_at IS NULL;
```

## ゲートVIEW（全て 0件 が合格）

```sql
-- URI決定性
CREATE OR REPLACE VIEW alo.gate_book_uri_drift AS
WITH ids AS (
  SELECT w.work_id, w.canonical_uri,
    max(wi.id_value) FILTER (WHERE wi.id_type='isbn')             AS isbn,
    max(wi.id_value) FILTER (WHERE wi.id_type='legallib_book_id') AS llid
  FROM alo.works w LEFT JOIN alo.work_identifiers wi ON wi.work_id = w.work_id
  GROUP BY w.work_id, w.canonical_uri)
SELECT work_id, canonical_uri FROM ids
WHERE canonical_uri <> alo.fn_book_uri(coalesce(isbn,''), coalesce(llid,''));

-- TOC親の孤児
CREATE OR REPLACE VIEW alo.gate_toc_orphan_parent AS
SELECT t.toc_node_id FROM alo.toc_nodes t
WHERE t.parent_toc_node_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM alo.toc_nodes p WHERE p.toc_node_id = t.parent_toc_node_id);

-- TOC ordinal重複（同一work内）
CREATE OR REPLACE VIEW alo.gate_toc_ordinal_dup AS
SELECT work_id, ordinal, count(*) FROM alo.toc_nodes
GROUP BY work_id, ordinal HAVING count(*) > 1;

-- TOC深さ不整合（親深さ+1でない）
CREATE OR REPLACE VIEW alo.gate_toc_depth_inconsistent AS
SELECT c.toc_node_id FROM alo.toc_nodes c
JOIN alo.toc_nodes p ON p.toc_node_id = c.parent_toc_node_id
WHERE c.depth <> p.depth + 1;

-- ISBN active 衝突（物理unique済みだが監視）
CREATE OR REPLACE VIEW alo.gate_fp_isbn_collision AS
SELECT fp_value, count(*) FROM alo.fingerprints
WHERE fp_type='isbn' AND is_active GROUP BY fp_value HAVING count(*) > 1;

-- provenance 採用一意（物理unique済みだが監視）
CREATE OR REPLACE VIEW alo.gate_provenance_multi_adopted AS
SELECT entity_type, entity_id, field_path, count(*) FROM alo.field_provenance
WHERE is_adopted AND superseded_at IS NULL
GROUP BY entity_type, entity_id, field_path HAVING count(*) > 1;
```

## P1 ロード手順（冪等）
1. legallib生JSON → `src_legallib_raw`（snapshot_id固定、raw_sha256記録）／`ingestion_runs` 1行起票
2. 各bookから `works`（canonical_uri=`fn_book_uri`）＋`work_identifiers`(isbn, legallib_book_id)＋`fingerprints`(同)
3. 書誌3フィールドを `field_provenance`（source=legallib, priority=50）
4. legallib `{l,p,t,level}` → `toc_nodes`：`t→label_raw`, `level→depth`, ordinal=文書順(1始まり), parent=levelの入れ子から再構築, `toc_node_id=fn_toc_node_id`, page_start=pdf/print_page
5. **全ゲートVIEWが0件**を確認 → `ingestion_runs.status='completed'`、統計記録
6. 冪等性：同一snapshotで再実行して差分0

## 後続フェーズ（接続点のみ・本プラン外）
- **P2 突合**：resolver結果→`match_candidates`→verified採用→fingerprints/provenance（誤マージ0ゲート）
- **P3 Derived**(`alo_derived`)：著者分解→persons、TOC種別→node_kind
- **P4 語彙**：TOC見出し・巻末索引→term候補(scheme_only)、term_dict staging接続
- **P5 リンク**：`edges` 表（条文/判例エッジは抽出器完成後、llm_inferred DB禁止）

## 要承認・要決定
- **C2（本質）**：toc_nodes を Canonical relational projection とする件 → 文献レイヤ仕様オーナー承認
- スキーマ名 `alo` で確定可否（BookDX命名衝突回避）
- page_start の pdf_page / print_page 優先順
- legallib JSON 実フィールド名最終確認（parent再構築ロジック確定）
