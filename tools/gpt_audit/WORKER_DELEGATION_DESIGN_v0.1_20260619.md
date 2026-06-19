# WORKER_DELEGATION_DESIGN v0.1 — 司令塔から3ワーカーへの差配設計

- status: **draft (未ratify・未実装)**
- date: 2026-06-19
- 関連正本:
  - `GPT_PRO_AUDIT_LOOP_RULE_v0.1_20260607.md`
  - `GPT_PRO_AUDIT_LANE_DESIGN_v0.3_20260607.md`
  - `GPT_PRO_AUDIT_LANE_APPROVAL_RULE_v0.1_20260606.md`
- 実装対象: `tools/gpt_audit/alo_gpt_audit.py`（既存の `next_action_type → queue`
  振分けに「担当 (assignee)」を1段足す）

---

## 0. なぜ要るか（問題）

司令塔 (claudehead) が自分で手を動かして実行まで抱えると、**司令塔の枠だけが先に
枯れる**（データリミット）。本来 claudehead の下には別枠のワーカーが3人いる:

| ワーカー | 枠 | 得意 |
|---|---|---|
| `local`（ローカルちゃん） | ローカル / 大モデル不要 | 事務・Box探索・資料復旧・単一書き手の移動 |
| `codex`（コーデックスちゃん） | 実行・コード枠 | 実装・改名・リファクタ・テスト実行 |
| `worker_cc`（ワーカーClaude Codeちゃん） | 別Claude枠 | 重い設計再思考・設計文書の改稿 |

ツイートの「計画担当が分解して実行担当に渡す／別カウントで枠が実質倍」を、うちの
内製ループに正しく写すと: **claudehead が分解・差配し、実行は3ワーカーの別枠へ
分散する**。これで司令塔の枠の出血が止まる。

## 1. 設計原則（不変条件。これを1つも崩さない）

1. **司令塔は手を動かさない。** claudehead の仕事は「分解 → `action-queue` に
   担当付きで積む」まで。実行枠は使わない。
2. **実行は別枠に分散する。** 担当 = どのワーカーの枠で回すか。各ワーカーは自分の
   担当ぶんだけを自分で拾う（セルフサービス）。
3. **監査(GPT Pro)と計画(claudehead)は実行に手を出さない。** GPT は監査席で不動。
   自分が監査した対象を自分で実行・計画しない（**自己監査の禁止**）。担当 enum に
   `gpt` も `claudehead` も含めない。
4. **単一書き手は不変。** レーンのファイル移動（`close` 退避 / `reflect` / relocate）
   は `local`（=Box同期済み Mac 1台）に固定。ワーカーの `worklist` は**読み取り
   のみ**で、退避・台帳追記を行わない。よって複数ワーカーが同時に動いても
   `to_gpt/processed/` の競合は起きない。
5. **owner-gated は不変。** accepted/canonical 化・本番DB・SF書戻し・外部送信は
   担当に関係なく従来どおり実行しない（`gate-check` exit 2）。

## 2. 担当の決め方（assignee derivation）

優先順位（上が強い）:

1. **REQUEST front-matter の明示 `assignee:`** — Owner / claudehead が個別指定したら
   それが勝つ。値は enum `{local, codex, worker_cc}` のみ許可。範囲外は無視して既定へ。
2. **gate による上書き（コード寄り）** — `CODE_GATES` に属する gate は `codex` へ。
   実装・改名・リファクタが主な DD（例: 機械的 rename 中心のもの）を運用で足していく。
3. **`next_action_type` 既定** — 下表。

| next_action_type | 既定 assignee | 根拠 |
|---|---|---|
| `patch` | `worker_cc` | 設計再思考が要る重い実行（別Claude枠） |
| `required_materials` | `local` | Box資料復旧・探索。大モデル不要 |
| `reject` | `worker_cc` | 別案起票＝設計判断 |
| `ratify` | （なし／Owner） | 人間が ratify。ワーカーに振らない |
| `none` | （なし） | — |

