# structure_profile v0.3.1 — rollout closeout（GPTお目付け役 ROLLOUT_MODIFY_REQUIRED 反映）

- **status**: v0.3 設計は **採用可**。docx batch 継続は **条件付き可**。**事務所スキャンPDFへの production 横展開は HOLD**。本v0.3.1で監査P0を closeout 仕様に落とす。
- **supersedes**: structure_profile_v0.3.md（schema分離方針は継承。本書は meta/anchor 修正と rollout 段階化・ゲート実装要件を追加）。
- **監査ソース**: `from_gpt/20260611_tmplstruct_v0.3_ROLLOUT_RESULT.md`（label=**ROLLOUT_MODIFY_REQUIRED**, reviewed 2026-06-10 JST）。
- **採用済みの核**: `docx_struct.paragraphs`＝原文ソース / `fixed_spans`＝索引 の分離、party_alias/defined_term 2分割、監査meta。

## 0. 判定の要旨（なぜ HOLD でなく「段階化」か）
rollout を**3段階に分離**せよ、が監査の核心。横展開GOは出ていないが、止められてもいない。
1. **Design/profile = PASS**: v0.3 schema と fixed_spans/paragraphs 分離は採用。
2. **Docx pipeline = PASS_WITH_CONDITIONS**: 下記 P0×4 を閉じてから batch2。
3. **Office scanned PDF = HOLD**: 事務所PDFは小規模 shadow-run を**別ゲート**で通してから production。

## 1. batch2 前に閉じる P0（×4・closeout ブロッカー）
| # | P0 | 根拠 | 担当 | クォータ |
|---|---|---|---|---|
| P0-1 | **content-type/zip 検証フェッチャ** | batch1 で 6/30 が `themeManager+xml`＝Word以外DLで無駄打ち | ワーカー実装 | 0（実装のみ） |
| P0-2 | **classify v0.3.1 無料再分類**（F1契約titleガード＋F2近似title重複除去） | 契約title+0条の本物契約をD誤送（真の誤送12件）／queue複製 | ワーカー（`classify_archetype_v0_3_1.py` 実行） | 0 |
| P0-3 | **deduped `docx_queue.csv`** → top30 番頭確認 → owner ratify | 複製にクォータを使わない | 番頭→owner | 0（ratifyまで） |
| P0-4 | **independent validator 実装＋全profile実行**（G1〜G7・json/md証跡） | F-1 は「仕様」では不可。**生成器と独立した実行証跡つきゲート**まで落とす | ワーカー実装＋既取得21profileで実行 | 0 |

**重要（監査3章）**: F-1 の `restorable_profile_ok` は文書化だけでは監査上ほぼ無価値（空虚ゲート）。**生成器と独立な validator が全 profile に gate を走らせ結果を保存**するまで rollout 不可。

## 2. スキーマ修正（v0.3 → v0.3.1・監査2章）
### 2.1 `meta` 拡張（機械可読・監査可能性）
```jsonc
meta: {
  profile_version, generator_version, validator_version,
  normalized_text_policy,                 // 例 "NFKC; brackets=fullwidth"
  source_file_type, source_content_type,  // 取得実体の型（P0-1で記録）
  source_zip_valid,                       // bool（[Content_Types].xml ∧ word/document.xml）
  docx_hash, ocr_text_hash, struct_hash, profile_hash,
  validation_status,                      // candidate|pass|fail
  validation_errors: [], validation_warnings: [],
  generated_at, canonical_image_ref, docx_file_ref,
  ocr_parser_version, slot_evidence, layout_profile, sample_bucket
}
```
### 2.2 `fixed_spans` に anchor を持たせる
```jsonc
fixed_spans: [{ text, role, para_i, char_start, char_end, normalized_text_hash }]
```
→ 「見出しラベルのみの索引」の意味が明確化し、**F-1 ゲート（G1/G3）の再計算対象が機械的に特定**できる。復元本文は引き続き `docx_struct.paragraphs[para_i]`。

