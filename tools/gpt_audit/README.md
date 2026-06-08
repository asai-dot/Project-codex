# tools/gpt_audit — GPT お目付け役 監査キュー v0.2 実装

`handoffs/gpt_ometsuke/` の状態管理を回す依存ゼロの Python CLI。
仕様は [`../../handoffs/gpt_ometsuke/PROTOCOL.md`](../../handoffs/gpt_ometsuke/PROTOCOL.md)。

| ファイル | 役割 |
|---|---|
| `queue.py` | CLI 本体（`build` / `report` / `check` / `append`）＋状態畳み込み・分類ロジック |
| `seed_20260608.py` | `QUEUE_EVENTS.jsonl` を 2026-06-08 の実 25 件で初期化（一回限り） |
| `test_queue.py` | `classify()` / closed 厳格化 / シード件数の単体テスト |

```bash
python3 tools/gpt_audit/queue.py report   # 件数分類（状態報告）
python3 tools/gpt_audit/queue.py build    # EVENTS → QUEUE_INDEX.md / CONSUMED.md 再生成
python3 tools/gpt_audit/queue.py check    # 生成物と EVENTS の不一致検出（CI 向け）
python3 tools/gpt_audit/test_queue.py     # テスト
```

Box v0.3 レーンの `alo-gpt-audit` と同一概念（対応表は PROTOCOL.md §9）。
`queue.py append` で EVENTS に 1 行足し、`build` で派生を再生成する運用。EVENTS の行は書き換えない。
