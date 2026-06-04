# 検索ベンチ ベースライン（A0-5 / Phase A 着手前に作成）

> **【位置づけ更新 2026-06-05】このテンプレは Stage2（owner 監修 gold）用。**
> Stage1 は gold を作らない観測ベースラインに変更した（owner判断「まず実測→後でgold」）。
> Stage1 の方法・結果は `baseline_method.md` / `baseline_result_20260605.md` / `measure_consultation_reach.py` を参照。
> 本テンプレの expected_concepts/expected_articles は Stage2 で owner が監修して埋める欄であり、Stage1 では使用しない。

> 目的: 語彙554・蔵書6,524・`bib_terms`未投入の**現状**で検索性能を1回測り、以後の投入効果を比較する基準にする。
> 価値の最終判定は「件数」でなく**この到達率**（owner方針＝根拠が見える・自己監査可能でなければ業務に入れない）。
> 50件は**浅井の実務相談類型**から作る（owner主導）。下は記入フォーマットと種例。

## 記入フォーマット（1クエリ＝1ブロック）
```yaml
- id: Q001
  query: "下請けに払う代金を一方的に減額された。何の法律問題か？"
  consultation_type: 商取引／下請取引          # 相談類型
  expected_concepts: [下請代金, 減額, 優越的地位の濫用]   # 到達すべき語彙(biblio.terms想定)
  expected_articles: ["下請法4条", "独占禁止法2条9項"]    # 到達すべき条文
  expected_books: []                            # 関連が期待される蔵書(任意・分かる範囲)
  notes: ""
```

## 測定指標（投入前=ベースライン / 投入後で再測）
| 指標 | 定義 |
|---|---|
| headword_hit_rate | expected_concepts が `biblio.terms` 検索でヒットした割合 |
| article_reach_rate | expected_articles に（条見出しリンク等で）到達できた割合 |
| book_reach_rate | expected_books / 関連蔵書に到達できた割合（bib_terms投入後に意味を持つ） |
| false_hit_rate | 上位結果に無関係な語/本が混じる割合 |

## 種例（owner が実務クエリへ差し替え・拡充して50件に）
```yaml
- id: Q001
  query: "契約を解除したいが、相手が応じない。どう構成するか。"
  consultation_type: 契約一般
  expected_concepts: [契約解除, 債務不履行, 催告]
  expected_articles: ["民法540条", "民法541条"]
  expected_books: []
- id: Q002
  query: "取締役が会社に損害を与えた。責任追及できるか。"
  consultation_type: 会社法務
  expected_concepts: [取締役, 任務懈怠, 役員等の責任]
  expected_articles: ["会社法423条"]
  expected_books: []
- id: Q003
  query: "個人情報が漏えいした。事業者の義務と責任は。"
  consultation_type: 情報法
  expected_concepts: [個人情報, 個人データ, 漏えい]
  expected_articles: ["個人情報保護法2条", "個人情報保護法26条"]
  expected_books: []
```

## 運用メモ
- ベースライン測定は read-only（現状の `biblio.terms` 検索＋条見出しリンクの到達）で実施。bib_terms 未投入なので
  book_reach は 0 近傍が基準値（＝橋を張る価値の伸びしろがここで定量化される）。
- 投入（A5/A6・B・C）後に同じ50件で再測し、各指標の前後差を記録 → Phase D の価値判定。
