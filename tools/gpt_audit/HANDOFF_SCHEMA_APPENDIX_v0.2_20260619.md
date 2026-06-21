# HANDOFF_SCHEMA_APPENDIX v0.2 — 共有パケットスキーマ登録簿（**規範的単一正本**）

- status: **draft (未ratify・未実装)**
- date: 2026-06-20
- revision: v0.1 → v0.2。`HANDOFF_MODIFY_REQUIRED`
  (`20260619_head_hand_handoff_design_v0.2_GPTPRO_AUDIT_RESULT.md` / 2297409910837)
  の v0.3 must_fix #1/#6/#7/#8/#9 を反映。
- **規範性宣言（監査 v0.3 must_fix #1）**: 本付録が `assignee`/`role`/パケットスキーマの
  **唯一の規範的正本**である。`HEAD_HAND_HANDOFF_DESIGN` / `WORKER_DELEGATION_DESIGN`
  本文中の YAML は **non-normative example**（説明用）であり、本付録を上書きしない。
  本付録は他文書へ正本を再委譲しない（v0.1 の循環参照を解消）。
- owner 決定（2026-06-20）:
  - role モデル = **governance_role / execution_role 分離**（§1.2）。
  - read-only 外部呼び出し = **原則 non_mutating**。状態変更軸（mutation_class）と
    外部送信軸（egress/機密）を分離（§4.3）。
- 将来: 本付録の規範 YAML 表から JSON Schema / Pydantic へ 1対1 で落とす。

凡例: req=必須 / opt=任意 / cond=条件付き必須。

---

## 1. 語彙（enum・規範）

### 1.1 基本 enum

| enum | 許可値 |
|---|---|
| `assignee`（execution lane のみ） | `local`, `codex`, `worker_cc` |
| `assignee` 禁止値 | `gpt`, `gpt_pro`, `claudehead`, `head`, `auditor`, `owner` |
| `governance_role` | `supervisor`, `auditor`, `owner` |
| `execution_role` | `worker`, `deterministic` |
| `assignee_source` | `front_matter`, `gate_override`, `action_default` |
| `next_action_type` | `design_patch`, `doc_patch`, `code_patch`, `test_patch`, `refactor`, `required_materials`, `reject`, `ratify`, `none` |
| `mutation_class` | `non_mutating`, `mutating` |
| `result_status` | `done`, `blocked`, `needs_more`, `proposal` |
| `index_status` | `queued`, `dispatched`, `result_in`, `closing`, `closed` |
| `block_reason` | `lease_required_but_unavailable`, `stale_packet`, `access_class_unknown`, `assignee_incompatible`, `egress_forbidden`, `oversize_no_reason` |
| `hash_status` | `verified`, `unavailable` |

### 1.2 governance_role / execution_role 分離（監査 v0.3 must_fix #7 / owner 決定）

役割は2軸に分ける。**DISPATCH（実行パケット）が持てる `execution_role` は
`worker` または `deterministic` のみ**。`supervisor`/`auditor`/`owner` は実行レーンに
出さず、gate metadata（`governance_role` / `gated_by`）として扱う。

| 局面 | governance_role | execution_role | assignee |
|---|---|---|---|
| 分解・差配・最終統合 | `supervisor`（claudehead） | — | — (実行しない) |
| 設計改稿・重い文書 | — | `worker` | `worker_cc` |
| 実装・テスト・リファクタ | — | `worker` | `codex` |
| Box探索・移動・単一書き手・軽事務 | — | `deterministic` | `local` |
| 独立監査 | `auditor`（GPT Pro） | — | — (assignee 不可) |
| ratify | `owner` | — | — (`status=owner_pending`) |

- `next_action_type=ratify` は worker dispatch にしない。`index_status` 外の
  `owner_pending` として実行レーンの外に置く（§2 注記）。
- v0.1 で対応表に使っていた `architect`/`drafter`/`code executor`/`clerk`/`ratifier`
  等の **enum 外語彙は廃止**。上表の enum のみを使う。

## 2. thin index スキーマ（規範。action-queue / worklist の1行）

triage 十分であること（監査 must_fix #6）。slash 表記は廃止し個別 field 名で定義。

