# ORCH-FEATURE-VALIDATE — ISSUE-FEATURE結果のサンプリング検査

```yaml
to: Worker Claude Code
priority: 中
```

## 目的
ISSUE-FEATURE (8,582号)の precision を測定。特集タイトルが実在の特集と一致するか。

## 処理
1. 各 confidence層(medium/low)から100号ずつサンプル
2. その issue_id 内の記事タイトル群を眺めて feature_title が妥当か判定
3. ambiguous_issue_count=391 を全件確認

## 出力
artifacts/periodical/feature_validate_v0.1.csv (issue_id, feature_title, sample_titles, judgement)
artifacts/periodical/feature_validate_summary_v0.1.json (medium_precision, low_precision, ambiguous_resolution_rate)

## 受入基準
- medium 90% / low 70% で本採用
