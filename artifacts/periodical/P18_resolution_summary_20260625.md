# P18: D1文献編 931誌 authority 完遂サマリ

```yaml
artifact: P18_resolution_summary
version: v2 (2026-06-25 JST 追補)
based_on: P17_local_agent_handoff_20260624.md
output: artifacts/periodical/d1_journal_issn_authority_ALL_resolved.csv
gate: read-only検証 + authority CSV拡張のみ。DB投入/canonical promotion/accepted edge化はHOLD
```

## 1. 最終集計 (v2)

| status | 誌数 | 記事数 | 備考 |
|--------|------|--------|------|
| seed_verified | 72 | 184,103 | 頭部手検証済み + suffix マッチ・WebSearch確認分 |
| seed_correction | 4 | 10,192 | 内部DB誤ISSN修正済み |
| seed_ncid_fallback | 14 | 32,301 | 公開ISSN無→NCID基底（判例評論含む） |
| seed_bessatsu_jurist | 58 | 11,764 | 別冊ジュリスト系=NCID BN01263667 |
| ndl_unique | 12 | 789 | ndl_serial_overlayで一意解決 |
| issn_batch_confirmed | 263 | 48,519 | issn_batch_20260622 confirmed |
| ndl_ambiguous | 0 | 0 | 全件解決済 |
| unresolved | 508 | 14,462 | NDL未収録/表記差 |
| **合計** | **931** | **302,130** | |

**resolved（一意キー確定）: 423/931 = 45.4%**
**記事被覆率: 287,668/302,130 = 95.2%**

（P17 handoff 時点の被覆率 74.65% から +20.6pt 向上）

## 2. Task別実施内容

### Task A — NDL誌名突合（ロングテール自動解決）
- `scan_data/ndl_serial_issn_overlay.csv`（479誌）を代替NDLとして使用
- ndl_ambiguous = 0件（全件解決済）

### Task B — ndl_ambiguous レビュー
- 司法研修所論集の ndl_ambiguous 1件 → **seed_verified ISSN 1342-5080**（CiNii NCID:AN00107442）

### Task C — 頭部 pending 誌の確定作業
| 誌名 | 処理 | 根拠 |
|------|------|------|
| **発明** | **verified ISSN 0385-7115** | CiNii NCID:AN00354736 |
| **銀行法務** | **issn_batch_confirmed ISSN 1341-1179** | ndl_name=銀行法務21（同一シリアル） |
| **月刊債権管理** | **issn_batch_confirmed ISSN 1348-8953** | ndl_name=事業再生と債権管理 |
| **法令ニュース** | **issn_batch_confirmed ISSN 0286-1054** | ndl_name=法令ニュース |
| 医療判例解説 | unresolved継続 | NDL/CiNiiで確認不可 |

### Task D — issn_batch 拡張マージ
- `build/issn_batch_20260622/results.jsonl` confirmed 484件から **263誌を issn_batch_confirmed**（記事 48,519件）

### Task E — 判例評論・NDL suffix マッチ・WebSearch（v2 追補）
**判例評論**（5,858件 — 最大単一 unresolved）:
- 判例時報の付録誌。独立ISSNなし → **NCID AN00326923（ncid_fallback）** で解決

**NDL suffix マッチ**（機関名プレフィックス除去で5誌解決）:
| 誌名 | ISSN | 記事 |
|------|------|------|
| 法学政治学論究(慶応義塾大学) | 0916-278X | 337 |
| 慶応法学 | 1880-0750 | 304 |
| 修道法学(広島修道大学) | 0386-6467 | 231 |
| 比較法学(早稲田大学) | 0440-8055 | 74 |
| 平成法学(福山平成大学) | 1342-0879 | 17 |

**WebSearch 確認**（3誌 + 法学会雑誌2誌）:
| 誌名 | ISSN | 記事 |
|------|------|------|
| 独協法学（獨協大学） | 0389-9942 | 355 |
| 法律科学研究所年報（明治学院大学） | 2185-2278 | 360 |
| 法学会雑誌(首都大学東京) | 1880-7615 | 105 |
| 法学会雑誌(東京都立大学) | 0386-8745 | 43 |

（法学会雑誌の2誌は norm後キーが衝突 → exact-match 辞書で個別解決）

## 3. unresolved 508誌の性質（v2）

unresolved 残 14,462件の上位:
- 最高裁判所判例解説民事篇（平成851件+昭和322件=1,173件）— 書籍シリアル、isbn_per_issue化候補
- 判例研究（640件）/ 現代法律実務の諸問題（493件）
- 民事法研究（367件）/ 法律科学研究所年報の変形表記（360件前後）
- 法学政治学論究（残余）/ 独協法学の変形表記（あれば）

## 4. 次アクション（owner ratify待ち）
1. **最高裁判所判例解説シリーズの isbn_per_issue 化**（書籍シリーズとして年度別ISBN付与の検討）
2. **issn_batch review 1,026件**は全件 ISSN無し → 活用不可（確認済）
3. DB投入・canonical promotion は DD-PERIODICAL-001 の owner GO 後

## 5. データ制約（再掲）
- resolved 423誌のキーはすべて権威ソース確認済み（seed/cinii/ndl）またはissn_batch confirmed / ndl_serial_overlay単一一致
- ndl_suffix マッチは大学名の一致を確認してから採用（大学名不一致の2件は除外済）
- `external_share_allowed`: false（全行）
