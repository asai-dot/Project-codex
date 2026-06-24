---
worker_task_id: W-20260623-002
status: queued
priority: P1
owner: claude-code-worker
created_at: 2026-06-23
repo: ALOBookDX
branch: main
goal: layout_hash の決定性を固定する回帰テストを追加する
mode: implementation
allowed_paths:
  - tests/xdoc/
  - docs/worker_queue/
forbidden_actions:
  - production_db_write
  - canonical_promotion
  - edit_accepted_dir
  - destructive_delete
  - external_api_bulk_call
  - schema_migration
test_command: pytest tests/xdoc/test_layout_hash.py -q
exit_criteria:
  - pytest tests/xdoc/test_layout_hash.py -q exits 0
  - 既存テストを壊していない
  - WORKER_RESULT is written
max_attempts: 2
result_expected_filename: W-20260623-002_RESULT.md
---

# Task
同一入力に対する layout_hash の決定性 (同入力→同ハッシュ、別入力→別ハッシュ) を固定する
回帰テストを追加する。

> 注: これは作業票フォーマットの **見本** です（対象 repo `ALOBookDX`）。

# Required Work
1. 既存 layout_hash の I/O 契約を確認する。
2. 決定性 / 衝突 / 順序非依存を検証する最小テストを追加する。
3. pytest を実行する。
4. 結果を RESULT に書く。

# Do Not
- 実装側 (src/) を変更するな。テスト追加のみ。
- fixture 以外の新規ファイルを作るな。
