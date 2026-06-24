# DDSELFHEAL-C0 — GPT 監査結果 (DDSELFHEAL_C0_PASS_WITH_NOTES) と反映

- 日付: 2026-06-16
- 投函: `to_gpt/20260615_DDSELFHEAL-C0_repair_phase0_review_REQUEST.md` (Box 2287662891789)
- 結果: `from_gpt/DDSELFHEAL-C0_result.md` (Box 2287692839804) = **DDSELFHEAL_C0_PASS_WITH_NOTES**
- 判定: Phase C0 dry-run は順調。**実書込 (C1) は ledger/idempotency/signoff package が整うまで HOLD**。
  最初に write 解禁すべき repairer は **BodyShaRecompute** (quarantine/offset ではない)。

## 実装レビュー反映 (今回・全て report-only)

| review 指摘 | 反映 |
|---|---|
| #1 派生 vs raw mutation | 派生は別 namespace 想定を維持。manifest に `derived` target を明示。**raw 非 mutation** をテストで固定 |
| #2 QuarantineOrphan 例外 | **索引/別表/付録/前付後付を除外** + `sparse`/`multi_volume` source を per-source 除外 (実装+テスト) |
| #3 OffsetPageConvert 閾値 | C0 dry-run は anchors≥2 で可。**write 解禁(C1)時は anchors≥3 へ**引上げ (本記録に明記) |
| #4 manifest 追加項目 | `pre_health/post_health/health_delta` / `idempotency_proof` / `no_op_second_run` / `rollback_verified` / `affected_count` / `owner_signoff` を **実装** (`repair_base.build_manifest` + `repair_engine._repair_metrics`) |

実証: demo で `body_sha_recompute` の `health_delta=+5.1` (欠落 sha 補完で health 改善)。
全 plan で `no_op_second_run=True` / `rollback_verified=True` / `health_delta>=0`。stdlib 430 checks green。

## must_fix status (GPT)
- class 5分類 / raw 非 mutation / identity 保護 / health-eligibility 分離 / manifest schema / semantic 隔離 = OK。
- quarantine KPI = PARTIAL (count/rate は C0 可。age/escape/recurrence ledger は **C1 quarantine write 前に必須**)。
- regression taxonomy = PARTIAL (設計のみで C0 可。**C1 前に実装必須**)。

## roadmap advice (GPT) — 確定方針

**優先順位: T2 → T1 → T3**
1. **T2 DD-EDIDENT ratify を最優先**。edition identity はほぼ全 repair / apply 適格 gate の土台。
2. **T1 DD-TOCADOPT 統合 corpus**。広い証拠で誤修復を減らす。
3. **T3 C1 write 解禁は最後**。T1/T2 安定 + golden 拡張後。

**C1 解禁の最小条件:**
- golden を 10→**30冊以上** (sparse / multi-volume / page-offset / orphan / no-TOC / conflict を網羅)
- 決定的 repairer 4種すべてが idempotency + no-op 二度がけテストを通過 (**今回実装済**)
- quarantine write をするなら quarantine ledger 実装
- repair class ごとの owner whitelist
- manifest に pre/post health + rollback proof (**今回実装済**)

**最初に write 解禁する repairer = BodyShaRecompute** (決定的・検証容易・identity/TOC/法的意味を変えない)。
第2候補 = NormalizeTitleRegen (derived namespace 限定)。Offset / Quarantine は golden 拡大まで保留。

**並行レーン統合:** DD-EDIDENT=共有 identity / DD-TOCADOPT=node・corpus 証拠 / DDSELFHEAL=report・gate・repair。
各レーンが独自の edition identity や health score を再発明しない。

**quarantine ledger:** quarantine の **状態変更**をする前に必須。BodyShaRecompute が C1 で report-only quarantine のままなら ledger は後でよい。

**撤退条件 (over-engineering の閾値):**
- repair plan の大半が human/quarantine に流れ clean_set が増えない
- false quarantine 率が高い
- health_score は上がるのに apply_eligibility が上がらない
- manifest が常習 defect の手動レビューより高コスト
- 決定的 repair が繰り返し semantic 例外を要する
- owner が dashboard から「なぜ clean/quarantine か」を理解できない

## 次の一手 (web-CC, 非ゲート)
- golden の **synthetic カテゴリ拡張** (sparse/multi-volume/no-TOC/conflict) を先行整備可 (実データ30冊は corpus 待ち)。
- quarantine ledger と regression taxonomy の **設計** (実装は C1 直前)。
- BodyShaRecompute の **C1 candidate packet** 準備 (owner whitelist 様式 + anchors/閾値表)。
- 実書込・production apply・RDB write・identity/canonical mutation・ledger 無し quarantine 変更 = **HOLD 継続**。

> 本記録時点まで canonical/legallib/final_toc/source への書込は一切なし (report-only / dry-run)。
