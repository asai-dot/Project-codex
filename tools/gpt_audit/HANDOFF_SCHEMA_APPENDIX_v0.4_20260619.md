# HANDOFF_SCHEMA_APPENDIX v0.4 — 共有パケットスキーマ登録簿（**規範的単一正本**）

- status: **draft (未ratify・未実装)**
- date: 2026-06-22
- revision: v0.3 → v0.4。`HANDOFF_MODIFY_REQUIRED`
  (`20260621_head_hand_handoff_design_v0.4_GPTPRO_AUDIT_RESULT.md` / 2300911710513)
  の v0.5 blocking（#5 per-attempt reconciliation / #6 hash runtime_envelope・unavailable /
  MF-2 resource_descriptor・audit_sensitive 直交化・free_bounded 上限）を反映。
- 前 revision: v0.2 → v0.3 で v0.4 must_fix 10件（3軸分離ほか）を反映済み。
- **規範性宣言**: 本付録が `assignee`/`role`/パケットスキーマ/3軸 effect 判定/
  reconciliation の**唯一の規範的正本**。`HEAD_HAND_HANDOFF_DESIGN` /
  `WORKER_DELEGATION_DESIGN` 本文の YAML は **non-normative example**。本付録は他文書へ
  正本を再委譲しない。
- owner 決定（2026-06-20 / 2026-06-21）:
  - role モデル = **governance_role / execution_role 分離**（§1.2）。
  - **effect は3軸**（§4）: `mutation_class`（lease）/ `egress_decision`（機密送信）/
    `resource_effect_class`（課金・quota・rate-limit・外部ログ）。read は **mutation 軸では
    non_mutating**。無償 public read は広く通す。**有料/quota/rate-limited read は resource
    permit 必須＝permit subsystem 不在なら fail-closed で blocked**（owner 決定）。

凡例: req=必須 / opt=任意 / cond=条件付き必須。

---

## 1. 語彙（enum・規範）

### 1.1 基本 enum

| enum | 許可値 |
|---|---|
| `assignee` | `local`, `codex`, `worker_cc` |
| `assignee` 禁止値 | `gpt`, `gpt_pro`, `claudehead`, `head`, `auditor`, `owner` |
| `governance_role` | `supervisor`, `auditor`, `owner` |
| `execution_role` | `worker`, `deterministic` |
| `assignee_source` | `front_matter`, `gate_override`, `action_default` |
| `next_action_type` | `design_patch`, `doc_patch`, `code_patch`, `test_patch`, `refactor`, `required_materials`, `reject`, `ratify`, `none` |
| `mutation_class` | `non_mutating`, `mutating` |
| `egress_decision` | `none`, `allowed`, `blocked` |
| `resource_effect_class` | `none`, `free_bounded`, `quota_metered`, `paid`, `rate_limited`（**`audit_sensitive` を撤去**・§4.5 で直交属性化） |
| `external_audit_logging`（直交属性・MF-2B） | `none`, `expected`, `sensitive` |
| `result_status` | `done`, `blocked`, `needs_more`, `proposal` |
| `index_status` | `queued`, `dispatched`, `result_in`, `closing`, `closed` |
| `reconciliation_relation` | `representative`, `duplicate`, `stale_generation`, `invalid`, `conflict` |
| `version_ref_type` | `box_file_version`, `git_blob`, `local_snapshot` |
| `block_reason` | `lease_required_but_unavailable`, `resource_permit_unavailable`, `egress_forbidden`, `stale_packet`, `access_class_unknown`, `assignee_incompatible`, `oversize_no_reason`, `invalid_assignee`, `ratify_not_dispatchable` |
| `hash_status` | `verified`, `unavailable` |

### 1.2 governance_role / execution_role 分離（owner 決定）

DISPATCH（実行パケット）が持てる `execution_role` は `worker`|`deterministic` のみ。
`supervisor`/`auditor`/`owner` は実行レーンに出さず gate metadata（`governance_role`）。

| 局面 | governance_role | execution_role | assignee |
|---|---|---|---|
| 分解・差配・統合 | `supervisor`（claudehead） | — | — |
| 設計改稿・重い文書 | — | `worker` | `worker_cc` |
| 実装・テスト・リファクタ | — | `worker` | `codex` |
| 事務・探索・移動・単一書き手 | — | `deterministic` | `local` |
| 独立監査 | `auditor`（GPT Pro） | — | — |
| ratify | `owner` | — | — (`owner_pending`) |

