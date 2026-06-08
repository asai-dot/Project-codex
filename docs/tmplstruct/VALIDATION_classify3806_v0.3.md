# VALIDATION — classify3806 v0.3 独立検証（番頭・横展開ゲート）

- **対象**: ワーカー全3,806件分類（Box `material_queue/20260608_classify3806`）。
- **方法**: validation_set 200件（4軸層化189bucket）の独立レビュー＋全件jsonlへの標的クエリ。
- **結論**: **VALIDATION PASS_WITH_NOTES**。OCR無料triage分類は横展開可。ただし docx月30枠の確定前に**決定論パッチ2つ（v0.3.1）**を当てて無料再分類すること。

## 1. 定量結果
| 指標 | 値 | 評価 |
|---|---|---|
| archetype分布 | A656 / B478 / C145 / D1291 / E1236 | A→D移動は主に「契約title・0条」由来（下記§2） |
| **「条検出ありなのにD」** | **0件** | ◎ 構造を無視する誤分類なし |
| docx_required | 274（うちA273・E1） | ◎ 枠は契約・規程に正しく集中 |
| confidence<0.5 | 492 (12.9%) | 妥当 |
| human_review_required | 40 (1.05%) | 妥当（英文契約・no_signalを正しく退避） |
| requires_shape_review | 162 (4.3%) | 妥当 |
| coverage | validation 200件/189bucket・全archetype/ subtype出現 | 代表性あり |

**precision（番頭推定）**: 上位分類で概ね **≥92%**。誤りは A↔D 契約境界に集中、他は低stakes（B↔D の1ページslot tie 等は requires_shape_review で適切に退避）。

## 2. 唯一の実害＝契約のD誤送（限定的だが高インパクト）
- 契約系(formType契約468＋title一致) のうち **131件がD**。内 **125件=0条**。
- うち `就任承諾書27/同意書18/誓約書8/承諾書/契約解除通知書7…` は**短い承諾・通知文＝Dで妥当**（誤りでない）。
- **真の誤送＝12件**: 秘密保持契約書(4163)/雇用契約書(3852)/転籍協定書(3884)/退職合意書(3936)/相殺合意書(3825)/弁済期限等変更合意書(14969)/合意書(3918)/Amendment Agreement(7968,9363)/Termination Agreement(9364,7981)/Affidavit(5311)。
- これらは **0条＝OCRが条を落としただけの本物の契約**。低docx優先(0.5)・未フラグ＝**忠実復元を取り逃す**。原因: 「OCRに第N条が無い」を D 確定の根拠にしたが、**OCRは契約の条を落とす**（v0.2 §0 実証）ため、契約titleでの0条は信用できない。

## 3. 修正（v0.3.1・決定論・無料再分類で適用）
- **F1 契約title ガード**: title が `契約書|協定書|合意書|Agreement|Contract`（ただし `承諾|同意|誓約|通知|解除|解約|申入|連絡|説明` を除外）に一致 ∧ archetype=D ∧ clause_count=0 → **archetype=A・source_fidelity=docx_required・要 docx ground-truth**（OCRの0条を信用しない）。対象≈12＋将来分。
- **F2 docx queue の重複除去**: docx_priority top に `定款【雛形】` 等の同題複製が多数（top20の過半）。**同一/近似titleは代表1〜2件に畳んでから月30枠を消費**（複製10件にクォータを使わない）。
- **F3（任意・低優先）**: `同意書/承諾書/誓約書` 群は D でなく「短文slot(B)」または独立 subtype 候補。stakes低のため次版で検討可。

## 4. 検収観点（ワーカー5問）への回答
1. E subtype形状判定: **採用**。議事録→E2/記載例→E3/チェックリスト・公告→E4/フォーム→E1 が妥当に分離。
2. ocr_gap誘導: **採用**。条抜けが docx_required へ正しく誘導（D側にclause検出ゼロ＝過誘導なし）。
3. docx top20: **修正採用**（F2 重複除去後に確定）。契約559の機械的並びは回避できている（NOTE7達成）。
4. validation coverage: **採用**。4軸189bucketで境界を踏めている。
5. category_state_flag: **採用**。「その他」捨て場は category_uncertain/requires_shape_review に置換され機能。

## 5. 次工程（ゲート開放条件）
1. **F1+F2 を v0.3.1 として無料再分類**（ワーカー・クォータ0）→ `classification_v0.3.1.jsonl` ＋ **deduped `docx_queue.csv`**。
2. 番頭が docx_queue top を確認 → **owner ratify** で docx月30枠を上位から開始。
3. それまで docx取得・事務所PDF横展開は **HOLD**。
