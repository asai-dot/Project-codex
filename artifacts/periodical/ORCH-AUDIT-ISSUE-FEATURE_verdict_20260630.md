# ORCH-AUDIT-ISSUE-FEATURE — head 検収 verdict（特集号メタ 精度）

- 判定: **PASS（高精度・本採用推奨）/ 軽微NOTES**
- 実施: head 直接 read-only 検証 / 2026-06-30
- 対象: `issue_feature_v0.1.csv`（8,582 号 / title_extract）＋ `issue_feature_v0.1.audit.json`

---

## 1. 結果

| 指標 | 値 |
|---|---|
| feature 付き号 | 8,582（confidence medium 5,673 / low 2,909）|
| **junk feature title**（≤3字）| **38（0.4%）** ／ 汎用ラベル **0** |
| **1号のみの feature（単発特集）** | distinct の **97.1%**（7,892/8,130）|
| 複数号に跨る feature（≥5号）| 20 distinct のみ |
| ambiguous（複数候補→最頻採用）| 391（self-flag・audit.json に候補併記）|

## 2. 評価

- **特集名抽出は高精度**。汎用ラベル混入ゼロ・短title 0.4% のみ。SERIES/AUTHOR と同様クリーン。
- 複数号 feature（独占禁止法違反事件の動向 29号 / 判例回顧と展望 / 改正税法詳解 12号 等）は
  **正当な恒例年次特集**＝誤りでない。
- 曖昧号（391, 4.6%）と低 confidence（34%）を**適切に自己フラグ**しており、下流が信頼度で扱える。

## 3. 推奨（軽微・低手戻り）

1. **短title 38件（'担保'/'時効'/'会社法' 等）** は分野名断片の可能性。`is_field_fragment` で注意フラグ化（誤用防止・任意）。
2. 「最高裁判決」「回顧と展望」等のやや汎用な複数号 feature（数件）は owner 目視で 特集/連載 を確定（任意）。
3. **本採用**（特集号メタ v0.1 を accepted）— owner GO。

## 4. caveat（honest_report）

- head 単独ヒューリスティック（title 長・出現号数で品質点検）。完全 ground-truth ではない。
- low confidence 2,909件は抽出側が既に不確実と申告（精度ではなく確信度の問題）。

## 5. HOLD

本採用昇格・フラグ実装・DB/canonical 反映は owner GO 必須。
