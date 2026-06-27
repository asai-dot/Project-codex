# ORCH-CASENAME-DICT — 評釈タイトルからの事件名辞書構築

```yaml
to: Worker Claude Code
priority: 高（L5本番のdisambiguation主鍵）
```

## 目的
L5-FEASIBILITYで発見した「事件名照合がL5主要 disambiguator」を受け、雑誌側の評釈タイトル全件から事件名を抽出して辞書化。

## 入力
- article_join_dryrun_v0.1.csv (タイトル)
- article_type_local_pilot_v0.1.csv ＋ 全量分類が完了していれば全量も(あれば)、なければパイロット範囲

## 処理
1. 「○○事件」「○○訴訟」「○○判決」のパターン抽出
2. (court, date) と紐付け
3. 事件名の表記ゆれ統合（"自動車学校事件" "名古屋自動車学校事件" "X事件"）

## 出力
artifacts/periodical/case_name_dict_v0.1.csv (case_name_normalized, court, date, variant_names[], article_ids[])
artifacts/periodical/case_name_dict_summary_v0.1.json (total_unique_cases, top20_most_cited_cases, multi_court_cases)

## 受入基準
- 事件名抽出 ≥ 1,500件
- 表記ゆれ統合で variant_names の中央値 ≥ 2
