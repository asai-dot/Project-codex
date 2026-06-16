# DDSELFHEAL-C1prep — C1 write 解禁の最小条件を report-only で充足

- 日付: 2026-06-16
- 親監査: `20260616_DDSELFHEAL-C0_PASS_WITH_NOTES.md` (DDSELFHEAL_C0_PASS_WITH_NOTES)
- 範囲: GPT が「今 許可」とした非ゲート作業 (golden 拡張 / quarantine ledger / regression taxonomy / manifest 追加)。
- 不変: **実書込・production apply・RDB write・identity/canonical mutation = HOLD 継続**。本作業は全て report-only / dry-run。

## GPT C0 監査の「C1 最小条件」に対する充足状況

| C1 最小条件 (GPT 指定) | 状態 | 実体 |
|---|---|---|
| golden 10→**30冊以上** (sparse/multi-volume/page-offset/orphan/no-TOC/conflict 網羅) | **充足** | `tests/golden/repair/synthetic_corpus_30.jsonl` (6 カテゴリ×5冊=30)。生成器 `scripts/make_synthetic_golden.py`、回帰+安全テスト `tests/test_golden_repair.py` (164 checks) |
| 決定的 repairer 4種が idempotency + no-op 二度がけ通過 | **充足** | C0 で実装済。golden 30 全冊で `all_no_op_second_run` / `all_rollback_verified` / `all_health_non_decreasing` = True を再固定 |
| quarantine ledger (age/escape/recurrence) | **充足** | `scripts/quarantine_ledger.py` (append-only + chain hash)。`tests/test_quarantine_ledger.py` (18 checks)。`corpus_health(ledger_path=…)` で needs_ledger を実 KPI に置換 |
| regression taxonomy | **充足** | `scripts/regression_taxonomy.py` (defect 分類 + 修復前後の回帰判定)。`tests/test_regression_taxonomy.py` (17 checks)。engine が各 plan に `regression` を載せ `no_repair_introduces_p0` を集計 |
| manifest に pre/post health + rollback proof | **充足** (C0 済) | + 今回 `regression` / `quarantine_ledger_pointer` を manifest schema に追加 |
| repair class ごとの owner whitelist | **owner 手番** | 様式は apply_guard 既存。owner 承認 ISBN リストが未投入 |

## このコミットの新規/変更

- `scripts/quarantine_ledger.py` (新) — 隔離状態遷移の append-only 台帳。enter/release/recur/escape を chain hash 付きで記録し、`kpi()` が age/escape_rate/recurrence_rate を履歴から決定的算出 (clock/now 注入可)。
- `scripts/regression_taxonomy.py` (新) — defect コードを family/severity/route に正規化。`regression_diff(before, after)` が fixed/persisted/new/new_p0 を機械判定。**決定的 repair は新規 P0 を作らない**を不変条件化。
- `scripts/make_synthetic_golden.py` (新) — 合成 corpus 30 生成器。生成時の実パイプライン観測値を expected として焼き込み (回帰ロック)。合成データのみ・実依頼者データなし。
- `scripts/repair_engine.py` — `_repair_metrics` に regression diff を追加。engine 返値に `no_repair_introduces_p0` / `regression_free` を追加。
- `scripts/repair_base.py` — manifest に `regression` / `quarantine_ledger_pointer` を追加。
- `scripts/data_health.py` — `corpus_health(ledger_path=, ledger_now=)` で quarantine KPI を実値供給 (無指定時は従来 needs_ledger)。
- tests: `test_golden_repair.py` (164) / `test_quarantine_ledger.py` (18) / `test_regression_taxonomy.py` (17) / `test_data_health.py` (+6=37)。

## 安全不変条件 (golden 30 で固定)

- ★ orphan / conflict カテゴリは **必ず apply 不適格** (P0 ブロッカー)。
- ★ 決定的 repair の適用シミュレーションで apply 不適格本を適格へ **昇格させない**。
- ★ 決定的 repair は **新規 P0 defect を作らない** (`no_repair_introduces_p0`)。
- ★ 全 plan が no-op 二度がけ / rollback 原状復帰 / health 非悪化。
- writes_executed=0 / write_allowed_count=0 (C0: phase が常に書込不許可)。

## 残る C1 ゲート (owner / 他レーン手番、本作業の対象外)

1. **T2 DD-EDIDENT-001 ratify** (owner) — edition v2 共有モジュール昇格。ほぼ全 apply 適格 gate の土台。
2. **T1 DD-TOCADOPT-001 統合 corpus** (Mac/GPT) — 第2 node 源。単一ソース本の noisy conflict / insufficient_evidence を解消し real 30冊 golden を可能にする。
3. **C1 write 解禁の owner 承認 + repair class 別 whitelist** — 最初の write 候補は **BodyShaRecompute**、anchors 閾値は offset write 時 ≥3。

## テスト

stdlib **635 checks green / 0 failed** (C0 時 430 → +205)。`test_phase0_inventory.py` は pytest 依存 (本 env に pytest なし) のため除外。

> 本記録時点まで canonical/legallib/final_toc/source への書込は一切なし (report-only / dry-run)。
