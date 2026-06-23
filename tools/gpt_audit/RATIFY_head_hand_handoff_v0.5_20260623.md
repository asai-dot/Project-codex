# RATIFY — head/hand handoff design v0.5

- decision_id: ALO-HEAD-HAND-HANDOFF-20260619
- ratified_by: owner
- ratified_at_jst: 2026-06-23
- gate: HANDOFF
- verdict_basis: `HANDOFF_PASS_WITH_NOTES`
  (`20260622_head_hand_handoff_design_v0.5_GPTPRO_AUDIT_RESULT.md` / 2302723874091)
- reviewed_pr: asai-dot/Project-codex#29 @ `c7992ceece40b6d972dffb41e7369b2910fba2c9`

## ratify されたもの（design/schema のみ）

- `HANDOFF_SCHEMA_APPENDIX_v0.5_20260619.md`（規範的単一正本）
- `HEAD_HAND_HANDOFF_DESIGN_v0.5_20260619.md`
- `WORKER_DELEGATION_DESIGN_v0.2_20260619.md`
- 上記が定める: シーム＝直列化境界 H1 / context-closed・result-closed / thin index＋fat
  packet / 3軸 effect（mutation・egress・resource）＋直交属性 external_audit_logging /
  governance_role・execution_role 分離 / per-attempt reconciliation / JCS hash /
  fail-closed 不変条件 / fixture set / pure validator 仕様。

## ratify で解禁される実装範囲（owner ratify 後 GO）

**fixture-bound prototype のみ**:
- schema validator
- fixture parser / expected・actual 判定 harness
- JCS hash fixture / reconciliation fixture / fail-closed fixture
- README の**非運用** test command

制約: 外部 call なし・queue/ledger/Box mutation なし・file move なし・永続運用 write なし。

## 引き続き HOLD（本 ratify では解禁しない）

operational dispatch / 実 worklist / RESULT close 運用 / route card・index・ledger write /
Box move・metadata mutation / external call / paid・quota・rate-limited call /
mutating lease path / AI access class 拡張 / DB write / DDL / canonical promotion / S8・S9。

これらは別 gate で改めて owner ratify を要する。

## operational implementation 着手前の must_fix（v0.5 監査 §7）

1. 付録 filename / document revision / packet_schema_version の対応明示 — **済**
   （v0.5 にリネーム＋front-matter で revision==v0.5・schema==*/0.5 を明記）。
2. integrity-required gate の registry/列挙表 — **済**（付録 §0）。
3. permit subsystem 未実装中は resource_permit_required packet を dispatch しないことを
   validator fixture に入れる — prototype で実装（F3 系 fixture）。
4. local closer の reconciliation event 出力例を1つ canonical fixture として保存 — prototype。
5. Box metadata mutation / move は prototype の外であることを README 明記 — prototype。

## should_fix（v0.5 監査 §8）

logging profile 例 / redirect allowlist in-out 両 fixture / weak_equivalence basis_code 必須化 /
stale_generation と stale_packet の fixture 名分離 / 旧 patch migration の README 参照。
prototype の fixture で順次反映。
