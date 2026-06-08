# handoffs/gpt_ometsuke — GPT お目付け役 監査キュー（v0.2）

GPT Pro お目付け役 ⇄ Claude（番頭）の非同期監査キュー。**状態管理**を安定化するための最小実装。

仕様の正典は [`PROTOCOL.md`](./PROTOCOL.md)（GPT_OMETSUEKE_QUEUE_PROTOCOL v0.2）。

## ファイル

| パス | 役割 | 編集 |
|---|---|---|
| `QUEUE_EVENTS.jsonl` | append-only 状態変更ログ。**真実** | 追記のみ（`queue.py append`） |
| `QUEUE_INDEX.md` | 現在状態の台帳（未済 4 分類 + closed） | 自動生成（手で書かない） |
| `CONSUMED.md` | GPT RESULT への Claude 採用判断記録 | 自動生成 |
| `PROTOCOL.md` | v0.2 仕様 + Box v0.3 レーンとの crosswalk | 仕様変更時のみ |
| `to_gpt/` `to_gpt/processed/` `from_gpt/` | REQUEST / 退避 / RESULT | 運用 |

実装 CLI: [`../../tools/gpt_audit/queue.py`](../../tools/gpt_audit/queue.py)（依存ゼロ Python 3）。

## よく使うコマンド

```bash
# 「監査溜まってない？」への状態報告（件数分類）
python3 tools/gpt_audit/queue.py report

# イベント追記後に台帳を再生成
python3 tools/gpt_audit/queue.py build

# 生成物が EVENTS と一致するか検証（再生成忘れ・手編集を検出）
python3 tools/gpt_audit/queue.py check

# テスト
python3 tools/gpt_audit/test_queue.py
```

## 状態モデル（要約）

```text
REQUEST_CREATED → 未監査
   └ RESULT_RETURNED → 未消費
        └ CONSUMED → 未反映  (要反映なら REFLECTED まで残る)
             └ REFLECTED → 浅井判断待ち  (要ratifyなら RATIFIED まで残る)
                  └ RATIFIED → closed
不採用(reject, ratify不要) / REQUEUED(後続置換) / CLOSED(事務的) も closed。
```

**RESULT が返っただけでは closed にしない。** これが v0.2 の核（`PROTOCOL.md` §4）。

## Box v0.3 レーンとの関係

これは Box `handoffs/gpt_ometsuke/` の既存 v0.3 レーン（`_AUDIT_LEDGER.jsonl` / `_ACTION_QUEUE.md` /
`alo-gpt-audit`）と**同一概念の git 実装**であり、別物の並行システムではない。対応表は `PROTOCOL.md` §9。
どちらを正本とするかは浅井さんの保留事項。

## シード

`QUEUE_EVENTS.jsonl` は Box `_ACTION_QUEUE.md`（2026-06-08）の実 25 件で初期化済み。
再シードは `python3 tools/gpt_audit/seed_20260608.py`（EVENTS を上書き）。
