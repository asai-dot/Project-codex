# ORCH-REPRINT-FIRST-PUB — タイトル+著者ベースの再録/初出 第1段試算

```yaml
order: ORCH-REPRINT-FIRST-PUB
from: Cloud Code Web (codex, head)
to: Worker Claude Code
protocol: docs/periodical/HEAD-ORDER-PROTOCOL.md (必読)
priority: 高（初出pacsigny実取込前の代替試算・大きい）
read-only: 既存CSV読み取りのみ。pacsigny lane には触らない(GO別)。
no_conflict_with: ALL
```

## 1. 目的
同一論者の同一/類似タイトルが**複数の号・複数の誌**で出現するケース(=再録)を検出し、
最古の出現を**初出候補**として記録する。これは本格 first_pub(pacsigny依存)を待たずに動く第1段試算。

## 2. 入力
1. article_join_dryrun_v0.1.csv (article_id, journal_canonical, pub_year, title)
2. article_series_v0.1.csv (連載は除外/別扱いに使う)
3. Mac側 article_meta_labeled.jsonl から authors 列が引ければ使う(無ければタイトルのみ)

## 3. 処理(Approach)
1. タイトル正規化: 「（上）（下）（再掲）」等の語尾を除去、句読点統一
2. クラスタリングキー: (normalized_title) または (normalized_title, author_lead)
3. クラスタサイズ≥2 を「再録候補」とする
4. 連載(series_id持ち)は除外(別物)
5. 初出判定: 各クラスタの pub_year 最小のものを first_pub_candidate
6. 信頼度: 同タイトル+同著者→高 / 同タイトル+異著者→中 / 類似タイトル→低

## 4. 出力スキーマ
- `artifacts/periodical/reprint_clusters_v0.1.csv`:
  `cluster_id, article_id, journal_canonical, pub_year, title, is_first_pub_candidate, confidence`
- `artifacts/periodical/reprint_summary_v0.1.json`:
  ```
  {total_clusters, total_articles_in_clusters, multi_journal_clusters,
   top20_most_reprinted[], first_pub_candidates_total,
   author_data_available(bool), caveats[], self_grade, subagents_used[]}
  ```

## 5. 受入基準
- 再録クラスタ ≥ 500（法律論考は再録/単行本化が多いはず）
- 同一 article_id が複数 cluster に属さない(衝突0)
- top20 を head が目視確認 → 「確かに同論者・同テーマ」と見える
- multi_journal_clusters (誌をまたぐ再録) ≥ 100

## 6. 不合格時
基準未達なら push せず原因報告。著者列が無くてタイトルのみだと精度が落ちる予測 → caveat に明記、head 判断で v0.2(著者付加)。

## 7. Self-Audit
- top20 を Worker 自身が目視確認し、明らかな誤クラスタ(別論者の同タイトル等)があれば caveats に
- author_data の有無を report

## 8. サブエージェント活用ガイド
- **Explore**: article_meta_labeled.jsonl で authors 列の存在/フォーマットを確認(1回)
- **Plan**: 正規化と類似度判定の戦略を相談(1回・編集距離 vs トークン一致)
- **general-purpose**: 不要、本ループで完結

## 9. 安全
read-only。pacsigny lane(HIGH-HOLD)には触らない。出力は新規CSV/JSON。

## 10. 再発注の前提
v0.2: pacsigny GO 後に first_pub_evidence='signy' を加え、本ORCHのcandidateと突合してconfidence格上げ。
