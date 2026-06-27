# ORCH-D2-AUTHORITY-RECONCILE — 別冊ジュリストD2のauthority CSV整合

```yaml
order: ORCH-D2-AUTHORITY-RECONCILE
from: Cloud Code Web (codex, head)
to: 次のheadセッション(Cloud Web自身) または 軽量実行担当
priority: 低（接合層で既に解消済・記号整理）
blocking: ORCH-L4-COVERAGE-LIFT 完了後に実行する（CSV編集競合回避）
read-only外: authority CSV の status列のみ変更。key_value 不変。
```

## 背景
別冊ジュリスト(NCID BN01263667) の判例百選58誌について、
- 接合層: D2(2026-06-24)で **isbn_per_issue として扱い済**。受入監査でhyakusen_collision=0確認済。
- authority CSV(v14)では `seed_bessatsu_jurist` のまま放置。記号整合のための書き換えが残ってる。

## やること（最新authorityに対して）
1. 最新の authority CSV(v15+) を読む。
2. `key_type=ncid` かつ `key_value=BN01263667` の 58誌について、`status` を
   `seed_bessatsu_jurist` → `isbn_per_issue` に書き換え。
3. `note` 列に「D2(2026-06-24) authority整合: 接合層では既にisbn_per_issue扱い」を追記。
4. その他列は不変。

## 受入基準
- 書き換え対象: ちょうど58誌（事前にcountして確認）。
- L3精度: ISSN/NCID衝突回帰検査(audit_article_join.py の延長 or 簡易python)で新規誤マージ0。
- L4接合: 再実行不要（接合層は既にisbn扱いなので status記号変更は接合結果に影響しない）。

## なぜブロッキング条件があるか
ワーカーCCのORCH-L4-COVERAGE-LIFTが同じauthority CSVを編集するため、並行編集すると競合する。
L4完了→commit→push を確認してから本ORCHを実行する。
