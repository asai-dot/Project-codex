# structure_profile v0.3 — 法律書式「再復元」確定設計（docx実証済）

- **status**: docx batch1（21件）で実証。**restorable_profile_v0.2.1 = VALIDATED（PASS_WITH_FINDINGS）**。本v0.3で設計確定 → GPT再監査ゲート → 事務所PDF横展開（production rollout）。
- **supersedes**: structure_profile_v0.2.md / archetype_classifier_spec_v0.3.md（A–E＋subtype, source_fidelity段階値, formType二層は継承）。
- **実証根拠**: `material_queue/20260611_docx_batch1_v0.2.1`（_REEXTRACT_DIFF / _per_template_v021 / _BANTOU_REVIEW）。

## 1. 確定モデル（実証で固定）
- **archetype A–E＋E subtype**（E1表/E2議事録/E3記載例/E4チェックリスト）。**形状判定**（titleでなく）。
- **復元単位 = restorable_profile**。**復元の原文ソースは `docx_struct.paragraphs`**。`fixed_spans` は**見出しラベルのみ**保持（復元本文の所在を示す索引）＝F-3訂正。
- **source_fidelity**: `docx_required`（A条文契約/規程・英文・OCR欠落）/ `ocr_slot_ok` / `ocr_search_only` / `ocr_sufficient`（B/C/E1の記入フォーム＝docx不要）/ `human_review_required`。
- **formType二層**: `category_id_lib`(prior) × `archetype`(復元戦略)。「その他」は状態フラグ。

## 2. 実証された復元品質（batch1・21件）
- **条見出しキャプション回収 216**（OCRは番号のみ・全欠落だった）。例: 3249 全17条をキャプション込みで fixed_spans 化。
- **英文/翻訳契約の条文回収（C修正）**: 11318 0→28 / 11325 0→27 / 11327 0→42（Article型・表組検出追加）。
- **slot精度（B修正）**: 括弧見出しの誤slot化を排除。3249 slots 30→4、4262就業規則 108→15、blank_lined比率 全件0.0。
- **F1差し戻し（D修正）**: 3852雇用契約書 A/docx_required → **B/ocr_sufficient**（docxで0条0表＝記入フォーム）。
- 全21 profile の fixed_spans が docx_struct.paragraphs に接地（孤立0・独立再計算で確認）。

## 3. restorable_profile スキーマ（確定）
```jsonc
{ template_id, archetype, subtype, formType_label,
  fixed_spans:[{text, role}],                 // 見出しラベルのみ（索引）。復元本文は docx_struct.paragraphs
  slots:[{name, kind, pattern, para_i, required, normalization, display_format}],
  repeat_groups:[{name, unit, of}],
  signature_block?:{date_slot, parties:[{role,name_slot,address_slot,seal}], para_range, samples},
  source_fidelity, confidence,
  meta:{canonical_image_ref, ocr_text_hash, docx_file_ref, docx_hash,
        ocr_parser_version, profile_version, slot_evidence, layout_profile,
        validation_status, sample_bucket} }
```
- **slot.kind**（実証語彙）: party / **party_alias** / **defined_term** / person_name / address / date / money / rate / authority / blank_lined / table_cell。

## 4. v0.3 で直す（番頭レビュー F-1/F-2 ＋ party_alias）
- **F-1 空虚ゲートの撤廃（closeoutブロッカー）**: v0.2.1抽出器の `restorable_profile_ok=True` はハードコード（非検査）。v0.3は**実検査に置換**＝「fixed_spans 全件が struct.paragraphs に正規化後接地 ∧ (B系除き) fixed+slots 非空」。**ゲートは生成器と独立に再計算可能であること**を要件化（DD自己申告不信の原則と同型）。
- **F-2 正規化の固定**: 現状 profile は丸括弧を半角化、struct は全角のまま → 下流 join が無音0ヒットの罠。**v0.3で正規化方針を1行明文化（推奨: NFKC・括弧は全角に統一）し、profile/struct 双方に適用**。
- **party_alias を採用、ただし2種に分割**（消えた「（以下「X」という）」slotの復活）:
  - `party_alias`（当事者の命名: 甲/乙/会社/在宅勤務者）
  - `defined_term`（目的物・概念・法令略称: 本件建物/本ペット/労基法）
  - pattern `（以下[「『][^」』]+[」』]という）`＋変種（「以下単に」「という。）」）。記録: alias文字列/定義para_i/被参照回数。判別は定義対象の直前句（人格 vs 物・概念・法令）で機械判定、曖昧は `defined_term` に倒す。**B/C/Dパッチと非干渉（4262で回帰試験）**。

## 5. クォータ運用（欠陥A・別パケット）
- batch1 で 6/30 が `themeManager+xml`＝Word以外DLで無駄打ち。**次月枠 batch2 前に、取得直後 content-type/zip 検証→不正は budget非カウント＋再取得 の フェッチャ修正**（別パケット起票予定）。6不正形式は次月枠で回収。

## 6. ロールアウト（GPTゲート後）
1. 本v0.3を `to_gpt` 投函 → GPT再監査（production rollout gate）。
2. PASS で: 欠陥A修正フェッチャ → 次月枠 batch2（docx_priority上位＋6再取得）。
3. restorable_profile を全docx_required対象へ拡張 → **事務所スキャンPDF書式へ同方式横展開**（画像→OCR triage→形状分類→高価値はdocx/手当て復元→restorable_profile→組織オブジェクト投入）。
4. 3852 の classification 反映（A→B）は **owner承認後**（破壊的変更）。
