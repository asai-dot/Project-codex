# P4（先行）: ISSN seed の達成可能リフト dry-compute — read-only

```yaml
artifact: P4_maxlift_drycompute
wo: WO-PERIODICAL-ISSN-SEED-EXPANSION (v0.2)
generated_at: 2026-06-19 JST
source: staging_periodical.issue_stage（read-only / SET TRANSACTION READ ONLY / mutation 0）
method: ISSN値に依存しない構造計算。「seed未投入の実在誌で issue_no(通巻) が有る号 = ISSNを入れれば canonical 化可能」「issue_no 欠 = ISSNを入れても不可」を分離。
note: 実ISSNの確定(confirmed)は別。本計算は「ISSNが入った時に最大どれだけ効くか」の上限。
```

## 結論（前提が覆った）

| 指標 | 値 |
|---|--:|
| seed未投入の実在誌・号数 | 810 |
| **ISSN seedで canonical 化できる（issue_no 有）** | **275** |
| **ISSNを入れても残る（issue_no 欠 → 通巻抽出が必要）** | **535** |
| └ うち jcaジャーナル + 税経通信 | **422** |

> **当初の「上位~12誌で約94%(≈768号)」は誤り**だった。raw号数で数えていたため。
> 実際は ISSN seed の効果は **275号**にとどまる。最大ターゲットだった
> **jcaジャーナル(216中214) と 税経通信(208のほぼ全部) は issue_no(通巻) が空**で、
> ISSN を確定しても `issn:{ISSN}#{通巻}` を生成できない＝canonical 化しない。

## 含意（ボトルネックの再定義）

雑誌号同定の残ボトルネックは**2層に分かれる**:

1. **ISSN不足（275号）** … 戸籍58 / 交通事故民事裁判例集50 / 季刊刑事弁護40 / 法律時報e-book36 / 労働判例33 / 金融法務事情15 / 労働経済判例速報10 / 法学教室6 …
   → これらは issue_no を持つので、**ISSN seed さえ入れば canonical 化する**。ISSN seed 拡張の正味の対象はこの集合（約275号）。
2. **通巻(issue_no)不足（535号、うち jca+税経通信 で422）** … ISSN は無関係。
   → ソース側メタ（lionbolt / bencom / legallib の生データ）から**巻号(通巻)を抽出する別ワーク**が必要。ここを ISSN seed で解こうとするのは手戻り。

## 推奨（計画の補正）

- **トラックA（ISSN seed・約275号）**: 対象を「issue_no 有の seedless 実在誌」に限定。jca/税経通信はトラックAから外す（ISSNを当てても無駄）。
- **トラックB（通巻抽出・約535号）**: jca/税経通信を筆頭に、ソース生データからの issue_no 復元を別WOで設計。これが号同定の次の主レバー。
- canonical 見込み: 1,923 →（トラックA成功時）約 **2,198**（68%→約77%）。残りはトラックB（通巻抽出）と希少誌・年版除外分。

## 制約メモ（confirmed ISSN の取得経路）

本リモート環境は NDL Search / ISSN Portal / CiNii への WebFetch がいずれも **403** で遮断。
よって confirmed ISSN（ndl_bib_id 根拠付き）の取得は **(a) Mac worker の NDL gz パース** か **(b) owner 手動確認** が必要。
本P4は ISSN値に依存しない構造計算のみで、捏造ISSNは1件も生成していない。
