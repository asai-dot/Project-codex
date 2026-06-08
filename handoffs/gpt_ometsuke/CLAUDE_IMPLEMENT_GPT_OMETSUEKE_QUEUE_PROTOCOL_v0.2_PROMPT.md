# Claude 投げ込み用 短縮指示 — GPT_OMETSUEKE_QUEUE_PROTOCOL v0.2

GPT 側で `GPT_OMETSUEKE_QUEUE_PROTOCOL_v0.2.md` を試作した。
この内容を、現在の `handoffs/gpt_ometsuke/` 運用に実装してほしい。
目的は、GPT 監査の品質向上ではなく、**監査キューの状態管理を安定化すること**。
特に次の 5 点を必ず実装すること。

1. `QUEUE_INDEX.md` を作成し、未監査・未消費・未反映・浅井判断待ちを分離して見えるようにする。
2. `QUEUE_EVENTS.jsonl` を append-only で作成し、REQUEST 作成・RESULT 返却・Claude 消費・closed 等のイベントを残す。
3. `CONSUMED.md` を導入し、GPT RESULT を Claude が読んだだけでなく、採用・不採用・反映内容まで記録する。
4. `closed` の定義を厳格化し、RESULT があるだけでは closed にしない。
5. 浅井さんから「監査溜まってない？」「未済ない？」と聞かれたら、件数分類で状態報告する。

## 実装メモ（このリポジトリでの所在）

- 仕様: `handoffs/gpt_ometsuke/PROTOCOL.md`
- 実装: `tools/gpt_audit/queue.py`（`build` / `report` / `check` / `append`）
- **先に Box `handoffs/gpt_ometsuke/` を必ず確認すること**（look-before-build）。既に v0.3 レーン
  （`_AUDIT_LEDGER.jsonl` / `_ACTION_QUEUE.md` / `alo-gpt-audit`）が存在し、v0.2 はその同一概念。
  並行する 3 つ目のシステムを作らない。対応表は `PROTOCOL.md` §9。

## v0.3 送り（今回入れない）

常時監視 daemon / GPT 自動送信 / Box 自動 move・delete / Web UI / DB 化 / 自動通知。
v0.2 の目的は手前にある: 状態定義の固定 / 完了定義の固定 / Claude・GPT・浅井さんの責務分界の固定。
