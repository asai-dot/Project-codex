# ORCH-DATA-PROFILE — 雑誌オブジェクト全体の統計プロファイル

```yaml
to: Worker Claude Code
priority: 低（軽い・補助）
```

## 目的
雑誌オブジェクトの全体像を1枚のプロファイルレポートに。下流UX設計と異常検出の baseline。

## 処理
- 誌別: 記事数 / 接合率 / 評釈率 / 連載率 / 特集数
- 年別: 記事数推移
- 通巻分布の異常（飛び番号、二重発行）
- isbn_per_issue 化されている誌のISBN 重複検出

## 出力
artifacts/periodical/data_profile_v0.1.md (Markdown report)
artifacts/periodical/data_profile_anomalies_v0.1.csv (issue_id, anomaly_type, evidence)

## 受入基準
- 異常検出 ≥ 100件（書誌上の歪みは必ずある、ゼロは検出失敗）