| field | req/opt | 型 | 備考 |
|---|---|---|---|
| `packet_id` | req | str | `DISP_<date>_<slug>_<seq>` |
| `packet_generation` | req | int | active generation 判定（§5） |
| `source_queue_item_id` | req | str | dedup 突合キー |
| `decision_id` | req | str | |
| `assignee` | req | enum | §1.1 |
| `execution_role` | req | enum | `worker`\|`deterministic` |
| `next_action_type` | req | enum | |
| `mutation_class` | req | enum | local 導出（§4） |
| `index_status` | req | enum | |
| `hold_flags` | req | list | local 導出（縮小不可） |
| `risk_class` | req | str | （旧 `risk_class / gate` を分離） |
| `gate` | req | str | |
| `data_access_class` | req | enum | 既存分類を継承（§7） |
| `priority` | opt | str | |
| `objective_oneline` | req | str | 一行 |
| `packet_ref` | req | path | → fat packet |
| `result_ref` | cond | path | 閉鎖時 |

注: `owner_pending`（ratify 待ち）は `index_status` enum に含めず、実行レーン外の
別キュー表示とする。

## 3. DISPATCH スキーマ（規範。`packet_schema_version: handoff-dispatch/0.3`）

| field | req/opt | 型 | 備考 |
|---|---|---|---|
| `packet_schema_version` | req | str | `handoff-dispatch/0.3` |
| `packet_id` | req | str | |
| `packet_generation` | req | int | 修正版で +1 |
| `packet_created_at_jst` | req | datetime | |
| `hash_algorithm` | req | const | `sha256` |
| `hash_scope_version` | req | str | `handoff-packet-hash/1`（§6） |
| `packet_hash` | req | str | `sha256:<hex>`。local が render 後・公開前に計算 |
| `source_queue_item_id` | req | str | |
| `source_request_id` | opt | str | |
| `decision_id` | req | str | |
| `source_artifacts` | req | list | §6 の構造（version_ref/digest/hash_status） |
| `governance_role` | cond | enum | gate metadata。実行パケットでは通常空 |
| `execution_role` | req | enum | `worker`\|`deterministic` |
| `assignee` | req | enum | |
| `assignee_source` | req | enum | |
| `next_action_type` | req | enum | |
| `mutation_class` | req | enum | **local が side_effect_flags から導出**（§4） |
| `side_effect_flags` | req | list | §4.1 |
| `result_artifact_exception` | req | bool | §4.2 |
| `lease_required` | req | bool | `mutation_class==mutating` ⇒ true |
| `gated_override_block` | req | const | `true` |
| `hold_echo` | req | list | local が source gate から導出。worker/head は縮小不可 |
| `data_access_class` | req | enum | 不明なら dispatch 禁止（§7） |
| `allowed_assignees` | req | list | 既定 `[local,codex,worker_cc]` |
| `external_egress_allowed` | req | bool | 既定 `false`（§4.3/§7） |
| `prohibited_actions` | req | list | |
| `objective` | req | str | done の定義 |
| `context_closure` | req | obj | `context_closure_index`{`inlined`,`referenced`[{`ref`,`digest`,`why`}]}, `pull_branch`, `excerpts` |
| `inputs` | req | list | id/path |
| `do` | req | list | |
| `acceptance` | req | list | ハンド単独で検証可能 |
| `soft_cap_bytes` | req | int | §8。policy version 連動 |
| `oversize_reason` | cond | str | cap 超過時 req |
| `must_read_sections` | cond | list | cap 超過時 req |
| `staleness_policy` | req | obj | §8（machine-checkable） |
| `output_contract` | req | obj | §3.1 |
| `proposal_only` | req | bool | |
| `clarification_budget` | req | int | 既定 0（超過時 §should_fix） |

### 3.1 output_contract（規範。attempt 衝突回避・監査 must_fix #4）

| field | req | 備考 |
|---|---|---|
| `output_root` | req | allowlisted root 配下のみ（traversal/任意 Box target は reject・§7） |
| `output_path_template` | req | `<output_root>/<packet_id>/<attempt_id>_RESULT.md` |
| `write_mode` | req | `create_new_no_overwrite` |
| `upload_target_root` | req | allowlisted root |
| `required_fields` | req | §4 RESULT の req field 一式 |

