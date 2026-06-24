# 短定義489 の正体: 75%が相互参照(資産)、真の再OCRは17件 20260625

> doc_kind: 実測記録（read-only） / author: Claude / date: 2026-06-25 / owner: 浅井
> 親: 06_DATA_QUALITY_AUDIT / 07_P0_5_SHORTDEF_TRIAGE / 08_HOMOGRAPH / tools/vocab_hub/short_def_triage.py
> 経緯: defrag後も残る短定義485を triage → 大半がOCR脱落でなく辞書の相互参照(see also)と判明

## 0. 結論（一行）

**「短定義489＝再OCRが必要な汚れ」は誤読だった。** defrag後485件を triage すると
**363件(75%)が相互参照(→X/「X」=see also)＝語彙ハブの別名/see_aliasリンク資産**。
真のOCR脱落(truncation)は **17件(3.5%)** のみ。短定義は品質問題ではなく、大半が活用すべき資産だった。

## 1. 実測（short_def_triage.py / defrag済 terms 15942）

| クラス | 件数 | 実体 | 扱い |
|---|---|---|---|
| **cross_reference** | **363 (75%)** | 矢印参照(共有持分`→持分`/外国債`⇨外債`/事務吏員`↳吏員`)・括弧参照(計理`「経理」`) | **別名/see_aliasリンク資産**。再OCR不要 |
| valid_short | 22 | 末尾完結の正規短定義(支払期日`満期。`/共同絶交`村八分。`) | そのまま load 可 |
| truncation | 17 (3.5%) | 空/句点のみ/1-2字未完結(`破``消``。`) | **真の再OCR候補(DD-DICT-006)** |
| other | 83 | 3字以上で末尾未完結(`共同海``中小事``犯罪の`) | 要目視(bare参照target + 末尾切れ混在) |

実データ20ケースで分類器検証(20/20一致)。

## 2. cross_reference は資産（P3 entity linking への入力）

辞書が明示的に持つ「○○を見よ」参照は、語彙オブジェクトでは**別名(alias)/see_also 関係**そのもの:
- `共有持分 → 持分`: 共有持分 は 持分 hub の別名/下位 → entity linking で 共有持分 を 持分 hub に解決可能。
- `計理 → 「経理」`: 表記揺れ/旧称 → 同一 hub の別 surface form。
- **DD-EL-001(legal WSD/entity linking)・DD-VOCAB-000 の別名解決に直接効く**。再OCRで「消す」のではなく
  `skos:related` / `alias_of` エッジとして**取り込む**のが正しい。

→ 提案: cross_reference 363 を「短定義 anchor」から外し、**参照エッジ candidate** として別レーンで構造化する
   (矢印先/括弧内の語を target headword として解決 → 同 scheme 内の hub に alias リンク)。

## 3. 品質監査の最終像（06→09 の収束）

| 当初の懸念(生カウント) | 実態(hub構築+triage実測) | 真の残作業 |
|---|---|---|
| 空定義 712 | 非tier1の参照行(seed除外が正) | 真の穴 3 hub |
| 読み欠落 2583 | reading補完4段で解消 | 0(統合は高品質キー) |
| homograph 44 | defragで44→3(staging断片化) | **owner判断2件**(参議/重懲役) |
| 短定義 489 | **75%が相互参照(資産)+正規短定義** | **再OCR 17件**(+other 83の一部) |

**大規模前処理は不要だった。** 真の残作業 = owner判断2件 + 再OCR ~17-50件 + cross_reference 363の構造化(資産化)。

## 4. ゲート

read-only。triage 分類とエッジ candidate の記録のみ。再OCR実行・alias エッジのDB投入は別ゲート
(DD-DICT-006 / canonical / owner GO)。short_def_triage.md / .jsonl は candidate 出力のみ。
