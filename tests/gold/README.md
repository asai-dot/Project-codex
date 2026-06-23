# tests/gold — 精度評価のゴールドセット（PLAN L1）

`scripts.eval` が突き合わせる **正解ラベル**。1 行 1 レコードの JSONL。
producer 出力（pred）と同じ **key 列** を持ち、人手検証した **label 列** を付す。
それ以外の列は自由（出典・検証者・メモ等を付けてよい）。

## 様式（最小）
```jsonl
{"article_path": "art:170", "delta_kind": "repeal",       "verified_by": "asai", "basis": "新旧対照表"}
{"article_path": "art:415", "delta_kind": "substitution", "verified_by": "asai", "basis": "新旧対照表"}
```
- **key**: pred と突き合わせる列（lawdelta=`article_path`、drafter=`assertion_key` か `pattern_id`、
  treatment=`dedup_key` か `pattern_id`）。
- **label**: 正解値（lawdelta=`delta_kind`、drafter=`change_type`、treatment=`treatment_relation`）。
- 値域は DD-LAWSUBTRANS-001 §2 の統制語彙に従う。

## 検証器（ラベルの典拠）
- **lawdelta**: 公式新旧対照表／名大「改め文」16 パターン／e-Gov 標準 XML の `textualMod`。
- **drafter**: 一問一答・逐条解説の該当スパン（quoted_text と span）。
- **treatment**: 判決の評価窓（citator 流儀＝裁判所が何をしたか）。

## ファイル
| ファイル | 状態 | 用途 |
|---|---|---|
| `lawdelta_demo_minpo.gold.jsonl` | **プレースホルダ**（demo 出力に一致） | ハーネス配線のスモーク（P/R=1.0） |

> ⚠️ demo gold は配線確認用で**実ゴールドではない**。実ラベルは L3（real-lane）で
> 実 e-Gov revision・実判決から人手検証して充填し、`--min-f1` で閾値を立てる。
> 充填後は CI が精度割れで赤くなる（＝守れる化 L2 と接続）。
