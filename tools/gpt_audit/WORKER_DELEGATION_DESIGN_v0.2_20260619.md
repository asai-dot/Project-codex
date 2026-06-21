# WORKER_DELEGATION_DESIGN v0.2 — 司令塔から3ワーカーへの差配設計

- status: **draft (未ratify・未実装)**
- date: 2026-06-21
- revision: v0.1 → v0.2。`HANDOFF_MODIFY_REQUIRED`
  (`20260620_head_hand_handoff_design_v0.3_GPTPRO_AUDIT_RESULT.md` / 2299340018054)
  の v0.4 must_fix #7（姉妹設計を付録正本へ同期）を反映。
- **スキーマの正本**: `HANDOFF_SCHEMA_APPENDIX_v0.3_20260619.md`（規範的単一正本）。
  本書の field/enum/schema は**自前定義しない**。本書中の YAML/値は non-normative example。
- 関連: `HEAD_HAND_HANDOFF_DESIGN_v0.4_20260619.md`（受け渡しシーム設計。**統合せず**
  付録を共有）。
- 関連正本: `GPT_PRO_AUDIT_LOOP_RULE_v0.1` / `LANE_DESIGN_v0.3` / `LANE_APPROVAL_RULE_v0.1`。
- 実装対象: `tools/gpt_audit/alo_gpt_audit.py`（`next_action_type → queue` 振分けに
  「担当 (assignee)」を1段足す）。

> **v0.2 同期メモ**: v0.1 は `next_action_type=patch` や `derive_assignee` を独自規範で
> 定義していたが、これは付録と二重定義になり実装者がどちらを採るか決められなかった。
> v0.2 では enum・assignee derivation・effect 判定を**すべて付録に委譲**する。

---

## 0. なぜ要るか（問題）

司令塔 (claudehead) が実行まで抱えると司令塔の枠だけ枯れる。下に別枠ワーカー3人:

| ワーカー | 枠 | 得意 |
|---|---|---|
| `local` | ローカル / 大モデル不要 | 事務・Box探索・資料復旧・単一書き手の移動 |
| `codex` | 実行・コード枠 | 実装・改名・リファクタ・テスト実行 |
| `worker_cc` | 別Claude枠 | 重い設計再思考・設計文書の改稿 |

「計画担当が分解して実行担当へ渡す／別カウントで枠が実質倍」を内製ループに写す。

## 1. 設計原則（不変条件。付録 §11 と一致）

1. 司令塔は手を動かさない（分解→差配まで）。
2. 実行は3ワーカーの別枠へ分散。
3. 自己監査の禁止: `assignee` に `gpt`・`claudehead` を入れない（付録 §1.1 禁止値）。
4. 単一書き手不変: 索引/台帳/ファイル移動は `local` 固定。worklist は読み取りのみ。
5. owner-gated 不変（付録 §11-3）。

## 2. 担当の決め方（assignee derivation。正は付録）

`assignee` enum・`assignee_source`・導出は **付録 §1.1 / §7** が正。本書では運用方針のみ:

優先順位（上が強い）:

1. **front-matter 明示 `assignee:`** — ただし**範囲外の明示値は黙って default に
   fallback せず validation error**（付録 §7・`block_reason=invalid_assignee`）。v0.1 の
   「範囲外は無視して既定へ」は**廃止**。
2. **gate override** — コード寄り gate は `codex`。
3. **`next_action_type` 既定** — §3 の対応表。

`allowed_assignees` は access policy registry から local が導出（縮小のみ可・付録 §7）。
レーン事務（close/reflect/relocate の --apply）は常に `local`。

## 3. next_action_type → 既定 assignee（v0.4 enum へ更新）

v0.1 の粗い `patch` は**廃止**し、付録 §1.1 の細分 enum に対応づける（must_fix #7）。

| next_action_type（付録 enum） | 既定 assignee | 根拠 |
|---|---|---|
| `design_patch` | `worker_cc` | 設計再思考 |
| `doc_patch` | `worker_cc` | 文書改稿 |
| `code_patch` | `codex` | 実装寄り |
| `test_patch` | `codex` | テスト |
| `refactor` | `codex` | リファクタ |
| `required_materials` | `local` | Box資料復旧・探索 |
| `reject` | `worker_cc` | 別案起票＝設計判断 |
| `ratify` | （なし／`owner_pending`） | DISPATCH 生成禁止（付録 §1.2） |
| `none` | （なし） | — |

> v0.1 の旧 `patch→worker_cc` は、`design_patch`/`doc_patch`→worker_cc・
> `code_patch`/`test_patch`/`refactor`→codex へ機械変換する。

## 4. セルフサービス（worklist）

`worklist <assignee>` = action-queue（thin index・付録 §2）を担当でフィルタ（読み取り
のみ）。各ワーカーは自分の枠で読み `do:` に従う。司令塔は積むだけ。索引の triage
フィールド（付録 §2）で、ワーカーは fat packet を開かずに優先度判断できる。

## 5. 実装ポイント（最小差分・ratify 後）

`alo_gpt_audit.py`:

1. assignee 導出は付録 §1.1/§7 に従う（独自 enum を持たない）。範囲外明示値は
   validation error。
2. `next_action_type` 既定対応表（§3）。旧 `patch` を新 enum へ変換。
3. `build_record` に `assignee` 付与、route カード/action-queue 行に表示（付録 §2 triage）。
4. `worklist <assignee>` 追加。owner-digest は担当を出さない。

台帳は `assignee` 等キー追加のみ・append-only・後勝ち・旧レコード未差配扱い（付録 §11-4）。

## 6. テスト（ratify 後）

| test | 内容 |
|---|---|
| assignee-default | design_patch→worker_cc / code_patch→codex / required_materials→local |
| assignee-override-fm | front-matter `assignee: codex` が既定に勝つ |
| assignee-invalid-fm | **範囲外明示値は validation error**（fallback しない） |
| assignee-override-gate | code 寄り gate は codex |
| worklist-filter | `worklist codex` が codex 担当だけ返す |
| ledger-back-compat | assignee 無し旧レコードでも action-queue が壊れない |

## 7. やらないこと（スコープ外）

- 担当への自動ディスパッチ（実セッション起動）。
- GPT/claudehead を assignee enum に入れること。
- field/enum/schema を本書で再定義すること（付録が正）。

## 8. ratify 後の段取り

§5 を1コミットで実装＋§6 テスト＋README。現行コマンド（status/close/...）の挙動は不変。
HEAD_HAND の受け渡しパケット契約と隣接し、スキーマは付録を単一の正とする。
