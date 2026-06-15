# golden conflict fixtures

legallibjoin v0.3.1 の **既知 conflict 回帰セット**。Mac Phase 0 の
`known_conflict_golden.md`（既知 conflict 10冊）が返送されたら、各冊を
1ファイル `*.json` としてここに置くだけで `tests/test_golden.py` が検証する。

## スキーマ（1ファイル = 1冊）

```json
{
  "id": "coverage_mismatch_sample",
  "note": "片ソースが極端に少ない coverage mismatch の代表例",
  "book": {
    "isbn": "9784...",
    "title": "...",
    "source_meta": { "legallib": {"isbn":"...","title":"...","publisher":"...","year":"...","page_count":600,"page_basis":"print_page"}, "bencom": {...} },
    "sources": { "legallib": [{"title":"第1章 ...","depth":1,"page_start":1}], "bencom": [...] }
  },
  "expect": {
    "risk": "medium",
    "conflict_patterns": ["coverage_mismatch"],
    "edition_identity_status": "resolved_same_manifestation",
    "all_nodes_accounted_for": true,
    "min_unresolved": 1
  }
}
```

- `expect.conflict_patterns`: **必ず現れるべき** pattern（部分集合チェック。余分は許容）。
- 任意キー（`edition_identity_status` / `all_nodes_accounted_for` / `min_unresolved` /
  `max_unresolved`）は指定された時のみ検査。

## 守秘

実依頼者データ本文は載せない。**最小限の章タイトル断片と件数のみ**で conflict の形を再現する
（golden は「形」の回帰であって本文アーカイブではない）。
