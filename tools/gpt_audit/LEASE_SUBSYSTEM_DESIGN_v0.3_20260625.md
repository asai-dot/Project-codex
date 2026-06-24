# LEASE_SUBSYSTEM_DESIGN v0.3 — mutating レーン解禁の最小設計

- status: **draft (未ratify・未実装)** — 監査 gate 用（v0.2 LEASE_MODIFY_REQUIRED への patch）
- date: 2026-06-25
- 前段: `LEASE_SUBSYSTEM_DESIGN_v0.2`（result 2306477639392, **LEASE_MODIFY_REQUIRED**,
  v0.3 patch + offline fixtures GO / mutating dispatch 解禁・実 mutate HOLD）
- 上位: `HANDOFF_SCHEMA_APPENDIX_v0.5` §4.4 / `HANDOFF_OPERATIONAL_IMPL_DESIGN_v0.1`
  （non_mutating レーン運用中・flag 既定 off）
- 目的: mutating レーンを **(認可 ∧ 排他 lease)** の二重条件付きで **dispatch 可判定まで**
  解禁する。実 mutate 実行・external は範囲外（別 gate）。**初期解禁対象は Box stable ID
  object に限定**（B7）。

## v0.2 → v0.3 差分（blocking B1–B8 対応表）

| # | v0.2 の穴 | v0.3 の手当て | 反映節 |
|---|---|---|---|
| B1 | lease を mutation 認可として使える | 認可 gate を分離し `authorized ∧ exclusive_lease` を AND（§2） | §2, §4 A-gate |
| B2 | 自称 scope が実 operation と未結合 / `next_action_type=file_move` は schema 違反 | mutation operation registry を新設、`required_scopes = derive(op, flags)`、`next_action_type` とは別 field（§1.2, §3） | §1.2, §3, §4 |
| B3 | 単一 target で multi-target を被覆できない | `required_lock_domains(packet)` を registry から導出、全 domain に lease 要求（§1.3） | §1.3, §4 L-gate |
| B4 | holder を packet から compose | `trusted_runtime_holder` を Env から注入、packet holder は echo・不一致は block（§1.4） | §1.4, §4 A-gate |
| B5 | ledger の state/event 模型が曖昧 | event-sourced（grant/release/revoke + sequence_no + prior_event_hash）、state は fold 導出（§1.5） | §1.5 |
| B6 | 原子性・同時実行・耐障害性 未定義 | single-writer/OS lock・O_APPEND・fsync・partial-tail quarantine・UUIDv7・HMAC（§1.6） | §1.6 |
| B7 | local realpath が object identity に不足 | 初期は Box stable ID 限定、local は stat identity(device/inode/generation)+parent、dispatch 直前再照合（§1.1） | §1.1 |
| B8 | G4/G10 の trusted input 契約不足 | chain 検証は genesis→tail 全体、lookup/active 列挙は検証済み ledger view 単一実装から供給（§1.6, §4） | §1.6, §4 |

---

## 0. 現状（解禁前）

`validator.validate_dispatch` §4.4 は `mutation=="mutating" ∧ ¬lease_subsystem_available
→ block`。boolean のみで「誰が・何の権限で・何を・いつまで」を検証しない。v0.2 で lease
実体検証を入れたが、(a) lease を認可と取り違える穴、(b) 実 operation と scope/target の
未拘束、(c) holder 自称、(d) ledger の event/並行性未定義 が残った。v0.3 でこれを閉じる。

---

## 1. データモデル

### 1.1 mutation target identity（B7）

- **初期解禁は Box object 限定**。key = `box:file:{file_id}` / `box:folder:{folder_id}`。
- local object は本リリースでは **dispatch 不可**（将来拡張）。拡張時は path 文字列でなく
  **stat identity**（`device:inode:generation`）+ parent namespace を保持し、grant 後の
  rename/path 再利用/hardlink/symlink 差替えに備え **dispatch 直前に再 stat 照合**、不一致は
  block（`target_identity_drift`）。create target は `parent_identity + basename` の別種別。
- realpath は alias 縮約の補助に留め、identity の正とはしない。

### 1.2 mutation operation registry（B2）

`next_action_type`（上位 schema enum: `design_patch/doc_patch/code_patch/test_patch/
refactor/required_materials/reject/ratify/none`）は **触らない**。mutating operation は
**別 field `mutation_op`** を新設し、固定 registry で定義する:

| `mutation_op` | required_scopes（導出） | lock_domains（導出, §1.3） |
|---|---|---|
| `box_file_move` | `{file_move}` | source item / source parent / destination parent |
| `box_metadata_set` | `{metadata_set}` | target item |
| `box_file_rename` | `{file_move}` | target item / parent |

- `required_scopes = derive(mutation_op, side_effect_flags)` は **local deterministic**。
  packet/worker は導出 scope を **縮小・上書きできない**（縮小要求は block `scope_understated`）。
