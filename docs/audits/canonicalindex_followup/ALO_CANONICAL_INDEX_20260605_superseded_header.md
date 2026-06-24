# [DRAFT] ALO_CANONICAL_INDEX_20260605 退役マーカー（先頭 prepend 用）

> 草案。承認後、Box `2266253855296` の **本文は一切変えず**、ファイル先頭にこの front-matter ブロックのみを追加する。
> full refresh / 部分追記はしない。削除もしない（historical context として価値があるため）。

適用する front-matter ブロック（GPT verdict §2.1 指定文言に準拠）:

```yaml
status: superseded
role: historical_index / reference_pointer
superseded_by: design_decisions.md Generated Index + 90_design_decisions.md sync Generated Index
superseded_at: 2026-06-07 JST
reason: stale snapshot; per-artifact status SoT consolidated into design_decisions Generated Index
```

意図: 「状態1行だけ追記して中身も更新済みに見せる」のではなく、**この index 全体を古い snapshot として退役させる**表示。
以降の per-artifact 状態 SoT は `design_decisions.md` Generated Index（primary `2172365558197`）／ sync mirror `90_design_decisions.md`（`2187272953323`）。
