# ORCH-NDL-RECONCILE — authority v14 と NDL最新書誌の整合チェック

```yaml
to: Worker Claude Code
priority: 中
depends_on: L4-COVERAGE-LIFT 完了後に最大効果（L4実行中でも開始可・L4のCSVは触らない）
```

## 目的
authority v14の各誌について NDL 最新書誌情報(刊行終了/改題/承継誌)との整合をチェック。改題を見逃すと L4 で誌の同一性が崩れる。

## 処理
- 各誌の NDL書誌を JSON で再取得（軽い API、Ollama 不使用）
- 改題・承継誌・統合・分割イベントを検出
- 雑誌オブジェクトの誌一覧に「succession_event」列追加候補をCSVで提案

## 出力
artifacts/periodical/journal_lifecycle_v0.1.csv (journal_canonical, ndl_status, succession_event, related_ncid)
artifacts/periodical/journal_lifecycle_summary_v0.1.json (active/discontinued/renamed, succession_clusters)

## 受入基準
- 承継誌イベント検出 ≥ 20件（現代刑事法→刑事法ジャーナル等の事例が拾えること）
