# PoC結果: L3(機械可読な深い構造)で「コーパス横断議論」は成立した

date: 2026-06-11 / 方針: PoC先行→設計。owner指摘「機械可読な構造で大量書式を議論したい」の検証。
対象: 自炊2契約をL3手エンコード（`poc_L3/*.L3.json`）→ `tools/formreason_poc.py` で横断クエリ。

## 何を実証したか（＝L0再現ではなく、AIが構造を理解した証）
13条項/2契約に対し、機械が以下を**自動生成**した（人手のOCR再現では出てこない）:

- **Q1 機能カバレッジ行列**: どの書式がどの機能(payment/ip_assignment/damages…)を持つか。
- **Q2 同機能の横断比較(payment)**: 2契約の支払条項を属性で並置 →
  | 属性 | 役務提供型 | 製造委託型 |
  |---|---|---|
  | 支払時期 | 月末締め→翌月末払い | 個別契約の支払期日 |
  | 遅延損害金率(%/年) | **規定なし** | **14.6** |
  | 振込手数料 | 委託者 | 委託者 |
  → 「遅延損害金の定めが一方に無い」を**機械が指摘**できる＝議論の素材。
- **Q3 義務のobligor別集計**: **受託者14 vs 委託者2** → 「義務が受託者に著しく偏る」という*契約の性質*を機械が surface。
- **Q4 意味型slotの分布**: doc4/date2/amount_jpy2/ref_individual_contract2/bank_account1…
- **Q5 ギャップ検出**: 製造委託は(捕捉範囲で)damages・ip_assignmentを欠く＝**標準条項の欠落**を機械が指摘。

→ **「大量書式を機械可読な構造で持ち、横断で比較・議論する」は成立する**ことを小規模で確認。
L0(文字再現)は副産物。**価値はこのL3構造**にある、というownerの主張が実証された。

## PoCで“立ち上がった”語彙（＝設計の入力）
- **条項機能(emergent 12)**: purpose / framework_individual_contract / payment / bailment_return / supplied_material / amendment / performance / completion_report / report / ip_assignment / ip_noninfringement / damages。
  → 本設計では正準オントロジー化（＋termination/term/confidentiality/governing_law/jurisdiction/force_majeure/antisocial_forces… を補完）。
- **機能別 属性スキーマ** が比較の鍵: 例 payment = {支払時期, 支払方法, 遅延損害金率_pct_pa, 消費税, 振込手数料負担}。
  → 機能ごとに「比較可能キー＋型／単位」を定義する必要。
- **意味型slot語彙**: date / amount_jpy / enum / doc / ref_attachment / ref_individual_contract / bank_account …。
- **義務モデル** {obligor(role), act}: obligor偏在の分析に有効。actの正規化(動詞)が次段。
- **archetype→期待機能プロファイル**: ギャップ検出には「業務委託契約が本来持つべき機能集合」が要る。

## 本設計(次)に落とすもの
1. **条項機能オントロジー v0.1**（id＋ラベル＋同義語＋上位カテゴリ）。
2. **機能別 比較属性スキーマ**（payment/damages/ip_assignment… の comparable keys＋型/単位）。
3. **意味型slot 型システム**（structure_profileのslotと統合）。
4. **archetype別 期待機能テンプレ**（完全性スコア／ギャップ検出の基準）。
5. **格納**: PoCはJSONLで十分。コーパス規模では toc_nodes 隣接テーブル（function/attributes を列+jsonb）＋ reasoner を SQL/view 化。

## 限界(正直に)
- 2契約・手エンコードのPoC。機能タグ/属性は人(=私)が付けた＝**自動抽出(vision→L3)の精度は未検証**。
- 捕捉は各契約の一部条項のみ（全条ではない）。
- だが「**L3があれば機械議論が成立する**」という仮説は支持された。次は (a) オントロジー設計 (b) vision→L3自動抽出の精度検証。
