# HEAD_HAND_HANDOFF_DESIGN v0.3 — ヘッド↔ハンドのシームレス受け渡し設計

- status: **draft (未ratify・未実装)**
- date: 2026-06-20
- gate: `HANDOFF`
- revision: v0.2 → v0.3。`HANDOFF_MODIFY_REQUIRED`
  (`20260619_head_hand_handoff_design_v0.2_GPTPRO_AUDIT_RESULT.md` / 2297409910837)
  の v0.3 must_fix 10件・should_fix を反映。
- **スキーマの正本**: `HANDOFF_SCHEMA_APPENDIX_v0.2_20260619.md`（規範的単一正本）。
  本文中の YAML/フィールドは **non-normative example**。フィールド定義の正は付録。
- owner 決定（2026-06-20）:
  - role モデル = **governance_role / execution_role 分離**。
  - read-only 外部呼び出し = **原則 non_mutating**（状態変更軸 mutation_class と
    egress/機密軸を分離。§5.3 / 付録 §4.3）。
- 関連設計: `WORKER_DELEGATION_DESIGN_v0.1_20260619.md`（assignee layer。**統合せず**
  付録を共有）
- 関連正本: `DD-CLAUDEHEAD-001-core_head_hand_role_protocol_accepted_v1.0` ほか
  GPT_PRO_AUDIT_LOOP/LANE 各正本。
- prior art: `handoff/WORKER_TASK_PACKET_*.md`

---

## 0. なぜ要るか（問題）

claudehead（ヘッド）と `local`/`codex`/`worker_cc`（ハンド）は**別セッション・共有
メモリなし**。渡れるのは**ファイルだけ**。

> **不変条件 H1: シームは直列化境界である。アーティファクトに書かれない文脈は
> 渡らない。**（監査 F1: governing invariant として保持）

シームレス ⇔ 下りが **context-closed**（ハンドはヘッドに訊かず実行できる）・上りが
**result-closed**（ヘッド/local は work 本体を読まず統合できる）。潰す失敗モード:
過少記述（往復→ヘッド枠出血）／過結合（生メモリ共有は不可）／肥大（inline 無制限→
ミニ書庫化）。

## 1. 設計原則（不変条件）

1. 直列化境界 H1。記憶依存の受け渡し禁止。
2. コスト非対称（ヘッドは書き一度・読み薄く。往復ゼロ）。
3. 単一書き手不変（索引/台帳/移動は local。ハンドは上りを書くだけ）。
4. gated は受け渡しで上書き不可。`hold_echo` は **local が source gate から導出・
   worker/head は縮小不可**（v0.3 強化）。
5. 役割は **governance_role / execution_role 分離**。DISPATCH の `execution_role` は
   `worker|deterministic` のみ。`assignee` は `local|codex|worker_cc` のみ（§7）。
6. **mutating ∧ lease 無し ⇒ blocked（fail-closed・override 不可）**（§5.4・v0.3 新設）。
7. mutation_class は **local が side_effect_flags から導出**・worker 縮小不可・
   **unknown→mutating**（§5.1）。

## 2. 解 — 二層アーティファクト

- **thin index**（action-queue/worklist 1行）= triage 十分。フィールドは付録 §2 が正
  （`packet_id`, `packet_generation`, `source_queue_item_id`, `assignee`,
  `execution_role`, `mutation_class`, `index_status`, `hold_flags`, `risk_class`,
  `gate`, `data_access_class`, `objective_oneline`, `packet_ref`, …）。
  slash 表記は廃止（`risk_class` と `gate` を分離）。
- **fat packet** = 自己完結パケット（`handoff/` 1ファイル）。スキーマは付録 §3。

## 3. 下りパケット（DISPATCH）

スキーマの正は **付録 §3**（`packet_schema_version: handoff-dispatch/0.3`）。要点:

- identity/integrity（付録 §6）: `packet_hash`（local が render 後・公開前に計算）、
  `hash_algorithm`/`hash_scope_version`、`source_artifacts[]`（version_ref/digest/
  hash_status）。
