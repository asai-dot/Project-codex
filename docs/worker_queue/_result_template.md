# WORKER_RESULT テンプレート

1 行目はラベル単独行。`done/` 行きは `WORKER_PASS` 系、`blocked/` 行きは
`WORKER_BLOCKED` / `WORKER_FAIL`。ファイル名は `<task_id>_RESULT.md`。

---

## PASS の場合 — `done/<task_id>_RESULT.md`

```markdown
WORKER_PASS
# Worker Result
worker_task_id: W-20260623-001
label: WORKER_PASS
completed_at: 2026-06-23T00:00:00+09:00

## 1. Summary
B21 support chain の failing test を修正し、指定テストは green。

## 2. Files Changed
- src/xdoc/support_chain.py
- tests/xdoc/test_support_chain.py

## 3. Commands Run
​```bash
pytest tests/xdoc -q
# 97 passed
​```

## 4. Diff Summary
- support node の parent resolution を deterministic に修正
- orphan support の扱いを explicit blocked に変更
- fixture B21 を追加

## 5. Remaining Issues
なし。

## 6. Next Recommended Task
W-20260623-002 に進行可能。
```

`WORKER_PASS_WITH_NOTES` は同形式で、`## 5` に「ratify 前に反映すべき blocking note」を
書く（PASS だが宿題あり）。

---

## BLOCKED の場合 — `blocked/<task_id>_RESULT.md`

```markdown
WORKER_BLOCKED
# Worker Result
worker_task_id: W-20260623-001
label: WORKER_BLOCKED
blocked_at: 2026-06-23T00:00:00+09:00

## 1. Blocker
指定されたテストファイル tests/xdoc/ が存在しない。

## 2. Evidence
​```bash
ls tests/xdoc
# No such file or directory
​```

## 3. What I Tried
- repo root 確認
- tests 配下確認
- rg "B21" 実行

## 4. Required Human / GPT Action
正しいテストパスまたは対象 commit を指定すること。

## 5. No Unsafe Action Taken
DB write / canonical promotion / destructive delete は実行していない。
```

---

## FAIL の場合 — `blocked/<task_id>_RESULT.md`

`WORKER_FAIL` は「やってみたが exit_criteria を満たせず、かつ blocker でもない（task 設計
自体が不適切／前提が崩れている）」とき。`## 4` に task 再設計の論点を書く。
