---
worker_task_id: W-20260624-170
status: queued
priority: P0
owner: external_se
created_at: 2026-06-24
request: docs/workflow_model/REQUEST_v0.2.md
poc: cross-cutting (security)
goal: Supabase "asai-dot's Project"(nixfjmwxmgugiiuqfuym) の dynamic スキーマ全テーブルで RLS が無効=anonキーで依頼者秘匿通信を含む全行が読取/改変可能。RLS有効化＋適切なポリシー設計を行い、秘匿特権データを保護する。
mode: security_hardening
requires_systems:
  - Supabase (production DB write — 要 external SE / owner 承認)
depends_on:
  - W-20260624-110
allowed_paths:
  - docs/workflow_model/v0.2/
allowed_actions:
  - external_se_apply (NOT a claude-worker task)
  - document remediation plan
forbidden_actions:
  - claude_worker_auto_apply   # production_db_write は worker 禁止。SEのみ。
  - enable_rls_without_policy  # ポリシー無しのRLS有効化は全アクセス遮断=稼働破壊
exit_criteria:
  - dynamic 全BASE TABLE で RLS 有効
  - service_role / 想定ロール向けの read/write ポリシーが定義され、ETL・参照が壊れないことを検証
  - anon ロールからの読取/改変が遮断されることを検証
  - 適用前後のアクセス検証ログを残す
max_attempts: 1
result_expected_filename: W-20260624-170_RESULT.md
---

# Task — Supabase dynamic スキーマ RLS ハードニング（セキュリティ P0）

## 背景（W-110 実査の付随発見）
Supabase 自動 advisor が **critical** を報告：
`dynamic` スキーマの **14 BASE TABLE 全てで Row Level Security (RLS) が無効**。
Supabase の anon / authenticated ロール（クライアントライブラリが使う公開鍵）で
**全行が読取・改変可能**。対象に `dynamic.comms`（`confidentiality_level='client_confidential'`
の依頼者通信 343 件）を含み、法律事務所の**秘匿特権データが露出**している。

対象テーブル: parties, cases, comms, documents, comm_party_links, comm_document_links,
chatwork_room_case_map, unconfirmed_links, pipeline_runs, llm_disclosure_log,
comm_versions, id_migration_map, etl_watermarks, etl_dead_letter

## なぜ Claude worker が自動適用しないか
- production DB への書込（DDL/ALTER）は worker の forbidden_actions。
- **ポリシー無しで RLS を有効化すると全アクセスが即遮断**され、稼働中の ETL／参照が壊れる。
  → 有効化とポリシー定義は不可分。external SE / owner の設計・承認・検証が必須。

## 推奨手順（external SE 向け）
1. 現行アクセス経路の棚卸し（どのロール／鍵が読み書きしているか：ETL書き手、参照アプリ等）。
2. service_role 等の正規ロールに必要十分な read/write ポリシーを定義。
3. 各テーブルで `ALTER TABLE dynamic.<t> ENABLE ROW LEVEL SECURITY;`。
4. anon/authenticated からの読取・改変が遮断されることを検証。ETL・参照が壊れないことを回帰確認。
5. 秘匿区分（confidentiality_level / access_class）に応じた行レベル制御の要否を owner 裁定。

## 参考 remediation SQL（そのまま適用しない＝ポリシー先行）
```
ALTER TABLE dynamic.parties ENABLE ROW LEVEL SECURITY;
ALTER TABLE dynamic.cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE dynamic.comms ENABLE ROW LEVEL SECURITY;
ALTER TABLE dynamic.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE dynamic.comm_party_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE dynamic.comm_document_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE dynamic.chatwork_room_case_map ENABLE ROW LEVEL SECURITY;
ALTER TABLE dynamic.unconfirmed_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE dynamic.pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE dynamic.llm_disclosure_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE dynamic.comm_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE dynamic.id_migration_map ENABLE ROW LEVEL SECURITY;
ALTER TABLE dynamic.etl_watermarks ENABLE ROW LEVEL SECURITY;
ALTER TABLE dynamic.etl_dead_letter ENABLE ROW LEVEL SECURITY;
```
doc: https://supabase.com/docs/guides/database/postgres/row-level-security
