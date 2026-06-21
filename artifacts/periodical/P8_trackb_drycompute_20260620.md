# P8: Track B 通巻昇格 ドライ集計（クロスウォーク staging 適用） — read-only

```yaml
artifact: P8_trackb_drycompute
wo: WO-PERIODICAL-TRACKB-TSUUKAN-CROSSWALK v0.1
generated_at: 2026-06-20 JST
source: staging_periodical.issue_stage（read-only / mutation 0）
crosswalk: artifacts/periodical/crosswalk/{zeikei,jca}_tsuukan_xwalk.csv
method: provisional行に (year,month)→通号 を当て issn:{ISSN}#{通号} を生成、distinct集約で統合効果を測定。
```

## 結果

### jcaジャーナル（検証式クロスウォーク）
| 指標 | 値 |
|---|--:|
| provisional行（214 ym + 2 通巻） | 216 |
| 通号マップ成功 | 216（全件・2026も式で算出） |
| **distinct 通巻号（統合後）** | **137** |
| 統合された重複行 | 79（クロスソース77 ＋ 通巻↔年月 cross-form 2） |

- cross-form 2 = lionbolt の `#813/#815`（通巻形）が bencom/legallib の 2025-03/05（年月形）と**同一idに収束**。
  → **Track Bが無ければ同一号が issn:#815 と issn:#2025-05 の2idに割れる**問題を解消。

### 税経通信（NDL実値クロスウォーク・増刊飛び保持）
| 指標 | 値 |
|---|--:|
| provisional_ym 行 | 208 |
| クロスウォーク命中 | 196（2014-2025） |
| 未命中（2026最新, NDL未収録） | 12 → canonical_ym 据置 |
| **distinct 通巻号（統合後）** | **144** |
| 統合された重複行 | 52（bencom/legallib クロスソース） |

## 含意
- 2誌で **424 source行 → 真通巻 canonical（jca137＋税経144=281号）＋ 税経2026の12行は canonical_ym 据置**。
- Track Bの正味効果は2層:
  1. **精度**: canonical_ym（月）→ canonical（通号）。
  2. **正しさ**: 通巻形/年月形の同一号を1idに統合（jcaで実証＝cross-form 2、ym単独では解けない）。
- 増刊飛び（税経 810→812 等）は NDL実値クロスウォークが正しく吸収。jcaは増刊なし＝式で安全。

## 残・注意
- 税経2026の12行: NDLは増刊で通号が飛ぶため**暦算しない**。NDL再取得まで canonical_ym据置（解決済み・精度のみ保留）。
- jca2026: 式で 823〜 を算出済（増刊なし検証済のため確定可）。
- 他「通巻あり」月刊（要棚卸し）も同方式で拡張可。「通巻なし」誌（ビジネス法務等）は対象外＝canonical_ym終端。
- **書き込み（status昇格）は owner GO 後**。本P8は read-only 試算。
