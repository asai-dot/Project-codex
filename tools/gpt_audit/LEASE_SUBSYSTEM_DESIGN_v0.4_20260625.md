# LEASE_SUBSYSTEM_DESIGN v0.4 — mutating レーン解禁の最小設計

- status: **draft (未ratify・未実装)** — 監査 gate 用（v0.3 LEASE_MODIFY_REQUIRED への patch）
- date: 2026-06-25
- 前段: `LEASE_SUBSYSTEM_DESIGN_v0.3`（result 2306525973159, **LEASE_MODIFY_REQUIRED**,
  v0.4 patch + offline fixtures GO / mutating dispatch 解禁・operational lease・実 mutate HOLD）
- 上位: `HANDOFF_SCHEMA_APPENDIX_v0.5` §4.4 / `HANDOFF_OPERATIONAL_IMPL_DESIGN_v0.1`
- 目的: mutating レーンを **(認可 ∧ 排他 lease)** 付きで **dispatch 可判定まで**解禁する最小設計。
  v0.4 は「本文だけで一意な fail-closed validator が実装可能」になるまで契約を固める。
  初期解禁対象は **Box stable ID object 限定**。実 mutate・external は別 gate。

## v0.3 → v0.4 差分（blocking B9–B16 対応表）

| # | v0.3 の穴 | v0.4 の手当て | 反映節 |
|---|---|---|---|
| B9 | gate 列から feature-flag 判定が脱落（回帰） | **G0** として最初に明記、flag off は authorize/ledger/card 一切なし block（§4 G0, §7 fx#0） | §4 G0 |
| B10 | `mutation_op` が上位 schema/packet hash に未接続 | HANDOFF DISPATCH schema に条件付き必須 field として正規追加（registry id/version/hash + digest 群）、packet hash 対象化（§2.1） | §2.1 |
| B11 | op 固有引数 schema 無く lock domain を一意導出不可 | op 別 **typed mutation_args** を固定、`required_lock_domains(args)` を純関数化、Box read で現状照合（§1.3, §2.2） | §1.3, §2.2 |
| B12 | packet が具体的 lease set に未固定 | packet に canonical-sorted `lease_refs[]`（lease_id/target/scope/grant_event_hash/expires_at）必須、`lease_set_digest` を hash 対象、active view と exact match（§2.3, §4 L） | §2.3, §4 |
| B13 | authorization registry 正本と principal 未確定 | 上位 HANDOFF versioned policy registry を正本、holder と authorization principal を別 field（§3） | §3 |
| B14 | event 遷移と sequence 粒度未定義 | 有効遷移を固定、global ledger sequence と per-lease ordinal 分離、invalid は view invalid で block（§1.5） | §1.5 |
| B15 | HMAC key lifecycle 未定義 | key id/version/algorithm・rotation・旧 key read-only verify・取得失敗 block・署名対象 bytes 固定（§1.6） | §1.6 |
| B16 | multi-lease partial failure 未処理 | acquisition attempt id・失敗時逆順 release・release 失敗は recovery queue、全 exact lease ref 成立時のみ dispatch（§2.4） | §2.4 |

B1/B4/B7/B8 は v0.3 で CLOSED/CLOSED_WITH_NOTES（本書でも維持）。B2/B3/B5/B6 の残りは上記で閉じる。

---

## 1. データモデル

### 1.1 mutation target identity（B7 維持）

初期解禁は Box object 限定。key = `box:file:{file_id}` / `box:folder:{folder_id}`。local object は
本リリース dispatch 不可（将来 gate）。

### 1.2 canonical_target_key

`box:file:{id}` / `box:folder:{id}` の stable ID 形式に正規化。形式外は block
（`target_unsupported`）。

### 1.3 required lock domains は引数の純関数（B3 残・B11）

