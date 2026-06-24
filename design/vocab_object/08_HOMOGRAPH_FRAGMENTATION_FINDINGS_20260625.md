# homograph 44 の正体: staging 定義断片化（owner判断ではなく前処理）20260625

> doc_kind: 実測記録（read-only） / author: Claude / date: 2026-06-25 / owner: 浅井
> 親: 06_DATA_QUALITY_AUDIT_FINDINGS / 07_P0_5_SHORTDEF_TRIAGE_PLAN / tools/vocab_hub/homograph_review.py
> 経緯: homograph 44 の owner レビューパケットを作る → 44件の定義本体を精査 → 大半が genuine 多義でないと判明

## 0. 結論（一行）

**homograph 44 は owner 判断案件ではなかった。** 定義本体を読むと大半が staging の
**定義断片化アーティファクト**（1エントリが複数 term 行に割れ、続き/スタブ/空行が別 hub 化）。
genuine な多義（要 owner 判断）は **重懲役(OCR矛盾疑い)・参議(別概念混入疑い)等ごく少数**のみ。
同じ断片化が **短定義489 の一部も水増し**している可能性が高い（断片＝短い）。

## 1. 自動分類（homograph_review.py / classify_pair）

44件の anchor(A)・split(B) 定義を素性で分類:

| クラス | 代表例 | 証拠 | 扱い |
|---|---|---|---|
| artifact_continuation | 会計, 苦情審査委員会, 審査会, 職業転換給付金, 医療, 物, 以外 | A が文途中で切れ B が続き（会計: 「…収支等を**規**」→「**定し**…」）| staging 再結合 |
| artifact_subitem | 規程(1→5), 休業補償(1→2), 選挙(→3), 店頭(1.→2), 評定 | B が番号サブ項目の続き | staging 再結合 |
| artifact_stub | 後(「後」(のち)), 災害補償(さいがい), 博士(はくし), 採捕(さいひ), 世帯(「世帯」(せい)), 適用(施行), 施行規程(規程), 交換公文(条約) | B が読み/相互参照の短い断片 | 除去 |
| artifact_empty | 施行法, 施行令, 施行 | B が「(定義なし)」 | 除去 |
| artifact_header | 資本取引(【1)】【2)】), 手当(【2）】) | B が見出し記号のみ | 除去 |
| artifact_list_marker | その1, その2 | 見出し自体がリストマーカー（語ではない）| 除去 |
| **genuine_candidate** | **重懲役, 会社, 会社更生法, 少年院/審判/法, 民法 等** | A/B 双方が完結した別定義 | **owner判断** |

> 注: genuine_candidate には「同概念の言い換え（会社更生法・少年法等＝merge妥当）」も混じる。
> 真に split 維持すべき別概念は **重懲役(OCR矛盾)・参議(別概念混入)** 級のごく少数。
> 分類は保守的（曖昧は genuine 側に残し owner が見る）。実データ14ケースで検証(14/14一致)。

## 2. なぜ起きたか（メカニズム）

有斐閣 staging(generate_staging_v3) で、**1つの辞書見出しが複数の term 行に分割**されている。
辞書定義が「①②③」の多義・複数段落・相互参照を含むとき、その各片が別 term（同 normalized_pref + 同 reading）
になり、定義重なりが低いため build_hubs が homograph_split する。**hub構築のバグではなく入力データの断片化**。

## 3. 計画への影響（07 P0.5 の更新）

- **homograph 44 を owner に投げない**。genuine 数件だけ owner、残りは staging 前処理で消す。
- **短定義489 の再測が要る**: 断片化 artifact を再結合/除去すると短定義も減るはず。
  → 短定義 triage（07 §2）の「③parse/結合ミス」がこの断片化と同根。先に断片化を解けば489も縮む。
- 推奨順:
  1. staging 断片再結合スクリプト（同 scheme+pref+reading で continuation/subitem を連結、stub/empty/header/list_marker を除去）を read-only 生成 → 効果測定。
  2. 再測した homograph(genuine のみ) と 短定義(真の末尾切れのみ) で owner パケットを作る。
  3. clean subset で P1 へ。

## 4. ゲート

read-only。本 findings は分類結果の記録。staging 再結合スクリプトの実適用・DB load は別ゲート。
homograph_review.py / .jsonl は candidate 出力のみ（DB書き込みなし）。
