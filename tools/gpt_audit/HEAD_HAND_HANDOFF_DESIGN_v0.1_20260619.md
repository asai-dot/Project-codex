# HEAD_HAND_HANDOFF_DESIGN v0.1 — ヘッド↔ハンドのシームレス受け渡し設計

- status: **draft (未ratify・未実装)**
- date: 2026-06-19
- gate: `HANDOFF`
- 関連設計: `WORKER_DELEGATION_DESIGN_v0.1_20260619.md`（assignee layer。本書はその
  「シーム＝受け渡し境界」を解く姉妹設計）
- 関連監査: `20260619_worker_delegation_design_v0.1_GPTPRO_AUDIT_RESULT.md`
  （`WORKERDELEG_PASS_WITH_NOTES`。本書は must_fix #1/#4/#5 を受け渡し実体の上で解く）
- 関連正本:
  - `GPT_PRO_AUDIT_LOOP_RULE_v0.1_20260607.md`
  - `GPT_PRO_AUDIT_LANE_DESIGN_v0.3_20260607.md`
  - `GPT_PRO_AUDIT_LANE_APPROVAL_RULE_v0.1_20260606.md`
- prior art: `handoff/WORKER_TASK_PACKET_*.md`（既存の task packet 形式を形式化する）

---

## 0. なぜ要るか（問題）

claudehead（ヘッド）と `local`/`codex`/`worker_cc`（ハンド）は**別セッション・共有
メモリなし**で動く。両者の間を渡れるのは**ファイル（アーティファクト）だけ**である。
ここから本設計の全てが従う不変条件が一つ出る。

> **不変条件 H1: シームは直列化境界である。ハンドオフ・アーティファクトに
> 書かれなかった文脈は、シームを渡らない。**

これにより「シームレス」が曖昧な願望ではなく**検証可能な契約**になる。
受け渡しがシームレスである ⇔

- **下り物が context-closed**: ハンドはこれ以上ヘッドに訊かず実行できる。
- **上り物が result-closed**: ヘッド/`local` はこれ以上 work 本体を読まず統合できる。

設計が潰すべき失敗モードは2つ。

| 失敗モード | 症状 | 対応する既存リスク |
|---|---|---|
| **過少記述**（薄い queue 行だけ渡す） | ハンドが文脈不足 → ヘッドへ往復 → **ヘッドの枠を出血**（守るはずのものを壊す） | 現 `action-queue` 行が薄すぎる |
| **過結合**（ヘッドの生メモリを共有しようとする） | 別セッションでは原理的に不可能・脆い | — |

WORKER_DELEGATION が「誰の枠で実行するか（assignee）」を決めたのに対し、本書は
「ヘッドの文脈をどうハンドへ無損失で渡し、結果を無損失で戻すか」を決める。

## 1. 設計原則（不変条件。1つも崩さない）

1. **シームは直列化境界（H1）。** 渡したい文脈は必ずアーティファクトに書く。
   ヘッドの記憶・会話履歴に依存した受け渡しを禁止する。
2. **コストの非対称を設計する。** ヘッドは dispatch 時（文脈が熱いうち）に**太い
   パケットを一度だけ書く**。以後は薄いインデックスを読むだけ。ハンドは太い
   パケットを読む（文脈は冷えていてよい＝自己完結だから）。ヘッドは統合時に
   薄い上りサマリだけ読む。**誰も再導出しない。往復ゼロ。**
3. **単一書き手は不変。** インデックス/台帳の更新・レーンのファイル移動は `local`
   固定。ハンドは上りパケットを**書くだけ**で、索引も台帳も触らない
   （WORKER_DELEGATION 原則4を継承）。
4. **gated は受け渡しで上書きされない。** assignee 明示があっても owner-gated /
   auditor-gated / production-gated は HOLD のまま（監査 must_fix #4）。
5. **二層を両持ちする。** パケットは「認知ロール（層1）」と「実行レーン＝assignee
   （層2）」を**両方**載せる（監査 must_fix #1）。受け渡し実体が二層の合流点になる。

