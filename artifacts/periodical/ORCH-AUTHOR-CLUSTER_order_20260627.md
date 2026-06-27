# ORCH-AUTHOR-CLUSTER — 著者名の正規化＆クラスタリング

```yaml
to: Worker Claude Code
priority: 中（L4補助メタ・後段L5/L6に直結）
no_conflict_with: L4-COVERAGE-LIFT, classify-full, SERIES-DETECT, ISSUE-FEATURE, L5-FEASIBILITY
```

## 目的
著者表記のゆれを統一する author_id を採番。「同一論者の論考群」を引けるようにする。

## 入力
- article_join_dryrun_v0.1.csv 既に Mac 側にあり著者列(authors)が含まれる(無ければ jsonl 側)

## 処理
1. 著者列(複数著者はカンマ/中点で分割)→ 正規化(空白/旧字/全半角統一)
2. 編集距離 + 同誌・近年での共著ネットワークでクラスタ化
3. 著名な研究者(誌をまたいで多数執筆)から優先採番
4. author_id = `author:{normalized_slug}#{hash6}`

## 出力
artifacts/periodical/author_index_v0.1.csv (author_id, normalized_name, variant_names[], article_count, journals_appeared[], representative_titles[5])
artifacts/periodical/author_index_summary_v0.1.json (total_unique_authors, top20_by_article_count, ambiguity_count)

## 受入基準
- ≥10記事の著者が**50人以上**抽出
- 同一 normalized_name に異なる author_id が同時付与されない(衝突0)
- 著名な民法学者・税法学者などが top10 に登場
