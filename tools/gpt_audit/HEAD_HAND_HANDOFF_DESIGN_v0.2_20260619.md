# HEAD_HAND_HANDOFF_DESIGN v0.2 — ヘッド↔ハンドのシームレス受け渡し設計

- status: **draft (未ratify・未実装)**
- date: 2026-06-19
- gate: `HANDOFF`
- revision: v0.1 → v0.2。`HANDOFF_PASS_WITH_NOTES`
  (`20260619_head_hand_handoff_design_v0.1_GPTPRO_AUDIT_RESULT.md`) の must_fix 6件・
  should_fix 5件を反映。
- 関連設計: `WORKER_DELEGATION_DESIGN_v0.1_20260619.md`（assignee layer。本書はその
  「シーム＝受け渡し境界」を解く姉妹設計。**統合せず相互参照**＝監査 should_fix #1）
- 共有スキーマ: `HANDOFF_SCHEMA_APPENDIX_v0.1_20260619.md`（両設計が共有するパケット
  スキーマ登録簿。監査 should_fix #1）
- 関連正本:
  - `DD-CLAUDEHEAD-001-core_head_hand_role_protocol_accepted_v1.0`（head/hand ロール正本）
  - `GPT_PRO_AUDIT_LOOP_RULE_v0.1_20260607.md`
  - `GPT_PRO_AUDIT_LANE_DESIGN_v0.3_20260607.md`
  - `GPT_PRO_AUDIT_LANE_APPROVAL_RULE_v0.1_20260606.md`
- prior art: `handoff/WORKER_TASK_PACKET_*.md`（既存 task packet 形式を形式化する）

---

## 0. なぜ要るか（問題）

claudehead（ヘッド）と `local`/`codex`/`worker_cc`（ハンド）は**別セッション・共有
メモリなし**で動く。両者の間を渡れるのは**ファイル（アーティファクト）だけ**である。
ここから本設計の全てが従う不変条件が一つ出る。

> **不変条件 H1: シームは直列化境界である。ハンドオフ・アーティファクトに
> 書かれなかった文脈は、シームを渡らない。**（監査 F1: governing invariant として保持）

これにより「シームレス」が曖昧な願望ではなく**検証可能な契約**になる。
受け渡しがシームレスである ⇔

- **下り物が context-closed**: ハンドはこれ以上ヘッドに訊かず実行できる。
- **上り物が result-closed**: ヘッド/`local` はこれ以上 work 本体を読まず統合できる。

設計が潰すべき失敗モードは3つ（v0.2 で1つ追加）。

| 失敗モード | 症状 | 対応する既存リスク |
|---|---|---|
| **過少記述**（薄い queue 行だけ渡す） | ハンドが文脈不足 → ヘッドへ往復 → **ヘッドの枠を出血** | 現 `action-queue` 行が薄すぎる |
| **過結合**（ヘッドの生メモリを共有しようとする） | 別セッションでは原理的に不可能・脆い | — |
| **肥大**（inline を無制限に同梱） | パケットがミニ書庫化・陳腐化・読むのが高コスト・監査困難 | 監査 F4 で指摘 |

## 1. 設計原則（不変条件。1つも崩さない）

1. **シームは直列化境界（H1）。** ヘッドの記憶・会話履歴に依存した受け渡しを禁止。
2. **コストの非対称を設計する。** ヘッドは dispatch 時（文脈が熱いうち）に太いパケットを
   一度だけ書く。以後は薄いインデックスを読むだけ。ハンドは太いパケットを読む。
   ヘッドは統合時に薄い上りサマリだけ読む。**誰も再導出しない。往復ゼロ。**
3. **単一書き手は不変。** 索引/台帳の更新・レーンのファイル移動は `local` 固定。
   ハンドは上りパケットを**書くだけ**。
4. **gated は受け渡しで上書きされない。** owner/auditor/production gated は HOLD のまま。
   全パケットに **HOLD echo** を載せて境界をハンドオフ越しに生存させる（should_fix #2）。
