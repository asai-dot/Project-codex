# LEASE_SUBSYSTEM — design gate 確定記録（ratification）

- date: 2026-06-25
- owner: asai
- decision: **LEASE_SUBSYSTEM_DESIGN v0.5 を design 確定とし、design gate を close**。
  GPT Pro の次ラウンド監査は回さない（オーナー裁定で確定）。
- 確定対象: `tools/gpt_audit/LEASE_SUBSYSTEM_DESIGN_v0.5_20260625.md`

## 監査経緯（GPT Pro design audit / 5 ラウンド）

| ver | REQUEST (Box to_gpt) | RESULT (Box from_gpt) | verdict | 主な指摘 |
|---|---|---|---|---|
| v0.1 | 2303989218514 | 2304096222240 | MODIFY_REQUIRED | ledger/target_key/holder/TTL/scope/二重active（6件） |
| v0.2 | 2306466253725 | 2306477639392 | LEASE_MODIFY_REQUIRED | B1-B8（lease≠認可, op/scope binding, multi-target, trusted holder, event sourcing, atomicity, identity, trusted view） |
| v0.3 | 2306503398024 | 2306525973159 | LEASE_MODIFY_REQUIRED | B9-B16（flag gate 回帰, schema 接続, typed args, exact lease set, authz registry, event 遷移, HMAC lifecycle, partial failure） |
| v0.4 | 2306546819863 | 2306561290821 | LEASE_MODIFY_REQUIRED | 新規 8→2 に収束。B11(payload binding)/B17(lease_echo) + B18(次gate契約) |
| v0.5 | （投函せず・オーナー確定） | — | RATIFIED | B11/B17 閉塞・B10/B12/B13/B14/B16 詰め・B18 は次gate契約として記述 |

## 確定の意味（スコープの正直な明示）

- 確定したのは「**実装に着手してよい安定した設計**」であって、**mutate が動くことではない**。
- 本設計が実装されても解禁されるのは「mutating dispatch **card を出してよい判定**」までで、
  実ファイル移動・metadata 書込みは一切行われない（feature flag 既定 off 継続）。
- 実 mutation は §8 の **独立した将来 gate**。実務で mutating が必要になるまで着手しない。

## なぜ v0.5 で GPT 監査を止めたか

- 5 ラウンドで新規 blocking は 8→2 に収束したが、監査者（LLM）の合格基準が「本文だけで曖昧ゼロ・
  実装一意」であり、構造的に clean PASS の fixed point を持たない（毎ラウンド何かしら指摘可能）。
- v0.4 で残った実質は 2 件（うち B17 は echo 廃止で単純化、B11 は payload digest 拘束）で、いずれも
  方向は明確。これ以上の GPT ラウンドは限界効用が低いとオーナー判断。
- よって design 確定はオーナー裁定で行い、実装は別タスク（offline validator prototype + fixtures）へ。

## 次アクション（着手は別タスク）

1. offline validator prototype（§4 gate 列）+ §7 fixtures。feature flag off のまま。
2. operational gate 前に確定する繰延事項: HANDOFF schema canonical patch / authorization registry
   version 管理 / HMAC 鍵運用 / recovery queue runbook。
3. 実 mutation gate（§8）は将来の独立 gate。