- `next_action_type=ratify` は **DISPATCH を生成しない**（schema constraint・§3 注記、
  違反は `block_reason=ratify_not_dispatchable`）。`owner_pending` として実行レーン外。
- enum 外語彙（architect/drafter/clerk 等）は廃止。

## 2. thin index スキーマ（規範）

| field | req/opt | 型 | 備考 |
|---|---|---|---|
| `packet_id` | req | str | |
| `packet_generation` | req | int | active generation 判定（§5） |
| `source_queue_item_id` | req | str | |
| `decision_id` | req | str | |
| `assignee` | req | enum | |
| `execution_role` | req | enum | |
| `next_action_type` | req | enum | |
| `mutation_class` | req | enum | local 導出（§4） |
| `egress_decision` | req | enum | local 導出（§4） |
| `resource_effect_class` | req | enum | local 導出（§4） |
| `index_status` | req | enum | |
| `hold_flags` | req | list | local 導出・縮小不可 |
| `risk_class` | req | str | |
| `gate` | req | str | |
| `data_access_class` | req | str | registry ref（§7） |
| `priority` | opt | str | |
| `objective_oneline` | req | str | |
| `packet_ref` | req | path | |
| `result_ref` | cond | path | 閉鎖時 |

`owner_pending`（ratify 待ち）は `index_status` に含めず別キュー。

## 3. DISPATCH スキーマ（規範。`packet_schema_version: handoff-dispatch/0.5`）

identity/integrity（§6）, routing, **3軸 effect（§4）**, gate/access（§7）, work,
size/staleness（§8）, return（§3.1）。主要 field:

| field | req/opt | 備考 |
|---|---|---|
| `packet_schema_version` | req | `handoff-dispatch/0.5` |
| `packet_id` / `packet_generation` / `packet_created_at_jst` | req | generation は修正版で +1 |
| `hash_algorithm` | req | `sha256` |
| `hash_basis` | req | `rfc8785_jcs`（§6・単一方式） |
| `hash_scope_version` | req | `handoff-packet-hash/3` |
| `packet_hash` | req | local が render 後・公開前に計算。**`attempt_id` を含めない**（§5.1） |
| `excluded_from_hash` | req | hash 除外 field の完全列挙（§6） |
| `source_queue_item_id` / `decision_id` | req | |
| `source_request_id` | opt | |
| `source_artifacts` | req | §6（`version_ref_type` 型付き） |
| `governance_role` | cond | gate metadata。実行パケットでは通常空 |
| `execution_role` | req | `worker`\|`deterministic` |
| `assignee` / `assignee_source` | req | invalid 明示値は **validation error**（黙って fallback しない・§7） |
| `next_action_type` | req | `ratify` は dispatch 生成禁止（§1.2） |
| `mutation_class` | req | local 導出（§4） |
| `egress_decision` | req | local 導出（§4） |
| `resource_effect_class` | req | local 導出（§4） |
| `side_effect_flags` | req | §4.1（**状態変更のみ**） |
| `egress_descriptor` | cond | egress を伴う場合 req（§4.4） |
| `resource_descriptor` | cond | resource_effect ≠ none 時 req（規範 schema §4.5） |
| `external_audit_logging` | req | `none`\|`expected`\|`sensitive`（resource と直交・§4.5 MF-2B） |
| `result_artifact_exception` | req | bool（§4.2・一意 RESULT 本体に限定） |
| `lease_required` | req | bool（mutating ⇒ true） |
| `resource_permit_required` | req | bool（quota_metered/paid/rate_limited ⇒ true） |
| `gated_override_block` | req | `true` |
| `hold_echo` | req | local 導出・縮小不可 |
| `data_access_class` | req | registry ref＋version。不明は dispatch 禁止（§7） |
| `allowed_assignees` | req | access policy registry から local 導出・縮小のみ可（§7） |
| `external_egress_allowed` | req | 既定 `false` |
| `prohibited_actions` | req | list |
| `objective` | req | |
| `context_closure` | req | `context_closure_index`{`inlined`,`referenced`[{`ref`,`digest`,`why`}]}, `pull_branch`, `excerpts` |
| `inputs` / `do` / `acceptance` | req | |
| `soft_cap_bytes` | req | int（§8） |
| `size_policy_version` | req | （§8・v0.3 で規範 field 化） |
| `oversize_reason` / `must_read_sections` | cond | cap 超過時 req |
| `staleness_policy` | req | §8 |
| `output_contract` | req | §3.1 |
| `proposal_only` | req | bool |
| `clarification_budget` | req | 既定 0 |

