# Claude Code Worker Queue

Claude Code ワーカーに **巨大で曖昧なタスク** を渡すと、コンテキスト肥大・計算資源制限・
安全停止・完了条件不明・書込失敗のどれかで止まる。だから「考えろ」ではなく **作業票
(worker task)** を食わせる。1 タスク = 1 目的 / 1 許可範囲 / 1 禁止リスト / 1 テスト /
1 RESULT、出口は **done / blocked の二択**。止まっても被害は 1 タスク分で、再開可能。

状態の SoT は **フォルダ位置 + RESULT ラベル**。遷移は `tools/worker_queue` の
`alo-worker` CLI が機械化し、`_registry.jsonl` に派生台帳を残す。運用規約は
[`_worker_protocol.md`](_worker_protocol.md)、RESULT 形式は
[`_result_template.md`](_result_template.md)。

```
inbox/    queued な作業票 (W-*.md)
doing/    着手中 1 件 (中断はここに残る = 復旧対象)
done/     完了 task + WORKER_PASS 系 RESULT
blocked/  WORKER_BLOCKED / WORKER_FAIL で畳んだ task + RESULT
```

## 使い方

```bash
export ALO_WORKER_QUEUE_ROOT="$PWD/docs/worker_queue"
# CLI は tools/worker_queue/ (pip install -e . か PYTHONPATH=src python -m alo_worker)

alo-worker status                    # レーンと残件
alo-worker next                      # 次の 1 件 (P0>P1>P2)
alo-worker lint                      # inbox task の front-matter preflight
alo-worker claim    W-20260623-001   # inbox -> doing
alo-worker complete W-20260623-001   # doing -> done  (WORKER_PASS 系 RESULT 必須)
alo-worker block    W-20260623-001   # doing -> blocked (WORKER_BLOCKED/FAIL RESULT 必須)
alo-worker recover                   # 中断 task を監査し畳み方を提示
alo-worker registry build            # _registry.md を再生成
```

## 双子レーン

`tools/gpt_audit` (`docs/gpt_ometsuke` 系) が **検査官 (GPT)** の行き帰りを機械化するのに対し、
ここは **作業者 (Claude Code)** の inbox→doing→done/blocked を機械化する。
WORKER_PASS は「設計反映済み」ではなく、台帳 `next_action` が GPT 再監査 / ratify を指す。

> `inbox/W-20260623-00*.md` は作業票フォーマットの **見本**（対象 repo は `ALOBookDX`）。
> 本リポジトリで実作業票を起票するときは、この 2 件を消すか別 repo の queue に移す。