- routing: `governance_role`（gate metadata・実行パケットでは空）/ `execution_role`
  （worker|deterministic）/ `assignee` / `assignee_source` / `next_action_type`。
- safety: `mutation_class`（local 導出）/ `side_effect_flags` / `result_artifact_exception`
  / `lease_required` / `gated_override_block:true` / `hold_echo` / `data_access_class` /
  `allowed_assignees` / `external_egress_allowed:false`。
- work: `objective` / `context_closure`（`context_closure_index`＝何を inline/参照したか、
  各参照に `why`／`excerpts` は decision-critical のみ）/ `inputs` / `do` / `acceptance`。
- size/staleness: `soft_cap_bytes`＋`size_policy_version`、超過は `oversize_reason`＋
  `must_read_sections`／`staleness_policy`（machine-checkable・付録 §8）。
- return: `output_contract`（§4）/ `proposal_only` / `clarification_budget:0`。

中核ルール: **「ハンドがヘッドに訊きたくなる事項は全部 `context_closure` に入れる」。**

## 4. 上りパケット（RESULT）と attempt 衝突回避（監査 must_fix #4）

スキーマの正は **付録 §9**（`result_schema_version: handoff-result/0.3`）。

二重実行で同じ `output_path` に上書きされると local が複数結果を観測できず dedup 設計が
崩れる。これを attempt 単位で防ぐ（付録 §3.1）:

```
output_path = <output_root>/<packet_id>/<attempt_id>_RESULT.md
write_mode  = create_new_no_overwrite
```

- 各 RESULT は immutable に attempt 固有 path へ書く。
- worker は `supersedes`/`duplicate_of` を**決めない**。local が reconciliation で付与。
- RESULT の `packet_hash` echo は**必須**（「取得可能なら」は削除）。

## 5. シーム閉鎖 — 重複結果の調停・mutation 境界・lease fail-closed

### 5.1 mutation_class 導出（付録 §4・監査 must_fix #2/#3）

local dispatcher が `side_effect_flags`（persistent_write / shared_namespace_write /
file_move / external_write / paid_or_quota_call / data_egress / destructive /
production_effect）から決定的に導出。front-matter/worker は弱められない。**unknown→
mutating**。RESULT artifact 例外（一意 path＋no-overwrite の transport write）は §4.2。

### 5.2 重複結果の調停（並行制御ではない・付録 §5）

no-lease は二重実行を防がない＝**重複結果の決定論的調停**。grouping は active generation
単位（`source_queue_item_id + packet_generation + packet_hash`）。古い generation は
`superseded/stale`。代表選定 = acceptance 合格 → (同値)earliest valid → (片方完全)完全側
→ **意味的衝突は `needs_head_resolution`（両保持・自動統合禁止）**。`evidence grade` は
local が schema/acceptance から算定（worker 自己申告でない）。

### 5.3 レーン安全境界 ＋ egress 軸の分離（owner 決定）

| mutation_class | 例 | 競合制御 |
|---|---|---|
| `non_mutating` | proposal/draft/review/調査、RESULT artifact 書込、**read-only 外部呼び出し** | no-lease 調停でよい |
| `mutating` | コスト・状態変更・file_move・external_write・破壊的・本番影響 | **lease/claim 必須**・no-lease 禁止 |

**read-only 外部呼び出しは状態変更軸では non_mutating**（owner 決定。lease で止めない）。
ただし機密送信は**別軸**: `data_egress` は mutation_class でなく egress 軸
（`external_egress_allowed:false` ＋ `data_access_class`）でガードし、機密 query を出す
read は non_mutating のまま `blocked/egress_forbidden` になり得る。無償・非機密・公開
read は広く通す（付録 §4.3）。

### 5.4 lease 不存在時の fail-closed（不変条件・監査 must_fix #3）

