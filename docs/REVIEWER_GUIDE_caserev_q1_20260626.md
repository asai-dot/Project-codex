# 人手レビュー第一バッチ 実施ガイド（Q1 法令参照 / caserev_q1_v0）

- date: 2026-06-26 / 番頭: Claude Code (remote)
- 対象: `CASE_HUMAN_REVIEW_SAMPLE_FRAME_20260618.md`(frame) の第一バッチを**実行可能化**したもの。
- ねらい: 真の律速＝**decision overlay 0 / accepted edge 0** を、最小バッチで **0→N** に動かす。
- 配管: `scripts/case_review_packet.py`（worksheet 生成＋集計）/ `test_case_review_packet.py`(green)。
- **HOLD 厳守**: accept しても canonical case / 法令正本 / `alo_edges` 反映なし。claim scope は「D1KOS分類文脈への支持証拠」のみ＝同一性主張ではない。商用本文は worksheet に出さない（正規化キーのみ）。

## 0. 役割分担
- **Mac CC**: 実 Q1 候補（法令参照 281、P1 77 ほか）を入力スキーマに整形 → worksheet 生成 → reviewer へ。記入後 tally。
- **reviewer（浅井先生／花岡さん）**: worksheet の `decision` 等を記入。
- **番頭（私）**: tally 結果を受け、stratum別 false-positive を DD-CASEID Tier B 基準 / SILVER QA へ反映。

## 1. 入力スキーマ（Mac CC が Q1 候補を整形）
1行=1候補の JSONL：
```json
{"ref_id":"Q1-0001","law_name":"民法","article":"709条","d1kos_node":"kos:fuhokoui",
 "article_side_root":"民事","taxonomy_root":"民事",
 "flags":["p1_top_root_aligned"]}
```
- `flags` ∈ `p1_top_root_aligned` / `cross_root` / `multi_law_token` / `suffix` / `provisional_kos`（frame §3 の risk flag。層化はこの flag から自動）。

## 2. worksheet 生成（Mac CC）
```
python3 scripts/case_review_packet.py build <q1_candidates.jsonl> caserev_q1_worksheet.csv
```
→ 層化抽出（S-A 全件 / S-C・S-D 全件 / S-B・S-E 各10）＋**負例control 8件**を注入した CSV。
列: `ref_id, stratum, is_negative_control, frame_version, 正規化キー5, expected_manual_check,
note_required_on_accept, decision, reason_code, review_note, decision_actor`。
（`sample_seed=20260618`・frame 凍結。rule 改訂は同 frame で前後比較）

## 3. reviewer の記入（1件あたり）
`expected_manual_check` 列に「何を見れば判定できるか」が出ています。それに沿って：

| `decision` に入れる語 | 意味 |
|---|---|
| `accept_d1kos_statute_ref_context` | この記事の法令参照は、この D1KOS分類文脈の**支持証拠**である |
| `reject_not_same_statute_context` | 支持証拠でない（**`reason_code` 必須**） |
| `needs_more_evidence` | 判断材料不足 |
| `defer` | 後回し |

記入ルール：
- **pending 以外は `decision_actor` 必須**（氏名/ID）。
- **reject は `reason_code` 必須**（例 `different_root` / `suffix_mismatch` / `foreign_context`）。
- **`note_required_on_accept=1` の層（S-B/C/D）で accept するなら `review_note` 必須**（なぜ支持と言えるか）。
- **`is_negative_control=1` の行は「正解=reject」**。ここに accept を付けたら過剰検出のサイン（tally が自動検知）。

## 4. 集計（Mac CC → 番頭）
```
python3 scripts/case_review_packet.py tally caserev_q1_worksheet.csv
```
出力（初めて非ゼロになる数値）：
- `decisions_made` … **decision overlay 0→N の証拠**。
- `by_stratum` … 層別 decision 分布。
- `negative_control.healthy` … 負例が全 reject なら true（normalizer 健全）。**false なら過剰検出バグ**。
- `issues` … actor/reason/note 欠落・語彙外・負例accept を列挙（空＝記入健全）。

## 5. 完了基準（frame §5）
- S-A 全件＋拡張＋負例 = 全行 non-pending。
- 負例 8 件すべて reject（`negative_control.healthy=true`）。
- → これが SILVER Tier B「初回人手→gold蓄積後に限定自動」の **gold 第一陣**。

## 6. この後
番頭が tally を受け、(a) `cross_root`/`provisional_kos` の機械accept可否を stratum別 false-positive で判定、(b) DD-CASEID Tier B 基準へフィードバック、(c) 第二バッチ（Q2 判例引用 batch-1）へ展開（frame §6）。
**production 反映（canonical/alo_edges/claim_support）は引き続き別 GO。**
