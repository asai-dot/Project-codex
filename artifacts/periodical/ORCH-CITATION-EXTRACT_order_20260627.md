# ORCH-CITATION-EXTRACT — タイトルからの法令・判例引用シグナル抽出

```yaml
to: Worker Claude Code
priority: 中
no_conflict_with: 上記全部
```

## 目的
タイトル文字列から「言及されている法令」「言及されている判例日付」を抽出し、後段L5/L6の事前材料とする。
L5本番(本文必要)を待たず、タイトルだけでも歩留まりを試算する。

## 処理
1. 法令名抽出: 民法/会社法/独禁法/金商法 等の主要法令名 + 略称辞書（小さなyamlで管理）
2. 判例日付抽出: L5-FEASIBILITY の正規表現を流用(元年含む)
3. 該当法令・該当判例の article_id 単位で indexing

## 出力
artifacts/periodical/title_law_citation_v0.1.csv (article_id, law_name, evidence_span)
artifacts/periodical/title_case_citation_v0.1.csv (article_id, court, date, evidence_span)
artifacts/periodical/title_citation_summary_v0.1.json (per-law_articles, top10_laws, top10_cited_dates)

## 受入基準
- 法令抽出 ≥ 5万件、判例日付抽出 ≥ 2万件（タイトル30万から)
- 同一article_id内の重複evidence_spanは1件に正規化
