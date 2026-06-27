# LEASE_SUBSYSTEM_DESIGN v0.5 — mutating レーン解禁の最小設計

- status: **RATIFIED (design) — GPT Pro `LEASE_PASS_WITH_NOTES` / owner-ratified 2026-06-27 / asai。未実装**
  - 監査経緯: v0.1→v0.5 の 5 ラウンド GPT Pro design audit。v0.4 で新規 blocking が 8→2 に収束し、
    v0.5 で残 2 件（B11/B17）を CLOSED。**v0.5 result 2312201353719 = LEASE_PASS_WITH_NOTES**
    （reviewer: GPT-5.5 Pro / independent design re-audit, 2026-06-27）。
    ※ 先行 result 2309123924652 (NEED_MORE) は Box representation pending による取りこぼしで実体判断ではない。
  - PASS の射程は **dispatch 可判定の設計**まで。§10 の binding notes は **実装時に必達**。実 mutation /
    feature flag 運用解禁 / operational grant·release·revoke / 外部公開は引き続き **HOLD（別 gate）**。
  - 次工程: HANDOFF schema patch の ratify packet 作成 → **offline validator 実装 + negative fixtures**
    → Box stable ID 限定の synthetic prototype（いずれも GPT GO 範囲・実 mutate なし）。
- date: 2026-06-25
- 上位: `HANDOFF_SCHEMA_APPENDIX_v0.5` §4.4 / `HANDOFF_OPERATIONAL_IMPL_DESIGN_v0.1`
- 目的: mutating レーンを **(認可 ∧ 排他 lease ∧ payload 拘束)** 付きで **dispatch 可判定まで**
  解禁する最小設計。初期対象は **Box stable ID object 限定**。実 mutate・external は別 gate。

> **重要（スコープの正直な明示）**: 本設計が確定しても解禁されるのは「mutating dispatch **card を
> 出してよい**という判定」までで、**実ファイル移動・metadata 書込みは一切行われない**。実 mutation は
> §8 の別 gate であり、feature flag は引き続き既定 off。確定の意味は「実装に着手してよい安定した
> 設計が固まった」ことであって「mutate が動く」ことではない。

## v0.4 → v0.5 差分（残 blocking の閉塞）

| # | v0.4 残 | v0.5 の手当て | 反映節 |
|---|---|---|---|
| B11 | mutation payload が packet/hash に未拘束 | `mutation_payload`/`immutable_payload_ref` + `mutation_payload_digest` + `conflict_policy` + `expected_item_type` + `expected_etag_or_sequence` を追加・hash 拘束、executor 渡し payload と digest 一致検査（§2.2, §4 G_payload） | §2.2, §4 |
| B17 | `lease_echo` が schema 未定義のまま参照 | **packet echo を廃止**。holder は trusted Env 由来のみで照合（spoof 対象が存在しない）。§4 から echo 比較を削除 | §1.4, §4 L |
| B10 | schema patch が未 pin | schema patch の version/hash を pin、未 ratify schema では mutating card 生成不可（`target_schema_unratified`）（§2.1） | §2.1, §4 G_schema |
| B12 | lease_refs sort/dup 注記 | target+scope で canonical sort・duplicate 拒否（§2.3, §4 L0） | §2.3 |
| B13 | policy staleness 注記 | packet に policy id/version/content_hash + authenticated principal を hash 拘束、policy 変更で再 dispatch 必須（§3） | §3 |
| B14 | event type 別 schema 注記 | event type 別 schema を固定（grant-only field は release/revoke で不可）（§1.5） | §1.5 |
| B16 | recovery queue 運用注記 | queue の正本/idempotency/retry 上限/掃除主体は **operational gate 前の runbook** として明示繰延（§2.4） | §2.4 |
| B18 | actual mutation gate 再検証 | **次 gate の契約**として §8 に明記（本版未実装） | §8 |

B1/B4/B7/B8/B9 は確定クローズ。B2/B3/B5/B6 は v0.3–v0.4 で閉塞済み。

---

## 1. データモデル

### 1.1 mutation target identity（確定）

初期は Box object 限定。key = `box:file:{file_id}` / `box:folder:{folder_id}`。local は別 gate。

### 1.2 canonical_target_key

`box:file:{id}` / `box:folder:{id}` の stable ID 形式へ正規化。形式外は block（`target_unsupported`）。

### 1.3 required lock domains（純関数）

`required_lock_domains(mutation_op, mutation_args) -> [{canonical_target_key, scope}, ...]` を typed
args から決定的生成（I/O なし）。Box read で解決した現状と args を別途照合（§4 G_args）。
canonical_target_key 昇順。

### 1.4 holder = trusted runtime identity（確定・echo 廃止 / B17）

