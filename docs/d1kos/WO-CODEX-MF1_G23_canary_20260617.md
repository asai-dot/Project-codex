# WO-CODEX-MF1 — DD-D1TAXO-001 v0.6-R3 MF-1 修正 ＋ 戸籍法 canary（コーデックスちゃん実装指示）

- 発注: 番頭（Claude Head） / owner: 浅井（本線優先・author/KAKEN 凍結を承認）
- 担当: **コーデックスちゃん（精緻な手・ローカル実ファイル/Postgres にアクセス可）**
- 監査根拠: `DD-D1TAXO-001 v0.6-R3 Pre-Apply`（`DDD1TAXO_PREAPPLY_CONDITIONAL_GO`）＋ `D1LAW_FULL_TAXONOMY_RDB_CONTRACT`（PASS_WITH_NOTES）
- 仕様: 番頭が確定（`MF1_G23_array_guard_patch_20260617.md` / `MF1_G23_negative_smoke.sql` / `AUDIT_STATUS_DD-D1TAXO_20260617.md`, PR #22）
- 種別: **canary まで。full batch は対象外（HOLD）**

## 0. ハードガード（厳守・逸脱したら停止して番頭へ）

- **HOLD（やらない）**: full batch / production DB write / DDL の production 適用 / canonical promotion /
  claim-support 化 / embedding / MCP publication / candidate shell apply / 法的同一性の判断。
- **canary は scratch / local 限定**。production テーブル・raw・canonical には触れない。
- `OR REPLACE` でゲート view を書き換えない（dump/restore 破綻防止）。新 version view ＋ migration note で。
- **正本（canonical）への書込みは番頭（head）が一本化**。コーデックスは自分の作業領域と evidence 出力にのみ書く。
- 迷ったら停止して番頭へ（特に legal identity / canonical / batch 境界）。

## 1. タスク（順序厳守）

### STEP 1 — MF-1 が未適用か確認
- 現 v0.6-R3 の **G23 gate view 定義**を特定。
- ローカルの `build/d1taxo_v06_r3_patch_proposed_20260617/apply_lowercase_v4_patch.py` は **v4 enumerator** であり MF-1 ではない。混同しない。
- G23 に `jsonb_typeof(...)='array'` ガードが**無ければ未適用** → STEP 2 へ。

### STEP 2 — MF-1 パッチ適用（`MF1_G23_array_guard_patch_20260617.md` の P1/P2）
- P1: `term_ids` 展開を `CASE WHEN jsonb_typeof(path_elem->'term_ids')='array' THEN ... ELSE '[]'::jsonb END` で array-guard。
- P2: `taxonomy_paths` 展開も同クラスで array-guard。
- 数値ガード `term_id_text ~ '^[0-9]+$'` は維持。非配列は violation でなく**空集合**扱い。

### STEP 3 — G23 negative smoke
- `MF1_G23_negative_smoke.sql` を scratch で実行。
- 受入: **エラーなく完走**／非配列6形状(`"123"`/`null`/object/number/boolean ほか)で **extracted 0・誤検出0**／配列(id1,7)のみ数値要素展開。
- 監査要請の adversarial 形状（missing/null/string/object/numeric-array）を網羅。

### STEP 4 — 戸籍法 canary（root=戸籍法, `source_item_key LIKE '1313-%'`, 362件）
- **transaction で包む**か、`scheme_id`/`snapshot_id`/`source_item_key LIKE '1313-%'` キーの **teardown/rollback script** を同梱。
- 一部テーブルだけ load 成功する partial rollback を防ぐ。

### STEP 5 — canary 構造カウンタ（row count だけでは不可）
以下を evidence に必ず含める:
- label 分布 = **pref:362 / alt:362 / hidden:362**
- 全 canary term の **term_tier = 2**
- **scheme_role = 'external_kos'** / **claim_support_eligible = false**
- `missing_broader_reason` 分布
- 戸籍法 root の `classified_under` **pending L3 edge 数**
- broader/pending どちらも無い term 数
- **G23 violation = 0** / **broader cycle = 0**
- 本 load で **hub membership を作っていない**こと

### STEP 6 — evidence 返却（artifact / narrative 完了は不可＝DD-D1TAXO-RDB-006準拠）
- `VERIFY_d1taxo_v06r3_canary_kosekiho_<date>.md`（各STEP PASS/件数表）＋ `..._result.json`（機械可読）
- 適用した gate view の diff（P1/P2）＋ migration note
- rollback/teardown script
- 返却先: 既存の D1TAXO evidence 経路（from_gpt / iteration 等、現に動いている所）。**死んでいる `_claude_dispatch/to_worker` は使わない。**

## 2. やってはいけない（明示）
- full batch / 2本目canary の本実行（2本目は番頭が canary1 evidence を見て別途指示）
- DDL の production 適用・canonical 反映・claim-support 投入
- raw label の改変（検査のみ。raw は pref として温存）

## 3. 完了基準（DoD）
- STEP1-5 が PASS（or 明示NG＋該当サンプル最大50件）。
- evidence package 返却。
- read-only/HOLD 厳守。逸脱なし。

## 4. 番頭(head)の受け
- コーデックスの patch/evidence を **MF-1 仕様＋監査ノートに対してレビュー**し、PR #22 と SoT に記録。
- canary evidence が揃えば、GPTお目付けの batch 判断へ渡す。
