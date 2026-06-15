---
request_id: DDSELFHEAL-C0
topic: 自己浄化 repair 層 Phase C0 実装レビュー + 今後の進め方アドバイス
gate: implementation_review + roadmap_advice
supersedes: なし
parallel_related: [DDSELFHEAL, DDLEGALLIBCONCORD, DD-TOCADOPT-001, DD-EDIDENT-001]
current_governing_result: DDSELFHEAL_PASS_WITH_NOTES (repair_write=HOLD_until_owner_ratify_and_gate)
result_expected_filename: DDSELFHEAL-C0_result.md
status: queued
queued_date: 2026-06-15
守秘: 設計・状態語彙・件数レベルのみ。実依頼者データ本文は含めない。
---

# DDSELFHEAL Phase C0 実装レビュー + 進め方アドバイス依頼

## 0. 依頼内容 (2点)
1. **実装レビュー**: DDSELFHEAL_PASS_WITH_NOTES の must_fix を Phase C0 (dry-run) 実装が
   満たしているかの監査。
2. **進め方アドバイス**: 3つの待機トリガ (統合 corpus / DD-EDIDENT ratify / C1 昇格) と
   複数並行レーンを抱えた状態で、**何をどの順で進めるべきか**の助言。

owner は ratify 済 (Phase C 着手許可)。**ただし実書込は HOLD 継続**。本レビューも report-only。

## 1. Phase C0 実装サマリ (全て report-only / dry-run / 物理書込ゼロ)

3層チェーン (L1 NDL書誌 / L2 詳細TOC / L3 本文) の自己浄化ループのうち、
**SCAN → 分類 → REPAIR plan → gate → 監査** を dry-run で一気通貫:

- `data_health`: health_score (0–100, 層別重み) と **apply_eligibility を分離** (must_fix #4)。
  P0 cap (edition未解決/nodes_unaccounted/unresolved_conflict) で高 health でも apply 不適格。
  `corpus_health` に quarantine KPI (count/rate, age/escape は ledger 要を明示) (must_fix #5)。
- `repair_base`: repair class 5分類 / Repairer 基底 / **manifest schema** (must_fix #1/#2/#7) /
  `is_write_allowed_in_phase` (C0=実書込なし / semantic は常に不可)。
- **決定的 repairer 4種** (全て raw 不変の派生 plan):
  | repairer | class | 内容 |
  |---|---|---|
  | OffsetPageConvert | det_no_canonical | 検証済み本単位 offset (conf1.0/validated/anchors≥2) で pdf_page→print_page を派生 |
  | BodyShaRecompute | det_no_canonical | 解決済み source_content から欠落 sha256 を再計算 (内容不変) |
  | NormalizeTitleRegen | det_no_canonical | 生 title から title_norm を再生成 (生 title 不変) |
  | QuarantineOrphan | quarantine_only | **2ソース以上**で照合失敗した orphan のみ reason_code 付き隔離 (単一ソースの自明 orphan は除外・silent drop なし) |
- `repair_engine`: 各 plan を apply_guard 7gate + phase gate に通し decision_log に append
  (chain hash)。**writes_executed 常に 0**。冪等 (派生済→detect False)・plan 決定的。
- テスト: stdlib 398 checks green (repair 46 含む)。

## 2. must_fix 適合の自己評価 (要・監査確認)

| # | must_fix | 実装 | 自己評価 |
|---|----------|------|---------|
| 1 | repair class 5分類 | repair_base | ✅ |
| 2 | raw source を mutate しない | 全 repairer は派生フィールドのみ plan | ✅ (要確認: 派生≠mutate の線引き) |
| 3 | identity/canonical は owner packet 無しで変えない | semantic_identity class + phase gate で隔離 | ✅ |
| 4 | health と apply_eligibility 分離 | data_health.apply_eligible/blockers + P0 cap | ✅ |
| 5 | quarantine KPI | count/rate 実装、age/escape/recurrence は ledger 要明示 | 🟡 一部 |
| 6 | regression taxonomy | DESIGN §6.5 設計のみ (実装は ledger と同時) | 🟡 設計 |
| 7 | repair manifest schema | build_manifest (input_hashes/before/after/rollback/gate/log/class) | ✅ |
| 8 | LLM/semantic を決定的ループ外 | semantic_identity は phase gate で常に自動書込不可 | ✅ |

## 3. 実装レビュー質問

1. **「派生フィールド」と「raw mutation」の線引き**: print_page/title_norm/source_sha256/
   quarantine_reason を *派生* として book に足す設計は hard rule #2 (raw 不変) を満たすか。
   それとも派生も別 namespace (derived projection) に物理分離すべきか。
2. **QuarantineOrphan の 2ソース閾値**: 「単一ソースは自明 orphan ゆえ隔離しない / 2ソース以上で
   照合失敗した orphan のみ隔離」は妥当か。多巻物・部分TOC で誤隔離しないか。
3. **OffsetPageConvert の発火条件** (conf=1.0 / validated / anchors≥2) は厳しすぎ/緩すぎないか。
   Phase0 実測 (本単位 offset 94.9% 単一) を踏まえた閾値の助言。
4. **manifest schema** に Phase C1 実書込で不足する項目はないか
   (例: pre/post health delta, idempotency proof, reviewer signoff)。

## 4. 進め方アドバイス質問 (本依頼の主眼)

現在 web-CC レーンは「設計承認 + C0 dry-run 完備」で、前進は3トリガ待ち:
- (T1) DD-TOCADOPT-001 統合 corpus 完成 (= 第2 node 源 / authoritative evidence ④⑤ の前提)
- (T2) DD-EDIDENT-001 ratify (= edition v2 を共有モジュールへ昇格 / config 1フリップ)
- (T3) C1 昇格 owner 承認 (= 決定的 class の実書込解禁) + golden 10→拡張

質問:
1. **優先順位**: T1/T2/T3 をどの順で片付けるのが、owner の運用リスク最小かつ価値最大か。
2. **C1 解禁の最小条件**: golden を何冊・どの defect 網羅まで広げれば、最初の決定的 repairer
   (どれを最初に?) の実書込を解禁してよいか。最初に解禁すべき repairer の推奨は。
3. **並行レーンの統合**: legallibjoin / DD-TOCADOPT / DD-EDIDENT / self-healing が同一ブランチで
   並走している。統合・順序・二重管理回避の指針。
4. **quarantine ledger**: age/escape/recurrence の永続化を C1 前に必須とするか、C1 後でよいか。
5. **撤退条件**: この自己浄化アプローチを縮小/中止すべき兆候 (over-engineering の閾値) は何か。

> production apply / RDB write / repair 書込は HOLD 継続。本依頼は実装レビューと助言のみ。
