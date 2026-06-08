# archetype_classifier_spec v0.3 — 全3,806件 無料OCR形状分類（GPT v0.2 NOTES反映）

- **status**: 提案（v0.3 spec）。GPT v0.2監査 `DESIGN_PASS_WITH_NOTES`（`from_gpt/20260608_tmplstruct_v0.2_DESIGN_RESULT.md`）の required_notes を実装仕様化。
- **位置づけ**: production化ではない。**無料OCRで全件triage→層化検証**まで。docx月30枠は本spec完了後に `docx_priority_score` 上位から。
- **正本依存**: archetype定義は `structure_profile_v0.2.md` の §1。本specはそれに NOTES の差分を足す。

## 1. archetype（top-level A–E は維持）＋ E subtype（NOTE1）
| archetype | subtype | 例 | docx優先 |
|---|---|---|---|
| A clause_contract | — | 契約/定款/規程/遺言(条文型) | 高 |
| B header_petition | — | 申立/申請 | 中（slot復元はOCR可） |
| C keyvalue_filing | — | 登記申請/届出 | 中 |
| D prose_notice | — | 通知/催告/内容証明 | 低〜中 |
| E table_or_record | **E1_table_form** | 申請書フォーム/明細表 | **高** |
| | **E2_minutes_record** | 議事録/記載例(再生成価値あり) | **高** |
| | **E3_example_only** | 請求の趣旨記載例 等のスニペット | 低（検索/画像） |
| | **E4_checklist_or_notice_board** | チェックリスト/公告 | 低（検索/画像） |
> 形状で判定（titleでなく）。公正証書は条文型ならA、単票ならB/C/D/Eへ形状で振る。同意書・議事録もtitleでなく形状。

## 2. source_fidelity（二値→段階値・NOTE2）
`ocr_shape_ok`（形状/分類のみ信頼）< `ocr_slot_ok`（slot抽出も信頼=B/C/D/E1）< `ocr_search_only`（検索のみ=E3/E4）／ `docx_required`（忠実復元に必要=A・E1表・英文・OCR欠落）／ `human_review_required`（曖昧/低信頼）。

## 3. docx_priority_score（月30枠の配分根拠・NOTE2/7）
```
score = 3*[archetype∈{A,E1,E2}] + 2*[ocr_gap]      # 条番号抜け/キャプション欠落を検出
      + 2*[is_english] + w_reuse(category_id_lib)   # カテゴリ価値の事前重み(owner調整可)
      + 1*[pages>=3]
```
docxは**上位スコアから**取得。契約559を機械的に全部並べない（NOTE7）。

## 4. restorable_profile 監査・版メタ追加（NOTE3）
profileに必須追加: `canonical_image_ref, ocr_text_hash, ocr_parser_version, docx_file_ref?, docx_hash?, profile_version, confidence, slot_evidence, layout_profile, validation_status, sample_bucket`。
slotに追加: `required, default_value?, normalization, display_format, example_value_redacted?`。
（ALO原則: rawを潰さず・派生は再生成可能・監査証跡を後付けにしない）

## 5. formType 入口＝状態フラグ化（NOTE4）
`category_id_lib`=分類prior / `archetype`=復元戦略 / `formType_label`=表示用、の三分離。
旧「その他」は formType でなく状態フラグ `category_uncertain` または `requires_shape_review`。

## 6. 全件run 出力スキーマ（NOTE2/6 — 最低限カラム）
`classification.jsonl`（3,806行）各行:
`template_id, title, category_id_lib, old_formType, page_count, clause_count, archetype, subtype, confidence, ambiguous_reason, source_fidelity, docx_priority_score`
加えて成果物:
- `confusion_matrix.csv` = `category_id_lib × archetype × clause_count_bucket`
- `ambiguous_top100.csv` = confidence下位/ambiguous上位100件（人手レビュー対象）
- `validation_set.csv` = 層化抽出 **200〜300件**（`category_id_lib × archetype × page_count × clause_count_bucket`）→ 人手/高精度レビューで precision/coverage/ambiguous_rate を算出

## 7. 横展開ゲート（NOTE5）
全件分類＋層化検証の precision/coverage/ambiguous_rate が出るまで **docx月30キュー確定・事務所PDF横展開は HOLD**。検証数値が基準を満たしたら docx_priority_score 上位から月30枠を開始。

## 8. v0.3.1 パッチ（番頭独立検証 `VALIDATION_classify3806_v0.3.md` 反映）
独立検証で「契約title・0条 → D 誤送＝12件」と docx_queue の同題重複を検出。決定論で修正:
- **F1 契約title ガード**: `title =~ 契約書|協定書|合意書|Agreement|Contract` ∧ `title !~ 承諾|同意|誓約|通知|解除|解約|申入|連絡|説明` ∧ `archetype==D` ∧ `clause_count==0` → `archetype=A` / `source_fidelity=docx_required` / フラグ `contract_zero_clause_needs_docx`。理由: OCRは契約の条を落とすため「契約titleの0条」をD根拠にしない。
- **F2 docx_queue 重複除去**: docx対象は同一/近似title（正規化後一致 or 先頭8字一致）を**代表1〜2件に畳む**。`docx_queue.csv` を別出力（tid,title,archetype,score,dup_group,representative_flag）。
- **F3（任意）**: `同意書/承諾書/誓約書` 群は将来 D→短文slot(B) 再検討（本パッチでは据え置き）。
出力: `classification_v0.3.1.jsonl` ＋ `docx_queue.csv`。クォータ消費0（無料OCR再分類）。
