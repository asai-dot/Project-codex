# VALIDATOR — restorable_profile 独立ゲート仕様（F-1 空虚ゲート置換）

- **目的**: GPT監査 ROLLOUT_MODIFY_REQUIRED §3 の要件＝「`restorable_profile_ok=True` のハードコード空虚ゲートを、**生成器と独立した実行証跡つきゲート**に置換」。
- **実装**: `loaders/validate_restorable_profile.py`（抽出器 `docx_extract`／分類器とは**別実装・別レビュー**）。
- **入力**: `<tid>.docx_struct.v021.json`（または最新struct）＋ `<tid>.restorable_profile.v021.json`。
- **出力**: `<tid>.profile_gate.json` ＋ batch 単位の `_GATE_SUMMARY.md`。
- **原則**: profile 側の自己申告（`restorable_profile_ok` 等）は**読まない**。struct/profile/正規化規則から独立再計算する。

## 正規化（全ゲート共通の前処理）
- `meta.normalized_text_policy` を読み、**推奨既定 = NFKC ＋ 括弧は全角に統一**。
- struct.paragraphs と profile.fixed_spans の双方へ同一規則を適用してから比較（F-2 無音0ヒット罠の回避）。
- 各 fixed_span の `normalized_text_hash` は本規則適用後の sha1。

## ゲート定義
```text
G1 fixed_spans_anchor_to_paragraphs
   全 fixed_spans が para_i を持ち、0 <= para_i < len(struct.paragraphs)。
   FAIL: anchor 欠落 or 範囲外が1件でもある。

G2 normalized_text_policy_match
   meta.normalized_text_policy が struct/profile で一致し、既知の許可値である。
   FAIL: 不一致 or 未宣言。

G3 no_orphan_fixed_span
   各 fixed_span の正規化テキストが struct.paragraphs[para_i] の正規化テキストに包含される。
   FAIL: 接地しない(=孤立) fixed_span が1件以上。

G4 non_empty_profile
   archetype が B/E フォーム系（source_fidelity=ocr_sufficient 等の記入フォーム）でない限り、
   fixed_spans と slots の合計が非空。
   FAIL: A/C/D 等で fixed_spans+slots が空。

G5 slot_not_clause_caption
   slot.text が fixed_spans（条見出しキャプション）と重複しない。
   括弧見出し（例「（合併の方法）」）が blank_lined/その他 slot に混入していない。
   FAIL: 条キャプションと一致する slot が存在。

G6 party_alias_defined_term_domain
   kind=party_alias は人格・当事者語（甲/乙/丙/当社/相手方/委託者/受託者/賃貸人/賃借人/売主/買主/会社/従業員 等）が
   定義対象の直前句・同一文に存在する場合のみ。該当しない／曖昧は defined_term。
   FAIL: 当事者語の裏付けなく party_alias になっている。

G7 source_content_type_valid
   meta.source_zip_valid=true かつ source_content_type が docx 系（application/vnd.openxmlformats-...wordprocessingml...）。
   FAIL: themeManager+xml 等 Word以外、または zip 検証未通過。
```

## 出力スキーマ `<tid>.profile_gate.json`
```jsonc
{
  "tid": "3249",
  "validator_version": "0.3.1",
  "normalized_text_policy": "NFKC; brackets=fullwidth",
  "gates": {
    "G1": {"pass": true,  "n_checked": 17, "n_fail": 0, "evidence": []},
    "G2": {"pass": true},
    "G3": {"pass": true,  "n_orphan": 0},
    "G4": {"pass": true,  "archetype": "A", "fixed": 17, "slots": 4},
    "G5": {"pass": true,  "n_caption_slots": 0},
    "G6": {"pass": true,  "n_party_alias": 2, "n_unsupported": 0},
    "G7": {"pass": true,  "source_content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "zip_valid": true}
  },
  "overall_pass": true,
  "blocking_failures": []
}
```

## 合否規則
- `overall_pass = G1∧G2∧G3∧G4∧G5∧G7`（G6 は warning 級でも可だが、unsupported>0 は warning 計上）。
- batch の rollout は **全 profile が overall_pass、かつ G6 warning が許容閾値内**で初めて Phase A closeout を満たす。
- `_GATE_SUMMARY.md` に: 件数、ゲート別 fail 内訳、blocking tid 一覧、G6 warning 一覧を出す。

## 既取得21 profile での初回実行（P0-4）
- batch1 v0.2.1 の21 profile に対し validator を走らせ、`material_queue/.../profile_gate/` へ証跡を出す。
- ここで G7 は batch1 に content-type 記録が無い場合 `unknown` を許容（P0-1 実装後の batch2 から必須化）。
