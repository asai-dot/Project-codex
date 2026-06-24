# P15: D1文献編 931誌の統合キーauthority（頭部・検証着手）

```yaml
artifact: P15_d1_journal_authority_head
generated_at: 2026-06-23 JST
depends_on: [P14_issn_verification_sweep, D1bunken_acquisition_status, label_journals_v0.2.1]
intent: D1文献編282,761記事/931誌(canonical)を、下流(D1×NDL×CiNii by ISSN+巻号)で名寄せ統合するための「誌名→ISSN/NCID/ISBN権威マップ」を、記事数・評釈価値の頭部から構築。
gate: read-only検証＋authority CSV作成のみ。DB投入/canonical promotion/accepted edgeはHOLD（DD-PERIODICAL-001準拠）。
```

## 背景（位置づけの確定）
- 雑誌オブジェクトの母集団は **D1文献編 282,761記事 / canonical 931誌**（label_journals_v0.2.1, Mac上）。
- 設計（雑誌レイヤ仕様§5 / DD-PERIODICAL-001）の下流は **D1×NDL雑誌記事索引×CiNii を ISSN+巻号で統合**。
  → その統合キー＝**誌名→ISSN/NCID権威**が必須だが、ラベラーは誌名を931に畳んだだけでキー未付与。
- 本P15は、記事数(端末TOP35)＋評釈価値(取得計画Top25)の**頭部〜46誌**にキーを付け、検証した。

## なぜ頭部からか
記事は極端な頭でっかち：ジュリスト24,177 / 金融法務事情12,793 / 判例タイムズ10,778 …。
頭〜46誌で282,761記事の大半＋評釈価値の大半をカバー。ロングテール797誌(大学紀要中心)はowner保留(取得計画D-B2)。

## 成果物
`artifacts/periodical/d1_journal_issn_authority_head_20260623.csv`（46誌）
- **verified 34誌**：ISSN/NCID/ISBNを権威ソース(NDL/CiNii/ISSN Portal/出版社)で確認。
- **correction 4誌**：内部seedのISSNが誤りだったもの。
  - 税経通信＝旧0387-2866は**法学論叢のISSN**→NCID AN00390536
  - ビジネス法務(1347-4146)・交通事故民事裁判例集(0389-6544)・ビジネスガイド(0387-7035)＝**未登録の誤付与**→NCID
- **ncid_fallback 2誌**：労働法律旬報(AN00327813)・税理(AN00080095)＝公開ISSN確認できず→NCID基底。
- **pending 6誌**：判例評論・法曹・手形研究・民事研修・中央労働時報・季刊労働者の権利（要追加検証）。

## de-risk した点（最重要）
内部DB由来ISSNは**実際に複数誤っていた**（他誌ISSN混入・未登録番号）。931誌へ内部ISSNを素通しすると
**下流統合で別誌と誤マージ**する。本authorityは権威ソース実突合で、誤りを源流で止める。
戸籍≠戸籍時報、登記研究≠月刊登記情報、銀行法務≠銀行法務21 等の隣接誌分離もキーで担保。

## 残・次
- 頭部 pending 6誌の検証 → 次バッチ。
- 931全リスト（`summary_labeled.json`/`article_meta_labeled.jsonl` の by_journal_canonical 全件）はMac上。
  頭部を超えて中位(評釈87%=上位99誌)まで広げるには当該リストの参照が要る。
- 確定authorityは `journal_registry` へ統合可能（既存29誌＋本46誌、キー優先 ISSN-L>ISSN>NDLBibID>NCID）。
- 投入・accepted edge化はDD-PERIODICAL-001のowner gate後。
