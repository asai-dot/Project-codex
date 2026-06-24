# homograph 44 の正体: staging 定義断片化（owner判断ではなく前処理）20260625

> doc_kind: 実測記録（read-only） / author: Claude / date: 2026-06-25 / owner: 浅井
> 親: 06_DATA_QUALITY_AUDIT_FINDINGS / 07_P0_5_SHORTDEF_TRIAGE_PLAN / tools/vocab_hub/homograph_review.py
> 経緯: homograph 44 の owner レビューパケットを作る → 44件の定義本体を精査 → 大半が genuine 多義でないと判明

## 0. 結論（一行）

**homograph 44 は owner 判断案件ではなかった。** 定義本体を読むと大半が staging の
**定義断片化アーティファクト**（1エントリが複数 term 行に割れ、続き/スタブ/空行が別 hub 化）。
defrag_terms.py で再結合/除去すると **homograph 44 → 3**（genuine_split のみ残存）。
genuine な真の owner 判断は **2件**（参議=別概念で split維持 / 重懲役=OCR取り違えで要修正）+
将来の給付の訴え1件（実は同概念=merge、保守バイアスで split側に出ただけ）。

**※ 当初仮説「同じ断片化が短定義489も水増し」は実測で外れた**: defrag後 短def 489→485(-4のみ)。
短定義489は homograph とは**別問題**（単一行で定義が元々短い = 末尾切れ/正規短定義/別parse）で、独自 triage が要る。

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

## 2.5 defrag_terms.py 実測 (2026-06-25)

クリーン term セット生成(read-only)→ build_hubs 前後比較:

| 指標 | before | after | 効果 |
|---|---|---|---|
| terms | 15985 | 15942 | 断片43行をクリーン(rejoin12/drop12/merge19/genuine5) |
| hubs | 13229 | 13188 | 重複統合で微減 |
| **homograph** | **44** | **3** | ✅ artifact再結合で解消、genuine_splitのみ残存 |
| 短def anchor | 489 | 485 | ❌ **-4のみ。仮説外れ** |
| 空def anchor | 6 | 3 | ✅ -3 |

## 3. 計画への影響（07 P0.5 の更新 / 実測反映）

- **homograph 44 → 3**: owner判断は実質2件（参議=split維持 / 重懲役=OCR修正）+将来=merge。defragで解決済み。
- **短定義489 は独立問題（実測で確定）**: defrag後 489→485。断片化とは無関係で、**単一行の元々短い定義**。
  → 07 §2 の短定義 triage を**そのまま独立に実施**する必要がある（末尾切れ再OCR / 正規短定義はそのまま / 別parse）。
  仮説「断片化と同根」は外れた。短定義は probe_quality --export の `*_short_def.jsonl` を直接 triage する。
- 推奨順（更新）:
  1. ✅ defrag_terms.py で homograph 解消（完了, read-only candidate）。
  2. owner: genuine_split 2件（参議/重懲役）を判断。
  3. 短定義489 を独立 triage（export→①末尾切れ②正規短定義③別parse）。
  4. clean subset（defrag済 + needs_preprocessing無し）で P1 へ。

## 4. ゲート

read-only。本 findings は分類・実測の記録。defrag の cleaned JSONL は candidate 出力のみ(DB書き込みなし)。
staging への実反映(generate_staging_v3 修正 or cleaned を正とする判断)・DB load は別ゲート。