- `side_effect_flags` は規範 enum に固定し、registry と齟齬があれば block
  （`op_sideeffect_inconsistent`）。registry 未登録 op は block（`mutation_op_unknown`）。

### 1.3 required lock domains（B3）

`required_lock_domains(packet) -> [{canonical_target_key, scope}, ...]` を registry から導出。
**全 domain について active かつ自分の lease が要る**。複数 lease は `canonical_target_key`
昇順で取得（deadlock 回避の canonical order）。一つでも欠ければ block
（`lock_domain_uncovered`）。

### 1.4 holder = trusted runtime identity（B4）

`holder = {assignee, machine_id, runner_instance_id, session_id?}`。

- **すべて dispatcher の認証済み Env から注入**（`trusted_runtime_holder`）。**primary identity
  は `runner_instance_id`**（worker 1 起動 = 1 値）、`session_id` は補助監査属性。
- packet 内 holder は **監査 echo のみ**。trusted 値と不一致なら block（`holder_spoofed`）。
- lease record の holder と trusted_runtime_holder の **合成完全一致**を要求（部分一致不可、
  欠落は `holder_underspecified`）。

### 1.5 lease ledger — event sourcing（B5）

append-only event log。record（1 行 = 1 event）:

```
{ lease_event_type: grant|release|revoke,
  lease_id, lease_event_id, sequence_no,
  canonical_target_key, scope[], holder{...},
  granted_at, expires_at,            // grant のみ
  prior_event_hash, record_hash }    // §1.6 chain
```

- **current state は valid chain 上の event fold で導出**（state を record に持たない）。
  grant→active、release/revoke→終了。同一 lease_id への release/revoke は同 id を参照。
- `expired` は **時刻評価で導出**（§3 TTL）。expiry は event として書かない（必要時のみ
  観測 event を別途）。延長は **旧 lease の release/expire 後の新 grant**（in-place 更新なし）。

### 1.6 ledger 原子性・並行・改ざん（B6, B8）

- 書き手は **single-writer daemon** 又は OS file lock / CAS で直列化。追記は `O_APPEND` +
  atomic record write + `fsync`。crash 時の **partial trailing line は quarantine** し読み飛ばさ
  ず block（`ledger_partial_tail`）。
- `lease_id` / `lease_event_id` は **UUIDv7**。duplicate は unique gate で block
  （`duplicate_event_id`）。`sequence_no` 連番、gap / fork は block（`ledger_sequence_gap` /
  `ledger_chain_fork`）。
- `prior_event_hash`+`record_hash`(sha256) で chain。さらに全履歴再 hash による改ざんを
  防ぐため **HMAC 署名（鍵は Env 管理）** を各 event に付す。「tamper-evident（hash chain）」
  と「tamper-proof（HMAC/外部 append-only）」を明示区別。検証は **genesis→tail 全 chain**
  （§4 G_chain）。
- ledger file は固定 path・固定 inode・symlink 禁止・secure open（`O_NOFOLLOW`）・所有者
  /permission 固定。逸脱は block（`ledger_unsafe_open`）。
- `lease_lookup` / `active_leases_for` は packet callback でなく **検証済み ledger view の
  単一実装**から供給（B8）。

---

## 2. 解禁条件（B1: 認可 ∧ 排他）

mutating dispatch 可は次の **AND**:

```text
mutation_dispatchable(packet) :=
    authorized(trusted_principal, mutation_op, lock_domains)   # 認可 gate (§4 A)
  ∧ ∀ d ∈ required_lock_domains: valid_exclusive_lease(d)      # 排他 gate (§4 L)
```

**lease 単独では認可を満たさない**。`authorized(...)` は別 policy で定義（§2.1）。

### 2.1 authorization policy

- `grant`/`release`/`revoke` の **issuer** と、mutation の **principal** を区別。両者とも
  trusted Env 由来。
- policy registry: `(principal, mutation_op, target_namespace) -> allow|deny`（version 付き）。
  既定 deny（fail-closed）。policy source・version・audit principal を record に残す。
- 自己発行 lease で認可を代替できない（lease issuer ≠ authorization source）。

---

## 3. TTL（時刻 semantics 固定）

- timestamp は **UTC tz-aware** で保存、表示のみ JST。`now >= expires_at` で expired。
- 検査: `granted_at < expires_at`、`TTL > 0`、future grant 許容幅（skew 上限）、clock skew。
- 既定 TTL **30 分**、上限 **2 時間**（超過 block `lease_ttl_exceeds_max`、無期限禁止）。
- runtime timeout は **monotonic clock**、監査記録は **wall clock** を使い分け。
- renewal = 旧 release/expire 後の新 grant（active 重複を作らない）。

---

## 4. validator gate（§4.4 置換・単一実装）