## 3. independent validator ゲート（G1〜G7・監査3章）
`loaders/validate_restorable_profile.py`（生成器と別実装）。全 profile に対し json/md を吐く。
```text
G1 fixed_spans_anchor_to_paragraphs : 全 fixed_spans が paragraph anchor(para_i 有効) を持つ
G2 normalized_text_policy_match     : struct/profile 双方が同一正規化規則（meta.normalized_text_policy 一致）
G3 no_orphan_fixed_span             : 正規化後 struct.paragraphs に接地しない fixed_spans = 0
G4 non_empty_profile                : B/Eフォーム例外を除き fixed_spans + slots が非空
G5 slot_not_clause_caption          : 条見出し括弧が slot に混入しない（B修正の回帰）
G6 party_alias_defined_term_domain  : party_alias/defined_term の型域・曖昧時 defined_term 倒し
G7 source_content_type_valid        : docx zip/content-type 妥当（P0-1 の記録を参照）
```
- 出力: `<tid>.profile_gate.json`（G1〜G7 pass/fail＋証拠）＋ `_GATE_SUMMARY.md`。
- **ゲートは生成器の自己申告を読まない**。struct/profile/正規化規則から独立再計算する（DD自己申告不信の原則と同型）。

## 4. party_alias / defined_term（監査4章・precision-first）
- **party_alias 発火は厳しめ**: 直前句／同一文に人格・当事者語（`甲/乙/丙/当社/相手方/委託者/受託者/賃貸人/賃借人/売主/買主/会社/従業員` 等）がある場合のみ。
- 物・文書・法令・制度・対象物に見える、または判別不能 → **`defined_term` に倒す**。
- 理由: 組織オブジェクト/当事者抽出で party を誤れば誤って当事者扱いするリスク。precision 優先。

## 5. P0-1 content-type 検証フェッチャ（監査5章・別パケット）
取得直後に: ①response content-type 記録 ②zip として開けるか ③`[Content_Types].xml` ∧ `word/document.xml` 存在確認 ④不正は `bad_downloads.jsonl` に落とし**内部 budget に数えない** ⑤**サービス公式 quota が実消費されるなら内部 budget と公式 quota を分離記録**。6不正形式（4163,4166,4168,4323,4324,4937）は次月枠で回収。

## 6. P0-2/P0-3 classify v0.3.1（監査6章・`VALIDATION_classify3806_v0.3.md` §3）
- **F1 契約title ガード**: title が `契約書|協定書|合意書|Agreement|Contract`（`承諾|同意|誓約|通知|解除|解約|申入|連絡|説明` 除外）∧ archetype=D ∧ clause_count=0 → **A/docx_required**（OCRの0条を信用しない）。真の誤送≈12＋将来分。
- **F2 近似 title 重複除去**: 同一/近似 title を代表1〜2件に畳んでから月30枠を消費 → deduped `docx_queue.csv`。
- 出力: `classification_v0.3.1.jsonl` ＋ deduped `docx_queue.csv` → 番頭が top30 確認 → owner ratify → batch2。

## 7. production rollout 条件（監査7章・Phase A/B/C）
### Phase A — docx側 closeout（本v0.3.1の射程）
1. content-type/zip 検証フェッチャ実装（P0-1）
2. classify v0.3.1 無料再分類完了（P0-2）
3. deduped docx_queue 完成（P0-3）
4. batch2 実行、bad download 再発率を報告
5. independent validator の all-profile gate 結果を保存（P0-4）
### Phase B — office PDF shadow-run（**別ゲート**）
6. 事務所スキャンPDFから**匿名・非案件・汎用ひな形のみ 20〜30件**抽出
7. OCR triage → 形状分類 → profile 生成まで（**組織オブジェクト投入なし**）
8. OCR誤slot・個人情報混入・手書き/押印/余白の影響を review
9. output は `shadow_profiles/` に**隔離**（本番DB/組織オブジェクトに入れない）
10. GPT/owner review 後に production GO
### Phase C — production limited rollout
11. 最初は汎用ひな形フォルダのみ
12. 案件実データ・依頼者情報入り PDF は除外
13. profile に source hash と redaction/access class を必須化

## 8. このゲートを閉じる順序（番頭＝git/PR担当の手順）
1. 本v0.3.1 ＋ validator spec ＋ worker packet をコミット（本作業）。
2. Box `to_gpt` の ROLLOUT_REQUEST に processed マーク。
3. ワーカーに **closeout パケット**（P0-1/P0-2/P0-4 はクォータ0で実装・実行可）を渡す。
4. ワーカー成果（v0.3.1分類・deduped queue・gate証跡）を番頭レビュー → owner ratify → batch2。
5. batch2 closeout 後に Phase B shadow-run を**別ゲート**で起票。
- 3852 の classification 反映（A→B）は引き続き **owner 承認後**（破壊的変更）。
