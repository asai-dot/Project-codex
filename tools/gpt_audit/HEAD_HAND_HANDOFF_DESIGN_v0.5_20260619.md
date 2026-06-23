# HEAD_HAND_HANDOFF_DESIGN v0.5 — ヘッド↔ハンドのシームレス受け渡し設計

- status: **RATIFIED (design)** — owner ratify 2026-06-23。実装は `fixture-bound prototype`
  のみ着手可、operational/外部/課金/変更系は HOLD。ratify_record:
  `RATIFY_head_hand_handoff_v0.5_20260623.md`
- date: 2026-06-23
- gate: `HANDOFF`
- revision: v0.4 → v0.5。`HANDOFF_MODIFY_REQUIRED`
  (`20260621_head_hand_handoff_design_v0.4_GPTPRO_AUDIT_RESULT.md` / 2300911710513)
  の v0.5 blocking を反映: per-attempt reconciliation（#5）/ hash `runtime_envelope` 完全
  列挙＋`hash_status=unavailable` の blocked（#6）/ `resource_descriptor` 規範 schema・
  `audit_sensitive` 直交化（`external_audit_logging`）・`free_bounded` 上限（MF-2）。
  3軸・**第4軸不要**・governance/execution 分離は accepted 維持。
- **スキーマの正本**: `HANDOFF_SCHEMA_APPENDIX_v0.5_20260619.md`（規範的単一正本）。
  本文 YAML/field は **non-normative example**。
- owner 決定:
  - role = **governance_role / execution_role 分離**。
  - **effect は3軸＋直交属性**: `mutation_class`（lease）/ `egress_decision`（機密送信）/
    `resource_effect_class`（課金・quota・rate）＋ `external_audit_logging`（外部ログ・直交）。
    read は mutation 軸で non_mutating。無償 public read は広く通す。**有料/quota/rate-limited
    read は resource permit 必須＝permit 不在なら fail-closed で blocked**。
- 姉妹: `WORKER_DELEGATION_DESIGN_v0.2_20260619.md`（v0.2 で付録正本へ同期）。
- prior art: `handoff/WORKER_TASK_PACKET_*.md`

---

## 0. なぜ要るか

ヘッドとハンドは別セッション・共有メモリなし。渡れるのはファイルだけ。

> **H1: シームは直列化境界。アーティファクトに書かれない文脈は渡らない。**

シームレス ⇔ 下りが context-closed・上りが result-closed。失敗モード: 過少記述（往復→
ヘッド枠出血）／過結合（生メモリ共有不可）／肥大（inline 無制限→ミニ書庫化）。

## 1. 設計原則

1. 直列化境界 H1。記憶依存の受け渡し禁止。
2. コスト非対称（ヘッドは書き一度・読み薄く。往復ゼロ）。
3. 単一書き手不変（索引/台帳/移動は local。ハンドは上りを書くだけ）。
4. gated は上書き不可。`hold_echo` は local 導出・縮小不可。
5. governance_role / execution_role 分離。`execution_role`=worker|deterministic、
   `assignee`=local|codex|worker_cc のみ。
6. **3軸 fail-closed**: `mutating ∧ lease 無し ⇒ blocked`／`resource_permit_required ∧
   permit 無し ⇒ blocked`（いずれも override 不可）。
7. 3軸 effect は local 導出・worker は安全側へのみ移動可・unknown は安全側。

## 2. 二層アーティファクト

thin index（付録 §2 が正）＝triage 十分。fat packet（付録 §3）＝自己完結。

## 3. 下りパケット（DISPATCH）

正は付録 §3（`handoff-dispatch/0.5`）。要点:
- integrity（付録 §6）: `packet_hash`（local が render 後・公開前に計算・**attempt_id 非包含**）、
  `hash_basis: rfc8785_jcs`、`excluded_from_hash`（包括語廃止・`runtime_envelope` object の
  全 field を完全列挙・hash 対象は allowlist 方式）、`source_artifacts`（`version_ref_type`
  型付き・**`hash_status=unavailable` は integrity-required gate で blocked**）。
- routing: `governance_role`（gate metadata）/ `execution_role` / `assignee`
  （invalid 明示値は validation error）。
- **3軸 effect＋直交属性（付録 §4）**: `mutation_class` / `egress_decision` /
  `resource_effect_class`（`audit_sensitive` 撤去）＋ `external_audit_logging`（直交）
  ＋ `side_effect_flags`（状態変更のみ）/ `egress_descriptor` / **`resource_descriptor`
  （規範 schema・provider/operation/units/permit_ref…）** / `lease_required` /
  `resource_permit_required`。
- access/gate（付録 §7）: `data_access_class`（registry ref+version）/ `allowed_assignees`
  （local 導出・縮小のみ）/ `external_egress_allowed:false` / `hold_echo` / `gated_by`。
- work: `objective` / `context_closure`（why 付き参照）/ `inputs` / `do` / `acceptance`。
- size/staleness: `soft_cap_bytes`＋`size_policy_version`（規範 field 化）/ `staleness_policy`。
- return: `output_contract`（§4）/ `proposal_only` / `clarification_budget:0`。
- `next_action_type=ratify` は **DISPATCH を生成しない**（`owner_pending`）。

## 4. 上りパケット（RESULT）と attempt（付録 §5/§9）

二重実行で同一 output_path 上書き→dedup 崩壊を attempt 単位で防ぐ:
- `attempt_id` は attempt 開始時に local/worker runtime が UUIDv7 発番。**packet 識別・
  grouping から独立、`packet_hash` に含めない**。