`required_lock_domains(mutation_op, mutation_args) -> [{canonical_target_key, scope}, ...]` を
**typed args（§2.2）から決定的に**生成（純関数・I/O なし）。Box read で解決した現状
（parent/item type/etag）と args を別途照合（§4 G_args）。canonical_target_key 昇順。

### 1.4 holder = trusted runtime identity（B4 維持）

`holder = {assignee, machine_id, runner_instance_id, session_id?}`、すべて Env 注入、primary =
`runner_instance_id`。**holder は排他占有者であって認可主体ではない**（§3 で principal を別立て）。

### 1.5 lease ledger — event 遷移と sequence（B5 残・B14）

append-only event log。event:

```
{ lease_event_type: grant|release|revoke,
  lease_id, lease_event_id(UUIDv7),
  ledger_sequence_no,        // global 連番（ledger 全体）
  lease_event_ordinal,       // per-lease 連番（当該 lease_id 内）
  canonical_target_key, scope[], holder{...},
  granted_at, expires_at,    // grant のみ
  hmac_key_id, hmac,         // §1.6
  prior_event_hash, record_hash }
```

**有効遷移（固定）**:

```
absent   --grant-->   active
active   --release|revoke-->   terminal
active   --expire(時刻導出)-->  expired(terminal)
terminal --*-->  (状態変更 event 不可)
```

- current state は **valid chain 上の event fold** で導出。次は chain valid でも **view invalid
  として全 block**: release-before-grant / 二重 release / revoke-after-release / 同一 lease_id の
  複数 grant / terminal 後の状態変更 event（`lease_event_invalid_transition`）。
- `ledger_sequence_no`（global）と `lease_event_ordinal`（per-lease）を分離。gap / fork は block。
- `expired` は時刻導出（§ TTL）。

### 1.6 ledger 原子性・並行・改ざん・HMAC key lifecycle（B6 残・B15）

- single-writer daemon 又は OS file lock/CAS、`O_APPEND`+atomic write+`fsync`、partial trailing
  line は quarantine し block（`ledger_partial_tail`）。固定 path/inode・`O_NOFOLLOW`・symlink 禁止・
  所有者/permission 固定。逸脱 block（`ledger_unsafe_open`）。
- 各 event に `hmac_key_id` / `hmac_algorithm` / `hmac_key_version` と署名 `hmac`。**署名対象
  bytes** は record の canonical JSON（`hmac`/`record_hash` 除く）と固定。
- key rotation: 新 event は現行 key、**旧 event は旧 key で read-only verify**（key id で解決）。
  retirement 後も verify 用に保持。key 取得失敗は block（`hmac_key_unavailable`）。HMAC は鍵秘匿
  下の改ざん検知（tamper-evident）であり、同一鍵を持つ writer に対する tamper-proof ではない旨
  明記（将来 外部 append-only log）。
- `lease_lookup` / `active_for` は **検証済み ledger view 単一実装**から（B8）。chain 検証は
  genesis→tail 全体（HMAC + hash + sequence + transition を内包）。

---

## 2. dispatch packet / schema

### 2.1 HANDOFF DISPATCH schema 追加（B10。上位 schema patch 提案・canonical 化は HOLD）

`HANDOFF_SCHEMA_APPENDIX_v0.5` DISPATCH に次を **条件付き必須**で正規追加（mutation_class=
mutating のとき）:

```
mutation_op                       : enum, registry ref（cond req）
mutation_op_registry_id / version / content_hash
mutation_args                     : op 別 typed object（§2.2）
required_lock_domains_digest      : §1.3 純関数出力の digest
required_scopes_digest            : derive(op,flags) の digest
lease_set_digest                  : §2.3 lease_refs[] の digest
```

これら全てを **packet hash 対象**に含める。未知 op・欠落・digest 不一致は block。thin index へも
投影し staleness rule を適用。

### 2.2 typed mutation_args（B11）

