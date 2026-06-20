# WO-CODEX: D1TAXO v0.6-R3 第2 canary（rich root・scratch scope）2026-06-20

> from: 番頭(head) / to: Codexちゃん(hand) / 監査根拠: DD-D1TAXO-001 v0.6-R3 計画 Step5（rich 2本目 canary）
> ＋ GPTお目付け closure notes（PASS_WITH_NOTES, file 2295958729905）の should-fix #3 を本 canary に内包。
> 種別: **scratch/dev DB 限定の canary evidence のみ。owner lift 不要・production方向の load は一切しない。**
> 前提: 戸籍法1313 scratch canary lane は CLOSED（`HEAD_VERIFY_canary1313_MFclosure_20260619.md`）。本件はその次段。

## 0. 目的
戸籍法(1313)は構造が素直な「軟らかい root」だった。**full-root batch 認可の前に、荒れた root（深いL階層・L4→L3 pending 多め・enumerator variation・sibling順の乱れ）で同じゲート群を叩いて耐性を実証**する。あわせて多root pending データを採り、後続の pending-L3 resolver DD 設計の入力にする。

## ハードガード（逸脱したら停止して番頭へ）
- **HOLD**: full batch / production DB write / production DDL apply / canonical promotion / claim-support /
  embedding / MCP publication / candidate shell apply / 法的同一性の判断 / owner lift を前提とする一切の操作。
- canary は **独立 scratch/dev DB 限定**（production 本体不可・物理隔離・search_path 明示・public/prod フォールバック禁止）。
- gate view を `OR REPLACE` で書換えない。**canary1 で確定した versioned G23 view**（`G23_gate_v06r3_mfclosure_view_diff.sql` 系）を使用。
- canonical 書込みは番頭一本化。あなたは作業領域と evidence 出力にのみ書く。
- 迷ったら停止して番頭へ（root選定が割れる/legal identity/canonical/batch 境界）。

## STEP 1. rich root の選定（あなたが選び、根拠を出す）
戸籍法(1313)を除く root から、richness score 最大の1本を選定。指標（各 root で集計）:
- taxonomy 最大深度（L4/L5 の有無・深さ）
- **L4→L3 pending edge 数**（多いほど良い＝resolver DD に効く）
- enumerator パターン該当ラベル数（v4 enumerator 影響行の有無）
- sibling順 variation / 非自明な並び
- term 総数（極端に小さい root は避ける／戸籍法362と同等以上を目安）

出力: **候補 top3 を指標付きで提示 → 採用1本＋採用理由**。割れたら **L4→L3 pending 数が多い方**を採る。採用 root の `source_item_key LIKE 'XXXX-%'` プレフィクスを明記。

## STEP 2. scratch canary 実行（canary1 と同一レール）
- 独立 scratch schema、**単一 BEGIN + SAVEPOINT + 最終 ROLLBACK**（COMMIT 0）、teardown/rollback script 同梱。
- versioned G23 view を scratch で実評価（OR REPLACE 禁止・MF-B 規律維持）。
- ※ scratch 検証のみ。production 方向の load は owner lift 後（やらない）。

## STEP 3. 構造カウンタ（canary1 と同項目・当 root の N で）
label pref/alt/hidden / term_tier=2 / scheme_role=external_kos / claim_support_eligible=false /
missing_broader_reason 分布 / broader+pending=term 整合 / broader/pending 無し term 数 /
**G23 violation=0** / **broader cycle=0** / hub membership 未作成 / candidate_shell_insert=0 / protected_writes=0。

## STEP 4. G23 negative smoke（**GPT should-fix #3 を内包＝強化版**）
canary1 の合成最小形に加え、**現実的なネスト JSON で、非配列 `taxonomy_paths` と 非配列 `term_ids` が両方同時に出る形**を負例に追加。
非配列は violation でなく**空集合**、配列のみ展開、エラー0・誤検出0。psql 出力を artifact 保存。

## STEP 5. pending-L3 per-root rollup（resolver DD 入力）
当 root の **L4→L3 pending edge を per-root / per-L で rollup**。未解決 pending を digshmcd 別にカウント。
戸籍法81件と並べて比較できる表形式で出す（後続 resolver DD の規模見積りに使う）。

## STEP 6. v4 enumerator provenance（**GPT must-fix #2 を前倒し**）
当 root で v4 enumerator 影響行があれば、各行に **parser_patch_id / enumerator_rule / decision_basis / owner_approval 参照**を付与した記録を出す。**raw label は immutable**（温存を確認）。

## STEP 7. evidence 返却（artifact 必須・narrative 不可＝RDB-006準拠）
`scratch_run_<TS>/` に: `VERIFY_d1taxo_v06r3_canary2_<root>_<date>.md` ＋ `result.json`（**`scratch_scope_only=true` フラグを必ず持たせる＝GPT should-fix #5**）、
構造カウンタ TSV、G23 強化 negative smoke 結果、pending-L3 per-root rollup、v4 provenance 記録、rollback script、`artifact_hashes.tsv`（sha256台帳）。
返却先 = 現に動いている D1TAXO evidence 経路（**from_gpt / iteration**）。死んだ `_claude_dispatch/to_worker` は使わない。

## DoD
- rich root が**指標付きで選定・正当化**されている。
- STEP2-6 PASS（or 明示NG＋該当サンプル最大50件）。`scratch_scope_only=true` が result.json にある。
- read-only/HOLD 厳守・永続書込ゼロ（BEGIN/SAVEPOINT/ROLLBACK 静的カウント＋rollback 後残存0で証明）。

## 番頭の受け
第2 canary evidence を監査ノートに照合してレビュー → PR #22/SoT 記録 → 多root pending データを基に **pending-L3 resolver DD** を起票 → owner lift → full batch 判断。