5. **二層を両持ちする。** パケットは認知ロール（層1）と実行レーン assignee（層2）を両方載せる。
6. **変更系には no-lease を使わない（v0.2 新設）。** 状態変更・金銭コスト・外部書込・
   破壊的タスクは lease/claim を要求する。no-lease レーンは非変更系に限る（§5、監査 F5）。

## 2. 解 — 二層アーティファクト

シームを「薄いインデックス」と「太いパケット」に分離する。

- **thin index** = `action-queue` / `worklist` の1行。**triage 十分**であること
  （監査 must_fix #6: 索引が薄すぎてヘッドがパケットを開く事態を防ぐ）。最低フィールド:

  `packet_id`, `source_queue_item_id`, `decision_id`, `assignee`, `role`,
  `next_action_type`, `status`, `hold_flags`, `risk_class`/`gate`,
  `priority`（使う場合）, `→packet`, 一行 `objective`, 閉鎖時 `→result`。

- **fat packet** = 索引が指す**自己完結パケット**（`handoff/` の1ファイル）。
  ハンドが読むのはヘッドの頭ではなく**これ**。スキーマは付録に登録。

この分離が原則2（コスト非対称）を物理的に実現する。

## 3. 下りパケット（DISPATCH）— context-closed 契約

スキーマの正は `HANDOFF_SCHEMA_APPENDIX`。中核ルールは
**「ハンドがヘッドに訊きたくなる事項は全部 `context_closure` に入れる」**。

```yaml
# --- identity / integrity（監査 must_fix #5） ---
packet_schema_version: handoff-dispatch/0.2
packet_id: DISP_20260619_<slug>_001          # 連結キー（不変）
packet_created_at_jst: 2026-06-19T..
packet_hash: <sha256 of canonical body>
source_queue_item_id: <action-queue item id> # 来歴（dedup 突合キー）
source_request_id / decision_id: ...
source_artifact_hashes: {<file_id>: <sha256>, ...}   # 参照元の固定（取得可能な範囲）
# --- routing（二層） ---
role: worker | deterministic | supervisor     # 層1：認知ロール
assignee: local | codex | worker_cc           # 層2：実行レーン（enum検証）
assignee_source: front_matter | gate_override | action_default
next_action_type: design_patch | doc_patch | code_patch | test_patch
                 | refactor | required_materials | reject | ...
# --- safety / gate ---
mutation_class: non_mutating | mutating       # ★§5 のレーン振分けキー
gated_override_block: true                     # owner/auditor/production gated は HOLD維持
hold_echo: [owner_gated, production, external_send, ...]   # should_fix #2
prohibited_actions: [no-production-db-write, no-DDL, no-SF-writeback, ...]
# --- work ---
objective: <一文。done の定義>
context_closure:            # ★シームレスの心臓部。ヘッドが文脈の熱いうちに一度だけ払う
  context_closure_index:    # 監査 must_fix #5: 何を inline / 何を参照 で渡したかの一覧
    inlined: [<section>, ...]
    referenced: [{ref: <file_id|path>, hash: <sha256>, why: <一言>}, ...]
  pull_branch: claude/...
  excerpts: |               # decision-critical な抜粋のみ inline（監査 F4 サイズ規律）
    ...
inputs / materials: [<file_id | path>, ...]
do: [手順1, 手順2, ...]
acceptance: [ハンドが done 宣言前に自己検証する条件]
# --- size discipline（監査 must_fix #1） ---
oversize_reason: <soft cap 超過時のみ必須>
must_read_sections: [<超過時に必ず読む節>, ...]
# --- return contract ---
output_contract:
  output_path: _claude_dispatch/from_worker/<...>_RESULT.md
  upload_target: Box .../material_queue/<...>
  required_fields: [result_schema_version, packet_id, source_queue_item_id,
                    status, verdict, outputs, acceptance_results]
proposal_only: true | false  # worker は設計判断を自分で accepted にしない
clarification_budget: 0      # should_fix #3: 「ヘッドに訊きたい」を可視化（既定0）
staleness_check: <参照が複数セッション跨ぐ時の鮮度確認方法>   # should_fix #4
```