```
box_file_move:
  source_file_id
  expected_source_parent_id
  destination_parent_id
  expected_source_etag_or_sequence?
box_metadata_set:
  target_item_type            # file|folder
  target_item_id
  metadata_template_scope / key
box_file_rename:
  target_item_id
  expected_parent_id
  new_name_digest_or_policy_ref
```

dispatch 直前に Box read で current parent/item type/etag を解決し args と照合、欠落/矛盾は block
（`mutation_args_mismatch`）。worker 自由文・path 推定は不可。

### 2.3 exact lease set binding（B12）

packet に canonical-sorted `lease_refs[]` 必須。各要素:
`{lease_id, canonical_target_key, scope, grant_event_hash, expires_at}`。`lease_set_digest` を
packet/card hash に含め、検証時に active view と **exact match**（§4 L）。実 mutation gate（別 gate）
でも再検証。これにより「古い packet が後発 lease で再通過」「検証時と実行時の lease すり替え」
「監査時にどの lease で許可されたか再現不能」を塞ぐ。

### 2.4 multi-lease 取得の partial failure（B16）

grant は canonical order。`acquisition_attempt_id` を持ち、N domain 中途で失敗したら **取得済みを
逆順 release**。release 失敗は **recovery queue** に載せ孤児 lease を可視化。dispatch は **全 exact
lease_refs 成立時のみ**許可（partial では不可）。

---

## 3. authorization（B13。lease と分離・上位 registry 正本）

- 正本は **上位 HANDOFF 配下の versioned policy registry**（validator は参照のみ・ハードコード禁止）。
  registry: `policy_id / version / content_hash`、`authenticated_actor | service_principal`、
  `credential_scope`、`target_namespace`、`allowed_operation`、`issuer_authority`。**既定 deny**。
- **holder（排他占有者）と authorization principal を別 field**にする。grant/release/revoke の
  **issuer** と mutation の **principal** を区別。自己発行 lease で認可代替不可。
- record に policy id/version/hash と authenticated principal を残す。

---

## 4. validator gate（§4.4 を置換・単一実装・fail-closed）

```
if mutation == "mutating":
  G0  if not env.lease_subsystem_available:                     → block("lease_required_but_unavailable")
      # flag off: authorize/ledger read/write/card を一切行わない (B9)
  G1  op = packet.mutation_op; if op not in REGISTRY:           → block("mutation_op_unknown")
      if packet.mutation_op_content_hash != REGISTRY[op].hash:  → block("mutation_op_registry_mismatch")
  G2  args = packet.mutation_args (typed §2.2); validate types  → else block("mutation_args_invalid")
  G_args resolve current via Box read; if mismatch args:        → block("mutation_args_mismatch")
  G3  req_scopes = derive_scopes(op, packet.side_effect_flags)
      if scopes_understated or digest != required_scopes_digest:→ block("scope_understated")
  G4  domains = required_lock_domains(op, args)                  # §1.3 純関数, canonical-sorted
      if digest != required_lock_domains_digest:                → block("lock_domains_digest_mismatch")
      if any d.target not box-stable-id:                        → block("target_unsupported")
  G_chain if not env.lease_view.chain_ok():                     → block("lease_ledger_tampered")
          # hash/HMAC/sequence/transition/partial-tail を内包 (B14/B15)
  # --- 認可 gate (B1/B13) ---
  GA  principal = env.trusted_principal
      if env.authorize(principal, op, domains) != ALLOW:        → block("mutation_unauthorized")
  # --- 排他 lease gate: 全 domain を exact lease_refs と突合 (B12) ---
  if digest(packet.lease_refs) != packet.lease_set_digest:      → block("lease_set_digest_mismatch")
  if domain set(lease_refs) != domains:                         → block("lease_set_incomplete")
  for ref in packet.lease_refs:                                  # canonical order
    actives = env.lease_view.active_for(ref.canonical_target_key, ref.scope)
    if len(actives) == 0:                                       → block("lock_domain_uncovered")
    if len(actives) > 1:                                        → block("lease_double_active")
    rec = actives[0]
    if rec.lease_id != ref.lease_id:                            → block("lease_set_mismatch")
    if rec.grant_event_hash != ref.grant_event_hash:            → block("lease_ref_stale")
    if env.now_utc >= rec.expires_at:                           → block("lease_expired")
    if ref.scope not in rec.scope:                              → block("lease_scope_mismatch")
    if rec.holder != env.trusted_runtime_holder:               → block("lease_holder_mismatch")
    if packet.lease_echo.holder != env.trusted_runtime_holder: → block("holder_spoofed")
  # 全通過 → mutating dispatchable（唯一の許可ケース・card に lease_set_digest を刻む）
```

