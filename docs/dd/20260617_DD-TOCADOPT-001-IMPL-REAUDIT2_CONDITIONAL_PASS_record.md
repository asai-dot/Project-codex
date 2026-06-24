# DD-TOCADOPT-001-IMPL-REAUDIT2 結果受領 + must_fix/should_fix 充足記録

verdict: **CONDITIONAL_PASS_WITH_NOTES** (GPT-5.5 Thinking, 2026-06-17, head 79ceda63)
status: report-only / production apply は HOLD 継続
result_file: Box `DD-TOCADOPT-001-IMPL-REAUDIT2_result.md` (file_id 2291571258660)

## 0. 総合

3 回目の監査で **CONDITIONAL_PASS_WITH_NOTES**。前回 MODIFY_REQUIRED の主要論点
(N1 二層 / A1 全ペア / B1B2 / C1 / C4 / D1D2 / E1 / F2) は **設計・policy 上ほぼ閉鎖**と認定。
残りは全て「**本番 apply 前**の must_fix」であり、production は元々 HOLD。
→ report-only の枠で**前倒しで潰せるものは潰した**。本書はその充足記録。

## 1. must_fix (本番 apply 前) の充足状況

| # | must_fix | 対応 | 所在 |
|---|---|---|---|
| 1 | reproduction gate の実行結果を添付 | gate1 を全冊実走し結果を artifact 化 (pass=true) | `evidence/.../baseline_equivalence_report.json` `gate1` |
| 2 | baseline equivalence report (node set/parent/page locator/base dist/projection hash の5次元比較) | **5次元を個別に**比較し全 true を記録 | 同上 `dimensions` (全 true) |
| 3 | DRAFT policy が本番 policy として参照されないことを CI/release guard で明示 | policy に `production_use_allowed=false`/`parallel_run_period`/`ci_release_guard` 追加 + `test_release_guard` で CI 固定 | policy `_draft` / `test_tocadopt.py::test_release_guard` |
| 4 | unresolved manifestation が合議・projection に参加しないことをテストで示す | 別版疑い源の固有 node が accepted/pending/projection に出ないことを固定 | `test_tocadopt.py::test_unresolved_manifestation_excluded` |

→ must_fix 4件すべて report-only の枠で**実証済み**。実 baseline (ALOBookDX 631クラスタ) 到着時は
同じ gate1/5次元レポートを実データで再実行する (比較器は実装・固定済)。

## 2. should_fix の充足状況

| # | should_fix | 対応 |
|---|---|---|
| 1 | confidence 未使用を test/README にも明記 | policy `confidence_usage` + `test_release_guard` が存在を固定 |
| 2 | Fork1 即廃止 HOLD と並走期間を明記 | policy `_draft.parallel_run_period` に並走条件 (reproduction gate green + owner ratify まで) を明記 |
| 3 | partinfo volume_structure の拒否先を DD-LITID parent/structure lane に明示リンク | policy `partinfo_kind_filter.note` = 「volume_structure型はDD-LITID親子レーンへ」(既存・維持) |
| 4 | edition_identity_v2 regression fixtures を索引化 | 本書 §4 に索引 |

## 3. 残置 (本番 apply ゲートへ持ち越し)

- 実 baseline (ALOBookDX 本流 projection / 631クラスタ・116,727ノード) との reproduction は
  実データ到着が前提 (本 repo に実データ無し)。比較器・5次元レポート・gate は実装済みで、到着即実行可。
- N1-a (book all-or-nothing vs node 単位 apply) は監査で再 MODIFY とはされず。owner review 事項として残置。

## 4. edition_identity_v2 regression fixtures 索引 (should_fix#4)

- `tests/golden/edition/known_conflict_10.jsonl` — 既知の別版衝突 10 件 (gate2 入力)。
- `tests/test_edition_identity_v2.py` — classify_edition_identity_v2 の分類回帰。
- `scripts/edition_identity_v2.py` — 全ペア worst-case 同定 (A1 の実体)。
- tocadopt 側の identity 連携: `tests/golden/tocadopt/synthetic_multisource.jsonl` の
  `edition_exclude` / `title_collision` (単一源) / 本書 §1 #4 の未解決版テスト。

## 5. HOLD 境界 (不変)

production apply / canonical projection apply / RDB write / source snapshot mutation /
policy 本番切替 / Fork1 即廃止 / unresolved manifestation の合議参加 = **HOLD 継続**。
本実装は投影層の表現・検査のみ。書込ゼロ。
