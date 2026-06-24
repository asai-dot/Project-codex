# silver-2 TOC→論点section 構造化レポート (dry-run / read-only)

- 入力 row (toc_row_reports_hanrei): **3**
- 論点section 解決不能 row: **0**
- 抽出 論点section: **2**

## 無意味共起の置換 (本ツールの主眼)
- 同一書籍 全結合ペア (naive, weight-1, 無意味): **3**
- 論点section 単位ペア (意味あり): **1**
- → 書籍粒度の weight-1 全結合を捨て, 論点section 内共起のみ残した.

## 論点section サイズ分布
| member数 | section数 |
|---|---|
| 1 | 1 |
| 2-5 | 1 |

## 共起ペア weight (共有論点section数) 分布
| weight | ペア数 |
|---|---|
| 1 | 1 |

## harvest / honest_empty 規律
- 論点見出しは文献TOC heading の harvest (人手 seed なし / 分野分類代替なし).
- 評釈密度ゼロ section = review (1). trace_absent として honest_empty 区別.
- DD-LRINDEX-001 v0.4 (G_HARVEST_NOT_MANUFACTURE) GPT確認パス前は accepted 論点扱いしない.

_本レポートは dry-run. candidate は staging 出力のみ. 本番 write なし._