### 3.1 output_contract（規範・attempt 衝突回避）

| field | req | 備考 |
|---|---|---|
| `output_root` | req | allowlisted root 配下のみ。traversal/任意 Box target は reject |
| `output_path_template` | req | `<output_root>/<packet_id>/<attempt_id>_RESULT.md` |
| `write_mode` | req | `create_new_no_overwrite` |
| `upload_target_root` | req | allowlisted root |
| `required_fields` | req | **§9 RESULT の req field 一式**（v0.2 の §4 参照誤りを訂正） |

## 4. 3軸 effect 判定（規範・v0.4 must_fix #1/#2）

effect は3独立軸。local dispatcher が決定的に導出。front-matter/worker は安全側へしか
動かせない。**各軸 unknown は安全側（mutating / egress blocked / resource は permit 要求）。**

```text
mutation_class         = non_mutating | mutating        → 永続/共有状態 write に lease
egress_decision        = none | allowed | blocked       → egress_descriptor + data_access_class
resource_effect_class  = none | free_bounded | quota_metered | paid | rate_limited
                                                        → resource permit / semaphore
external_audit_logging = none | expected | sensitive    → resource と直交（§4.5 MF-2B）
```

### 4.1 side_effect_flags（**状態変更のみ**。paid/egress は除外）

`persistent_write`, `shared_namespace_write`, `file_move`, `external_write`,
`destructive`, `production_effect`。いずれか立てば `mutating`（§4.2 例外を先に適用）。
**`paid_or_quota_call` と `data_egress` は本リストから除外**し、それぞれ resource 軸・
egress 軸へ移す（v0.2 の自己矛盾を解消）。

### 4.2 RESULT artifact 例外

指定された**一意の RESULT 本体を書くだけ**の transport write は non_mutating に例外化。
条件: attempt 固有 path＋`create_new_no_overwrite`。**shared cache / index / route card /
metadata 更新は含めない**（含めば mutating）。

### 4.3 read 決定表（owner 決定・3軸）

| ケース | mutation_class | egress_decision | resource_effect_class | dispatch 可否 |
|---|---|---|---|---|
| local/offline read | non_mutating | none | none | OK |
| allowlisted public GET | non_mutating | allowed(`public_query`) | free_bounded | OK |
| quota/有料 read | non_mutating | policy 適合 | quota_metered / paid | **permit あれば OK・無ければ `blocked/resource_permit_unavailable`** |
| rate-limited read | non_mutating | policy 適合 | rate_limited | 同上（semaphore/permit 必須） |
| 機密 query を外部送信する read | non_mutating | **blocked**（明示許可 destination/payload policy がある場合のみ allowed） | 実態に応じ | egress 不許可なら `blocked/egress_forbidden` |
| shared cache へ永続 write を伴う read | **mutating** | 実態 | 実態 | lease 必須（RESULT artifact 例外と別） |

### 4.4 egress_descriptor（§7 と連動）

`egress_policy_id`＋`version`, `allowed_destinations` または `destination_class`,
`outbound_payload_class`, `request_field_allowlist`, `credential_scope`,
`external_logging_profile`, `retention_or_terms_profile`。公開 GET も外部観測（URL/query/
IP/認証主体）を生むため「対象外」にせず `public_query` として明示 allowlist。

### 4.5 resource_descriptor schema ＋ fail-closed（MF-2A/2B/2C）

**MF-2A: `resource_descriptor` を規範 schema 化**（resource_effect_class ≠ none 時 req）。

| field | req/opt | 備考 |
|---|---|---|
| `resource_policy_id` | req | |
| `resource_policy_version` | req | |
| `provider_or_service` | req | |
| `operation_class` | req | |
| `resource_effect_class` | req | §1.1 enum |
| `estimated_units` | cond | 不明時は §safe default |
| `unit_type` | req | call / token / byte / request 等 |
| `maximum_units` | req | 上限。超過は blocked |
| `budget_or_quota_scope` | req | |
| `permit_ref` | cond | permit 必須クラスで req |
| `permit_expires_at` | cond | permit_ref 有時 req |
| `semaphore_or_rate_key` | cond | rate_limited 時 req |
| `external_logging_profile` | req | `external_audit_logging` と連動 |

`estimated_units` 不明時の safe default = **`maximum_units` を要求し、無ければ
permit-required へ倒す**（保守側）。

