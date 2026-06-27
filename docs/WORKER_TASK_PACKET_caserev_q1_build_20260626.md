# WORKER_TASK_PACKET — 人手レビュー第一バッチ Q1 worksheet 生成（L-RV / S5）

> 正本: `asai-dot/Project-codex` ブランチ `claude/precedent-object-progress-gwb47u` の本ファイル ＋
> `scripts/case_review_packet.py` / `docs/REVIEWER_GUIDE_caserev_q1_20260626.md` /
> `docs/CASE_HUMAN_REVIEW_SAMPLE_FRAME_20260618.md`(frame正本)。
> ワーカーは本ブランチを pull して実行。**worksheet 生成まで。判定(accept/reject)は人手＝範囲外。**

```yaml
task_id: WORKER_20260626_CASEREV_Q1_BUILD_001
executor: claude-worker   # Mac CC（D1KOS↔OPAC 法令参照レビューキュー実体と認証を持つ実行者）
permission_tags: [read-only, no-canonical-promotion, no-alo_edges-write, no-claim_support, no-DDL, no-commercial-text-export, no-Box-delete]
output_path: _claude_dispatch/from_worker/20260626_caserev_q1_build_RESULT.md
worksheet_out: artifacts/review/caserev_q1_worksheet_20260626.csv   # 正規化キーのみ・商用本文なし→commit可
stop_condition: one-pass-complete | needs_decision | blocked | budget_exhausted | max_turns
```

## 意味づけ（owner）
判例オブジェクトの**真の律速＝decision overlay 0 / accepted edge 0**。本タスクは最小バッチ（Q1 法令参照・P1 77＋負例8）の **reviewer worksheet を生成**し、人手判定を初めて流せる状態にする。**worksheet 生成のみ・read-only。canonical/alo_edges/claim_support 反映は HOLD（別 GO）。** frame は `caserev_q1_v0`（凍結）。

## 手順（bounded・順に）
1. ブランチ pull → `python3 scripts/test_case_review_packet.py` green 確認（FAIL なら blocked 報告）。
2. **Q1 法令参照 候補(281, D1KOS↔OPAC/CiNii statute ref)を特定**。frame §1/§3 の strong 281（P1 77/P2 135/P3 69）と risk flag（cross_root/multi_law_token/suffix/provisional_kos/p1_top_root_aligned は**既付与**）。
   - キュー実体（merged_review_queue / D1KOS報告系）を Mac 上で特定。**確信を持って特定できなければ blocked**（見つけた候補ファイル名と件数を報告）。
3. **入力スキーマへ整形** `caserev_q1_candidates.jsonl`（1行=1候補・**正規化キーのみ・商用/raw本文を含めない**）:
   `{"ref_id","law_name","article","d1kos_node","article_side_root","taxonomy_root","flags":[...]}`
   - 既存の risk flag をそのまま `flags` へ。P1 top-root-aligned は `p1_top_root_aligned`。
4. **worksheet 生成**: `python3 scripts/case_review_packet.py build caserev_q1_candidates.jsonl artifacts/review/caserev_q1_worksheet_20260626.csv`
   → 期待: S-A 全件＋S-B/S-E 各10＋S-C/S-D 全件＋**負例control 8**。stratum別件数を確認。
5. **manifest** `artifacts/review/caserev_q1_manifest_20260626.json`: `{frame_version, total_candidates, by_stratum{}, negative_control_n, seed}`。
6. worksheet(正規化キーのみ＝商用本文なし)と manifest を **commit & push**。`output_path` に件数・stratum分布・特定したキュー出所を報告。

## Forbidden
- **判定そのもの（accept/reject の記入）＝人手専管。ワーカーは decision を埋めない**（全行空欄で出す）。
- worksheet に **raw/商用本文を入れない**（正規化キー＋expected_check のみ。frame §7）。
- canonical case / `alo_edges` / `claim_support` / `reviewed=true` 反映、DB/DDL、Box削除。
- `case_review_packet.py` / frame の**設計改変**（番頭領分。不足は report で）。
- 実案件個人情報の露出（あれば匿名化 or 除外し needs_decision）。

## 完了後
番頭(remote Claude=head)が manifest を受け、(a) reviewer（浅井/花岡）へ worksheet 受け渡しの段取り、(b) 記入後 `tally` で decisions_made(0→N)・負例健全性・stratum別 false-positive を受入検査、(c) cross_root/provisional_kos の機械accept可否を DD-CASEID Tier B 基準へ反映。production 反映は別 GO。