`holder = {assignee, machine_id, runner_instance_id, session_id?}`、すべて Env 注入、primary =
`runner_instance_id`。**packet 側 holder echo は廃止**。holder は信頼境界内（Env）からのみ取得し、
各 active lease record の holder と直接照合する（packet から来ないので spoof 対象が無い）。holder は
排他占有者であり、**認可主体ではない**（§3 で principal を別立て）。

### 1.5 lease ledger — event sourcing（確定 + event 型別 schema / B14）

append-only event log。event 型別 schema を固定:

```
grant   : { lease_event_type:"grant", lease_id, lease_event_id(UUIDv7),
            ledger_sequence_no, lease_event_ordinal,
            canonical_target_key, scope[], holder{...},
            granted_at, expires_at,            // grant のみ required
            hmac_key_id, hmac_key_version, hmac_algorithm, hmac,
            prior_event_hash, record_hash }
release : { lease_event_type:"release", lease_id, lease_event_id, ledger_sequence_no,
            lease_event_ordinal, hmac*..., prior_event_hash, record_hash }  // grant-only field 不可
revoke  : { ... release と同形, lease_event_type:"revoke", revoke_reason? }
```

**有効遷移（固定）**: `absent --grant--> active`、`active --release|revoke--> terminal`、
`active --expire(時刻導出)--> expired(terminal)`、`terminal --*--> 不可`。
current state は valid chain 上の fold。release-before-grant / 二重 release / revoke-after-release /
複数 grant / terminal 後 event / grant-only field を非 grant に含む → **view invalid で block**
（`lease_event_invalid_transition`）。`ledger_sequence_no`(global) と `lease_event_ordinal`(per-lease)
分離、gap/fork は block。`expired` は時刻導出（§5）。

### 1.6 ledger 原子性・並行・HMAC（確定）

single-writer/OS lock、`O_APPEND`+atomic write+`fsync`、partial trailing line は quarantine し block
（`ledger_partial_tail`）。固定 path/inode・`O_NOFOLLOW`・symlink 禁止・所有者/permission 固定
（逸脱 `ledger_unsafe_open`）。各 event に `hmac_key_id/version/algorithm` + 署名 `hmac`（署名対象 =
`hmac`/`record_hash` 除く canonical JSON）。key rotation: 新 event 現行 key、旧 event は旧 key で
read-only verify、取得失敗 block（`hmac_key_unavailable`）。HMAC は tamper-evident（同一鍵 writer に
対する tamper-proof ではない／将来 外部 append-only log）。`lease_lookup`/`active_for` は検証済み
ledger view 単一実装から。chain 検証は genesis→tail 全体。
（rotation 周期・鍵保管主体は operational gate 前に確定で可。）

---

## 2. dispatch packet / schema

### 2.1 HANDOFF DISPATCH schema 追加（B10 確定・pin）

mutation_class=mutating で条件付き必須:

```
mutation_op / mutation_op_registry_id / version / content_hash
mutation_args                         # §2.2 typed
mutation_payload | immutable_payload_ref   # §2.2 (B11)
mutation_payload_digest
conflict_policy                        # 例: no_overwrite / fail_on_conflict
required_lock_domains_digest / required_scopes_digest / lease_set_digest
authz_policy_id / version / content_hash / authenticated_principal   # §3 (B13)
target_schema_id / target_schema_version / target_schema_hash        # 本 patch の pin
```

全て **packet hash 対象**。schema patch（本追加）の version/hash を pin し、**未 ratify schema では
mutating card を生成しない**（§4 G_schema → `target_schema_unratified`）。未知 op・欠落・digest
不一致は block。canonical HANDOFF schema への正規反映は **別 ratify gate**（本書は提案 pin）。

### 2.2 typed mutation_args + payload binding（B11 確定）

```
共通: expected_item_type, expected_etag_or_sequence(変更可能 object は required), conflict_policy
box_file_move:
  source_file_id, expected_source_parent_id, destination_parent_id, expected_source_etag_or_sequence
box_metadata_set:
  target_item_type, target_item_id, metadata_template_scope, metadata_template_key,
  mutation_payload(field/value) | immutable_payload_ref, mutation_payload_digest
box_file_rename:
  target_item_id, expected_parent_id,
  new_name | immutable_payload_ref, mutation_payload_digest   # actual name を digest 照合
```

- dispatch 直前に Box read で current parent/item type/etag を解決し args と照合、欠落/矛盾は block
  （`mutation_args_mismatch`）。
- **payload は packet hash 内に拘束**。validator は packet-hash 内 payload と executor へ渡す payload の
  **digest 一致**を検査（§4 G_payload, `payload_digest_mismatch`）。**payload を後段の自由文・別入力から
  補ってはならない**。