**permit 判定 ＋ fail-closed**: `resource_effect_class ∈ {quota_metered, paid,
rate_limited}` は `resource_permit_required: true`。

```text
resource_permit_required == true AND resource_permit_subsystem_available == false
  => dispatchable=false ; result_status=blocked ; block_reason=resource_permit_unavailable
```

override 不可。permit subsystem 実装まで該当 call は配布・実行しない。

**MF-2B: `audit_sensitive` を直交属性化。** `resource_effect_class` enum からは撤去し、
`external_audit_logging = none | expected | sensitive` を**独立 field**として持つ
（resource class と直積で評価）。これにより `paid かつ audit-sensitive` のような複合状態を
表現できる。`external_audit_logging=sensitive` は audit permit 又は明示 policy
acknowledgement を必須とし、無ければ blocked。第4軸ではなく resource descriptor 内の
直交属性である。

**MF-2C: `free_bounded` の bounded 条件を registry 化。** 「無償・固定 rate・cache 可」だけ
では local が決定できないため、policy registry に `max_requests` / `time_window` /
`payload_limit` / `retry_ceiling` / `cache_write_allowed` を置く。**上限不明は
`rate_limited`（permit-required）へ倒す**。retry 超過・上限超過も blocked。

## 5. attempt と重複結果調停（規範）

### 5.1 attempt_id（v0.4 must_fix #4）

- attempt 開始時に **local または worker runtime が UUIDv7 等で発番**。
- packet identity / grouping から**独立**。
- **`packet_hash` に含めない**（含めると同一 packet の複数 attempt が別 hash になり active
  generation dedup group から外れる）。
- RESULT へ echo。`create_new_no_overwrite` で一意性確保。

### 5.2 reconciliation event schema（local-only・per-attempt・#5 blocking 反映）

event 単一 `relation` では representative＋duplicate＋invalid 混在を表現できないため、
**per-attempt relation を必須化**する（v0.4 監査 #5）。

| field | req/opt | 備考 |
|---|---|---|
| `reconciliation_id` | req | |
| `grouping_key` | req | `source_queue_item_id + packet_generation + packet_hash`（§5.3） |
| `source_queue_item_id` | req | |
| `packet_generation` | req | |
| `packet_hash` | req | |
| `attempt_relations` | req | list（下記）。各 attempt の関係を個別表現 |
| `representative_attempt_id` | **nullable** | conflict / 全 invalid 時は `null`（常時 req にはできない） |
| `needs_head_resolution` | req | bool |
| `recorded_at` | req | |

`attempt_relations[]` の要素:

| field | req/opt | 備考 |
|---|---|---|
| `attempt_id` | req | |
| `relation` | req | `reconciliation_relation` enum |
| `related_to_attempt_id` | cond | duplicate/stale 等の基準 attempt |
| `basis_codes` | req | 選定根拠コード list |
| `acceptance_grade` | req | local 算定（worker 自己申告でない） |
| `output_hash_state` | req | 例: matches_representative / divergent / absent |

`representative_attempt_id` の required/nullable: 代表が一意に決まる場合 req、
`conflict`（意味衝突）又は全 `invalid` の場合は `null`＋`needs_head_resolution=true`。

### 5.3 grouping / 代表選定

- grouping = `source_queue_item_id + packet_generation + packet_hash`。古い generation は
  `stale_generation`。同一 generation の duplicate のみ代表選定。
- 代表選定: ①acceptance 合格 → ②output hash / semantic 同値なら earliest valid →
  ③片方のみ required evidence 完全なら完全側 → ④意味的衝突は `conflict` ＋
  `needs_head_resolution=true`（両保持・自動統合禁止） → ⑤不合格/不正は `invalid`。
- `evidence grade` は worker 自己申告でなく local が schema/acceptance から算定。
- semantic 同値判定の規則は §5.4。

### 5.4 semantic 同値（最小規範）

`output_artifact_hashes` 完全一致 = 同値。不一致時は acceptance_results の pass 集合が
一致しかつ宣言 outputs 集合が一致する場合のみ「弱同値」とし earliest valid 可。それ以外は
非同値として③④へ。

## 6. hash / source version（規範・v0.4 must_fix #6）

- `hash_algorithm: sha256`、`hash_basis: rfc8785_jcs`（**単一方式**。exact bytes 方式は廃止）、
  `hash_scope_version: handoff-packet-hash/3`。