```
mutation_class == mutating AND lease_subsystem_available == false
  => dispatchable=false ; result_status=blocked
  => block_reason=lease_required_but_unavailable   （override 不可）
```

lease 実装まで mutating packet は**生成しても配布・実行しない**。

## 6. 「シームレス＝往復ゼロ」を gate 化

context-closed 5条件:（1）objective（2）inputs が id/path でヘッド不在でも解決可能
（3）do が inline/リンク材料のみ参照（4）output_contract が上り物を完全指定
（5）acceptance がハンド単独で検証可能。

サイズ規律: inline は decision-critical のみ・完全版は path/digest 参照・各参照に why・
`soft_cap_bytes` 超過は reason＋must_read_sections 明記時のみ（機械判定可能）。

clarification: `clarification_budget`（既定0）超過時は**推測継続せず** `needs_more` ＋
`required_materials` を返す（should_fix）。

## 7. role / governance / assignee 整合（監査 must_fix #7 / owner 決定）

owner 決定により **governance_role / execution_role を分離**（付録 §1.2）。

- DISPATCH（実行パケット）の `execution_role` は `worker|deterministic` のみ。
- `supervisor`/`auditor`/`owner` は実行レーンに出さず gate metadata。
- `assignee` は `local|codex|worker_cc` のみ。`gpt`/`claudehead`/`head`/`auditor`/`owner`
  は禁止値。
- `next_action_type=ratify` は worker dispatch にせず `owner_pending`（実行レーン外）。
- enum 外語彙（architect/drafter/clerk 等）は廃止。

## 8. access / gate 境界（監査 must_fix #9）

`data_access_class`（既存分類を継承・不明は dispatch 禁止）、`allowed_assignees` と
assignee の互換検査（不一致 `blocked/assignee_incompatible`）、`external_egress_allowed`
既定 false、`hold_echo` は local 導出・縮小不可、`output_root`/`upload_target_root` は
allowlisted root 配下のみ（traversal・任意 Box target は reject）。詳細は付録 §7。

## 9. 実装ポイント（最小差分・ratify 後）

`alo_gpt_audit.py`:

1. dispatch 生成（local）: `packet_hash` 計算・source version 固定・`mutation_class`
   導出・`hold_echo`/`data_access_class` 導出・付録 §3 のフィールド出力。
2. action-queue 行（thin index）: 付録 §2 の triage フィールド。
3. dispatch 前 validation: context-closed 5条件＋`mutating∧lease無し→blocked`＋
   access-class 不明/assignee 非互換/egress 禁止/oversize-no-reason の block＋staleness。
4. local close 系: attempt 固有 path・active generation dedup（付録 §5）・代表選定・
   `superseded/`・hash/echo/acceptance 検証。

台帳はキー追加のみ・append-only・後勝ち不変・旧レコード未差配扱い。

## 10. テスト計画（ratify 後・監査 must_fix #10）

dispatch-context-closed / missing-context-closure / down-up-packet-schema /
up-packet-linkage(packet_hash echo) / **stale-generation** / **duplicate-output-collision**
/ dedup-valid-vs-invalid / dedup-two-valid / **valid-but-conflicting→needs_head_resolution**
/ **hash-canonicalization-mismatch** / oversize-with-without-reason /
**lease-unavailable-fail-closed** / forbidden-no-lease-mutating / **external-read-api** /
**access-class-mismatch** / gated-override-block / ledger-back-compat。

## 11. やらないこと（スコープ外）

- 自動ディスパッチ（実セッション起動）。
- lease/claim ledger **実装**（境界は確定。fail-closed で mutating は配布しない）。
- GPT/claudehead を assignee enum に入れること。
- mutating task の dispatch・実行（別 gate まで HOLD）。

## 12. ratify 後の段取り

ratify されたら §9 を最小差分で実装＋§10 テスト＋README。まず **non_mutating レーンのみ**
最小実装可。mutating/lease レーンは別 gate まで HOLD。スキーマは付録を単一の正とする。
