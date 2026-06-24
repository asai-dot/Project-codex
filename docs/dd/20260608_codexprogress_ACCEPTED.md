# ACCEPTED: DDPROGRESS codexprogress — owner ratify

- gate: **DDPROGRESS**
- topic: codexprogress（パイプライン進捗ダッシュボード = runtime_status 観測レイヤ）
- status: **accepted**（候補 → 受理）
- ratified_by: 浅井（owner）/ 2026-06-08 / 経路: web CC セッション
- final_disposition: **accepted as runtime observation dashboard**（正本の進捗台帳ではなく
  観測 dashboard として運用。GPT 差分再監査 final に準拠）

## 監査トレイル

| 版 | REQUEST | RESULT | 判定 |
|---|---|---|---|
| v0.1 | `to_gpt/20260606_codexprogress_v0.1_DDPROGRESS_REQUEST.md` | `from_gpt/20260606_codexprogress_v0.1_DDPROGRESS_RESULT.md` | `DDPROGRESS_PASS_WITH_NOTES`（6 findings） |
| v0.2 | `to_gpt/20260607_codexprogress_v0.2_DDPROGRESS_REQUEST.md` | `from_gpt/20260607_codexprogress_v0.2_DDPROGRESS_RESULT.md` | `DDPROGRESS_PASS_WITH_NOTES`（F1/F2/F3/F5/F6 CLOSED, F4 PARTIAL, N1〜N3） |
| v0.2.1 | （差分修正・再投函なしで owner ratify） | — | N1/N2 closed, N3 documented |

## 受理条件の充足

- F1 runtime_status 命名 / F2 front-matter 優先 roundtrip / F3 orphan probe /
  F5 exists 非% 表示 / F6 snapshot メタ … **CLOSED**（v0.2）。
- **N1**（F4 完全閉鎖）: `collect()` が manifest 不正時に `ManifestError` を送出
  （`refuse_on_errors=True` 既定）。`pipeline_probe.py` と
  `pipeline_dashboard.py --root` の両経路で probe 前に拒否 … **CLOSED**（v0.2.1）。
- **N2**: 重複 `request_id` を `duplicate_count`/`duplicates` で可視化 … **CLOSED**（v0.2.1）。
- **N3**: front-matter を正規運用に固定（stem fallback は最後の逃げ道）… **documented**。

## 成果物（受理対象）

- `pipeline/pipeline.json` / `scripts/pipeline_probe.py` / `scripts/pipeline_dashboard.py`
- `docs/pipeline_dashboard.md`（§v0.2 / §v0.2.1）/ `tests/test_pipeline.py`（45 checks）
- PR: https://github.com/asai-dot/Project-codex/pull/5

## 運用上の取り扱い（accepted の意味）

- runtime_status（実行・運用状態）軸は DD-STATUS-REGISTRY の artifact lifecycle 軸とは
  別物。混同しない。
- manifest=正本（Git投影）、snapshot/dashboard=観測派生物。snapshot を「正本の状態」と
  みなさない。
- 以降の機能追加（ETA/throughput/履歴トレンド等）は別 DD で増分提案。
