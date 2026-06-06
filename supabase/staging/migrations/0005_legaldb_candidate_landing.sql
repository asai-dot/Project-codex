-- 0005_legaldb_candidate_landing.sql  (適用先: codex-staging)
-- legaldb v0.5（判例/法令/文献DB）の候補スキーマを landing(検疫/候補)ゾーンに起こす。
--
-- 出所 : STATIC_DB_INTEGRATION_PLAN v0.5（番頭/Mac CC 提案, ratify前 draft）
-- 監査 : from_gpt/20260606_legaldb_v0.5_DESIGN_RESULT.md = DESIGN_MODIFY_REQUIRED
-- 扱い : owner ratify・実装確定前のため、全行 candidate（quality_status 既定 unverified）。
--        prod へは昇格しない。landing→staging→prod の昇格は門番②で物理ブロックする
--        （0006 / docs/data-governance/legaldb-candidate-status.md 参照）。
--
-- GPT 指摘の構造的修正を反映:
--   F1 anchor lifecycle（不変 stable_anchor_id ⊥ 可変 human_locator、発番系譜）
--   F2 識別子責務分離（alo_work_uri / external 識別子 / expression / locator を別管理）
--   F3 offset は版固有 locator（text_version と複合、同一性に使わない）
--   F4 法令時間軸は DD-LAWTIME v0.2 依存で BLOCKED（版期間 ⊥ 効力期間、as_of unknown 可）
--   F5 article_work_id を一意キーにし DOI 等は identifier 側へ
--   F6 citation は二層 raw 保存＋状態機械（parse_status / treatment_status を別軸で）
--   F7 KG安全則（LLM出力は candidate のみ。本番昇格は別ゲート）

create schema if not exists legaldb;
comment on schema legaldb is
  'legaldb ドメインの型・統制語彙。zone(landing/staging/prod)とは別レイヤ。v0.5 candidate。';

-- ドメインの「処理状態」型。いずれも単一軸。codex.quality_status(成熟度)とは別軸として併存させる
-- （状態列は一軸に保つ原則: docs/data-governance/README.md）。
do $$
begin
  if not exists (select 1 from pg_type where typname='work_type' and typnamespace='legaldb'::regnamespace) then
    create type legaldb.work_type as enum ('case','law','article');
  end if;
  if not exists (select 1 from pg_type where typname='expression_kind' and typnamespace='legaldb'::regnamespace) then
    create type legaldb.expression_kind as enum ('original','anonymized','journal_published','temporal');
  end if;
  if not exists (select 1 from pg_type where typname='anchor_kind' and typnamespace='legaldb'::regnamespace) then
    create type legaldb.anchor_kind as enum ('case_paragraph','law_element','article_section');
  end if;
  if not exists (select 1 from pg_type where typname='parse_status' and typnamespace='legaldb'::regnamespace) then
    create type legaldb.parse_status as enum ('raw','parsed','resolved','reviewed','promoted');
  end if;
  if not exists (select 1 from pg_type where typname='treatment_status' and typnamespace='legaldb'::regnamespace) then
    create type legaldb.treatment_status as enum ('unclassified','candidate','reviewed');
  end if;
  if not exists (select 1 from pg_type where typname='treatment_kind' and typnamespace='legaldb'::regnamespace) then
    -- F6: 当面は粗い語彙に留める。正式な学説分類語彙は別DDで定義（over-reach 回避）。
    create type legaldb.treatment_kind as enum
      ('mentions','discusses','cites_as_authority','criticizes_candidate','distinguishes_candidate');
  end if;
end $$;

-------------------------------------------------------------------------------
-- Work / 識別子（F2: 責務分離）
-------------------------------------------------------------------------------
create table if not exists landing.legal_work (
  alo_work_uri  text,                 -- ALO 正準の Work URI（内部 PK の置換ではなく正準同一性）
  work_type     legaldb.work_type,
  title         text,
  jurisdiction  text default 'JP'
);
select codex.add_provenance('landing','legal_work');
alter table landing.legal_work add constraint legal_work_pkey primary key (id);
create index if not exists legal_work_uri_idx on landing.legal_work (alo_work_uri);

