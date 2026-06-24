# P20: 最高裁判所判例解説 isbn_per_issue 化

```yaml
artifact: P20_saikosai_isbn_per_issue
generated_at: 2026-06-25 JST
base: artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v3.csv (P19精度監査後)
output: artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v4.csv
supporting: artifacts/periodical/saikosai_isbn_map.csv (年度→ISBN対応表, 26件)
gate: read-only検証 + authority CSV拡張のみ。DB投入/canonical promotion/accepted edge化はHOLD（DD-PERIODICAL-001）。
```

## 1. 対象誌（8 journal_canonical, 1,409記事）

| journal_canonical | 記事数 | 備考 |
|---|---|---|
| 最高裁判所判例解説――民事篇<平成 | 851 | 22年度分 |
| 最高裁判所判例解説――民事篇<昭和 | 322 | 9年度分 |
| 最高裁判所判例解説――刑事篇<平成 | 85 | |
| 最高裁判所判例解説――民事篇<令和 | 60 | |
| 最高裁判所判例解説――刑事篇<昭和 | 52 | |
| 最高裁判所判例解説――民事篇<平成元年度>』所収p | 30 | 掲載誌等の変形パース由来 |
| 最高裁判所判例解説――刑事篇<平成元年度>』所収p | 6 | 同上 |
| 最高裁判所判例解説――刑事篇<令和 | 3 | |

**合計: 8誌 1,409記事**

## 2. 方針

- 書籍シリーズ確定（ISSN全件空 / 発行所=法曹会 / 年度×篇で独立書籍）
- 別冊ジュリスト系（`seed_bessatsu_jurist`）と同じ設計：key_type=isbn_per_issue, key_value=''
- 新ステータス `seed_isbn_per_issue`（isbn_per_issueの宣言 = 号レベルIDは別処理）
- 各年度の ISBN は `saikosai_isbn_map.csv` に 26件収録（平成23年度〜令和4年度。昭和期・平成初期は ndl_isbn_index 未収録）

## 3. ISBNマップ概要（saikosai_isbn_map.csv）

- ndl_isbn_index.csv（851万行）から「最高裁判所判例解説」でフィルタ
- 有効 ISBN 26件（民事篇14 / 刑事篇12）
- 民事篇一部年度は上下2冊（令和2年度(上)/（下）等）
- 昭和期・平成元〜22年度は ndl_isbn_index に収録なし → 別途 NDL API/CiNii で補完余地あり

## 4. 最終状態（v4.csv）

| status | 誌数 | 記事数 |
|---|---|---|
| seed_verified | 72 | 184,103 |
| seed_correction | 4 | 10,192 |
| seed_ncid_fallback | 14 | 32,301 |
| seed_bessatsu_jurist | 58 | 11,764 |
| ndl_unique | 12 | 789 |
| issn_batch_confirmed | 254 | 45,143 |
| **seed_isbn_per_issue** | **8** | **1,409** |
| unresolved | 506 | 13,952 |

**resolved: 422/931 = 45.3%**
**被覆率: 285,701/302,130 = 94.6%**（v3 94.1% から +0.5pt）

## 5. 残 unresolved 上位（v4.csv基準）

- 月刊債権管理（682件）— P19で誤吸着判定。正ISSNを権威ソースで確認できれば解決余地あり
- 判例研究（640件）— 複数機関に同名誌が存在する可能性
- 現代法律実務の諸問題<平成（493件）— 日弁連研修叢書の書籍シリーズ（isbn_per_issue候補）
- 民事法研究（367件）/ 大阪弁護士会（344件）/ 判例セレクト（316件）

## 6. 次アクション
1. **月刊債権管理の正ISSN確認**（季刊事業再生と債権管理ではなく、月刊債権管理自体のISSN）
2. **現代法律実務の諸問題の isbn_per_issue 化**（日弁連研修叢書シリーズ、P19 unresolved 493件）
3. **銀行法務 vs 銀行法務21（3,827件）の owner 裁定**（P19 保留事項）
4. DB投入・canonical promotion は DD-PERIODICAL-001 の owner GO 後

`external_share_allowed`: false（全行）
