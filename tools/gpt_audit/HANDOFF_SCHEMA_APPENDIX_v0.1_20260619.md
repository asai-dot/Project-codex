# HANDOFF_SCHEMA_APPENDIX v0.1 — 共有パケットスキーマ登録簿

- status: **draft (未ratify・未実装)**
- date: 2026-06-19
- 目的: `WORKER_DELEGATION_DESIGN`（誰の枠で実行するか＝assignee）と
  `HEAD_HAND_HANDOFF_DESIGN`（文脈がどうシームを渡るか）が**共有する**
  パケットスキーマと語彙を1か所に登録する。両設計は**統合せず**本付録を
  相互参照する（HANDOFF 監査 should_fix #1 / F8）。
- スキーマの正: 本付録。各設計はここを単一の正として参照する。

---

## 1. 語彙（enum）

| 名前 | 値 | 出典設計 |
|---|---|---|
| `assignee` | `local` \| `codex` \| `worker_cc` | WORKER_DELEGATION |
| `assignee` 禁止値 | `gpt`, `gpt_pro`, `claudehead`, `head`, `auditor`, `owner` | 自己監査禁止 |
| `role`（層1） | `supervisor` \| `worker` \| `deterministic` \| `auditor` \| `owner` | WORKERDELEG 二層 |
| `assignee_source` | `front_matter` \| `gate_override` \| `action_default` | WORKER_DELEGATION |
| `next_action_type` | `design_patch` \| `doc_patch` \| `code_patch` \| `test_patch` \| `refactor` \| `required_materials` \| `reject` \| `ratify` \| `none` | 両設計 |
| `mutation_class` | `non_mutating` \| `mutating` | HEAD_HAND §5.1 |
| `status`（result） | `done` \| `blocked` \| `needs_more` \| `proposal` | HEAD_HAND |
| `status`（index） | `queued` \| `dispatched` \| `result_in` \| `closing` \| `closed` | HEAD_HAND |

### 1.1 role × assignee 二層対応表（WORKERDELEG must_fix #1）

| governance/cognitive role（層1） | execution lane / assignee（層2） | 備考 |
|---|---|---|
| supervisor / architect | claudehead | 実行しない。分解・差配・最終統合 |
| worker / drafter | worker_cc | 設計改稿・重い文書作業 |
| code executor | codex | 実装・テスト・リファクタ |
| deterministic tool runner / clerk | local | Box探索・移動・単一書き手・軽事務 |
| auditor | GPT Pro | assignee 不可 |
| ratifier | owner | assignee ではなく `owner_pending` |

## 2. thin index スキーマ（action-queue / worklist の1行）

triage 十分であること（HANDOFF must_fix #6）。

```yaml
packet_id: <DISP_...>
source_queue_item_id: <id>
decision_id: <id>
assignee: <enum>
role: <enum>
next_action_type: <enum>
mutation_class: <enum>
status: <index status enum>
hold_flags: [<...>]
risk_class / gate: <...>
priority: <optional>
objective_oneline: <一行>
packet_ref: <→fat packet>
result_ref: <→result, 閉鎖時>
```

## 3. DISPATCH（下り）スキーマ — `packet_schema_version: handoff-dispatch/0.2`

必須・整合フィールドは HEAD_HAND §3 を正とする。要点のみ再掲:

- identity/integrity: `packet_schema_version`, `packet_id`, `packet_created_at_jst`,
  `packet_hash`, `source_queue_item_id`, `source_request_id`/`decision_id`,
  `source_artifact_hashes`
- routing: `role`, `assignee`, `assignee_source`, `next_action_type`
- safety: `mutation_class`, `gated_override_block`, `hold_echo`, `prohibited_actions`
- work: `objective`, `context_closure`(`context_closure_index`/`excerpts`),
  `inputs`, `do`, `acceptance`
- size: `oversize_reason`, `must_read_sections`
- return: `output_contract`, `proposal_only`, `clarification_budget`, `staleness_check`

## 4. RESULT（上り）スキーマ — `result_schema_version: handoff-result/0.2`

必須・整合フィールドは HEAD_HAND §4 を正とする。要点:

- `result_schema_version`, `packet_id`(echo), `packet_hash`(echo),
  `source_queue_item_id`(echo), `status`, `verdict`, `outputs`,
  `output_artifact_hashes`, `diff_summary`, `acceptance_results`(基準ごと pass/fail),
  `for_head`/`unresolved`, `supersedes`/`duplicate_of`, `proposal_only`(echo), `next`

## 5. 重複結果の調停（HEAD_HAND §5。並行制御ではない）

- 単位キー: `source_queue_item_id`。
- 代表選定順序: ① acceptance 合格 → ② evidence 完全性/証拠グレード → ③ 最早の有効結果。
  不合格・スキーマ不正は `superseded/`（証跡保持）。
- `mutation_class==mutating` は no-lease レーン禁止（lease/claim 必須）。

## 6. 不変条件（両設計が共有）

1. 単一書き手: 索引/台帳/ファイル移動は `local` 固定。
2. 自己監査禁止: `assignee` に `gpt`/`claudehead` 等を入れない。
3. owner/auditor/production gated は受け渡しで上書きされない（`hold_echo` で生存）。
4. 台帳 (`_AUDIT_LEDGER.jsonl`): append-only・後勝ち・キー追加のみ・旧レコード未差配扱い。

## 7. バージョニング

- スキーマ変更は本付録の `*_schema_version` を上げる。
- 各設計（WORKER_DELEGATION / HEAD_HAND）は本付録の version を参照し、自前で
  スキーマを再定義しない（モノリス化回避＝should_fix #1）。
