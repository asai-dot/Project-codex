# 判例精度 ①〜⑤ v0.2 — non-blocking note 消化 closure packet

accepted 5本（DDCASE_QUEUE_DRAIN_PASS_WITH_NOTES, 2026-06-23, result 2303200695802）の
non-blocking note を v0.2 でクローズ。**設計のみ・read-only・production HOLD 継続**。

## closure 一覧（各 accepted DD の accept-notes に対応）

| DD | note | v0.2 closure | 実装 |
|---|---|---|---|
| ① CASEEVAL (AC-3) | cluster-level 補助指標 | **B-cubed precision/recall** を `score()` に同梱（pairwise と併用） | `case_eval.bcubed` |
| ② CASEBIND (AC-4) | conflict を source 横断へ | **G6**: 同一外部参照 `source:id` が複数 case_key に跨る矛盾を検出→review（非merge） | `case_bind_guard.detect_cross_source_conflicts` |
| ④ CASECITE (AC-5) | matter scope 認可 | **V8**: matter機密 cite は要求者が当該 matter を認可されている場合のみ通過。未認可/別matter/None は fail-closed reject | `case_cite_gate.validate_bundle(requester_matters=…)` |
| ⑤ CASEREVIEW (AC-4) | サンプルサイズ/CI/unsure率 | **required_sample_size**（正規近似、既定 z=1.96）、**Wilson CI**、**unsure_rate**、per-tier `recommended_n`/`ci95` を `estimate_precision` に追加 | `case_review_sample` |

③ CASECORROB の note は「annotation/relation を非merge 維持」＝既定方針の確認のため新規実装不要（accept-notes AC-1/AC-3 で恒久則化済）。

## 検証
- 新規: `scripts/test_case_precision_v02.py` = **12/12 green（exit 0）**。①bcubed ②cross-source ④V8(3パターン) ⑤sample/CI/unsure。
- 回帰: 既存5テスト（case_eval / bind_guard / corroborate / cite_gate / review_sample）すべて **OK**（破壊なし）。

## 提案デフォルト（owner 確定待ち＝⑤ AC-4）
- `required_sample_size`: 目標 p ごと（A0.99 / B0.95 / C0.90）、margin=±0.02、信頼95% → 例 A≈96 / B≈456 / C≈864。owner が margin・信頼を調整可。
- unsure_rate を運用 KPI に追加（高 unsure は worksheet 表示項目不足の信号）。

## HOLD
production DDL / DB write / canonical mint / serving / accepted 昇格は継続 HOLD。実 corpus・実運用は Mac CC。

## 取り扱い
本 v0.2 は accepted 正本の **non-blocking note 消化**。各 accepted DD を supersede せず、accept-notes の該当 AC に対する実装証跡として併存。DDCASE 再監査で確認後、必要なら各正本に v0.2 反映を追記。
