# P6: issue_id_v2 実リフト測定（確定seed適用・本番） — read-only

```yaml
artifact: P6_lift_realcompute
wo: WO-PERIODICAL-ISSN-SEED-EXPANSION (v0.2)
generated_at: 2026-06-20 JST
source: staging_periodical.issue_stage（read-only / mutation 0）
seed: artifacts/periodical/issn_seed_v2_consolidated_20260619.csv（confirmed/ncid_key/candidate）
rule: issue_id_v2 = key#通巻, key優先 ISSN-L > ISSN > NDLBibID > NCID（P5裁可）
method: 「key有 ∧ 通巻(issue_no)有 ∧ 現状非canonical」= 新規canonical化。捏造ISSNなし。
```

## 結論：確定seedで新規 canonical 化 = **+218号（solid）**

| 経路 | 新規canonical | 内訳 |
|---|--:|---|
| **ISSN key** | **108** | 交通事故民事裁判例集50 / 労働判例33 / 金融法務事情15 / 法学教室6 / law&technology2 / jcaジャーナル2 |
| **NCID key** | **110** | 戸籍58 / 季刊刑事弁護40 / 労働経済判例速報10 / 登記研究2 |
| **solid 計** | **218** | confirmed ISSN + 裁可済みNCIDキー |
| 法律時報e-book（別manifestation） | +36 | 親=印刷版0387-3420へ通巻リンク。印刷canonicalとは別オブジェクト |
| 法と哲学（candidate） | +4 | ISSN 2188-711X 未検証のため保留。検証で確定 |
| **到達上限（全部入り）** | **258** | dry-compute上限275に対し94% |

canonical 見込み: **1,923 → 2,141（68%→約76%）**（solidのみ）。e-book+candidate確定で最大 2,181（約77%）。

## key有でも効かない（通巻欠＝トラックB送り）
ISSNを入れても通巻が無く canonical 化しない集合（本seed内）:

| 誌 | 号数 | 現status |
|---|--:|---|
| 税経通信 | 208 | provisional_ym（通巻0） |
| ビジネス法務 | 66 | provisional_ym（通巻0） |
| 警察学論集 | 41 | canonical_ym（既にym同定済） |
| 法律のひろば | 30 | provisional_ym（通巻有3は既canonical） |
| 人事の地図 | 24 | provisional_ym（通巻0・かつkey無） |
| jcaジャーナル | 214 | 通巻欠（216中214） |

→ これらは**ISSN seedの対象外**。ソース生データからの**通巻抽出（トラックB）**が次のレバー。jca214+税経208が最大。

## key無しで保留
| 誌 | 号数 | 理由 |
|---|--:|---|
| jcaaビジネスジャーナル | 4 | 2025創刊の新誌。ISSN/NCID未付番（通巻は有）→key採番待ち |
| 人事の地図 | 24 | ISSN/NCID未取得＋通巻欠（二重に不足） |

## 注記
- 印刷版「法律時報」は staging に行が無く（e-bookのみ36号）、0387-3420 の直接リフトは0。e-bookは別manifestationとして上表に計上。
- NCIDキー化（戸籍/季刊刑事弁護/労経速/登記研究=110号）はP5裁可ルールに基づく。ISSN判明時はISSN-L優先で差し替え。
- 本計算は read-only。canonical の実書き込みは別ステップ（owner GO後）。
