# owner 決定記録: homograph genuine_split 2件 20260625

> doc_kind: 決定記録（owner承認済） / author: Claude / date: 2026-06-25 / owner: 浅井
> 親: 08_HOMOGRAPH_FRAGMENTATION_FINDINGS / tools/vocab_hub/homograph_review.py
> 経緯: homograph 44→defrag→genuine_split 3件 → owner が下記2件を確定（3件目=将来の給付の訴えは merge）

## 決定

| # | 見出し(読み) | 判定 | 根拠 | 適用 |
|---|---|---|---|---|
| 1 | 参議（さんぎ） | **split維持** | A=明治の官職「参議」/ B=家庭裁判所の参与役。別概念で同読み = 真の同綴異義 | 2 hub 維持（既定動作）。B側ラベルが「参与員」相当か要スポット確認 |
| 2 | 重懲役（じゅうちょうえき） | **B採用・A是正** | A「定役に服さ**ない**・有期**禁錮**」は重懲役の定義として誤り（隣項「重禁錮」の混入疑い）。B「定役に服**する**・有期**懲役**」が正 | B を重懲役の定義に確定。A は重禁錮への再帰属 or 除去（staging是正・DD-DICT-006） |
| - | 将来の給付の訴え | merge | A/B 同概念（民訴135の将来給付）。分類器が「見出し語を本文に再掲しない」ため split に誤分類しただけ | 1 hub に統合 |

## 適用方針

- **参議**: コード上は既に split（homograph_split）。追加対応なし。B側の見出し妥当性のみ再OCR時に確認。
- **重懲役**: staging 是正案件。A行を「重禁錮」候補として切り出す or 除去。実適用は DD-DICT-006/staging ゲート。
  P0 dry-run 上は B を anchor とする（A の定義重なりが低いので現状でも別 hub、B 側が canonical 候補）。
- **将来の給付の訴え**: defrag の merge_candidate 判定で1 hub に統合済み相当。owner 承認で確定。

## ゲート

決定記録のみ。重懲役の staging 是正・再OCR は別ゲート（DD-DICT-006 / owner GO）。