さらに、`action-queue` に出ない**レーン事務**（`close`/`reflect`/relocate の
`--apply`）は常に `local` 固定（= `LANE_ADMIN_ASSIGNEE`、単一書き手の体現）。

> 実例（2026-06-07 の未反映4件）での差配:
> - `legaldb v0.5 DESIGN` [MODIFY] → **worker_cc**（over-reach抑制 / anchor_id定義）
> - `claudehead v1.1` [MODIFY] → **worker_cc**（fallback path 明記）
> - `statusregistry v0.1` [MODIFY] → **codex**（row_disposition 改名＝実装寄り。
>   `CODE_GATES` か front-matter で上書き）
> - `quasijudicial` [NEED_MORE] → **local**（不足3ファイルの復旧）

## 3. セルフサービス（ワーカーが自分で拾う）

新コマンド `worklist <assignee>`: `action-queue` を担当でフィルタして出す。

```bash
alo-gpt-audit worklist codex      # codex の担当ぶんだけ
alo-gpt-audit worklist worker_cc  # worker_cc の担当ぶんだけ
alo-gpt-audit worklist local      # local の担当ぶん（+ レーン事務の指示）
```

- 各ワーカーは自分の枠のセッションでこれを読み、`do:` に従って作業する。
- 読み取りのみ。レーンのファイルは触らない。
- claudehead は積むだけで離れられる（逐一手渡ししない＝枠を使わない）。

## 4. 実装ポイント（最小差分。既存の形に乗せる）

`alo_gpt_audit.py`:

1. 語彙追加: `ASSIGNEES = {"local","codex","worker_cc"}`, `ASSIGNEE_FOR_ACTION`,
   `CODE_GATES = set()`（初期空、運用で育てる）, `LANE_ADMIN_ASSIGNEE = "local"`。
2. `derive_assignee(verdict, next_action, gate, front_matter) -> str | None`
   を追加（§2 の優先順位）。
3. `build_record(...)` の戻り record に `"assignee"` を追加。
4. `write_route_card(...)` のカード本文に `- assignee:` を出す。
5. `cmd_action_queue` の各行に `担当 : <assignee>` を表示。
6. 新コマンド `worklist <assignee>`（`action_queue` を assignee で絞るだけ）。
7. `owner-digest` は担当を出さない（Owner には5行のまま。差配は内部事情）。

台帳 (`_AUDIT_LEDGER.jsonl`) に1キー (`assignee`) 増えるだけ。append-only・後勝ちの
読み方は不変。既存レコード（assignee 無し）は `worklist` で「未差配」として扱う。

## 5. テスト計画（既存 unittest に追加）

| test | 内容 |
|---|---|
| assignee-default | patch→worker_cc / required_materials→local / reject→worker_cc |
| assignee-override-fm | front-matter `assignee: codex` が既定に勝つ |
| assignee-override-gate | `CODE_GATES` の gate は codex へ |
| assignee-enum-guard | 範囲外 `assignee:` は無視して既定へ落ちる |
| worklist-filter | `worklist codex` が codex 担当だけ返す |
| ledger-back-compat | assignee 無し旧レコードでも action-queue が壊れない |

## 6. やらないこと（スコープ外）

- 担当への**自動ディスパッチ**（実際に codex/worker_cc セッションを起動する）は
  この版では作らない。本版は「担当の付与」と「worklist での可視化」まで。起動の
  自動化は別版で、単一書き手・owner-gated を崩さない形を別途設計する。
- GPT / claudehead を担当 enum に入れること（§1-3 自己監査禁止）。

## 7. ratify 後の段取り

この設計が ratify されたら、§4 を1コミットで実装 + §5 のテスト + README へ
コマンド追記。実装は既存の `next_action → queue` 振分けの隣に置くだけで、
現行コマンド（status/close/close-all/...）の挙動は不変。