- `conflict_policy` 既定 no_overwrite。`expected_etag_or_sequence` は変更可能 object で required
  （欠落 block `expected_state_required`）。

### 2.3 exact lease set binding（B12 確定）

packet に `lease_refs[]`（要素 `{lease_id, canonical_target_key, scope, grant_event_hash, expires_at}`）
を **target+scope で canonical sort**、duplicate 拒否（`lease_refs_duplicate`）。`lease_set_digest` を
packet/card hash に含め、active view と exact match（§4 L）。

### 2.4 multi-lease partial failure（B16 確定 + 運用繰延）

grant は canonical order、`acquisition_attempt_id` 保持、中途失敗で取得済みを逆順 release、release
失敗は recovery queue へ。dispatch は全 exact lease_refs 成立時のみ。**recovery queue の正本・
idempotency・retry 上限・掃除主体は operational gate 前の runbook で確定**（本 design では繰延を明示）。

---

## 3. authorization（B13 確定）

- 正本は **上位 HANDOFF versioned policy registry**（validator 参照のみ・ハードコード禁止）:
  `policy_id/version/content_hash`、`authenticated_actor|service_principal`、`credential_scope`、
  `target_namespace`、`allowed_operation`、`issuer_authority`。**既定 deny**。
- packet は `authz_policy_id/version/content_hash` + `authenticated_principal` を **hash 拘束**。
  **policy 変更（version 進行）で packet は stale → 再 dispatch 必須**（`authz_policy_stale`）。
- holder（排他占有者）と authorization principal を別 field。grant/release/revoke の issuer と
  mutation の principal を区別。自己発行 lease で認可代替不可。
- registry の version 管理主体（owner ratify）は operational gate 前に確定で可。

---

## 4. validator gate（§4.4 置換・単一実装・fail-closed）

```
if mutation == "mutating":
  G0      if not env.lease_subsystem_available:               → block("lease_required_but_unavailable")
  G_schema if packet.target_schema_* not ratified-pin:        → block("target_schema_unratified")
  G1      op=packet.mutation_op; if op not in REGISTRY:        → block("mutation_op_unknown")
          if packet.mutation_op_content_hash != REGISTRY[op].hash: → block("mutation_op_registry_mismatch")
  G2      args=packet.mutation_args(typed); validate          → else block("mutation_args_invalid")
          if mutable object and no expected_etag_or_sequence:  → block("expected_state_required")
  G_args  resolve current via Box read; if mismatch:          → block("mutation_args_mismatch")
  G_payload if digest(packet.mutation_payload|ref) != packet.mutation_payload_digest: → block("payload_digest_mismatch")
  G3      req_scopes=derive(op,flags)
          if understated or digest!=required_scopes_digest:    → block("scope_understated")
  G4      domains=required_lock_domains(op,args)               # canonical-sorted
          if digest!=required_lock_domains_digest:             → block("lock_domains_digest_mismatch")
          if any d.target not box-stable-id:                   → block("target_unsupported")
  G_chain if not env.lease_view.chain_ok():                    → block("lease_ledger_tampered")
  GA      principal=env.trusted_principal
          if packet.authz_policy_version != registry.current:  → block("authz_policy_stale")
          if env.authorize(principal,op,domains)!=ALLOW:       → block("mutation_unauthorized")
  L0      if lease_refs not canonical-sorted or has dup:       → block("lease_refs_duplicate")
          if digest(lease_refs)!=lease_set_digest:             → block("lease_set_digest_mismatch")
          if domain_set(lease_refs)!=domains:                  → block("lease_set_incomplete")
  for ref in lease_refs:                                        # canonical order
    actives=env.lease_view.active_for(ref.canonical_target_key, ref.scope)
    if len==0: → block("lock_domain_uncovered");  if len>1: → block("lease_double_active")
    rec=actives[0]
    if rec.lease_id!=ref.lease_id:           → block("lease_set_mismatch")
    if rec.grant_event_hash!=ref.grant_event_hash: → block("lease_ref_stale")
    if env.now_utc>=rec.expires_at:          → block("lease_expired")
    if ref.scope not in rec.scope:           → block("lease_scope_mismatch")
    if rec.holder!=env.trusted_runtime_holder: → block("lease_holder_mismatch")   # echo 廃止 (B17)
  # 全通過 → mutating dispatchable（唯一の許可・card に lease_set_digest と payload_digest を刻む）
```

検証は `handoff_proto/validator.py` 単一実装。運用ツールは import のみ。

---

## 5. TTL（確定）

