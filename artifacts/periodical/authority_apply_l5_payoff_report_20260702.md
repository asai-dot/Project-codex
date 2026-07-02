# authority反映のL5 payoff 実測レポート 20260702（read-only・正直な結果）

- 目的: 判例authority の court化け15復元＋dedup614 が L5(評釈→判例) court突合を改善するかの実測。
- 方法: 実 `l5_feasibility_build.py` の関数を import し、HANREI_FILES を 旧2ファイル vs 新dedup で切替え、判例評釈790件の court_match を比較（read-only）。

## 結果（差分ゼロ）
| authority | court_match | date_only_court_miss | index行数 |
|---|---:|---:|---:|
| 旧(20260605+backfill・化けあり) | 674 | 41 | 212,602 |
| 新(dedup_canonical_20260702・復元) | 674 | 41 | 211,988 |
| **差分** | **0** | **0** | **−614** |

## 解釈（正直）
- **court化け復元のL5効果 ≒ 0**。復元15裁判所は簡裁/区裁で、評釈は最高裁/高裁/著名地裁を対象とするため、court突合に現れない（当初の「L5改善」期待は空振り）。
- **dedupは非破壊と実証**: 614行削除でも court_match は674不変＝実在突合を1件も喪失していない（重複だけを正しく除去）。
- **修正の真の価値はauthority整合性**（判例ID重複600→0・identity_key重複・court_key正確化）＝判決件数集計・引用join・事件番号lookup で効く。評釈court metricでは出ない。

## 位置づけ
consumer配線(producer WO)は「L5精度向上」ではなく「重複のない正しいauthorityを下流へ流す(正しさ担保)」が目的、と訂正して記録する。
