# WO-PERIODICAL-TRACKB-TSUUKAN-CROSSWALK v0.1（通巻復元）

```yaml
wo: WO-PERIODICAL-TRACKB-TSUUKAN-CROSSWALK
version: 0.1
generated_at: 2026-06-20 JST
depends_on: [P5_id_decisions, P7_resolution_gate_correction]
status: design + 実証アーティファクト同梱（read-only検証済 / mutation 0）
```

## 1. 目的（Track Bの真価＝精度ではなく「クロスソース統合」）
canonical_ym は月刊を月精度で解決するが、**同一号が source により通巻形/年月形に分かれると別idになり統合に失敗する**。
例: jcaジャーナル 2025年5月号は
- lionbolt → `issn:0386-3042#815`（通巻）
- bencom/legallib → `issn:0386-3042#2025-05`（年月）
→ 同一実体が2id。**年月↔通巻クロスウォークで1idに畳む**のがTrack Bの本質。副次的に canonical_ym→canonical（真通巻）へ精度も上がる。

## 2. 通巻の有無（NDL書誌で確定・誌別）
| 誌 | 通巻 | 根拠 | 方針 |
|---|---|---|---|
| 税経通信 | **有(通号)** | `80巻13号(通号1144) 2025年12月` | クロスウォークで通巻canonical化 |
| jcaジャーナル | **有(通号)** | `63巻1号(通号703) 2016年1月` | 同上 |
| ビジネス法務 | **無(巻号のみ)** | `13巻1号 2013年1月`（通号表記なし） | canonical_ymで終端（通巻は存在しない） |
| ビジネスガイド/人事の地図 | 無想定 | 要同様確認 | canonical_ym |

→ **Track Bの対象は「通巻を持つ月刊」のみ**。通巻なし誌に通巻を付けようとしない。

## 3. クロスウォーク（同梱・実証済）
`artifacts/periodical/crosswalk/`
- `zeikei_tsuukan_xwalk.csv`（281件, 2002-2025）: **NDL専用TSV(file 2049089503039)実値**。
  通号は増刊で飛ぶ（810→812, 817→819…）ため暦算不可＝NDL実値が必須。
- `jca_tsuukan_xwalk.csv`（144件, 2015-2026）: **検証式** `通号=703+(年-2016)×12+(月-1)`。
  NDL27点＋lionbolt実値(815/813)で**100%一致検証済**。増刊飛びなし。

## 4. 適用ロジック
```
staging row (provisional_ym: jp:{j}#{YYYY-MM})
  └ join crosswalk on (journal, year, month)
       ├ hit → issue_id = issn:{ISSN}#{通号}, status=canonical
       │        （既存 lionbolt issn:{ISSN}#{通号} と自然統合＝クロスソースdedup）
       └ miss → canonical_ym のまま（フォールバック）
```

## 5. 歩留まり（staging実測）
| 誌 | provisional_ym | クロスウォーク命中 | 2026最新(未収録) |
|---|--:|--:|--:|
| 税経通信 | 208 | 196（2014-2025） | 12（NDL再取得 or 増刊注意の暦算） |
| jcaジャーナル | 214 | 204（式で全域可, 実質214） | 10（式で算出済=823〜） |

## 6. 検証・受入基準
- 通号単調性チェック（誌ごと、増刊飛びは許容しログ）。
- lionbolt等の既存通巻と**ダブルキー一致**（不一致は増刊/改題の疑い→保留）。
- 適用後 `issn:#通号` 重複は**同一号クロスソース統合のみ**であること（別号衝突0）。
- 2026未収録分: jcaは検証式で確定可。税経は増刊飛びのため**NDL再取得まで canonical_ym 据置**（暦算しない）。

## 7. スコープ外（別レーン）
- unassigned 113 / 非seed小newsletter 55 / no-key誌（人事の地図・jcaaビジネスジャーナル）。
- 書き込み（status昇格）は owner GO 後。本WOまでは read-only + アーティファクト生成のみ。