## 2. 解 — 二層アーティファクト

シームを「薄いインデックス」と「太いパケット」に分離する。

- **thin index** = `action-queue` / `worklist` の1行。フィールドは
  `packet_id`, `assignee`, `next_action_type`, `status`, `hold_flags`, `→packet`。
  `worklist <assignee>` が読むのはここだけ。ヘッドがスキャンするのもここだけ。
- **fat packet** = インデックスが指す**自己完結パケット**（`handoff/` に1ファイル）。
  ハンドが読むのはヘッドの頭ではなく**これ**。既存 `WORKER_TASK_PACKET` の形式化。

この分離が原則2（コスト非対称）を物理的に実現する。

## 3. 下りパケット（DISPATCH）— context-closed 契約

既存 `WORKER_TASK_PACKET` の yaml front-matter を拡張する。中核ルールは
**「ハンドがヘッドに訊きたくなる事項は全部 `context_closure` に入れる」**。

```yaml
packet_id: DISP_20260619_<slug>_001          # 連結キー（不変）
source_queue_item_id: <action-queue item id> # 来歴（監査 must_fix #5 の突合キー）
decision_id / source_request_id: ...
role: worker | deterministic | supervisor     # 層1：認知ロール（監査 must_fix #1）
assignee: local | codex | worker_cc           # 層2：実行レーン（enum 検証 must_fix #2）
assignee_source: front_matter | gate_override | action_default   # should_fix #3
next_action_type: design_patch | doc_patch | code_patch | test_patch
                 | refactor | required_materials | reject | ...   # must_fix #3 細分化
objective: <一文。done の定義>
context_closure:            # ★シームレスの心臓部。ヘッドが文脈の熱いうちに一度だけ払う
  pull_branch: claude/...
  canonical_refs: [<file_id>, ...]
  prior_results: [<RESULT file_id>, ...]
  excerpts: |               # 訊かれそうな前提を inline で同梱
    ...
inputs / materials: [<file_id | path>, ...]
do: [手順1, 手順2, ...]
constraints / forbidden: [no-production-db-write, no-DDL, no-SF-writeback, ...]  # 既存 permission_tags
gated_override_block: true  # must_fix #4：assignee 明示でも owner/auditor/production gated は HOLD維持
output_contract:            # ★上り物の名前と形を下りで先に固定 → ループが決定論で閉じる
  output_path: _claude_dispatch/from_worker/<...>_RESULT.md
  upload_target: Box .../material_queue/<...>
  required_fields: [status, verdict, outputs, source_queue_item_id]
acceptance: [ハンドが done 宣言前に自己検証する条件]
proposal_only: true | false # should_fix #5：worker は設計判断を自分で accepted にしない
```

`role`（層1）と `assignee`（層2）を**同じパケットが両方持つ**ことで、監査論点C
（既存 5.5/5.3/Python 分業との整合）が抽象論ではなく**ハンドオフ実体の上で**解ける。

## 4. 上りパケット（RESULT）— result-closed 契約

名前と形は下りの `output_contract` が指定済み。ハンドはそれに従って書く。

```yaml
packet_id: <下りを echo>          # ループを閉じる
source_queue_item_id: <echo>     # local の突合・dedup・processed化キー（must_fix #5）
status: done | blocked | needs_more | proposal
verdict / summary: <ヘッドが読む用。何が変わったか。work本体は読ませない>
outputs: [<生成 file_id/path>, ...]
diff_summary: ...
for_head / unresolved: [上げ返す判断（特に proposal_only 項目）]
acceptance_results: [自己検証の結果]
next: <推奨フォロー（決めるのはヘッド、提案するのはハンド）>
```

## 5. シームの閉鎖 — local 単一書き手 ＋ lease なし dedup

- 上りパケットは**ハンドが書くだけ**。索引/台帳の更新は `local` 固定（原則3）。
  `local` が `packet_id` / `source_queue_item_id` で索引行に突合し、move/close/reflect。
