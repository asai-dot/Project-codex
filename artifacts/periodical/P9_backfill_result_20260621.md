# P9: バックフィル実行結果（M1 適用済）

```yaml
artifact: P9_backfill_result
migration: M1_backfill_issue_id_20260621.sql
applied_at: 2026-06-21 JST
source: staging_periodical.issue_stage（mutation 実施）
```

## ステータス遷移（前後比較）

| status | 適用前 | 適用後 | Δ |
|---|--:|--:|--:|
| canonical | 1,833 | 2,463 | **+630** |
| canonical_ym | 90 | 178 | **+88** |
| provisional_no_issn | 277 | 57 | -220 |
| provisional_ym | 534 | 36 | -498 |
| unassigned | 113 | 113 | 0 |
| **合計** | **2,847** | **2,847** | 0 |

→ **718行昇格**（P7予測+716との差2＝警察學論集旧字2行、P6/P7未カウント分）

## 被覆率

| 指標 | 値 |
|---|--:|
| canonical + canonical_ym | 2,641 |
| 全体 | 2,847 |
| **被覆率** | **92.8%** |

（P7予測 92.7% とほぼ一致）

## Phase 別内訳（Δcanonical +630 の内訳）

| Phase | 対象 | 昇格先 | 行数 |
|---|---|---|--:|
| A-1 ISSN | 交通事故民事裁判例集 | canonical | 50 |
| A-1 ISSN | 労働判例 | canonical | 33 |
| A-1 ISSN | 金融法務事情 | canonical | 15 |
| A-1 ISSN | 法学教室 | canonical | 6 |
| A-1 ISSN | law&technology | canonical | 2 |
| A-1 ISSN | 警察學論集（旧字） | canonical | 2 |
| A-1 ISSN | jcaジャーナル (#813/#815) | canonical | 2 |
| A-2 NCID | 戸籍 (AN00274615) | canonical | 58 |
| A-2 NCID | 季刊刑事弁護 (AN10468265) | canonical | 40 |
| A-2 NCID | 労働経済判例速報 (AN00327835) | canonical | 10 |
| A-2 NCID | 登記研究 (AN00157564) | canonical | 2 |
| B-1 jca formula | jcaジャーナル (2015-2026 全214) | canonical | 214 |
| B-2 zeikei xwalk | 税経通信 (2014-2025, 196) | canonical | 196 |
| **canonical 小計** | | | **630** |
| A-3 ISSN | ビジネス法務 | canonical_ym | 66 |
| A-3 ISSN | ビジネスガイド | canonical_ym | 10 |
| A-3+miss | 税経通信 2026 (NDL未収録) | canonical_ym | 12 |
| **canonical_ym 小計** | | | **88** |

## 検証サンプル

### jca cross-form dedup（Track B 正規化の核心）
| source | issue_id | status |
|---|---|---|
| lionbolt | `issn:0386-3042#815` | canonical |
| bencom | `issn:0386-3042#815` | canonical |
| legallib | `issn:0386-3042#815` | canonical |

→ 旧 `jp:jcaジャーナル#815`(lionbolt) と `jp:jcaジャーナル#2025-05`(bencom/legallib) が**1 id に統合**。

### 税経通信 増刊飛び保持（NDL実値）
- 2025-09 → `issn:0387-2866#1141` canonical ✓
- 2026-01 → `issn:0387-2866#2026-01` canonical_ym ✓（据置・NDL再取得待ち）

## 残 provisional（57+36=93行、全件意図的除外）

| 分類 | 件数 | 理由 |
|---|--:|---|
| 法律時報e-book | 36 | P5決定: separate_manifestation（印刷版と統合しない） |
| 法と哲学 | 4 | ISSN 2188-711X 未検証（candidate） |
| jcaaビジネスジャーナル | 4 | 2025新刊・ISSN未付番 |
| 人事の地図 | 24 | ISSN/NCID 未取得（needs_pull） |
| lifesciencenewsletter | 6 | ISSN なし（小規模 newsletter） |
| competitionnewsletter | 4 | ISSN なし |
| asia&emergingcountrieslegalupdate | 1 | ISSN なし |
| 警察実務重要裁判例令和6年版 | 1 | 雑誌ではなく書籍 |
| malformed / 非雑誌 | 13 | パース誤りや告示文書 |

## 残ボトルネック（M1 適用後）

1. **unassigned 113**: issue_id 未付与行の素性調査（M1 対象外）
2. **人事の地図 24**: ISSN/NCID が来れば canonical_ym 化可能（M1 追補対象）
3. **法と哲学 4**: ISSN 2188-711X 出典確認後に canonical 化
4. **税経通信 2026 12**: NDL 再取得後に B-2 追補で canonical 化
