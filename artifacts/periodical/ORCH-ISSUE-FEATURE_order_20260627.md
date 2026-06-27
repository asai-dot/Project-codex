# ORCH-ISSUE-FEATURE — Worker Claude Code 発注: 特集号メタ抽出

```yaml
order: ORCH-ISSUE-FEATURE
from: Cloud Code Web (codex, head)
to: Worker Claude Code
priority: 中（L4と並行可・リソース衝突なし）
read-only: 入力読み取りのみ。
ref: DD-PERIODICAL-002 (L4補助メタ)
no_conflict_with: ORCH-L4-COVERAGE-LIFT, classify-full
```

## 目的
各 `issue_id` に紐づく**特集タイトル**を集約。検索ファセット最強候補（「金融法務事情の◯◯特集」一発引き）。

## 入力候補（順に確認・存在するものを使う）
1. `build/labeled_v0.2.1/article_meta_labeled.jsonl` の `special_feature` 列（存在すれば最優先）
2. Supabase `staging_periodical.issue_stage` の `special_feature` 列
3. タイトル抽出 fallback: 記事タイトル先頭の `【特集】|＜特集＞|特集／|特集◯◯|シンポジウム|大特集` パターン

## 処理
1. 入力データの `special_feature` を issue_id ごとに集約。同一号で値が複数あれば、最頻値 or 連結（記録）。
2. fallback時は、同一 issue_id 内の記事タイトルから特集語を多数決抽出。
3. 信頼度を付与（直接列＝高 / タイトル抽出＝中・低）。

## 出力
- `artifacts/periodical/issue_feature_v0.1.csv`:
  `issue_id, feature_title, source(meta|sql|title_extract), article_count, confidence`
- `artifacts/periodical/issue_feature_summary_v0.1.json`:
  `total_issues_with_feature, source_breakdown{}, top20_features_by_articles[]`

## 受入基準
- 特集が付いた issue_id が**少なくとも500件以上**抽出（法律雑誌なら大量にあるはず）。
- 同一 issue_id に複数の異なる feature_title が同時付与されない（曖昧時は最頻値 + 候補リスト併記）。
- top20 を手目視で「実在しそう」（後で監査）。

## 安全
- read-only。出力は新規CSV。L4と衝突しない。
- Supabase列にアクセスする場合は SELECT のみ（書込なし）。

## 実行
1. 入力存在確認 → 取得経路を1つ決定。
2. 処理スクリプト(`tools/periodical/extract_issue_feature.py`)を作成して実行。
3. 出力 + summary を push。
