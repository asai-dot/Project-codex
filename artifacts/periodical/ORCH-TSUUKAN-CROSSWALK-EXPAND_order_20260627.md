# ORCH-TSUUKAN-CROSSWALK-EXPAND — 主要誌の巻号↔通巻フル変換表

```yaml
order: ORCH-TSUUKAN-CROSSWALK-EXPAND
from: Cloud Code Web (codex, head)
to: Worker Claude Code
protocol: docs/periodical/HEAD-ORDER-PROTOCOL.md (必読)
priority: 中（L4の足元を強くする・将来全クエリに効く）
read-only: 入力読み取りのみ。authority CSVは触らない(L4と非衝突)。
related_to: L4-COVERAGE-LIFT の orphan tsuukan_unavailable 問題と同根
```

## 1. 目的
主要法律雑誌について **(vol, issue_no) ↔ 通巻** の完全変換表を整備。L4の通巻算出を「規則(formula/ndl_actual)」から「lookup」に格上げし、orphan = tsuukan_unavailable を構造的に減らす。

## 2. 入力
1. authority v14 — 対象誌のNCID/ISSN取得用
2. article_join_dryrun_v0.1.csv — どの vol/issue_no が出現するか
3. 必要に応じてNDL書誌API(軽い)で通巻番号を取得

## 3. 対象誌(Worker判断で増減可、まず以下を必須)
| 誌 | 理由 |
|---|---|
| ジュリスト(ISSN 0448-0791) | 30万件中の最大シェア |
| 銀行法務21(1341-1179) | 3,000記事 |
| 法学教室(0389-2220) | 別冊系との接続 |
| 旬刊商事法務(0287-1057) | 連載複数 |
| 法学セミナー(0439-3295) | 別冊/増刊との統合済 |
| 判例タイムズ(0438-5896) | 増刊系の接続 |
| 金融法務事情 | DVD系の前段 |
| ジュリスト増刊系 | 別冊ジュリスト除く |
他、article_join で vol/issue_no が頻出している誌(誌別上位20)を追加可。

## 4. 処理(Approach)
1. 各誌の (vol, issue_no, pub_year, pub_month) が出現するレコードを article_join から抽出
2. NDL/CiNiiで通巻番号取得 → クロスウォーク (vol, issue_no) → tsuukan
3. 既知 tsuukan_crosswalk (artifacts/periodical/crosswalk/) があれば併用・拡張
4. 通巻採番の整合確認(連続性・年跨ぎの不整合検出)

## 5. 出力スキーマ
- `artifacts/periodical/tsuukan_crosswalk_expand_v0.1.csv`:
  `journal_canonical, journal_key, vol, issue_no, tsuukan, pub_year, pub_month, source(ndl|cinii|formula|inferred), confidence`
- `artifacts/periodical/tsuukan_crosswalk_expand_summary_v0.1.json`:
  ```
  {journals_covered, total_rows, per_journal_coverage{},
   inconsistency_detected[], orphan_potentially_reducible_count(L4のtsuukan_unavailableをどれだけ救えるか試算),
   caveats[], self_grade, subagents_used[]}
  ```

## 6. 受入基準
- 対象誌8誌以上で coverage ≥ 90%(出現する vol/issue_no のうち通巻が引けた率)
- orphan_potentially_reducible_count ≥ 400(L4 orphan tsuukan_unavailable 1,123 の30%以上)
- 不整合検出が**ゼロでない**(完全に無いのは検出能力欠如のサイン)
- source 内訳が公開されること

## 7. 不合格時
受入未達の場合、対象誌を絞って再発注。NDL書誌の取得不能誌は authority_unresolved として記録。

## 8. Self-Audit
- ランダム10レコードについて Worker 自身が NDL書誌で再検証
- 連続性チェック(同一誌で通巻がN→N+1→N+2 と連続するか)を実施し caveats に件数

## 9. サブエージェント活用ガイド
- **Explore**: 既存 tsuukan_crosswalk の中身と source.py 規則を確認
- **Plan**: NDL/CiNii の取得バッチ設計(rate limit 配慮、retry戦略)
- **general-purpose**: NDL API のbulk取得部分を1サブエージェント化してもよい(本ループ汚さない)

## 10. 安全
read-only authority。出力は新規 CSV/JSON。NDL/CiNii は SELECT のみ。

## 11. 再発注の前提
v0.2: L4-COVERAGE-LIFT 完了後の新 authority を input にして対象誌を増やす。
