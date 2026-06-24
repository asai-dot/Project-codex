-- DD-FORMOBJ-002 v0.2 知識層スキーマ（静的DB / 書式オブジェクト＝独立first-class）
-- filled_instance(案件層)は本スキーマに置かない＝物理分離(別DB/案件ストア)。owner ratify(2026-06-16)済。
-- 多くのゲートを DB CHECK で defense-in-depth 化。cross-table系(forum_required/private_defect)は app validator(validate_form_object.py)。
create schema if not exists formobj;
comment on schema formobj is 'DD-FORMOBJ-002 v0.2 知識層。書式オブジェクト(独立first-class)。filled_instance(案件層)はここに置かない=物理分離。';

create table if not exists formobj.form_object (
  form_uid text primary key,
  identity_status text not null default 'provisional'
    check (identity_status in ('provisional','candidate','resolved','split_required','deprecated_alias')),
  recorded_act text,
  legal_function text,
  document_role text,
  practice_domain text,
  party_posture text,
  forum text,                              -- nullable: 私契約は null 可
  temporal_applicability text,
  temporal_floor_year int,
  canonical_text_synthesized boolean not null default false,
  created_at timestamptz not null default now(),
  constraint form_uid_opaque check (form_uid ~ '^alo:form:'),     -- G_FORM_ID_OPAQUE
  constraint form_uid_no_isbn check (form_uid !~ '[0-9]{13}')     -- ISBN焼込み禁止
);

create table if not exists formobj.form_variant (
  variant_id text primary key,
  form_uid text not null references formobj.form_object(form_uid) on delete cascade,
  variant text not null,
  variant_split_reason text not null       -- G_VARIANT_SPLIT_REASON_PRESENT
    check (variant_split_reason in ('legal_function_shift','party_posture_shift','forum_shift','regulatory_context_shift','risk_allocation_shift')),
  note text
);

create table if not exists formobj.form_witness (
  witness_id text primary key,
  form_uid text not null references formobj.form_object(form_uid) on delete cascade,
  source_type text not null
    check (source_type in ('biblio_item','web','court','registry','internal_generated','uploaded_sample','statute')),
  source_uri text,
  source_identifier text,
  edition_or_version text,
  edition_year int,
  toc_node text,
  section_path text,
  page_span text,
  pdf_page_span text,
  page_offset int,
  content_hash text,
  extraction_method text,
  extracted_at timestamptz,
  extractor_version text,
  source_confidence numeric,
  provenance_family text,
  verified_status text not null
    check (verified_status in ('edition_verified','toc_only','toc_only_coarse','statute_citation','EDITION_MISMATCH_FLAGGED','pending')),
  adopted boolean not null default false,
  counts_as_independent boolean not null default false,
  constraint witness_mismatch_not_adopted check (not (verified_status='EDITION_MISMATCH_FLAGGED' and adopted))  -- G_WITNESS_EDITION_VERIFIED
);

create table if not exists formobj.requisite (
  requisite_id bigint generated always as identity primary key,
  form_uid text not null references formobj.form_object(form_uid) on delete cascade,
  term text not null,
  label_ja text,
  requisite_class text not null
    check (requisite_class in ('statute_required','regulation_or_rule_required','forum_required','validity_required','enforceability_required','advisable','optional_design')),
  defect_kind text
    check (defect_kind in ('invalidity','rejection_by_forum','registration_defect','evidentiary_weakness','risk_warning')),
  grounded_in_law text,
  grounded_in_forum_rule text,
  grounded_in_source_type text,            -- advisable/optional の出所種別
  source_basis text,
  confidence numeric,
  favors_role text,
  note text,
  constraint mandatory_grounded check (    -- G_MANDATORY_GROUNDED
    requisite_class not in ('statute_required','regulation_or_rule_required','forum_required','validity_required','enforceability_required')
    or grounded_in_law is not null or grounded_in_forum_rule is not null),
  constraint advisory_source_typed check ( -- G_ADVISORY_SOURCE_TYPED
    requisite_class not in ('advisable','optional_design') or grounded_in_source_type is not null),
  constraint defect_severity_monotonic check ( -- G_NO_OPTIONAL_DESIGN_AS_INVALIDITY / G_DEFECT_SEVERITY_MONOTONIC
    requisite_class not in ('advisable','optional_design')
    or defect_kind is null or defect_kind in ('risk_warning','evidentiary_weakness'))
);

create table if not exists formobj.form_edge (
  edge_id bigint generated always as identity primary key,
  form_uid text not null references formobj.form_object(form_uid) on delete cascade,
  edge_type text not null
    check (edge_type in ('witnessed_in','serves','submitted_under','required_items_grounded_in','advised_by','typed_by','cites','effect_from','records_act','documents_transaction','memorializes_agreement','notifies','authorizes','certifies')),
  target_object text,                      -- law | case | literature | periodical | vocabulary | procedure
  target_ref text,
  provenance_family text,
  confidence numeric,
  verified_status text
);

create index if not exists ix_formobj_variant_form on formobj.form_variant(form_uid);
create index if not exists ix_formobj_witness_form on formobj.form_witness(form_uid);
create index if not exists ix_formobj_requisite_form on formobj.requisite(form_uid);
create index if not exists ix_formobj_edge_form on formobj.form_edge(form_uid);
