# 読み（ふりがな）三点測量 → adjudication 成果（2026-06-02）

JLT(権威読み100%) × 有斐閣(99%) × 学陽(2%) の共有見出し語で読みを突合し、裁定。
`phases/reading_triangulate.py`（検出）→ `phases/reading_adjudicate.py`（裁定）。
生データ非改変・訂正は提案層（`auto_apply=false`）。片仮名↔平仮名は正規化（表記差を誤検出しない）。

## バケット
- **`*_confirmed.jsonl`（37件）**: 構造的誤り（欠落/挿入/置換/小書き）。権威JLT or 3源多数決で
  訂正方向を確定。内訳: 有斐閣33 / 学陽4。len_diff23 / substitution10 / small_kana4。
  例: 機関訴訟 そう**しょう**→そしょう、又は また**わ**→または、被疑者 ひ**きぎ**しゃ→ひぎしゃ、
  過誤納 かご**う**のう→かごのう、標識 ひょう**じ**しき→ひょうしき、選考[学陽]もせん→せんこう。
  ※要一瞥の競合読み: 図画 ずが/とが、競売 きょうばい/けいばい（JLTを正としたが両用あり）。
- **`*_review.jsonl`（48件）**: 純濁点差＝連濁の正当ゆれの可能性（保健所しょ/じょ 等）。
  JLT優先案は付すが自動確定しない。3源目（岡口辞書等）が入れば多数決で確定可。
- **`*_artifact.jsonl`（6件）**: 学陽の読み抽出欠け（truncation）。辞書誤りでない。

## 用途
有斐閣 all_entries.jsonl / 学陽 の reading フィールド訂正の提案リスト（人手確認後に適用）。

## 適用（2026-06-02）
- `reading_corrections_ledger_20260602.jsonl`：37件の統一台帳（target, before→after, confidence）。
  - **有斐閣33件＝パッチ**：canonical `all_entries.jsonl`(Box 2185088113728) の reading 訂正用。
    適用は owner 手順（reading フィールドを before→after、`confidence=verify` の2件=図画/競売 は要確認）。
  - **学陽4件＝適用済**：`data/gakuyo/gakuyo_all_entries.jsonl` に in-place 反映
    （`reading_orig` 保存・`reading_corrected:true`・git履歴で原状復帰可）。verify は保留。
- 生データの md/canonical は非改変。本台帳が唯一の適用仕様（監査可能）。
