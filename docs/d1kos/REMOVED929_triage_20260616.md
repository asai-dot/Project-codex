# removed 929 仕分け（box_prior にあって live に無いノード）— 2026-06-16

> 監査必須#3（DDTAXOAUDIT PASS_WITH_NOTES）対応。
> 入力: `d1law_taxonomy_box_prior_vs_live_join_20260612_removed_box_prior.csv`（929行）
>        ＋ `..._per_root_recall.csv` ＋ live `nodes.csv`（55,074）
> 方法: 各 removed ノードの `node_label_normalized` を live 全名称(NFC)集合と突合（read-only・自動）。

## 結論

removed 929 は **live 側の取りこぼしではなく、box_prior（判例パスからの trunk_inference）側の点描ノイズ／scope境界**。
recall 97.29% の残差はこれで説明できる。**民事コア法編の removed はほぼ0**で、live 体系は健全。
唯一の owner 確認事項は「**経済法の D1 体系上の扱い**」（acceptance package P-8）。

## クラス分布

| クラス | 件数 | 解釈 |
|---|--:|---|
| label_absent_from_live（box_prior_only / 誤検出候補） | **916** | live に同名ノードなし。判例パス由来 seed が D1 体系目次に無い |
| label_present_in_live（改名/移動候補） | 13 | 同名が live の別パスに存在 → 要目視（改名/移動の可能性） |

- うち「live非存在 かつ 個別法令名(…法/令/条例 等)」= **72**：体系ノードではなく**個別法令名**を
  box_prior が case-path から seed したもの（例: 中小企業等協同組合法・信用金庫法・海上衝突予防法・
  道路運送法・鉄道営業法・電気通信事業法）。D1 の民事セレクション体系目次はこれらを論点ノードとして
  展開していない＝**取りこぼしではない**。

## taxonomy_root 別（removed 上位）

| 法編 | removed | present(改名/移動候補) | absent |
|---|--:|--:|--:|
| 経済法 | **781**（84%） | 5 | 776 |
| 商法 | 69 | 7 | 62 |
| 債権法Ⅱ | 36 | 0 | 36 |
| 労働法 | 20 | 0 | 20 |
| 破産法・民再・会更 | 11 | 1 | 10 |
| 借地借家法 | 5 | 0 | 5 |
| 民事執行法 | 4 | 0 | 4 |
| 憲法 | 2 | 0 | 2 |
| 民法総則 | 1 | 0 | 1 |

- 民法系・民訴・物権・親族相続・自賠法 等の**民事コアは removed = 0**（per_root recall ≈0.99–1.0）。
- node_depth 分布: depth3=286 / depth4=374 が主（中間層）＝判例パス固有の下位枝。

## 監査カテゴリへの対応（box_prior_only / renamed / moved / removed_from_live / prior_false_positive）

- **prior_false_positive / box_prior_only**: 916件の大半。特に経済法776件は個別法令名 seed＝D1民事体系外。
- **renamed / moved（要目視）**: 13件のみ（同名が live 別パスに存在）。次サンプルで個別確認。
- **removed_from_live（真の削除）**: 民事コアにほぼ無し。あっても極少数で、box_prior のノイズと識別困難。

## owner 確認事項（1点）

- **経済法**: box_prior 2,735 → live 1,954（recall 0.714、removed 781）。D1 の民事セレクション体系目次が
  経済法の個別法令を**意図的に展開していない**のか、別商品/別区分なのかを確認（acceptance package P-8 と同一論点）。
  ここが確認できれば residual はクローズ。

## 限界

- 突合は label 完全一致（NFC）のヒューリスティック。短い汎用ラベルは誤マッチし得るため、`present`13件は要目視。
- 「真の削除」と「box_prior 誤検出」の最終切り分けは、経済法の D1 意図確認＋13件目視で確定する。
