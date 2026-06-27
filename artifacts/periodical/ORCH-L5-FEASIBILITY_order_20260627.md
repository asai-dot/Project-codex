# ORCH-L5-FEASIBILITY — Worker Claude Code 発注: L5(評釈→判例リンク) 接合可能性試算

```yaml
order: ORCH-L5-FEASIBILITY
from: Cloud Code Web (codex, head)
to: Worker Claude Code
priority: 中（軽量・分析のみ・L4と並行可）
read-only: 入力読み取りのみ、分析CSV/JSONを生成。判例オブジェクト本体への書込なし。
ref: DD-PERIODICAL-002 L5
no_conflict_with: ORCH-L4-COVERAGE-LIFT, classify-full, SERIES-DETECT, ISSUE-FEATURE
```

## 目的
L5発注書を起こす前に、**雑誌側の評釈タイトル → 判例オブジェクト側ID への接合歩留まり**を試算する。
やみくもに全件流して低歩留まりだと無駄なのを防ぐ。

## 入力
1. `artifacts/periodical/article_join_dryrun_v0.1.csv`（article_id, title, journal, pub_year, issue_id）
2. パイロット分類結果 `artifacts/periodical/article_type_local_pilot_v0.1.csv`（type=判例評釈 のサブセット）
3. 判例オブジェクト側のID体系（リポジトリ内 docs/ や schemas/ から確認。なければ Mac側 build 配下を探索）

## 処理
1. **タイトル正規表現抽出**: 各評釈タイトルから判決メタを抽出
   - 裁判所: `最(判|決)|最高裁第[一二三]小法廷|大(判|決)|大阪|東京|名古屋|広島|福岡|札幌(高|地)(判|決)`
   - 年月日: `令和(\d+)\.(\d+)\.(\d+)|平成(\d+)\.(\d+)\.(\d+)|令和(\d+)年(\d+)月(\d+)日|平成…`
   - 事件性質: 「保険」「税」「民事」「刑事」等のキーワード
2. **抽出率の計測**: 評釈サブセットのうち何%が (court, date) を取り出せるか。
3. **既存判例ID側との突合試算**:
   - 判例オブジェクトの ID schema を確認(例: `jp:hanrei:{date}:{court}:{...}` 等)。
   - 抽出した (court, date) が判例ID側に存在するかをサンプル100件で確認。
4. **歩留まり報告**: 接合可能性を A(>80%) / B(50-80%) / C(<50%) で判定。

## 出力
- `artifacts/periodical/l5_feasibility_v0.1.csv`:
  `article_id, title, court_extracted, date_extracted, extracted_ok, hanrei_id_candidate, match_status`
- `artifacts/periodical/l5_feasibility_summary_v0.1.json`:
  `total_hyoshaku, court_date_extracted, extraction_rate, hanrei_match_rate, grade(A|B|C), notes[]`

## 受入基準
- パイロット判例評釈サブセット(≈790件)全件を対象。
- 抽出率と歩留まりを正直に報告（低くてもOK、L5発注書の精度設計に使う）。

## 安全
- read-only。判例オブジェクト側は SELECT/Read のみ。
- L4 とは authority CSV を触らないので衝突しない。
