# DD-TOCADOPT-001-IMPL v0.3.0 — owner ACCEPTED (report-only closed packet)

ratified_by: owner (asai)
ratified_at: 2026-06-17
gate: implementation_review → owner ratify
prior: DD-TOCADOPT-001-IMPL-REAUDIT2 = CONDITIONAL_PASS_WITH_NOTES (GPT-5.5, head 79ceda63)
scope: report-only 実装を次ゲートへ進める受理。**production apply は HOLD 継続 (実 apply 許可ではない)**。

## 1. owner 決定

| ID | 決定 | 内容 |
|---|---|---|
| **D-A** | **受理して次ゲートへ** | v0.3.0 report-only 実装を closed packet として受理。実 baseline reproduction ゲートへ進む。production apply は HOLD のまま。 |
| **D-B** | **当面 all-or-nothing 維持** | apply 粒度は book 単位。node 単位 partial-apply は実 apply 設計時に再検討 (policy OQ-5)。 |
| **D-C** | 並走維持 (既定) | Fork1 (legallib_join) policy は reproduction green + owner ratify まで廃止せず並走 (policy OQ-4)。 |

## 2. 受理対象 (branch claude/legallib-integration-design-Jgrtf, c9429e9 時点)

- `scripts/toc_adopt.py` (TOC_ADOPT_VERSION 0.3.0) — 5 ステップ採用エンジン + book-envelope/4-lane。
- `scripts/toc_adopt_gates.py` — 8 gate (gate1 5次元 equivalence / gate8 lane 構造分離)。
- `data/toc_merge_policy_unified_DRAFT.json` — 実装契約 (DRAFT / production_use_allowed=false)。
- `tests/test_tocadopt.py` 285 checks + 合成 12 シナリオ (敵対含む)。全テスト 947 green。
- `docs/dd/evidence/tocadopt_reaudit/` — baseline export / 5次元 equivalence / lane summary。
- `docs/dd/20260617_..._N1_envelope_lane_spec.md` — book-envelope/node-lane 仕様。

## 3. 監査トレイル (3 ラウンド)

1. 実装初版 (自己申告 weak points 付き) → **MODIFY_REQUIRED** (H9/blocker6)。
2. 是正 v0.2.0 → **MODIFY_REQUIRED** (N1 blocker 昇格・証拠不足)。
3. 証拠付き是正 v0.3.0 → **CONDITIONAL_PASS_WITH_NOTES** → 本 owner ratify。

## 4. 受理で GO になること

- report-only reproduction test の継続。
- 実 baseline 到着時の gate1 + 5次元 equivalence 実行 (比較器は実装・固定済)。
- 追加 regression / 敵対テストの拡充。
- 次段階 (本番 apply 設計) の検討着手。

## 5. HOLD 継続 (受理しても発生しない)

production apply / canonical projection apply / RDB write / source snapshot mutation /
policy 本番切替 / Fork1 即廃止 / unresolved manifestation の合議参加。

## 6. 次ゲート (production apply の前提)

1. 実 baseline (ALOBookDX 631クラスタ / 116,727ノード) 到着。
2. gate1 + 5次元 equivalence を**実データで実行** → 完全再現を確認。
3. owner が production policy 切替を別途 ratify。
4. canonical projection apply は人手承認レーン (pending_human_review) 経由でのみ。