- `output_path = <output_root>/<packet_id>/<attempt_id>_RESULT.md`、
  `write_mode=create_new_no_overwrite`。
- worker は `supersedes`/`duplicate_of` を決めない。local が reconciliation event
  （付録 §5.2）で付与。RESULT の `packet_hash` echo 必須。

## 5. シーム閉鎖 — 3軸 effect・lease/permit fail-closed・調停

### 5.1 3軸 effect 導出（付録 §4）

local dispatcher が決定的導出。worker は安全側へのみ移動可。unknown は安全側
（mutating / egress blocked / resource permit 要求）。`paid_or_quota_call`・`data_egress`
は side_effect_flags（mutation）から外し resource 軸・egress 軸へ（v0.3 の自己矛盾解消）。

### 5.2 read 既定（owner 決定・付録 §4.3）

| read | mutation | egress | resource | dispatch |
|---|---|---|---|---|
| local/offline | non_mutating | none | none | OK |
| public GET | non_mutating | allowed(public_query) | free_bounded | OK |
| 有料/quota/rate-limited | non_mutating | policy 適合 | paid/quota/rate_limited | **permit 必須・無ければ blocked** |
| 機密 query 送信 | non_mutating | **blocked**（明示許可時のみ allowed） | 実態 | egress 不許可なら blocked |
| shared cache 永続 write 伴う | **mutating** | 実態 | 実態 | lease 必須 |

無償 public read は広く通す（owner）。課金・機密送信だけ別軸で止める。

### 5.3 fail-closed（不変条件）

```
mutating ∧ lease 無し ⇒ blocked(lease_required_but_unavailable)
resource_permit_required ∧ permit 無し ⇒ blocked(resource_permit_unavailable)
```
いずれも override 不可。lease/permit 実装まで該当 packet は配布・実行しない。

### 5.4 重複結果の調停（付録 §5・per-attempt relation）

grouping=`source_queue_item_id+packet_generation+packet_hash`。古い generation は
stale_generation。代表選定=acceptance 合格→(同値)earliest valid→(片方完全)完全側→意味
衝突は `conflict`＋`needs_head_resolution`（両保持・自動統合禁止）→不合格/不正は invalid。
**reconciliation event は per-attempt `attempt_relations[]`**（付録 §5.2）に保存し、
representative＋duplicate＋invalid 混在を個別表現。`representative_attempt_id` は conflict /
全 invalid 時 `null`。evidence grade は local 算定。semantic 同値は付録 §5.4。

## 6. 往復ゼロ gate 化

context-closed 5条件（objective / inputs 解決可能 / do は材料のみ参照 / output_contract
完全指定 / acceptance ハンド単独検証）。サイズ規律（decision-critical のみ inline・
soft_cap_bytes 超過は reason＋must_read_sections・機械判定）。`clarification_budget`
（既定0）超過は推測継続せず `needs_more`＋`required_materials`。

## 7. role / governance / assignee（付録 §1.2）

governance_role/execution_role 分離。DISPATCH の execution_role は worker|deterministic
のみ。supervisor/auditor/owner は gate metadata。assignee=local|codex|worker_cc。
`next_action_type=ratify` は dispatch 生成禁止→`owner_pending`。invalid assignee は
validation error。enum 外語彙廃止。

## 8. access / gate 境界（付録 §7）

`data_access_class`（registry ref+version・不明は dispatch 禁止）、`allowed_assignees`
（local 導出・縮小のみ・非互換は block）、`external_egress_allowed:false`、`hold_echo`
（local 導出・縮小不可）、allowlisted output/upload root（traversal reject）、`gated_by`。

## 9. 実装ポイント（最小差分・ratify 後）

1. local の dispatch 生成: `packet_hash`（JCS）・source version 固定・3軸 effect 導出・
   `hold_echo`/`data_access_class`/`allowed_assignees` 導出・付録 §3 field 出力。
2. action-queue 行: 付録 §2 triage（3軸 effect 含む）。
3. dispatch 前 validation: context-closed 5条件＋`mutating∧lease無し→blocked`＋
   `resource_permit_required∧permit無し→blocked`＋egress/access/assignee/oversize/ratify
   の各 block＋staleness。
4. local close: attempt 固有 path・active generation dedup・代表選定・reconciliation event
   記録・hash/echo/acceptance 検証。

台帳キー追加のみ・append-only・後勝ち・旧未差配。

## 10. テスト（付録 §10 fixture が正・ratify 後）

付録 §10 の入力＋期待値 fixture を用いる（F1 local read / F2 public GET / F3 paid no-permit
→blocked / F4 confidential egress→blocked / F5 file move→lease / F6 ratify→不可 / F7 unknown
access→blocked、ほか stale-generation / duplicate-output-collision / valid-but-conflicting→
conflict / hash-JCS / invalid-assignee / oversize）。test 名でなく期待値付き fixture 本体。

## 11. やらないこと（スコープ外）

自動ディスパッチ。lease/claim・resource permit subsystem の**実装**（境界は確定・fail-closed
で配布しない）。GPT/claudehead を assignee に入れること。mutating/有料/機密 egress の
dispatch・実行（別 gate まで HOLD）。

## 12. 適用範囲の境界＋ratify 後（付録 §12）

- **fixture-bound prototype**（owner ratify 後 GO）: schema validator / test harness。
  外部 call・queue/ledger/file move・永続運用 write なし。
- **operational implementation**（HOLD）: v0.5 再監査閉鎖＋owner ratify 後、non_mutating
  レーンから。mutating/lease/resource permit は別 gate まで HOLD。
- スキーマは付録を単一の正とする。
