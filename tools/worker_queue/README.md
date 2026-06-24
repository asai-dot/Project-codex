# alo-worker — Claude Code Worker Queue CLI

`docs/worker_queue/` の inbox / doing / done / blocked レーンを「**フォルダ位置 + RESULT
ラベル = 状態**」として強制する単一書き手 CLI。設計の双子は [`../gpt_audit`](../gpt_audit)
(GPT 目付け役レーン)。あちらは検査官の行き帰りを、こちらは作業者 (Claude Code) の
着手→完了/ブロックを機械化する。

巨大で曖昧なタスクを渡すと Claude Code は止まる。だから 5〜15 分単位の作業票に切り、
1 件ずつ claim → 実装 → complete/block する。止まっても損失は 1 タスク分、再開可能。

## インストール

```bash
cd tools/worker_queue
pip install -e .
```

`pip` を使わず単体実行も可能:

```bash
PYTHONPATH=src python -m alo_worker status --root /path/to/docs/worker_queue
```

## root の解決順

`--root` > 環境変数 `ALO_WORKER_QUEUE_ROOT` > `./docs/worker_queue`

```bash
export ALO_WORKER_QUEUE_ROOT="$PWD/docs/worker_queue"
```

## コマンド

| command | 役割 | 副作用 |
|---|---|---|
| `status [--json]` | レーン状態一覧 | 読み取りのみ |
| `next [--json] [--allow-wip]` | 次に着手すべき 1 件 (P0>P1>P2) | 読み取りのみ |
| `lint [--strict] [--all] [--json]` | task front-matter preflight | 読み取りのみ |
| `claim <id> [--dry-run]` | inbox → doing | ファイル移動 |
| `complete <id> [--dry-run] [--force]` | doing → done (`WORKER_PASS` 系必須) | 移動 + 台帳追記 |
| `block <id> [--dry-run] [--force]` | doing → blocked (`WORKER_BLOCKED/FAIL` 必須) | 移動 + 台帳追記 |
| `recover` | doing の中断 task を監査し畳み方を提示 | 読み取りのみ |
| `registry build` | `_registry.md` を jsonl から再生成 | md 書き出し |

## 不変条件 (CLI が弾くもの)

- **RESULT 不在で complete/block 不可** — `done|blocked/<id>_RESULT.md` が要る。
- **ラベルとレーンの不整合を弾く** — `done` には PASS 系、`blocked` には BLOCKED/FAIL のみ
  (`--force` で上書き可)。置き場所がラベルと食い違えば `terminal_bad_label` 事故として検出。
- **冪等** — 同じ遷移を二度流しても二重移動・二重台帳追記しない (`already` no-op)。
- **台帳だけ更新は不可能** — 追記は遷移成功時のみ。SoT はフォルダ位置。

## テスト

```bash
cd tools/worker_queue
PYTHONPATH=src python -m pytest -q
```

| test file | 内容 |
|---|---|
| `test_frontmatter.py` | スカラ / block list / nested map 耐性 / inline comment |
| `test_queue.py` | scan 分類・claim/complete/block・冪等・accident 検出・force |
| `test_lint.py` | 必須キー欠落 / priority 不正 / id-filename 不一致 |
| `test_registry.py` | append/load・md 決定性・後勝ち |
| `test_cli.py` | status/next/lint/claim/complete/recover/registry の exit code と出力 |
| `test_acceptance.py` | drain 一件ずつ / 中断→recover→畳む / 冪等リプレイ |