-- 外部識別子（ECLI/ELI/e-Gov/NII/DOI/NDL/CiNii/裁判所事件キー…）は work にぶら下げる。
-- 衝突テスト完了まで自然キーは candidate（is_candidate_key=true）。
create table if not exists landing.work_identifier (
  work_id          uuid,              -- soft ref → landing.legal_work.id
  scheme           text,
  value            text,
  is_candidate_key boolean default true
);
select codex.add_provenance('landing','work_identifier');
alter table landing.work_identifier add constraint work_identifier_pkey primary key (id);
create index if not exists work_identifier_work_idx on landing.work_identifier (work_id);
create index if not exists work_identifier_scheme_idx on landing.work_identifier (scheme, value);

-------------------------------------------------------------------------------
-- Expression / TextVersion（版・匿名/実名・各誌）
-------------------------------------------------------------------------------
create table if not exists landing.expression (
  work_id         uuid,
  expression_kind legaldb.expression_kind,
  label           text
);
select codex.add_provenance('landing','expression');
alter table landing.expression add constraint expression_pkey primary key (id);
create index if not exists expression_work_idx on landing.expression (work_id);

create table if not exists landing.text_version (
  expression_id uuid,
  version_label text,
  ocr_basis     text,
  retrieved_at  timestamptz
);
select codex.add_provenance('landing','text_version');
alter table landing.text_version add constraint text_version_pkey primary key (id);
create index if not exists text_version_expr_idx on landing.text_version (expression_id);

-------------------------------------------------------------------------------
-- Anchor（F1: 不変 stable_anchor_id = この行の id(opaque uuid)。human_locator は提示用で親FKにしない）
-------------------------------------------------------------------------------
create table if not exists landing.anchor (
  object_work_id       uuid,
  expression_id        uuid,
  anchor_kind          legaldb.anchor_kind,
  mint_basis           text,   -- 発番根拠。OCRテキストや可変 locator を hash seed にしない
  supersedes_anchor_id uuid,   -- 再mint/merge/split の系譜
  merge_split_status   text,
  human_locator        text    -- Num/段落番号/char offset ラベル等（可変・再計算可能）
);
select codex.add_provenance('landing','anchor');
alter table landing.anchor add constraint anchor_pkey primary key (id);
create index if not exists anchor_work_idx on landing.anchor (object_work_id);

-------------------------------------------------------------------------------
-- Stand-off 注釈（F3: offset は版固有 locator。text_version と必ず複合。同一性に使わない）
-------------------------------------------------------------------------------
create table if not exists landing.standoff_annotation (
  anchor_id            uuid,
  text_version_id      uuid,        -- offset と必ず複合
  offset_start         integer,
  offset_end           integer,
  role_code            text,        -- landing.role_vocabulary.code（統制語彙）
  alignment_confidence numeric      -- 匿名↔実名対応など低信頼は candidate に留める材料
);
select codex.add_provenance('landing','standoff_annotation');
alter table landing.standoff_annotation add constraint standoff_pkey primary key (id);
create index if not exists standoff_anchor_idx on landing.standoff_annotation (anchor_id);
create index if not exists standoff_tv_idx on landing.standoff_annotation (text_version_id);

-- 判例 role 統制語彙（主文/事実/争点/理由/結論/意見 …）。ALO が正式採番・版管理。
create table if not exists landing.role_vocabulary (
  code         text,
  label        text,
  vocab_version text
);
select codex.add_provenance('landing','role_vocabulary');
alter table landing.role_vocabulary add constraint role_vocab_pkey primary key (id);
create unique index if not exists role_vocab_code_idx on landing.role_vocabulary (code, vocab_version);

