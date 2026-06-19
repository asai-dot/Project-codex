# silver-1 掲載位置→判例ID 解決レポート (dry-run / read-only)

- 入力エッジ総数: **7**
- 解決済 (≥1候補): **5** (71.4%)  ※基準値 概算24%
- strong (issue_page_exact 単一): **2**  ← D2: これのみ staging write 候補
- review queue: **3**
- 未解決 (honest_empty): **2**

## match_method 別
| method | 件数 |
|---|---|
| issue_page_exact | 3 |
| (none) | 2 |
| issue_page_fallback | 1 |
| court_date | 1 |

## 未解決理由 (honest_empty)
| reason | 件数 |
|---|---|
| locator_unresolvable | 1 |
| db_unbuilt | 1 |

## 二層分離の確認
- strong は issue_page_exact 単一のみ (2). fallback/court_date/多候補は review.
- strong と review は別レーン. review は自動確定しない (P4 信号保存).

_本レポートは dry-run. candidate は staging 出力のみ. 本番 write なし._