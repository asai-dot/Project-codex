# CC_DISPATCH — Codex 実装指示: D1TAXO v0.6-R3 canary前 must-fix closure（4件）＋ 戸籍法 canary

- date: 2026-06-19 / from: 番頭(Claude Head) / to: コーデックスちゃん（精緻な手）
- 正本WO: `docs/d1kos/WO-CODEX-MF1_G23_canary_20260617.md`（rev2, PR #22）
- 監査根拠: DD-D1TAXO-001 v0.6-R3 Pre-Apply（CONDITIONAL_GO）＋ pre-apply short（4 must-fix）
- 種別: **must-fix closure ＋ scratch canary evidence まで。実 load 実行は owner lift 後（やらない）**

---

## 役割
あなた=ハンド（精緻な実装＋テスト）。私=ヘッド（仕様確定・レビュー・ゲート・SoT記録）。
仕様は確定済み。あなたはローカルの実 gate SQL / scratch Postgres に当てて evidence を返す。

## ハードガード（逸脱したら停止して番頭へ）
- **HOLD**: full batch / production DB write / production DDL apply / canonical promotion / claim-support /
  embedding / MCP publication / candidate shell apply / 法的同一性の判断 / 2本目canaryの本実行。
- canary は **独立 scratch/dev DB 限定**（production 本体不可・物理隔離・search_path明示・public/prodフォールバック禁止）。
- gate view を `OR REPLACE` で書換えない（新version張り直し＋migration note）。
- canonical 書込みは番頭一本化。あなたは作業領域と evidence 出力にのみ書く。
- 迷ったら停止して番頭へ（legal identity / canonical / batch 境界）。

## やること（canary前 must-fix 4件 → smoke → 戸籍法 canary → evidence）

### STEP 1. 現状確認
v0.6-R3 の **G23 gate view 定義**を特定。`build/d1taxo_v06_r3_patch_proposed_20260617/apply_lowercase_v4_patch.py` は
**v4 enumerator** で MF-C ではない（混同しない）。G23 に array guard が無ければ未適用。

### STEP 2. must-fix closure（4件すべて・evidence化）
- **MF-A normalizer_version review**: label normalizer の version を1本に確定・記録（v4 enumerator 適用有無/対象52件/raw温存含む）。
- **MF-B gate version discipline**: `OR REPLACE` 禁止。新version view を張り直し＋migration note。適用 gate の version id を記録。
- **MF-C G23 array guard**: term_ids / taxonomy_paths を array-guard。
  ```sql
  -- term_ids
  jsonb_array_elements_text(
    CASE WHEN jsonb_typeof(path_elem->'term_ids')='array' THEN path_elem->'term_ids' ELSE '[]'::jsonb END
  )
  -- taxonomy_paths も同クラスで guard
  ```
  数値ガード `term_id_text ~ '^[0-9]+$'` は維持。非配列は violation でなく**空集合**。
- **MF-D pending除外**: `pending:d1law_taikei_l3:{key}` 系 pending L3 edge を claim-support / CaseBundle evidence /
  legal reasoning から除外する gate/view/constraint を明示。未解決 pending を root/digshmcd 別にカウント。

### STEP 3. G23 negative smoke
`docs/d1kos/MF1_G23_negative_smoke.sql` を scratch で実行。非配列6形状（missing/null/string/object/number/boolean）で
**エラー0・violation誤検出0**、配列のみ展開。結果ファイル（path＋件数/hash）を保存。

### STEP 4. 戸籍法 canary（`source_item_key LIKE '1313-%'`, 362件）
独立 scratch schema、**単一 BEGIN..ROLLBACK ＋ SAVEPOINT**（partial rollback 不可）、teardown/rollback script 同梱。
※ scratch 検証のみ。実 load(production方向) は owner lift 後。

### STEP 5. 構造カウンタ（row count だけ不可）
label pref362/alt362/hidden362 / term_tier=2 / scheme_role=external_kos / claim_support_eligible=false /
missing_broader_reason 分布 / pending L3 edge 数 / broader/pending 無し term 数 / **G23 violation=0** /
**broader cycle=0** / hub membership 未作成。

### STEP 6. evidence 返却（artifact 必須・narrative 不可＝RDB-006準拠）
`scratch_run_<TS>/` に: `VERIFY_d1taxo_v06r3_canary_kosekiho_<date>.md`＋`result.json`、gate view diff（MF-B/MF-C）＋migration note、
rollback script、G23 negative smoke 結果、MF-A normalizer_version 記録、MF-D pending除外 gate＋未解決カウント。
返却先=現に動いている D1TAXO evidence 経路（from_gpt / iteration）。**死んだ `_claude_dispatch/to_worker` は使わない。**

## DoD
- **must-fix 4件すべて closure＋evidence化**。STEP1-6 PASS（or 明示NG＋該当サンプル最大50件）。
- read-only/HOLD 厳守。実 load は owner lift 後。

## 番頭の受け
4件＋canary evidence を **監査ノートに照合してレビュー → PR #22/SoT 記録 → owner lift → GPTお目付けの batch 判断** へ。