-------------------------------------------------------------------------------
-- §4 法令（F4: 時間軸は DD-LAWTIME v0.2 依存で BLOCKED。版期間 ⊥ 効力期間を分離）
-------------------------------------------------------------------------------
create table if not exists landing.law_element (
  law_work_id  uuid,
  element_path text,    -- 条/項/号 の人間 locator（可変）
  anchor_id    uuid     -- 不変 stable_anchor_id への参照
);
select codex.add_provenance('landing','law_element');
alter table landing.law_element add constraint law_element_pkey primary key (id);
create index if not exists law_element_work_idx on landing.law_element (law_work_id);

-- 版期間 = テキスト差分の抽出期間（効力ではない）。diff 計算結果は candidate。
create table if not exists landing.element_version_period (
  law_element_id uuid,
  version_label  text,
  period_start   date,
  period_end     date,
  computed_by    text default 'diff:unverified'
);
select codex.add_provenance('landing','element_version_period');
alter table landing.element_version_period add constraint element_version_period_pkey primary key (id);

-- 効力期間 = 施行日ベースの効力（版期間とは別軸）。as_of_date は欠損(unknown)可。
create table if not exists landing.legal_effective_period (
  law_element_id uuid,
  effective_from date,
  effective_to   date,
  as_of_date     date,    -- NOT NULL にしない（unknown 保持）
  basis          text
);
select codex.add_provenance('landing','legal_effective_period');
alter table landing.legal_effective_period add constraint legal_effective_period_pkey primary key (id);

-------------------------------------------------------------------------------
-- §5 文献（F5: article_work_id(=legal_work.id) が一意。DOI 等は work_identifier へ）
-------------------------------------------------------------------------------
create table if not exists landing.article_meta (
  work_id            uuid,   -- landing.legal_work(work_type=article).id
  journal_full_title text,
  journal_abbrev_title text, -- landing.journal_abbrev で統制
  issn_print         text,
  issn_electronic    text,
  volume             text,
  issue              text,
  year               integer,
  title              text,
  first_page         text,
  last_page          text
);
select codex.add_provenance('landing','article_meta');
alter table landing.article_meta add constraint article_meta_pkey primary key (id);
create index if not exists article_meta_work_idx on landing.article_meta (work_id);

create table if not exists landing.journal_abbrev (
  abbrev     text,    -- 『判タ』『判時』等
  full_title text
);
select codex.add_provenance('landing','journal_abbrev');
alter table landing.journal_abbrev add constraint journal_abbrev_pkey primary key (id);
create unique index if not exists journal_abbrev_idx on landing.journal_abbrev (abbrev);

-- 注: 二次資料の Restatement 4層(commentary_node/illustration/reporters_note/authority weighting)は
--     GPT が over-reach と指摘（日本の評釈/コンメンタール構造への固定は時期尚早）。v0.6 で別途定義する。

-------------------------------------------------------------------------------
-- §6 引用グラフ（F6: 二層 raw 保存＋状態機械。raw は常時保存、解析/解決/レビューは段階）
-------------------------------------------------------------------------------
create table if not exists landing.citation_edge (
  citing_work_id          uuid,                       -- 引用する側（二次:文献など）
  cited_authority_work_id uuid,                       -- 一次(判例/法令)。resolve 前は NULL 可
  raw_citation_text       text not null,              -- 常時保存（未解析でも残す）
  pin_cite                text,
  cited_journal_title     text,
  cited_volume            text,
  cited_issue             text,
  cited_first_page        text,
  cited_year              integer,
  structured_flag         boolean default false,
  parse_status            legaldb.parse_status default 'raw',
  treatment               legaldb.treatment_kind,     -- 粗い語彙(F6)
  treatment_status        legaldb.treatment_status default 'unclassified',
  alignment_confidence    numeric
);
select codex.add_provenance('landing','citation_edge');
alter table landing.citation_edge add constraint citation_edge_pkey primary key (id);
create index if not exists citation_citing_idx on landing.citation_edge (citing_work_id);
create index if not exists citation_cited_idx on landing.citation_edge (cited_authority_work_id);
