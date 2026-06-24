# DD-TOCADOPT-001-IMPL v0.3.0 — owner review packet

prepared: 2026-06-17
for: owner (asai)
status: CONDITIONAL_PASS_WITH_NOTES (GPT-5.5, 3 監査ラウンド) → owner ratify 待ち
scope: report-only 実装パケットの受理可否。**production apply は本書では求めない (HOLD 継続)**。

## 1. 何を ratify してほしいか (1行)

「統一TOC採用ルールの **report-only 実装 (v0.3.0)** を、本番 apply ゲートへ進める前の
**closed packet として受理**してよいか」。実 apply の許可ではない。

## 2. ここまでの経緯 (3 ラウンド)

| ラウンド | 投函 | 判定 |
|---|---|---|
| 実装初版 (自己申告 weak points 付き・owner 指示の「雑な箇所を全部出せ」) | 6759258 | **MODIFY_REQUIRED** (H9/blocker6) |
| 是正 v0.2.0 (blocker6 + 是正必須) | eab091e | **MODIFY_REQUIRED** (N1 blocker 昇格・証拠不足) |
| 証拠付き是正 v0.3.0 (N1 二層 + gate8 + 証拠成果物) | 79ad08c | **CONDITIONAL_PASS_WITH_NOTES** |

GPT は「green だけでは足りない」と2度突き返し、3度目で主要 blocker を「設計・policy 上ほぼ閉鎖」と認定。

## 3. 実装の到達点 (report-only)

- 5 ステップ採用エンジン (`scripts/toc_adopt.py`) + 8 gate (`scripts/toc_adopt_gates.py`)。
- **二層構造**: book-level envelope (apply 単位, apply_target=accepted_node_set) と
  node-level 4-lane (accepted / pending_human_review / rejected / non_adoptable)。
- adoptable = identity_ok ∧ provenance_ok ∧ consensus_ok ∧ authority_resolved ∧ no_hard_blocker。
- 合成 12 シナリオ (敵対含む) / `test_tocadopt.py` 285 checks / 全テスト 947 green。
- 証拠成果物: `docs/dd/evidence/tocadopt_reaudit/` (baseline export / 5次元 equivalence / lane summary)。
- must_fix 4件 (reproduction gate / 5次元 equivalence / release guard / 未解決版除外) は
  report-only の枠で**前倒し実証済み**。

## 4. owner が決める点 (本書の核心)

### D-A: v0.3.0 closed packet を受理するか
- 推奨: **受理**。3 監査通過・全テスト green・HOLD 厳守。
- 受理しても production apply は依然 HOLD (実 baseline reproduction + 本番ゲートが別途必要)。

### D-B: N1-a — book all-or-nothing vs node 単位 apply
- 現状: 1 冊は「全 node が3独立origin裏取り」でないと adoptable にならない (安全側・保守)。
- 論点: 将来 **accepted node set だけを apply し、本は partial-adoptable とする**運用を許すか。
- 監査は再 MODIFY とせず owner review 事項として残置。
- 推奨: **当面 all-or-nothing 維持** (report-only の今は影響なし)。実 apply 設計時に再検討。

### D-C: Fork1 (legallib_join) 即廃止 HOLD / 並走期間
- 現状: 本 DRAFT が既存 dry-run を完全再現するまで Fork1 policy は廃止せず並走 (policy 明記済)。
- 推奨: **並走維持**。reproduction green + owner ratify 後に Fork1 廃止。

## 5. owner が承認しても発生しないこと (安全確認)

production apply / canonical projection apply / RDB write / source snapshot mutation /
policy 本番切替 / Fork1 即廃止 / unresolved manifestation の合議参加 — **すべて HOLD のまま**。
本パケット受理は「実装を次ゲートへ進めてよい」という承認に限られる。

## 6. 次ゲート (受理後)

1. 実 baseline (ALOBookDX 631クラスタ/116,727ノード) 到着 → gate1 + 5次元 equivalence を**実データで実行**。
2. 完全再現を確認 → owner が production policy 切替を別途 ratify。
3. その後に canonical projection apply (人手承認レーン経由)。
