# P23: unresolved 一括解決 batch2（NDL NCID + ISSN大学紀要 + 増刊bessatsu）

```yaml
artifact: P23_unresolved_batch2
generated_at: 2026-06-25 JST
base: d1_journal_issn_authority_ALL_resolved_v6.csv
output: d1_journal_issn_authority_ALL_resolved_v7.csv
gate: read-only検証 + authority CSV更新のみ。DB投入/canonical promotion/accepted edge化はHOLD（DD-PERIODICAL-001）。
```

## 1. 変更内容（51誌）

### 1a. NDL SRU で NCID/ISSN 取得 → seed_verified / ndl_unique（7誌 1,378件）

| journal_canonical | 記事数 | 取得識別子 | 備考 |
|---|---|---|---|
| ローヤー | 152 | ISSN 0913-1124 / NCID AN10391794 | 月刊ハイ・ローヤー(辰已法律研究所) |
| 刑事弁護 | 188 | NCID AN10468265 | 季刊刑事弁護(現代人文社) |
| 大阪弁護士会 | 344 | NCID AN10522258 | 月刊大阪弁護士会(大阪弁護士会月報改題後) |
| 大東文化大学法学研究所報 | 67 | NCID AN10486981 | 大東文化大学法学研究所 |
| 大学院研究年報(法学研究科篇)(中央大学) | 272 | NCID AN00135903 | 中央大学 |
| 東京大学大学院法学政治学研究科専修コース研究年報 | 254 | NCID AN10438537 | 東京大学 |
| Law & Practice | 86 | ISSN 1883-8529 | 早稲田大学大学院法務研究科 |

### 1b. 判例タイムズ系増刊 → seed_bessatsu_jurist（2誌 374件）

| journal_canonical | 記事数 | ISSN | 備考 |
|---|---|---|---|
| 民事法研究 | 367 | 0438-5896 | 季刊・民事法研究 Vol.4-21(判タ507-656号増刊) |
| 法学セミナー増刊,p | 7 | 0439-3295 | 法学セミナー増刊(日本評論社) |

### 1c. ISSN直接確認・大学紀要等 → seed_verified（42誌 約750件）

article_meta ISSN フィールドから直接取得・100%被覆の単一機関誌

主要誌: 現代法学(東京経済大学)・用地・労働福祉・駒沢法学・関西大学法科大学院ジャーナル・季刊用地・法と秩序・Hitotsubashi Journal of Law and Politics・東北法学会会報(東北大学)・群馬法専紀要・法政法学(法政大学)・明治大学大学院紀要(法学篇)・英米法学(中央大学)・自治研修・法学研究論集(亜細亜大学)・駒沢大学法学部研究紀要・CCR・法学研究年誌(東北学院大学)・関西大学法学研究所研究所報・賠償医学・法学会誌(明治大学)・秋田法学2種（ISSN 0286-2859, ノースアジア大学=秋田経済法科大学改名）等

## 2. 保留した誌（精度優先）

- **月刊債権管理**（682件）: NDL n=0 = 未収録確定。正ISSN取得困難。
- **判例研究**（640件）: 発行所4機関混在（金財/有斐閣/三協法規/信山社）
- **商事法務**（50件）: 発行所複数（商事法務研究会41+国際商事法研究所8） → 誤混入
- **タイム**（25件）: 発行所3種（日本労働文化協会/富士銀行/判例タイムズ社）
- **法学研究**（7件 generic）: 3機関混在

## 3. v7.csv 集計

| status | 誌数 | 記事数 |
|---|---|---|
| seed_verified | 131 | 190,897 |
| seed_correction | 4 | 10,192 |
| seed_ncid_fallback | 14 | 32,301 |
| seed_bessatsu_jurist | 61 | 12,254 |
| ndl_unique | 17 | 1,914 |
| issn_batch_confirmed | 253 | 41,316 |
| seed_isbn_per_issue | 16 | 2,606 |
| seed_override | 2 | 2,449 |
| collision_split | 1 | 28 |
| **unresolved** | **432** | **8,173** |

**resolved: 499/931 = 53.6%**  
**被覆率: 293,957/302,130 = 97.3%**（v6: 96.4% から +0.9pt）

## 4. 次アクション（unresolved 432誌 8,173件）

残 unresolved の大部分は:
- 月刊債権管理（682件） → NDL未収録・長期保留
- 判例研究（640件） → 多機関混在・owner判断推奨
- 小規模紀要・廃刊誌 → 優先度低

97.3%被覆到達により、残 2.7%（8,173件）は小規模誌多数で個別対応が必要。

`external_share_allowed`: false（全行）