- **二重実行は壊さない**: 全上りパケットが `source_queue_item_id` を持つので、`local`
  は同一 id の複数上りを見たら**代表を残し**（acceptance 合格 or first-by-time）、
  他を `superseded/` へ退避する。分散ロック不要。
- これが監査 must_fix #5 への正直な回答 = 「v0.1 は自動 lease を作らない。競合防止は
  『単一書き手 ＋ id 突合 dedup』に限定し、二重**着手**そのものは防がない」。
  lease/claim ledger は将来拡張のまま据え置く。

## 6. 「シームレス＝往復ゼロ」を gate 化（context-closed チェック）

ヘッドが dispatch 前に自己検証するチェック。1つでも欠ければ**未差配**とし、
パケットを濃くしてから出す（＝「シームレス」が願望ではなく**通過条件**になる）。

1. `objective` がある（done の定義が一意）。
2. `inputs` が全て id/path で**ヘッド不在でも解決可能**。
3. `do` が inline/リンク済み材料**のみ**を参照（ヘッドの記憶に依存しない）。
4. `output_contract` が上り物を完全指定している。
5. `acceptance` が**ハンド単独で**検証可能。

## 7. 監査ノート（WORKERDELEG_PASS_WITH_NOTES）との接続

| 監査ノート | 本設計での解決箇所 |
|---|---|
| must_fix #1 二層モデル | パケットが `role` ＋ `assignee` を両持ち（§3, 原則5） |
| must_fix #2 enum 検証 | `assignee` enum、`gpt/claudehead/head/auditor/owner` は不可 |
| must_fix #3 patch 細分化 | `next_action_type` を design/doc/code/test/refactor/material に分割（§3） |
| must_fix #4 override 限界 | `gated_override_block: true`（§3, 原則4） |
| must_fix #5 worklist 限界 | §5 の id 突合 dedup ＋ 将来 lease 注記 |
| should_fix #3 / #5 | `assignee_source` / `proposal_only`（§3） |

## 8. 実装ポイント（最小差分。ratify 後）

`alo_gpt_audit.py` 側:

1. `write_route_card` / dispatch 生成に `packet_id`, `context_closure`,
   `output_contract`, `gated_override_block`, `proposal_only` を出す。
2. `action-queue` 行（thin index）に `status`, `hold_flags`, `→packet` を追加。
3. `local` の close 系に「同一 `source_queue_item_id` の上りパケット dedup
   （代表残し・他は `superseded/`）」を追加。
4. context-closed チェック（§6）を dispatch 前バリデーションとして追加。

台帳 (`_AUDIT_LEDGER.jsonl`) へは `packet_id` 等のキー追加のみ。append-only・
後勝ち読みは不変。旧レコードは「未差配」扱い（WORKER_DELEGATION と同じ back-compat）。

## 9. テスト計画（ratify 後・既存 unittest に追加）

| test | 内容 |
|---|---|
| dispatch-context-closed | §6 の5条件を満たさない下りは未差配で弾く |
| down-packet-schema | `packet_id`/`role`/`assignee`/`output_contract` 必須 |
| up-packet-linkage | 上りが `source_queue_item_id` を echo している |
| dedup-same-source | 同一 source の上り2通 → 代表残し・他 superseded |
| gated-override-block | assignee 明示でも owner/auditor/production gated は HOLD |
| ledger-back-compat | packet キー無し旧レコードでも action-queue が壊れない |

## 10. やらないこと（スコープ外）

- 自動ディスパッチ（実 codex/worker_cc セッション起動）は本版で作らない
  （WORKER_DELEGATION と同じ）。
- 自動 lease/claim ledger は作らない（§5）。将来必要時に別版で設計する。
- GPT / claudehead を assignee enum に入れること（自己監査禁止）。

## 11. ratify 後の段取り

この設計が ratify されたら、§8 を最小差分で実装 + §9 のテスト + README へ追記。
現行コマンド（status/close/close-all/action-queue/worklist）の挙動は不変。
WORKER_DELEGATION の assignee layer の隣に「受け渡しパケット契約」を足すだけ。
