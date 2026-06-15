# DDSELFHEAL — GPT 監査結果 (DDSELFHEAL_PASS_WITH_NOTES) と反映状況

- 日付: 2026-06-15
- 投函: `to_gpt/20260615_self_healing_data_platform_DDSELFHEAL_REQUEST.md` (Box 2286184002957)
- 結果: `from_gpt/DDSELFHEAL_result.md` (Box 2286209883693) = **DDSELFHEAL_PASS_WITH_NOTES**
- 判定: 設計方針は承認。report-only の SCAN/分類/dashboard は続行可。
  **repair の書込は owner ratify + must_fix + gate 強制まで HOLD**。

## must_fix 反映状況 (8点)

| # | 内容 | 反映 |
|---|------|------|
| 1 | repair class 5分類を定義 | ✅ DESIGN §6.1 (設計確定) |
| 2 | raw source snapshot を mutate しない hard rule | ✅ DESIGN §6.2 |
| 3 | identity/canonical は owner apply packet 無しで変えない | ✅ DESIGN §6.2 |
| 4 | health_score と apply_eligibility を分離 (高 health≠apply 許可) | ✅ **実装済 (report-only)** `data_health` apply_eligible/apply_blockers + P0 cap |
| 5 | quarantine KPI (count/age/reason/escape/recurrence) | 🟡 一部実装 (count/rate/defect分布)。age/escape/recurrence は履歴 ledger 要 (Phase C) |
| 6 | regression taxonomy | ✅ DESIGN §6.5 (設計)。実装は ledger と同時 (Phase C) |
| 7 | repair manifest schema | ✅ DESIGN §6.6 (設計)。実装は Phase C |
| 8 | LLM/semantic を決定的ループ外へ | ✅ DESIGN §6.7 + repair class で隔離 |

## should_fix 反映状況

- 層別重みを thresholds 可変: ✅ 実装済 (`config/thresholds.json` health weights)
- apply_eligibility を別 dashboard track: ✅ `corpus_health.apply_eligible_count` (health と別軸)
- golden を10冊から拡張してから repair 書込: ⏳ 統合 corpus 到着後 (golden 拡張は Phase C 前提)
- `repair_noop_idempotent` gate: ⏳ Phase C (repair 実装時)
- `clean_set_membership_reason`: ✅ 実装済 (`book_health.clean_reason`)

## release boundary (GPT 確定)

**今 許可**: DDSELFHEAL を設計方針として採用 / report-only SCAN・分類・dashboard 継続 /
data_health・thresholds・golden で可視化 / repair manifest・gate の設計準備。

**HOLD 継続**: production apply / RDB write / repair 書込 / canonical projection 変更 /
raw source 変更 / semantic・LLM repair / owner whitelist 緩和。

## owner ratify (2026-06-15)

owner ratify 済 → Phase C 着手を許可。**ただし repair の実書込は HOLD 継続**
(golden 拡張 + owner whitelist + phase C1/C2 昇格を全通過するまで dry-run のみ)。

## Phase C0 実装状況 (dry-run / 物理書込ゼロ)

- `scripts/repair_base.py`: repair class 5分類 + Repairer 基底 + manifest schema (#1/#2/#7) +
  `is_write_allowed_in_phase` (C0 は実書込なし / semantic は常に不可)。
- `scripts/repair_offset.py`: 最初の決定的 repairer。検証済み本単位 offset (conf 1.0/validated/
  アンカー2+) で pdf_page→print_page を**派生**。raw pdf_page は不変 (hard rule #2)。
- `scripts/repair_engine.py`: dry-run オーケストレータ。各 plan を apply_guard 7gate で評価し
  decision_log に append (chain hash)。**writes_executed は常に 0**。冪等 (派生済→detect False)。
- `tests/test_repair.py` 26 checks: 物理書込ゼロ / C0 は write_allowed=0 / whitelist 無しは
  物理拒否 / rollback 可逆 / plan 決定的 / decision_log chain ok。

## 残 (実書込解禁の前提)

1. golden を10冊から拡張 (should_fix) — 統合 corpus 到着後。
2. owner whitelist。
3. phase C1 昇格 (pre-approved 決定的 class のみ実書込) → C2 (identity/canonical は owner approve)。
4. quarantine ledger (age/escape/recurrence) の永続化 (Phase C 後半)。

> 本記録時点まで canonical/legallib/final_toc/source への書込は一切なし (report-only / dry-run)。
