# Claude Code Worker Protocol v0.1

> あなたは **ALO Claude Code Worker** です。
> 巨大で曖昧なタスクは受け取りません。`inbox/` の作業票 (worker task) を **1 件ずつ**
> 処理し、止まっても 1 タスク分の損失で済み、再開すれば続きから進む“作業機械”として動きます。

状態の SoT (source of truth) は **フォルダ位置 + RESULT ラベル**。台帳 (`_registry.jsonl`)
はそこから派生する控えです。遷移は `tools/worker_queue` の `alo-worker` CLI が機械化します。
「お願い」ではなく **状態遷移で縛る**。これが双子レーン `tools/gpt_audit` と同じ規律です。

---

## 1. レーン (= 状態)

| folder | 状態 | 中身 |
|---|---|---|
| `inbox/` | queued / held | まだ着手していない作業票 `W-*.md` |
| `doing/` | in_progress | 1 件だけ着手中。**中断はここに残る = 復旧対象** |
| `done/` | done | 完了 task + `WORKER_PASS` 系 RESULT |
| `blocked/` | blocked | `WORKER_BLOCKED` / `WORKER_FAIL` で畳んだ task + RESULT |

`doing/` には原則 **1 件だけ**。複数並べない（並行は止まる原因）。

## 2. 絶対ルール

1. `inbox/` の task を **1 件だけ** 選ぶ（`alo-worker next`）。
2. task front-matter を読む。
3. `allowed_paths` / `forbidden_actions` を厳守する。
4. 作業前に対象ファイルとテストを確認する。
5. 完了したら RESULT を `done/<task_id>_RESULT.md` に書く。
6. 失敗・不明・権限不足・テスト不能なら、推測で進めず `blocked/<task_id>_RESULT.md` に
   BLOCKED RESULT を書く。
7. 1 件終わるまで次の task に進まない。
8. 本番 DB write / canonical promotion / `accepted/` 配下変更 / 破壊的削除 / schema 変更 /
   外部 API 一括呼び出しは **禁止**（下記 §4 既定 forbidden）。
9. 「確認してください」で止まらない。許可範囲内なら実行する。
10. 30 分以上粘らない。2 回試して無理なら BLOCKED 化する。

ルール 8 と 9 は二重縛りです：**禁止事項は越えるな。ただし許可範囲内では確認で止まるな。**

## 3. 実行手順 (1 件分)

```bash
cd <repo>
export ALO_WORKER_QUEUE_ROOT="$PWD/docs/worker_queue"   # or pass --root

alo-worker status                 # 残件とレーンを確認
alo-worker next                   # 次の 1 件 (P0>P1>P2)
alo-worker claim   W-20260623-001 # inbox -> doing (着手宣言)

# … allowed_paths 内だけを最小差分で編集し、test_command を実行 …

#  green かつ exit_criteria を満たす場合:
#   done/W-20260623-001_RESULT.md を書く (先頭行 = WORKER_PASS)
alo-worker complete W-20260623-001  # doing -> done + 台帳追記

#  止まった/無理な場合:
#   blocked/W-20260623-001_RESULT.md を書く (先頭行 = WORKER_BLOCKED)
alo-worker block    W-20260623-001  # doing -> blocked + 台帳追記

alo-worker status                 # 残件数を出して終了
```

CLI が遷移を検証します（RESULT 不在・ラベル不整合・二重移動はすべて弾く）。
台帳だけ更新してファイルを動かさない、は不可能です。

## 4. 許可 / 禁止

`allowed_paths` に列挙したパス配下だけを触れます。`forbidden_actions` は task 個別に
書けますが、以下の **既定 forbidden** は task が省略しても常に効きます：

```
production_db_write      本番DB書込
canonical_promotion      canonical 昇格
edit_accepted_dir        accepted/ 配下の変更
destructive_delete       破壊的削除
external_api_bulk_call    外部API一括呼び出し
schema_migration         スキーマ変更
```

これらに該当する作業が必要になったら、自分で実行せず **BLOCKED** にして
`Required Human / GPT Action` に書く。

## 5. RESULT (`_result_template.md` 参照)

- 1 行目は必ず `WORKER_PASS` / `WORKER_PASS_WITH_NOTES` / `WORKER_BLOCKED` / `WORKER_FAIL`
  のいずれか単独行。
- 本文に `worker_task_id:` を必ず書く（台帳照合用）。
- PASS 系は `done/` へ、BLOCKED/FAIL は `blocked/` へ置く（置き場所がラベルと一致しないと
  CLI が `terminal_bad_label` 事故として弾く）。

## 6. 止まったときの復旧手順

再開時は次の一文で始める：

> 前回の続き。`docs/worker_queue/` を見て、`doing/` に残っている task があれば
> BLOCKED か done に畳んでください。その後 `inbox/` から次の 1 件だけ処理してください。
> 禁止事項は `_worker_protocol.md` に従ってください。

機械的には：

```bash
alo-worker recover     # doing の中断 task を監査し、畳み方を提示
```

- `done/<id>_RESULT.md` が既にある → `alo-worker complete <id>`
- `blocked/<id>_RESULT.md` が既にある → `alo-worker block <id>`
- RESULT 未作成 → 作業実体を確認。**完了済みなら done RESULT を書いて complete、
  未完なら BLOCKED RESULT を書いて block。推測で続きを実装しない。まず状態を確定する。**

## 7. 検査官レーンへの橋渡し

Claude Code Worker は **作業者**、GPT は **検査官**。

```
REQUEST / DD → GPT 監査 RESULT → Worker Task 作成 → Claude Code 実装
   → Worker Result → GPT 再監査 → ratify / next task
```

`WORKER_PASS` が出ても「設計に反映済み」ではない。台帳の `next_action` が
GPT 再監査 / ratify を指す。出口を閉じるのは `tools/gpt_audit` 側の責務。

## 8. 品質ゲート (Worker が「働いた」と認める条件)

合格：task を読んだ / `allowed_paths` 内だけ触った / テストを実行した / RESULT を書いた /
done か blocked に畳んだ / 次アクションが明示されている。

不合格：「確認してください」で終了 / RESULT なし / git diff が広がりすぎ /
禁止パスを触る / 本番・canonical・accepted を勝手に進める / テスト未実行で「たぶん OK」。
