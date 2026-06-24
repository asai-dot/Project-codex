# 既存 e2e（製造委託）を DD-FORMOBJ-002 v0.2 へ載せ替えた結果

date: 2026-06-15 / 監査§13-2 の実施。`seizo_kihon.formobj.v2.json` ＋ 共通ツール `check_mandatory_requisites.py`。

## やったこと
旧 e2e（`seizo_kihon.e2e.json`：文献witnessの読取に寄った構造）を、v0.2 の**独立書式オブジェクト＋4層＋記載事項細分**に作り直した。

## 1. 4層分離が効いた
- **form_object**：製造委託基本契約書（recorded_act=製造の継続的委託の基本条件合意 / document_role=契約書 / practice_domain=業務委託(製造委託) / forum=私人間）。
- **form_variant**：製造委託型(標準) / PB商品型 / OEM型 ＝ 同一 form_object 下の型違い。
- **form_witness**：5冊＋αを観測点として列挙（次項）。
- **filled_instance**：扱わない（業務データ分離）。

## 2. ★witness の版検証が今日の事故を捕まえた（gate_witness_edition_verified）
| witness | 版 | verified_status |
|---|---|---|
| 近藤〈第2版〉 | 第2版2022 | **edition_verified**（自炊scanとbencom TOCが同版一致・読取済） |
| 滝川〔全訂版〕 | 全訂版2022 | toc_only（本文OCR源なし） |
| **滝川 自炊512MB** | **条項別記載例集（全訂版と別構成）** | **EDITION_MISMATCH_FLAGGED** ← 本日の誤接続。タイトル一致で全訂版TOCに当てて崩壊。この witness は『製造委託基本契約書 form_object』としては**不採用**（別 form_object 群の witness）。 |
| 長谷川〈第2版〉 | 第2版 | toc_only_coarse |
| 波光・横田 | — | toc_only_coarse |
→ **タイトル一致のみの witness リンクを禁止**し、版不一致を構造的に弾く＝本日の事故の再発防止が機構として働く。

## 3. 記載事項の細分が、私契約と法定書式を正しく区別（監査必須#4）
同一ツールで両方を処理:
- **製造委託（私契約）**：statute_required は無し。
  - 対価(製造代金)・委託対象 ＝ **validity_required → 🛑無効**（essentialia。欠けると不成立）
  - 検収 ＝ **enforceability_required → △立証弱**（契約不適合の主張立証が弱る）
  - 再委託・損害賠償・知財・管轄 ＝ **optional_design**（favors付き）／秘密保持・反社 ＝ advisable
- **定款（法定）**：商号等 ＝ statute_required → 🛑無効／発行可能株式総数 ＝ validity_required → ⚠登記不可。
→ **「欠落＝一律瑕疵」にせず、無効／登記不可／立証弱／注意 を出し分け**。法定書式（forum=法務局）と私契約（forum=私人間）を同じ機構で扱えた。

## 4. 設計知識（押し引き）は advised_by に source_type/authority_weight 付きで保持
再委託：`liability_scope` 軸で「選定・監督のみに限定→受託者有利」（source_type=commentary, authority_weight=treatise, 旧民法105条1項削除の caveat）。判例由来・事務所ノウハウ由来とは混ぜない（監査should）。

## 結論
- 旧 e2e は v0.2 の独立オブジェクト観に**載せ替え完了**。文献witnessは `witnessed_in` の多源リンクに格下げ、書式同一性は form_object 側に移った。
- **今日の誤接続が gate で弾かれる**ことを実データで確認。
- **法定／私契約を1つの記載事項モデルで出し分け**られることを確認（定款＝法定 vs 製造委託＝私契約）。
- HOLD：DDL／DB／canonical発番／filled_instance。
