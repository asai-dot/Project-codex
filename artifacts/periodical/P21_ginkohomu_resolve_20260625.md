# P21: 銀行法務 ISSN 統合確定（P19 owner保留事項の解決）

```yaml
artifact: P21_ginkohomu_resolve
generated_at: 2026-06-25 JST
base: artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v5.csv
input_v4: artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v4.csv
gate: read-only検証 + authority CSV更新のみ。DB投入/canonical promotion/accepted edge化はHOLD（DD-PERIODICAL-001）。
```

## 1. 経緯
P19で「銀行法務(3,827件) vs 銀行法務21(3,000件)」が同一シリアルかを owner が「記事内容で確認して」と委任。

P19.md §5 に owner が NDL/CiNii 調査結果を事前記載:
- 手形研究(ISSN 0494-9692, 経済法令研究会, 1957–1994) → 1995年改題 → 銀行法務21(ISSN 1341-1179)
- NDL/CiNiiの継続前誌は「手形研究」であり、独立した「銀行法務」誌は存在しない

## 2. article_meta による確認

### 2a. 性質確認
`article_meta_labeled.jsonl` から両 journal_canonical の掲載誌等フィールドを比較：

| journal_canonical | 件数 | 掲載誌等パターン | 性質 |
|---|---|---|---|
| 銀行法務21 | 3,000 | `銀行法務２１ 70-4, p1〜` | 雑誌各号の記事（スペースあり） |
| 銀行法務 | 3,827 | `銀行法務２１70-4, p1〜` | 同じ雑誌の記事（スペースなし → 誤canonical化） |

→ **同一誌。D1の誌名抽出が「銀行法務２１70-3」（スペースなし）を誤切り出しして別canonical化したもの。**

### 2b. 年代分布確認（P19 §5 残留リスク解消）
「銀行法務」バケツの発行年月日分布：

| 期間 | 件数 |
|---|---|
| pre-1995（手形研究期） | **0件** |
| 1995年（改題年） | 99件 |
| 2006–2026年 | 3,728件 |

→ **pre-1995 = 0件確認。手形研究(0494-9692)の混入なし。完全統合確定。**

## 3. v5.csv での変更

| フィールド | v4 | v5 |
|---|---|---|
| status | issn_batch_confirmed | **seed_verified** |
| source | issn_batch_20260622 | seed:article_meta_confirmed |
| note | (旧NDL証跡のみ) | 手形研究改題チェーン+年代分布確認(pre-1995=0件)を明記 |

## 4. v5.csv 集計

| status | 誌数 | 記事数 |
|---|---|---|
| seed_verified | 73 | 187,930 |
| seed_correction | 4 | 10,192 |
| seed_ncid_fallback | 14 | 32,301 |
| seed_bessatsu_jurist | 58 | 11,764 |
| ndl_unique | 12 | 789 |
| issn_batch_confirmed | 253 | 41,316 |
| seed_isbn_per_issue | 8 | 1,409 |
| unresolved | 506 | 13,952 |

**resolved: 422/931 = 45.3%**  
**被覆率: 285,701/302,130 = 94.6%**（v4と同値。銀行法務は v4 時点で既に issn_batch_confirmed として被覆済み）

## 5. 次候補（unresolved 506誌 13,952件）

優先順：
1. **月刊債権管理（682件）** — ISSN 1348-8953 は誤吸着（季刊事業再生と債権管理）。正ISSN確認要
2. **現代法律実務の諸問題<平成（493件）** — 日弁連研修叢書シリーズ、isbn_per_issue候補
3. **判例研究（640件）** — 複数機関同名誌の可能性、機関別分離要検討

`external_share_allowed`: false（全行）