## 4. mutation_class 導出（規範・監査 v0.3 must_fix #2/#3）

`mutation_class` は自由記述の分類値ではない。**local dispatcher が
`side_effect_flags` から決定的に導出する。** front-matter / worker は
`mutating→non_mutating` へ弱められない。**未知・曖昧は `mutating` に倒す。**

### 4.1 side_effect_flags

`persistent_write`, `shared_namespace_write`, `file_move`, `external_write`,
`paid_or_quota_call`, `data_egress`, `destructive`, `production_effect`。

導出規則: 上記いずれかが立てば `mutating`。ただし §4.2 例外を先に適用。

### 4.2 RESULT artifact 例外

指定された**一意の RESULT アーティファクトを書くだけ**の transport write は
`result_artifact_exception: true` として non_mutating に例外化できる。条件:
attempt 固有 path（§3.1）かつ `create_new_no_overwrite`。

### 4.3 read-only 外部呼び出し（owner 決定・状態変更軸と egress 軸の分離）

owner 決定により、**read-only 外部呼び出しは状態変更軸では non_mutating**（lease を
要求しない）。外部状態を書き換えないため `mutating` フラグ（persistent_write 等）は
立たない。

ただし**機密・送信のリスクは別軸**で残すので捨てない。

- `data_egress`（機密 query の外部送信）は mutation_class ではなく **egress 軸**で扱い、
  `external_egress_allowed`（既定 false）＋ `data_access_class`（§7）でガードする。
- したがって「読み取り専用だが機密 query を外へ出す」呼び出しは、non_mutating の
  まま **egress ガードで `blocked`（`block_reason=egress_forbidden`）** になり得る。
- 無償・非機密・公開情報の read は `external_egress_allowed` の対象外（または allowlist）
  として広く通す。

> 設計意図: 「読むだけなら lease で止めない」（owner 判断）を通しつつ、監査が懸念した
> 機密 egress は別軸で必ずガードする。mutation_class は**並行制御**のため、egress は
> **機密保持**のための、独立した2軸とする。

### 4.4 lease 不存在時の fail-closed（不変条件・監査 must_fix #3）

```text
mutation_class == mutating AND lease_subsystem_available == false
  => dispatchable = false
  => index_status = （配布しない）
  => result_status = blocked
  => block_reason = lease_required_but_unavailable
```

手動 override / front-matter / gate override で迂回不可。lease 実装まで mutating packet は
**生成しても配布・実行しない**。

## 5. 重複結果の調停（規範・並行制御ではない・監査 must_fix #4/#5）

- これは local による**重複結果の決定論的調停**であって並行制御ではない。二重実行は
  依然起こりうる。
- **attempt 単位**: 各 RESULT は attempt 固有 path に immutable に書かれる（§3.1）。
  worker は `supersedes`/`duplicate_of` を決めない。local が別の reconciliation event で
  代表・superseded を記録する。
- **grouping（active generation 単位）**:
  `primary grouping = source_queue_item_id + packet_generation + packet_hash`。
  古い generation は比較対象外で `superseded/stale`。同一 generation の duplicate だけを
  代表選定にかける。
- **代表選定**:
  1. acceptance 合格が勝つ。
  2. output hash / semantic summary が同値なら earliest valid を代表にしてよい。
  3. 内容が非同値だが片方のみ required evidence 完全 → 完全側。
  4. 両方有効で**意味的に衝突** → `needs_head_resolution`。両方保持・自動統合禁止。
  5. 不合格・スキーマ不正は `superseded/`（証跡保持）。
- `evidence grade` は **worker 自己申告でなく local が schema/acceptance から算定**。

## 6. hash / source version（規範・監査 must_fix #6）

- `hash_algorithm: sha256`、`hash_scope_version: handoff-packet-hash/1`。
- canonicalization: canonical JSON（key order 固定・UTF-8・NFC・LF・**hash field 除外**）を
  hash basis にする。または immutable payload の exact bytes を hash し `hash_scope_version`
  を明記。
