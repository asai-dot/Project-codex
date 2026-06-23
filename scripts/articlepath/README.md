# scripts.articlepath — 条文同定の正準化（PLAN L4：同定の地盤）

法令テキスト・XML・house path で**バラバラに書かれる条番号を、ひとつの正準 `ArticlePath` に統一**し、
**数値ソートキー**と**旧↔新 crosswalk** を出す。dispute グルーピング（assembler）と接続軸（DD-LAWREF-001
の `references`/`delegates_to` edge）は「同じ条文か」の判定に全面的に依存しており、その土台。

## 3 つの入力を 1 つに
| 入力形 | 例 | 由来 |
|---|---|---|
| e-Gov XML `Num` | `398_22` | 法令標準 XML の `Article/@Num`（第398条の22） |
| house path | `art:398-22` | lawdelta / DD-LAWTIME の article_path tail |
| 漢数字テキスト参照 | `第三百九十八条の二十二第二項` | 逐条解説・判決文中の参照（→ 将来の参照 edge の素） |

```python
from scripts.articlepath import parse
parse("398_22").canonical()              # 'art:398-22'
parse("第三百九十八条の二十二").canonical()  # 'art:398-22'  (3 形が一致)
parse("art:5:para:2:item:1").sort_key()  # 数値タプル（文字列順でなく数値順）
parse("art:415:para:1").root()           # 条 root: art:415（grouping 用）
```

漢数字変換は `scripts.drafterintent.patterns.kanji_to_int` を再利用（単一の真実源）。

## CLI
```
python -m scripts.articlepath --delta out/law_textual_delta_<run>.jsonl --out out/articlepath_<run>
```
- `<out>_crosswalk.jsonl`: 変更条の旧↔新マッピング（insertion/repeal/split/join/substitution）。
- `<out>_report.json`: 正準化結果＋**文字列ソート vs 数値ソートの不一致監査**。

## 実データでの所見
`docs/status/20260623_reallane_minpo_articlepath_findings.md`（実民法 1167 条で走らせた知見＝ALO DB 設計の参考）。
要点: **文字列ソートは 1167 条中 1156 条で誤る → 同定層は数値キー必須**。枝番は深さ1（398条の22 まで）。
3 形の正準化は実データで 0 件 unparseable。crosswalk は要検証の疑わしい対応も炙り出す（＝事実でなく assertion）。