- canonicalization: RFC 8785 (JCS)。ALO 前処理として文字列 NFC 正規化・改行 LF 統一を明記。
- `excluded_from_hash`（**包括語廃止・完全列挙**・#6）: `packet_hash` 自身、および
  `runtime_envelope` object の全 field。runtime が付加しうる値は独立 object
  `runtime_envelope` に隔離し packet hash 外に置く。`runtime_envelope` の規範 field:
  `attempt_id`, `attempt_started_at`, `runner_id`, `session_id`, `transport_meta`。
  hash 対象は **allowlist 方式**（hash 対象 schema を明示）とし、計算前後で payload 不変で
  あることを fixture（§10 F7）で確認。normative field 追加は hash 変化、runtime_envelope
  追加は hash 不変。
- `source_artifacts[]`:

  | field | req | 備考 |
  |---|---|---|
  | `ref` | req | id/path |
  | `version_ref_type` | req | `box_file_version`\|`git_blob`\|`local_snapshot` |
  | `version_ref` | req | 上記型の値 |
  | `digest` | cond | typed digest（取得不能時 null） |
  | `hash_status` | req | `verified`\|`unavailable` |
  | `unavailable_reason` | cond | `unavailable` 時 req |

- ライフサイクル: ①local が render 後・公開前に `packet_hash` 計算＋source version 固定 →
  ②worker が開始前に packet hash と source version 検証（不一致は `blocked/stale_packet`）→
  ③worker が output hash 計算し RESULT 記載 → ④local closer が echo/active generation/
  output existence・hash/acceptance を検証して index/ledger 更新。
- RESULT の `packet_hash` echo は必須。
- **`hash_status=unavailable` の扱い（#6 blocking）**: digest unavailable を無条件には許さない。
  1. integrity-required gate（owner/auditor/production/canonical 等）では digest unavailable は
     **`blocked`（`block_reason=stale_packet`）** に倒す。
  2. unavailable を許す非 integrity gate でも `version_ref`＋取得主体（fetcher）＋
     `unavailable_reason`＋**staleness 代替検査**（version_ref のみでの一致確認）を必須化。
  3. staleness_policy（§8）が `artifact_version_and_digest` を要求する gate では、digest 欠落は
     代替検査では満たせず `blocked`。

## 7. access / gate 境界（規範・v0.4 must_fix #8/#9）

- `data_access_class`: **registry ref＋version** を持つ（enum を「既存」とだけ書かない）。
  正本 registry は `data_access_class_registry`（ref/version で参照）。不明は dispatch 禁止
  （`access_class_unknown`）。
- `allowed_assignees`: packet 作成者の任意 list ではなく **access policy registry から local
  が導出。縮小のみ可**。assignee 非互換は `assignee_incompatible`。
- 明示された invalid assignee は黙って default に fallback せず **validation error**
  （`invalid_assignee`）。
- `external_egress_allowed` 既定 false。egress は §4.4 egress_descriptor で判定。
- `hold_echo` は local が source gate から導出。worker/head の欠落・縮小は reject。
- `output_root`/`upload_target_root` は allowlisted root 配下のみ。traversal・任意 Box は reject。
- `gated_by`: gate metadata field として規範化（governance_role と対）。
- **egress 判定の補足（#3 note）**: destination URI と destination_class の優先順位は
  **明示 URI allowlist 優先**。redirect 時は遷移先で**再判定**（allowlist 外なら blocked）。
  DNS/CDN alias・query value の secret scan を行う。これらは §10 の fixture で検証。
- **単一正本 lint（#7 note）**: 旧 document（v0.1 等）が規範として再参照されないことを
  lint で検出。旧 `patch` enum は migration fixture（§10）で新 next_action_type へ変換。

## 8. サイズ / staleness（規範）

- `soft_cap_bytes`（数値・bytes）＋ `size_policy_version`（**規範 DISPATCH field**）。超過は
  `oversize_reason`＋`must_read_sections` 明記時のみ dispatch（機械判定可能）。
- `staleness_policy`:

  ```yaml
  staleness_policy:
    check: artifact_version_and_digest
    on_mismatch: blocked          # block_reason=stale_packet
    max_age_minutes: <int, optional>
  ```

## 9. RESULT スキーマ（規範。`result_schema_version: handoff-result/0.5`）

