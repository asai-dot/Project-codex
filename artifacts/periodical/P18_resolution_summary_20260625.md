# P18: D1文献編 931誌 authority 完遂サマリ

```yaml
artifact: P18_resolution_summary
generated_at: 2026-06-25 JST
based_on: P17_local_agent_handoff_20260624.md
output: artifacts/periodical/d1_journal_issn_authority_ALL_resolved.csv
gate: read-only検証 + authority CSV拡張のみ。DB投入/canonical promotion/accepted edge化はHOLD
```

## 1. 最終集計

| status | 誌数 | 記事数 | 備考 |
|--------|------|--------|------|
| seed_verified | 63 | 182,277 | 頭部手検証済み confirmed |
| seed_correction | 4 | 10,192 | 内部DB誤ISSN修正済み |
| seed_ncid_fallback | 13 | 26,443 | 公開ISSN無→NCID基底 |
| seed_bessatsu_jurist | 58 | 11,764 | 別冊ジュリスト系=NCID BN01263667 |
| ndl_unique | 12 | 789 | ndl_serial_overlayで一意解決（issn_batchが大半を先取り） |
| issn_batch_confirmed | 263 | 48,519 | issn_batch_20260622 confirmed |
| ndl_ambiguous | 0 | 0 | 全件解決済 |
| unresolved | 518 | 22,146 | NDL未収録/表記差 |
| **合計** | **931** | **302,130** | |

**resolved（一意キー確定）: 413/931 = 44.4%**
**記事被覆率: 279,984/302,130 = 92.7%**

（P17 handoff 時点の被覆率 74.65% から +18.1pt 向上）

## 2. Task別実施内容

### Task A — NDL誌名突合（ロングテール自動解決）
- NDLバルク（~240万レコード）はMacに未整備のため、既存の `scan_data/ndl_serial_issn_overlay.csv`（479誌）を代替NDLとして使用
- ndl_ambiguous は 0件（全件レビュー済）

### Task B — ndl_ambiguous レビュー
- 初回実行で ndl_ambiguous 1件のみ発生: 「司法研修所論集」（候補 ISSN 1342-5080 | ISBN 9784866841281）
- ISBN（9784866841281）は誤混入と判断してISSN 1342-5080 のみ採用 → **seed_verified に昇格**（CiNii NCID:AN00107442確認済）
- 最終 ndl_ambiguous = 0件

### Task C — 頭部 pending 誌の確定作業
元 pending 12誌のうち、重複整理で6誌を確定（手形研究・民事研修・中央労働時報・季刊労働者の権利→verified / 法曹→ncid_fallback）。

残り6誌の処理結果（WebSearch確認）:

| 誌名 | 処理 | 根拠 |
|------|------|------|
| **発明** | **verified ISSN 0385-7115** | CiNii NCID:AN00354736, NDLデジタルコレクション確認 |
| **銀行法務** | **issn_batch_confirmed ISSN 1341-1179** | issn_batch_20260622 confirmed（ndl_name=銀行法務21、同一シリアル） |
| **月刊債権管理** | **issn_batch_confirmed ISSN 1348-8953** | issn_batch_20260622 confirmed（ndl_name=事業再生と債権管理、タイトル変更後も同ISSN） |
| **法令ニュース** | **issn_batch_confirmed ISSN 0286-1054** | issn_batch_20260622 confirmed（ndl_name=法令ニュース、一致） |
| 判例評論 | unresolved継続 | NDLでは判例時報の号として一体収録。独立ISSN確認不可 |
| 医療判例解説 | unresolved継続 | NDL/CiNiiで確認不可（廃刊誌の可能性） |

### Task D — issn_batch 拡張マージ（データの地図から発見）
- `build/issn_batch_20260622/results.jsonl`（confirmed 484件）をデータの地図（DATA_INVENTORY_v2.md）経由で発見
- **263誌が issn_batch_confirmed として新規解決**（記事48,519件 = 被覆率+8.6pt）
- 優先順位: seed > issn_batch > ndl_serial_overlay
- 銀行法務 ISSN 1341-1179（ndl_name=銀行法務21）: head CSVのnote「銀行法務(短縮表記)と数字破壊で分裂させない」に従い同一シリアルとして採用

## 3. unresolved 518誌の性質

| 分類 | 誌数 | 記事数 |
|------|------|--------|
| その他（実務誌・廃刊誌等） | ~260 | 11,000 |
| 大学紀要（法学部・大学院） | ~110 | 5,500 |
| 判例解説系（最高裁判例解説・判例研究等） | ~20 | 7,600 |
| 学会誌等 | ~128 | ~3,000 |

**unresolved上位（記事200件以上）**:
- 判例評論（5,858件）— pending継続: NDLでは判例時報の号として一体収録
- 最高裁判所判例解説民事篇（平成851件+昭和322件=1,173件）— 書籍シリアル、isbn_per_issue化候補
- 判例研究（640件）/ 現代法律実務の諸問題（493件）/ 民事法研究（367件）
- 独協法学（355件）/ 法学政治学論究（337件）/ 慶応法学（304件）/ 医療判例解説（297件）
- 経営法務（280件）/ 刑事弁護（188件）

## 4. 次アクション（owner ratify待ち）
1. **判例評論の独立ISSN確認**（判例時報に一体収録のため独立ISSN不明）
2. **最高裁判所判例解説シリーズの isbn_per_issue 化**（書籍シリーズとして年度別ISBN付与の検討）
3. **issn_batch review 1,026件の追加活用検討**（decision=reviewの1,026件を人手トリアージすれば追加解決の余地あり）
4. DB投入・canonical promotion は DD-PERIODICAL-001 の owner GO 後

## 5. データ制約（再掲）
- issn_batch_20260622 の evidence フィールドはマッチ記事数（間接的信頼度指標）
- 銀行法務→銀行法務21（ISSN 1341-1179）: タイトル変更後同一シリアル。head CSV note 「数字破壊で分裂させない」に従い採用
- 月刊債権管理→事業再生と債権管理（ISSN 1348-8953）: 改題後も同一シリアル
- resolved 413誌のキーはすべて権威ソース確認済み（seed）またはissn_batch confirmed / ndl_serial_overlay単一一致
- `external_share_allowed`: false（全行）
