# ORCH-ISSUE-INDEX — issue完全インデックス（雑誌オブジェクトの正本検索データ）

```yaml
order: ORCH-ISSUE-INDEX
from: Cloud Code Web (codex, head)
to: Worker Claude Code
protocol: docs/periodical/HEAD-ORDER-PROTOCOL.md (必読)
priority: 高（後段検索/UX/L5 すべての primary index になる）
read-only: 入力は既存push済CSV/JSON。新規派生のみ生成。
no_conflict_with: ALL（authority/Ollama/外部API いずれも触らない）
```

## 1. 目的
雑誌オブジェクトを「号(issue)」単位で**検索/参照する正本インデックス**を作る。issue_id 1つに紐づく
すべての記事メタ・著者・特集・連載・ページ範囲を1ファイルに集約 → 下流の検索/UX/L5 全てのbaseになる。

## 2. 入力
1. `artifacts/periodical/article_join_dryrun_v0.1.csv` — (article_id, issue_id, journal_canonical, pub_year, title, vol, issue_no, page_start, seq_in_issue)
2. `artifacts/periodical/article_series_v0.1.csv` — (article_id, series_id, title_normalized)
3. `artifacts/periodical/issue_feature_v0.1.csv` — (issue_id, feature_title, confidence)
4. `artifacts/periodical/article_type_local_pilot_v0.1.csv` — type ラベル (ある記事のみ・パイロット範囲のみ)
5. authority v14 — 誌メタ(ISSN/NCID/出版者)を引くため

## 3. 処理(Approach)
issue_id ごとに以下を集約した JSONL (1行=1issue):
- `issue_id`, `journal_canonical`, `journal_key`, `pub_year`, `vol`, `issue_no`, `tsuukan`
- `article_count`, `page_range_summary` (最小start〜最大end), `articles[]` (article_id, title, seq, page_start, type)
- `authors_distinct[]` (issue内ユニーク著者リスト・タイトルから抽出済なら使う)
- `feature_title`, `feature_confidence` (あれば)
- `series_present[]` (この号に登場する series_id 一覧)
- `provenance`: 入力ファイルとversion
**実装方針の自由度**: pandas で結合してもよいし、生csvでdict集約でもよい。Worker判断。

## 4. 出力スキーマ
- `artifacts/periodical/issue_index_v0.1.jsonl` (1行1issue, 上記すべて)
- `artifacts/periodical/issue_index_summary_v0.1.json`:
  ```
  {total_issues, issues_with_feature, issues_with_series, issues_with_type_data,
   avg_articles_per_issue, journals_covered,
   sample_full_issues[3],   # 完全に埋まったissueの実例3つ
   caveats[], self_grade(A|B|C|D),
   subagents_used[{type, why}]}
  ```

## 5. 受入基準(head独立検査)
- 総 issue 数 ≥ 30,000（article_join の issue_id 一意数程度）
- 「全列埋まりissue」が全体の **40%以上**（feature+series+type が3つ揃う号）
- article_count の合計が article_join の joined 行数(299,957)とほぼ一致(±0.5%)
- JSONLの各行が JSON.parse可能・スキーマ完全
- summary.self_grade と head独立判定の差が1段階以内

## 6. 不合格時の挙動(On-Fail)
Worker は受入基準を**自分でも回す**こと。FAIL なら **push しない** で、不合格summary だけ書いて報告。
head が改善方針付き v0.2 発注を起こす。

## 7. Self-Audit(Worker側 push前)
- JSONL を 100行ランダムサンプルしてスキーマ準拠を確認
- article_count の合計 vs joined 件数チェック
- 結果を summary.caveats に記録

## 8. サブエージェント活用ガイド
- **Explore**: 入力5ファイルの実在/列名/サイズ確認に1回
- **Plan**: 5ソースの結合戦略を1回相談（pandas vs dict、メモリ vs 速度）
- **general-purpose**: JSONL生成本体は本ループで実行(委譲しない=ヘッドが流れを追える)

## 9. 安全
read-only。authority も触らない。出力は jsonl/json 新規のみ。force-push禁止。

## 10. 再発注の前提
v0.2 で考えうる改善: 全量分類完了後にtype網羅率を上げる、reprint候補列を追加、cross-reference issue_id を入れる等。
v0.1 では現状データで最大限の網羅をする。
