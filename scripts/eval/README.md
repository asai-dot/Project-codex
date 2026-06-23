# scripts.eval — 精度評価ハーネス（PLAN L1：測れる化）

producer 出力（pred JSONL）を **ゴールド（gold JSONL）** と突き合わせ、
**label 単位（delta_kind / change_type / treatment_relation / pattern_id 等）の
precision・recall・F1 と confusion** を出す。stdlib のみ。DB 不要。

## なぜこれが要るか
lawdelta の閾値（`SUBST_MIN` / `RENUMBER_SIM`）も drafter/treatment の cue 確度も、
いまは fixture の勘の値で、**一度も採点されていない**。本ハーネスが無いと
「閾値を変えたら精度が上がった/下がった」を数字で言えず、L5–L7（粒度・stance・cue/ML）の
改善が全部“感想”になる。これは複利の元本。

## 使い方
```
python -m scripts.eval --task <名前> \
    --gold <gold.jsonl> --pred <pred.jsonl> \
    --key <join列> --label <比較列> \
    [--out out/eval_<名前>] [--min-f1 0.8]
```
- `--key`: gold と pred を突き合わせる列（例 `article_path`、`assertion_key`、`dedup_key`）。
- `--label`: 正解と予測を比べる列（例 `delta_kind`、`change_type`、`treatment_relation`）。
- 片側にしか無いキーは「取りこぼし(FN)」「過剰生成(FP)」として計上される。
- `--min-f1`: micro-F1 がこれ未満なら exit 2（**gold が非空のときだけ**発火）。

## 空 gold でも緑（CI 常駐の前提）
gold が空/未配置なら **no-op で exit 0**（"no gold labels yet" を表示）。
これで実ラベルが入る前から CI に常駐でき、ラベル充填＋閾値設定後に初めて赤くなる。

## タスク別の推奨 key/label
| task | pred | key | label |
|---|---|---|---|
| lawdelta | `law_textual_delta_*.jsonl` | `article_path` | `delta_kind` |
| drafter | `drafter_substantive_assertions_*.jsonl` | `assertion_key` | `change_type` |
| treatment | `case_treatment_candidates_*.jsonl` | `dedup_key` | `treatment_relation` |
| dispute | `resolved_assertions_*.jsonl` | `target_key` | `stance` |

## ゴールドの作り方
`tests/gold/README.md` を参照。実ラベルは **L3（real-lane：実 e-Gov revision / 実判決）** と
同期して充填する。最初は債権法改正の数十条＋判決十数件で十分に効く。
現状 `tests/gold/lawdelta_demo_minpo.gold.jsonl` は **配線確認用のプレースホルダ**
（demo 出力に一致＝P/R=1.0 のスモーク）であり、実ゴールドではない。