- `source_artifacts[]`:

  | field | req | 備考 |
  |---|---|---|
  | `ref` | req | id/path |
  | `version_ref` | req | Box file version \| Git blob SHA \| local stat snapshot |
  | `digest` | cond | typed digest（取得不能時 null＋下記理由） |
  | `hash_status` | req | `verified`\|`unavailable` |
  | `unavailable_reason` | cond | `unavailable` 時 req |

- ライフサイクル: ①local が render 後・公開前に `packet_hash` 計算＋source version 固定 →
  ②worker が作業開始前に packet hash と source version を検証（不一致は実行せず
  `blocked/stale_packet`）→ ③worker が output hash を計算し RESULT へ記載 →
  ④local closer が echo・active generation・output existence/hash・acceptance を検証して
  index/ledger 更新。
- **RESULT の `packet_hash` echo は必須**（v0.2 の「取得可能なら」は削除）。output_contract
  の required_fields にも含める。

## 7. access / gate 境界（規範・監査 must_fix #9）

- `data_access_class`（既存分類を**新設せず継承**）を全パケットに echo。**不明は dispatch
  禁止**（`block_reason=access_class_unknown`）。
- `allowed_assignees`（既定 `[local,codex,worker_cc]`）と assignee の互換を dispatch
  validation で検査。不一致は `blocked/assignee_incompatible`。
- `external_egress_allowed` 既定 false。機密 egress は §4.3 の egress 軸でガード。
- `hold_echo` は local が source gate から導出。worker/head による欠落・縮小は reject。
- `output_root`/`upload_target_root` は **allowlisted root 配下のみ**。path traversal・
  任意 Box target は reject。

## 8. サイズ規律 / staleness（規範・監査 must_fix #8）

- `soft_cap_bytes`: 数値・単位（bytes）・`size_policy_version` を持つ。超過は
  `oversize_reason`＋`must_read_sections` 明記時のみ dispatch 許可（hard cap でない）。
  oversize は機械判定可能（cap と実バイト比較）。
- `staleness_policy`（machine-checkable・free-text 廃止）:

  ```yaml
  staleness_policy:
    check: artifact_version_and_digest   # 開始前に source_artifacts と照合
    on_mismatch: blocked                 # block_reason=stale_packet
    max_age_minutes: <int, optional>
  ```

## 9. RESULT スキーマ（規範。`result_schema_version: handoff-result/0.3`）

| field | req/opt | 備考 |
|---|---|---|
| `result_schema_version` | req | `handoff-result/0.3` |
| `packet_id` | req | echo |
| `packet_generation` | req | echo |
| `packet_hash` | req | echo（必須・§6） |
| `attempt_id` | req | §3.1 |
| `source_queue_item_id` | req | echo |
| `result_status` | req | enum |
| `block_reason` | cond | `blocked` 時 |
| `verdict` | req | ヘッド読む用。work 本体は読ませない |
| `outputs` | req | list |
| `output_artifact_hashes` | req | {path: sha256} |
| `diff_summary` | opt | |
| `acceptance_results` | req | [{criterion, pass}] |
| `for_head` | cond | unresolved / proposal_only 項目 |
| `proposal_only` | req | echo |
| `next` | opt | 推奨（決めるのはヘッド） |

注: `supersedes`/`duplicate_of` は **worker が書かない**（local が reconciliation で付与）。

## 10. 不変条件（両設計が共有）

1. 単一書き手: 索引/台帳/ファイル移動は `local` 固定。
2. 自己監査禁止: `assignee` に `gpt`/`claudehead` 等を入れない。
3. owner/auditor/production gated は受け渡しで上書き不可（`hold_echo` で生存・縮小不可）。
4. 台帳 (`_AUDIT_LEDGER.jsonl`): append-only・後勝ち・キー追加のみ・旧レコード未差配扱い。
5. `mutating ∧ lease 無し ⇒ blocked`（fail-closed・§4.4・override 不可）。
6. mutation_class は local 導出・worker 縮小不可・unknown→mutating。

## 11. バージョニング

- スキーマ変更は該当 `*_schema_version` を上げる。
- 各設計（WORKER_DELEGATION / HEAD_HAND）は本付録を参照し**自前で再定義しない**。
  本文 YAML は non-normative example（§規範性宣言）。