| field | req/opt | 備考 |
|---|---|---|
| `result_schema_version` | req | `handoff-result/0.5` |
| `packet_id` / `packet_generation` / `packet_hash` | req | echo（packet_hash 必須） |
| `attempt_id` | req | §5.1 |
| `source_queue_item_id` | req | echo |
| `result_status` | req | enum |
| `block_reason` | cond | `blocked` 時 |
| `verdict` | req | ヘッド用。work 本体は読ませない |
| `outputs` | req | list |
| `output_artifact_hashes` | req | {path: sha256} |
| `diff_summary` | opt | |
| `acceptance_results` | req | [{criterion, pass}] |
| `for_head` | cond | unresolved / proposal_only 項目 |
| `proposal_only` | req | echo |
| `next` | opt | |

`supersedes`/`duplicate_of` は worker が書かない（local が §5.2 reconciliation event で付与）。

## 10. fixture（規範・v0.4 must_fix #9）

test 名でなく入力＋期待値の表。各 fixture は以下列を持つ:

`input_side_effect_flags`, `input_access_class`, `input_destination`, `input_cost_profile`
→ `expected_mutation_class`, `expected_egress_decision`, `expected_resource_effect_class`,
`expected_resource_permit`, `expected_dispatchable`, `expected_result_status`,
`expected_block_reason`。

最小 fixture 行（抜粋）:

| # | flags/access/dest/cost | mutation | egress | resource | dispatchable | block_reason |
|---|---|---|---|---|---|---|
| F1 local read | none / internal / none / free | non_mutating | none | none | true | — |
| F2 public GET | none / public / allowlist / free | non_mutating | allowed | free_bounded | true | — |
| F3 paid read (no permit) | none / public / allowlist / paid | non_mutating | allowed | paid | **false** | resource_permit_unavailable |
| F4 confidential egress | none / confidential / external / free | non_mutating | **blocked** | none | false | egress_forbidden |
| F5 file move | file_move / internal / none / free | **mutating** | none | none | （lease 無ければ）false | lease_required_but_unavailable |
| F6 ratify | — / — / — / — | — | — | — | false | ratify_not_dispatchable |
| F7 unknown access | none / **unknown** / — / — | non_mutating | blocked(安全側) | — | false | access_class_unknown |

v0.4 監査 §4 が要求する追加 fixture（必須）:

1. representative＋duplicate＋invalid が同一 group に混在する reconciliation（per-attempt
   relation を検証）。
2. `conflict` で representative なし・`needs_head_resolution=true`・`representative_attempt_id=null`。
3. all-invalid group。
4. `external_audit_logging=sensitive` 単独、および `paid + audit_sensitive` の複合。
5. `free_bounded` 上限不明（→rate_limited へ倒す）／上限超過／retry 超過。
6. source digest unavailable ＋ integrity-required gate → `blocked`。
7. runtime_envelope field 追加で packet_hash 不変・normative field 追加で hash 変化。
8. redirect 先が egress allowlist 外へ変わる public GET（再判定で blocked）。
9. egress/resource descriptor 欠落の fail-closed。

その他 fixture: stale-generation / duplicate-output-collision / hash-canonicalization(JCS) /
invalid-assignee / oversize / 旧 `patch`→新 next_action_type の migration（#7）。

## 11. 不変条件（両設計が共有）

1. 単一書き手: 索引/台帳/移動は `local` 固定。
2. 自己監査禁止: `assignee` に `gpt`/`claudehead` 等を入れない。
3. owner/auditor/production gated は受け渡しで上書き不可（`hold_echo` 縮小不可）。
4. 台帳: append-only・後勝ち・キー追加のみ・旧レコード未差配扱い。
5. `mutating ∧ lease 無し ⇒ blocked`（fail-closed・override 不可）。
6. `resource_permit_required ∧ permit 無し ⇒ blocked`（fail-closed・override 不可）。
7. 3軸 effect は local 導出・worker は安全側へのみ移動可・unknown は安全側。

## 12. 適用範囲の境界（v0.4 must_fix #10）

- **fixture-bound prototype**（owner ratify 後 GO）: schema validator / test harness。
  外部 call なし・queue/ledger/file move なし・永続運用 write なし。
- **operational implementation**（HOLD）: 実 dispatch/worklist/RESULT close、実レーン起動。
  v0.4 閉鎖＋owner ratify 後に non_mutating レーンから。mutating/lease/resource permit
  レーンは別 gate まで HOLD。

## 13. バージョニング

スキーマ変更は該当 `*_schema_version` を上げる。各設計（WORKER_DELEGATION / HEAD_HAND）は
本付録を参照し自前で再定義しない。本文 YAML は non-normative example。
