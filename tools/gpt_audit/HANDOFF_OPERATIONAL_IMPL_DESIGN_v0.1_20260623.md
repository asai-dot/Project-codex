# HANDOFF_OPERATIONAL_IMPL_DESIGN v0.1 — alo_gpt_audit.py への組み込み計画

- status: **draft (未ratify・未実装)** — 本実装 gate 監査用
- date: 2026-06-23
- gate: `HANDOFF` (operational implementation 段階)
- 前提: 設計 v0.5 は RATIFIED（`RATIFY_head_hand_handoff_v0.5_20260623.md`）。
  fixture-bound prototype（`handoff_proto/`）は緑。本書は **operational 実装**の
  最小組み込み計画であり、別 owner ratify を要する（design ratify では解禁されない）。
- スキーマの正本: `HANDOFF_SCHEMA_APPENDIX_v0.5_20260619.md`。
- prototype 参照: `handoff_proto/validator.py`（effect 導出・dispatch 検証・JCS hash・
  per-attempt reconciliation・active generation・patch migration）。

---

## 0. 目的と段階

prototype（純オフライン検証機）を `alo_gpt_audit.py` の運用ループへ最小差分で組み込む。
ただし **non_mutating レーン限定**で立ち上げ、mutating/lease/resource permit は subsystem
未実装の fail-closed のまま据える。

## 1. ロールアウト境界（何を operational にするか）

| レーン | 本実装で GO 候補 | 根拠 |
|---|---|---|
| non_mutating ＋ 非機密 ＋ permit 不要（design_patch/doc_patch/required_materials の一部） | **GO 候補** | lease/permit 不要・fail-closed に当たらない |
| mutating（file_move/台帳/Box 等） | **HOLD** | lease subsystem 未実装 → fail-closed で blocked のまま |
| paid/quota/rate_limited read | **HOLD** | resource permit subsystem 未実装 → blocked のまま |
| 機密 egress | **HOLD** | egress 軸で blocked |

prototype の `test_operational_default_lane` がこの境界をコードで固定済み
（既定 Env で mutating/paid は blocked、non_mutating レーンのみ dispatchable）。

## 2. alo_gpt_audit.py への最小差分（HEAD_HAND §9 を具体化）

1. **validator 取り込み**: `handoff_proto/validator.py` を `alo_gpt_audit` から import
   可能な内部モジュールへ昇格（コピーでなく単一実装。重複定義を避ける）。
2. **dispatch 生成（local）**: `write_route_card` 隣に `build_dispatch_packet()` を追加。
   付録 §3 の field を出力し、`packet_hash`（JCS）・`source_artifacts` version 固定・
   3軸 effect 導出・`hold_echo`/`data_access_class`/`allowed_assignees` を local 導出。
3. **dispatch validation**: 生成直後に `validate_dispatch()` を必ず通し、`dispatchable=false`
   は配布しない（route card を出さず blocked 理由を記録）。
4. **thin index 表示**: `cmd_action_queue` 各行に 付録 §2 の triage field（assignee/
   execution_role/mutation_class/egress_decision/resource_effect_class/hold_flags/
   risk_class/gate）。
5. **worklist**: `worklist <assignee>` は thin index を読み取りのみでフィルタ（既存
   WORKER_DELEGATION v0.2 と整合）。
6. **local close**: `close`/`reflect` に reconciliation を組み込む。同一 grouping の
   attempt を `reconcile()` で代表選定し、`needs_head_resolution` は owner/head へ上げる。
   attempt 固有 output path・`create_new_no_overwrite` を強制。
7. **台帳**: `packet_id`/`packet_generation`/`attempt_id`/`mutation_class` 等のキー追加のみ。
   append-only・後勝ち・旧レコード未差配扱い（back-compat 不変）。

## 3. fail-closed の据え置き（subsystem availability）

`Env` の既定 = `lease_subsystem_available=False`,
`resource_permit_subsystem_available=False`, `audit_permit_available=False`。
operational では**この既定のまま起動**。つまり mutating/paid/機密は生成しても dispatch
段で必ず blocked。lease/permit subsystem は別設計・別 gate（本書スコープ外）。

## 4. テスト（移植・追加）

- prototype の 15 test（dispatch 18 fixtures + hash + reconcile + redirect + migration +
  operational default lane）を CI に組み込む。
- 追加: `cmd_action_queue` triage 表示の back-compat（旧レコードで壊れない）、
  `worklist` フィルタ、route card 非出力（blocked 時）。

## 5. 監査してほしいポイント（本実装 gate）

A. non_mutating レーン限定の operational 立ち上げは安全か。fail-closed の据え置き
   （既定 Env 全 false）で、mutating/paid/機密が**運用経路に漏れない**ことは担保されるか。
B. validator を単一実装として本体へ昇格する方針（重複定義回避）は妥当か。
C. local close への reconciliation 組み込みで、単一書き手・append-only 台帳・
   `needs_head_resolution` の owner escalation は崩れないか。
D. 本書を operational 実装着手の design として GO とするか。実装着手はなお owner ratify
   前提でよいか。

## 6. スコープ外（HOLD 継続）

lease/claim・resource permit subsystem の実装。自動ディスパッチ（実セッション起動）。
mutating/paid/機密 egress の実行。Box move/metadata mutation。DB/DDL/canonical。
外部 AI への privileged 投入。これらは本書では一切触れない。

## 7. ロールアウト後の段取り（GO の場合）

design GO → owner ratify → §2 を1〜2コミットで実装（non_mutating レーンのみ有効化）→
§4 テスト緑 → README 更新 → 実運用観測 → mutating/permit レーンは別 gate で順次。
