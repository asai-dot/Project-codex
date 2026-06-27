# ORCH-SERIES-VALIDATE — SERIES-DETECT結果の手目視サンプリング検査

```yaml
to: Worker Claude Code
priority: 中（精度ゲート確認・分量小さい）
```

## 目的
SERIES-DETECT (10,243系列)の precision を測定する。head監査の延長として系列レベルの妥当性を Worker に検証させる。

## 入力
- article_series_v0.1.csv
- article_join_dryrun_v0.1.csv (タイトル原文)

## 処理
1. ランダムサンプル200系列を抽出 (層別: 連載長 3/5-10/10+ の3層から各60-70件)
2. 同系列のタイトル列を見比べて「明らかに別連載が混入」「同連載なのに別系列に割れている」を判定
3. precision/recall を概算

## 出力
artifacts/periodical/series_validate_sample_v0.1.csv (series_id, sampled_articles, judgement, reason)
artifacts/periodical/series_validate_summary_v0.1.json (precision_est, recall_clue_examples, suggested_threshold)

## 受入基準
- 精度 ≥ 90% で SERIES-DETECT v0.1 を本採用
- 90%未満なら誤検出パターンを抽出し v0.2 の改善点を提示
