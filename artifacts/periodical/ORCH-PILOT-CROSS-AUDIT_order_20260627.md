# ORCH-PILOT-CROSS-AUDIT — 分類パイロットの誌偏り検証・補追サンプリング

```yaml
to: Worker Claude Code
priority: 中
ref: HEAD-NOTE_classify_pilot_skew_20260627.md
```

## 目的
パイロット2000件は全件ジュリストだった。全量分類完了を待たず、他誌(銀行法務21/金融法務事情/判タ/法学教室等)のサンプル分類を qwen3:30b で実行し誌横断精度を試算。

## 処理（GPU 全量分類が走行中の場合は控えめに）
1. 主要他誌から500件ずつサンプル（全量分類prog から拝借するか別途分類）
2. ジュリストでのクロスチェック方式と同じハーネスで一致率測定
3. 「その他」過多が他誌でも起きるか確認

## 出力
artifacts/periodical/pilot_cross_audit_v0.1.csv (article_id, journal, type, expected_signal_match)
artifacts/periodical/pilot_cross_audit_summary_v0.1.json (per_journal_crosscheck_rate, other_ratio_per_journal)

## 受入基準
- 主要4誌で一致率 80%以上、または失敗誌の改善対象が判明