`role`（層1）と `assignee`（層2）を**同じパケットが両方持つ**ことで、監査論点C
（既存 5.5/5.3/Python 分業との整合）が抽象論ではなく**ハンドオフ実体の上で**解ける。

## 4. 上りパケット（RESULT）— result-closed 契約

名前と形は下りの `output_contract` が指定済み。

```yaml
result_schema_version: handoff-result/0.2
packet_id: <下りを echo>          # ループを閉じる
packet_hash: <下りの packet_hash を echo（取得可能なら）>
source_queue_item_id: <echo>     # local の突合・dedup・processed化キー
status: done | blocked | needs_more | proposal
verdict / summary: <ヘッドが読む用。何が変わったか。work本体は読ませない>
outputs: [<生成 file_id/path>, ...]
output_artifact_hashes: {<path>: <sha256>, ...}     # 監査 must_fix #5
diff_summary: ...
acceptance_results: [{criterion: <...>, pass: true|false}, ...]   # 基準ごとに pass/fail
for_head / unresolved: [上げ返す判断（特に proposal_only 項目）]
supersedes / duplicate_of: <該当時、対象 packet_id/result>
proposal_only: <下りを echo>
next: <推奨フォロー（決めるのはヘッド、提案するのはハンド）>
```

これにより「**正しく見える別パケットの結果**」（監査 F7）を hash/echo で弾ける。

## 5. シーム閉鎖 — local 単一書き手 ＋ 重複結果の調停（並行制御ではない）

**v0.2 の再定義（監査 must_fix #2/#3）。** no-lease の仕組みは**二重実行を防がない**。
これは local が**重複した結果を決定論で調停する**機構であって、並行制御ではない。
正直に次のとおり扱う。

- 二重**実行**は依然起こりうる。これは並行制御機構ではない。
- local は同一 `source_queue_item_id` の複数上りを**重複結果**として調停し、代表を残し
  他を `superseded/` へ退避する。
- 上りはハンドが書くだけ。索引/台帳更新は `local` 固定（原則3）。

### 5.1 レーン安全境界（mutation_class による振分け・監査 must_fix #3）

| mutation_class | 例 | 競合制御 |
|---|---|---|
| `non_mutating` | proposal / draft / review / 設計改稿案 / 調査 | **no-lease dedup でよい**（重複は調停で吸収） |
| `mutating` | 金銭コスト・状態変更・**ファイル移動**・外部書込・破壊的・本番影響 | **lease/claim 必須**。no-lease レーンで実行しない |

dispatch 時に `mutation_class` を必須にし、`mutating` を no-lease レーンに流すのは
バリデーションで弾く。lease/claim ledger 自体は本版スコープ外（§10）だが、**境界**は
v0.2 で確定させる。

### 5.2 代表選定の順序（監査 must_fix #4。`first-by-time` 単独は禁止）

1. **acceptance 合格**の結果が勝つ。
2. 複数合格なら、**evidence 完全性 / 宣言された証拠グレード最高**が勝つ。
3. それでも区別不能なら、**最も早い有効結果**。
4. 不合格・スキーマ不正は統合せず `superseded/`（証跡として保持）。

## 6. 「シームレス＝往復ゼロ」を gate 化（context-closed チェック ＋ サイズ規律）

ヘッドが dispatch 前に自己検証。1つでも欠ければ**未差配**。

**context-closed 5条件:**
1. `objective` がある。
2. `inputs` が全て id/path で**ヘッド不在でも解決可能**。
3. `do` が inline/リンク済み材料**のみ**を参照。
4. `output_contract` が上り物を完全指定。
5. `acceptance` が**ハンド単独で**検証可能。