検証は `handoff_proto/validator.py` 単一実装。運用ツールは import のみ。

---

## 5. TTL（B14 時刻 semantics）

UTC tz-aware 保存・表示のみ JST。`now_utc >= expires_at` で expired。`granted_at < expires_at`・
`TTL>0`・future grant skew 上限・clock skew 検査。既定 30 分／上限 2h（超過 block・無期限禁止）。
runtime timeout は monotonic、監査は wall clock。renewal = 旧 release/expire 後の新 grant。

---

## 6. スコープ境界

**解禁する**: Box stable ID object の mutating を (認可 ∧ 排他 lease) 下で **dispatch 可** 判定
（card 生成まで）。

**解禁しない（HOLD）**: mutating dispatch feature flag 運用解禁、operational な grant/release/
revoke、実 file_move/rename/metadata_set/Box mutation、local object、external/paid/quota/egress、
本番 DB/DDL、canonical、SF 書戻し、card→実 mutate 自動連結。

---

## 7. 必須 fixture（GPT §4 GO 項を取り込み）

- fx#0: **flag off で authorize/ledger read/write/card すべてゼロ・block**（B9）
- fx#1: mutation_op registry hash 不一致 → block
- fx#2: typed args 欠落/型違反 → `mutation_args_invalid`
- fx#3: Box read current parent と args 不一致（dest 差替え/source 古さ）→ `mutation_args_mismatch`
- fx#4: scope understatement / required_scopes_digest 不一致 → `scope_understated`
- fx#5: lock_domains_digest 不一致・domain 欠落 → block
- fx#6: lease_set_digest 不一致 / lease_refs と active view すり替え / grant_event_hash stale → 各 block
- fx#7: file_move で destination parent lease 欠落 → `lock_domain_uncovered`
- fx#8: holder 偽装 → `holder_spoofed`
- fx#9: unauthorized principal → `mutation_unauthorized`（既定 deny）
- fx#10: event 遷移違反（release-before-grant / 二重 release / revoke-after-release / 複数 grant /
  terminal 後）→ `lease_event_invalid_transition`
- fx#11: partial tail / chain fork / sequence gap / duplicate event_id / HMAC 不一致 → 各 block
- fx#12: HMAC key rotation 後の旧 event verify 成功 / key 取得失敗 block
- fx#13: multi-lease 3 件中 2 件取得後失敗 → 逆順 release・recovery queue・dispatch 不可
- fx#14: `now == expires_at` → expired
- fx#15: 全条件成立の唯一 positive → dispatchable

OS 別 atomicity property test（fsync/partial write）を併設。

---

## 8. owner への問い（残論点）

1. HANDOFF schema への `mutation_op`/`mutation_args`/`lease_refs` 追加は v0.4 で**提案**に留め、
   canonical patch は別 ratify gate で良いか（本書は HOLD 前提）。
2. authorization policy registry の version 管理主体（owner 単独 ratify か）。
3. HMAC 鍵の rotation 周期と保管（Env secret + key id で当面確定して良いか）。
4. recovery queue（孤児 lease）を誰が掃くか（運用ツール手動 release で v0.4 は十分か）。