`Env` に: `lease_subsystem_available`(bool), `trusted_runtime_holder`,
`authorize(principal, op, domains)`, 検証済み ledger view（`lease_view`）, `now_utc`,
`hmac_verify`。gate 列（fail-closed）:

```
if mutation == "mutating":
  # --- 入力・registry ---
  G1  op = packet.get("mutation_op"); if op not in REGISTRY:   → block("mutation_op_unknown")
  G2  req_scopes = derive_scopes(op, packet.side_effect_flags)
      if scopes_understated(packet, req_scopes):               → block("scope_understated")
      if sideeffects_inconsistent(op, flags):                  → block("op_sideeffect_inconsistent")
  G3  domains = required_lock_domains(packet)                   # §1.3, canonical-sorted
      if any d.target not box-stable-id:                       → block("target_unsupported")  # B7 初期
  # --- ledger 健全性（B8, genesis→tail）---
  G_chain if not lease_view.chain_ok():                        → block("lease_ledger_tampered")
          # sequence gap/fork/partial tail/duplicate/HMAC fail を内包
  # --- 認可 gate (A) : B1 ---
  GA1 principal = env.trusted_runtime_holder
  GA2 if env.authorize(principal, op, domains) != ALLOW:       → block("mutation_unauthorized")
  # --- 排他 lease gate (L) : 全 domain ---
  for d in domains:
    L1 leases = env.lease_view.active_for(d.target_key, d.scope)   # 検証済み view
    L2 if len(leases) == 0:                                    → block("lock_domain_uncovered")
    L3 if len(leases) > 1:                                     → block("lease_double_active")
    L4 rec = leases[0]
    L5 if env.now_utc >= rec.expires_at:                       → block("lease_expired")
    L6 if d.scope not in rec.scope:                            → block("lease_scope_mismatch")  # 完全一致
    L7 if rec.holder != env.trusted_runtime_holder:            → block("lease_holder_mismatch")
    L8 if packet.lease_echo.holder != env.trusted_runtime_holder: → block("holder_spoofed")
  # 全 domain 通過 ∧ 認可 → mutating dispatchable（唯一の許可ケース）
```

検証は `handoff_proto/validator.py` の **単一実装**。運用ツールは import のみ
（operational must_fix #3 継続）。

---

## 5. 運用ツール側

- `handoff-lease`（`grant`/`release`/`revoke`/`list`）。発行・解放・取消は §1.5/§1.6 の
  event 追記。`grant` は同一 (target,scope) に active があれば失敗、authorize 不可なら失敗。
- `handoff-validate` は flag on のとき Env に lease subsystem + authorize + lease_view を結線。
  **flag 既定 off 継続**（operational must_fix #4）。
- mutating dispatch card は出すが **実 mutate は実行しない**。card は「認可済み・占有確認済み・
  実行可」の証跡。実行は別レーン（別 gate）。

---

## 6. スコープ境界

**解禁する**: Box stable ID object の mutating（file_move/metadata_set 等）を、(認可 ∧ 排他
lease) 下で **dispatch 可** と判定（card 生成まで）。

**解禁しない（HOLD 継続）**: mutating dispatch feature flag の運用解禁、lease grant/release の
operational 稼働、実 file_move/metadata_set/Box mutation、local object、external/paid/quota/
egress、本番 DB/DDL、canonical、SF 書戻し、card→実 mutate 自動連結。

---

## 7. 必須 fixture（GPT §5 を取り込み）

1. 自称 scope と実 operation 不一致 → `scope_understated`
2. side_effect 複数のうち一つだけ lease 被覆 → `lock_domain_uncovered`
3. file_move で destination namespace lease 欠落 → `lock_domain_uncovered`
4. packet holder 偽装と trusted Env 不一致 → `holder_spoofed`
5. unauthorized principal の grant / dispatch → `mutation_unauthorized`
6. concurrent grant で同 tail hash 競合 → fork 検出 block
7. partial trailing JSON / chain fork / sequence gap / duplicate lease_id → 各 block
8. release 後 / expire 後 / revoke 後の current state fold が正しい
9. path 再利用・rename・symlink 差替え・hardlink（local 拡張時）→ `target_identity_drift`
10. `now == expires_at` → expired（`>=`）
11. feature flag off で ledger write ゼロ
12. 全条件を満たす唯一の positive fixture → dispatchable
13. HMAC 不一致（全履歴再 hash 改ざん）→ `lease_ledger_tampered`

---

## 8. owner への問い（残論点）

1. 認可 policy registry の置き場（validator 同梱 / 別 policy file / 上位 schema 追加）。
2. `mutation_op` を上位 HANDOFF schema に正規追加するか、lease subsystem ローカル registry に留めるか。
3. HMAC 鍵管理（Env 注入で良いか / 将来の外部 append-only log への移行余地）。
4. local object 解禁は次々 gate で良いか（v0.3 は Box stable ID 限定で確定）。