**サイズ規律（監査 must_fix #1 / F4）:**
- inline は decision-critical な抜粋のみ。完全版は path/hash 参照。
- 各参照に「なぜ要るか」を `context_closure_index.referenced[].why` で付す。
- soft cap を設ける。超過時は `oversize_reason` ＋ `must_read_sections` 明記時のみ
  dispatch 許可（hard cap ではない）。

## 7. 監査ノート（HANDOFF_PASS_WITH_NOTES）との接続

| 監査ノート | v0.2 での反映箇所 |
|---|---|
| must_fix #1 サイズ規律 | §3 `oversize_reason`/`must_read_sections`、§6 サイズ規律 |
| must_fix #2 dedup 再定義 | §5 冒頭「重複結果の調停。並行制御ではない」 |
| must_fix #3 no-lease レーン限定 | §5.1 `mutation_class` 振分け、原則6 |
| must_fix #4 代表選定順序 | §5.2 acceptance→evidence→earliest |
| must_fix #5 整合フィールド | §3/§4 schema_version/packet_hash/artifact_hashes/echo |
| must_fix #6 索引 triage | §2 thin index 最低フィールド |
| should_fix #1 共有付録 | `HANDOFF_SCHEMA_APPENDIX`（統合せず相互参照） |
| should_fix #2 HOLD echo | §3 `hold_echo`、原則4 |
| should_fix #3 clarification_budget | §3 `clarification_budget: 0` |
| should_fix #4 staleness_check | §3 `staleness_check` |
| should_fix #5 test fixtures | §9 |

## 8. 実装ポイント（最小差分。ratify 後）

`alo_gpt_audit.py` 側:

1. `write_route_card` / dispatch 生成に identity/integrity/safety/size/return の各
   フィールド（§3）を出す。
2. `action-queue` 行（thin index）に §2 の triage フィールドを追加。
3. `local` の close 系に「同一 `source_queue_item_id` の重複結果調停（§5.2 順序で
   代表残し・他 `superseded/`）」を追加。
4. dispatch 前バリデーション: context-closed 5条件（§6）＋ `mutation_class==mutating`
   は no-lease レーン禁止（§5.1）＋ サイズ規律。

台帳 (`_AUDIT_LEDGER.jsonl`) へは `packet_id` 等のキー追加のみ。append-only・
後勝ち読みは不変。旧レコードは「未差配」扱い。

## 9. テスト計画（ratify 後・既存 unittest に追加。should_fix #5）

| test | 内容 |
|---|---|
| dispatch-context-closed | §6 の5条件を満たさない下りは未差配で弾く |
| dispatch-missing-context-closure | context_closure 欠落で弾く |
| down/up-packet-schema | 必須フィールド・schema_version・hash を検証 |
| up-packet-linkage | 上りが packet_id/source_queue_item_id/hash を echo |
| dedup-valid-vs-invalid | 合格1・不正1 → 合格を代表、不正は superseded |
| dedup-two-valid | 2合格 → evidence 完全性で代表選定 |
| oversize-with/without-reason | 超過パケットは reason 有りのみ許可 |
| forbidden-no-lease-mutating | `mutating` を no-lease レーンに流すと弾く |
| gated-override-block | assignee 明示でも gated は HOLD |
| ledger-back-compat | packet キー無し旧レコードでも壊れない |

## 10. やらないこと（スコープ外）

- 自動ディスパッチ（実 codex/worker_cc セッション起動）は本版で作らない。
- lease/claim ledger の**実装**は本版スコープ外。ただし `mutation_class` による
  **境界**は v0.2 で確定（§5.1）。lease 実装は別版。
- GPT / claudehead を assignee enum に入れること（自己監査禁止）。

## 11. ratify 後の段取り

ratify されたら §8 を最小差分で実装 + §9 のテスト + README 追記。現行コマンド
（status/close/close-all/action-queue/worklist）の挙動は不変。WORKER_DELEGATION の
assignee layer の隣に受け渡しパケット契約を足すだけ。スキーマは付録を単一の正とする。