UTC tz-aware 保存・表示のみ JST。`now_utc>=expires_at` で expired。`granted_at<expires_at`・TTL>0・
future grant skew 上限・clock skew 検査。既定 30 分／上限 2h（超過 block・無期限禁止）。runtime は
monotonic、監査は wall clock。renewal=旧 release/expire 後の新 grant。

---

## 6. スコープ境界

**解禁する**: Box stable ID object の mutating を (認可 ∧ 排他 lease ∧ payload 拘束) 下で **dispatch
可** 判定（card 生成まで）。

**解禁しない（HOLD）**: feature flag 運用解禁、operational な grant/release/revoke、実 file_move/
rename/metadata_set/Box mutation、local object、external/paid/quota/egress、本番 DB/DDL、canonical、
SF 書戻し、card→実 mutate 自動連結。

---

## 7. 必須 fixture（実装時）

flag off 全停止(fx0) / op registry hash 不一致 / typed args 欠落・型違反 / Box current と args 不一致 /
payload digest 不一致(metadata values 差替え・rename actual name 不一致) / scope understatement /
lock_domains digest 不一致 / lease_set すり替え・grant_event_hash stale・lease_refs 重複/順序違反 /
dest parent lease 欠落 / unauthorized principal(既定 deny) / authz_policy version 変更で stale /
event 遷移違反(各種) / partial tail・fork・gap・dup event・HMAC 不一致 / key rotation 後 旧 verify・
取得失敗 block / multi-lease partial→逆順 release・queue / `now==expires_at`→expired / 未 ratify
schema で card 生成拒否 / 全条件成立の唯一 positive→dispatchable。OS 別 atomicity property test 併設。

---

## 8. 次 gate の契約（B18・本版は未実装の記述のみ）

実 mutation は別 gate。その gate では dispatch card から実行までの drift を塞ぐため、**実行直前に
再検証**する契約とする（v0.5 では実装しない／設計の前方拘束のみ）:

- feature flag、authorization policy(id/version/hash)、packet hash、`mutation_payload_digest`、
  Box current state（etag/parent/item type/name conflict）、全 `lease_refs`、`expires_at` を再検証。
- いずれか 1 つでも変化 → block（card は実行許可ではなく「その時点の許可証跡」に過ぎない）。
- conflict_policy(no_overwrite 等) を実行側で強制。

---

## 9. 監査依頼（v0.5・decision_requested）

- v0.4 残 blocking（B11 payload binding / B17 lease_echo）が閉じたか。
- §4 の G0→…→L gate 列で、本文だけから一意な fail-closed validator が実装可能か（実装一意性）。
- §8 の次 gate 再検証契約の前方拘束が妥当か。
- 繰延事項（HANDOFF schema canonical patch / authorization registry version 管理 / HMAC 鍵運用 /
  recovery queue runbook）を operational gate 前に回す切り方の是非。
- feature flag 既定 off 継続・単一実装維持の確認。

---

## 10. binding notes（v0.5 PASS_WITH_NOTES の付帯条件・実装時必達）

GPT Pro 監査 result 2312201353719 が PASS の条件として課した事項。実装/ratify packet で必ず満たす:

1. **payload digest 確定**: `mutation_payload_digest` の対象 bytes と canonicalization を固定する。
   `immutable_payload_ref` 利用時は **ref 先の version/hash も packet hash に拘束**する。
2. **expected_state 必須**: mutable object では `expected_etag_or_sequence` を required とし、
   実行側で `conflict_policy`（no_overwrite 等）を **再検証**する。
3. **policy はハードコード禁止**: policy id/version/content_hash・authenticated principal・
   credential_scope・target_namespace・allowed_operation・issuer_authority は上位 HANDOFF policy
   registry に置き、validator 内ハードコードを禁止する。
4. **未 ratify schema は card 生成不可**: canonical HANDOFF schema へ正式反映されるまで実 card 生成は
   HOLD。`target_schema_unratified` の negative fixture を必須化する。
5. **HMAC lifecycle**: key id/version/algorithm・旧 key read-only verify・key 取得失敗 block までを実装。
   rotation 周期・鍵保管主体・外部 append-only log 採否は operational gate 前に確定で可。
6. **multi-lease partial failure**: 逆順 release / recovery queue 投入 / idempotency / retry 上限 /
   掃除主体は operational gate 前の runbook で確定（design では繰延を明示で足りる）。
7. **§8 実行直前再検証**: 実 mutation gate で feature flag・authz policy・packet hash・
   `mutation_payload_digest`・Box current state・全 `lease_refs`・`expires_at` を再検証し、
   1 つでも変化すれば block。

これらは **design ratify を止める blocker ではなく、offline validator 実装・ratify packet で満たすべき
具体化事項**（GPT 監査 §3 Binding notes / §4 必須 fixture を写経）。
