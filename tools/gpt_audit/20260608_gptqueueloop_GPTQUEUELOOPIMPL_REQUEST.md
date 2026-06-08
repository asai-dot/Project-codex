```yaml
request_id: 20260608_gptqueueloop_GPTQUEUELOOPIMPL
topic: gptqueueloop
gate: GPTQUEUELOOPIMPL
status: queued
result_expected_filename: 20260608_gptqueueloop_GPTQUEUELOOPIMPL_RESULT.md
supersedes_request_id: 20260608_queueaudit_loop_GPTQUEUE_REVIEW
review_scope:
  include:
    - .processed.md の物理退避と命名統一（A-01対応）の実配置
    - _AUDIT_LEDGER.json（機械可読台帳）の妥当性 — 25件・next_action_type固定・reflected
    - _ACTION_QUEUE.md（反映キュー派生ビュー）の妥当性
    - alo-gpt-audit CLI の TEST-1〜6 検収（status/close/close-all/action-queue/lint）
    - loop_state（returned/requeued/ratify_wait/reflected）の付与判断
  exclude:
    - 各 from_gpt RESULT の中身（設計内容）の再審査（本件は監査ループ実装の検収であって設計再監査ではない）
    - accepted/canonical 昇格の可否（Owner ratify ゲート）
regression_anchors:
  - GPT_PRO_AUDIT_LANE_DESIGN_v0.3 (Box:2269736541410) — フォルダ位置=状態 / §C label→next_action / §D action queue / §H TEST
  - GPT_PRO_AUDIT_LOOP_RULE_v0.1 (Box:2270127270632) — §8 action queue / §11 owner_digest/claude_rethink/loop_state
  - ALO_GPT_AUDIT_ROUTE_RULES_v0.1 (Box:2269686181805) — Rule4 label routing
decision_requested:
  - 監査ループ実装の検収として PASS / PASS_WITH_NOTES 可否
  - .jsonl を書けない制約下で _AUDIT_LEDGER.json（配列形）を機械台帳正本とする運用の是非
  - loop_state の付与（特に requeued=後続版投函済みを reflected 相当として扱う）の妥当性
self_doubt:
  - .jsonl 拡張子を Box MCP が書けないため機械台帳を .json 配列に切替えた。jsonl 前提のツール/運用と齟齬しないか
  - owner_digest_5line / claude_rethink_prompt をスペース節約のため _AUDIT_LEDGER.json から外し _ACTION_QUEUE.md に集約した。台帳の最小フィールド要件(§2)を満たすと言えるか
  - 旧 _AUDIT_LEDGER.jsonl(2269735330886) は MCP で上書き不能のため description で superseded 表示に留めた。実体が残ることで二重台帳と誤認されないか
  - matterevent に RESULT ファイルが2つ（_DDMATTEREVENT_RESULT.md と _DDMATTEREVENT_REQUEST_RESULT.md）。後者を重複として reflected 扱いにしたが妥当か
  - reflected の初期値は全件 false にせず、後続版が投函済みのものを requeued+reflected=true とした。GPTの「全RESULT reflected:false で台帳化」という指示と運用解釈が割れないか
questions_for_gpt:
  - この実装で「監査結果をClaudeが消化して次作業へ進むループ」の検収は閉じるか。残る blocking があれば具体的に
  - 機械台帳は .json 配列で確定してよいか、それとも .jsonl を Box UI 経由で別途維持すべきか
  - reflected を true 化する正式条件（GPT再監査PASS時 / Owner ratify時 / 後続版投函時）の定義を固定したい
artifacts:
  - Box _AUDIT_LEDGER.json (2271020613373) — 機械可読台帳 25件
  - Box _ACTION_QUEUE.md (2271025917499) — 反映キュー（reflected:false=14）
  - Box _VERIFY_20260608_GPTQUEUELOOPIMPL.md — 検収ログ（本REQUESTと同梱）
  - Box ledger/_AUDIT_LEDGER_pre20260608_backup.jsonl (2270958229506) — 旧台帳backup
  - git Project-codex tools/gpt_audit/ — alo_gpt_audit.py / tests / backfill_seed_20260608.py / 生成jsonl
target_mode: box_pointer_only
source_hash: sha1:unresolved_pointer_only
```

# GPTQUEUELOOPIMPL — GPT監査ループ実装の検収依頼

## 1. 背景

`20260608_queueaudit_loop_GPTQUEUE_REVIEW`（= GPTQUEUE_MODIFY_REQUIRED）に対する Claude 側 patch。
required_patches 1-7 を実施し、監査が「キューは空です」で止まらず、反映キューの実体化まで進む状態にした。

## 2. 実施内容（required_patches → 実体）

1. **物理退避 + 命名統一（A-01）**: `to_gpt/` 直下の回答済み `.processed.md` 7件を `to_gpt/processed/` へ移動し
   `.processed` suffix を除去。processed/ 内の旧3件も正規名化。→ `to_gpt/` 直下は未回答2件(legaldb v0.6 / purchaserec v0.2)のみ。
2. **_AUDIT_LEDGER 実体化**: from_gpt RESULT 全25件を機械可読台帳化（`_AUDIT_LEDGER.json`）。
   各件に request_id/result_label/next_action_type/ratify_required/requeue_expected/reflected/loop_state/
   file_id を保持。digest/rethink/blocking は `_ACTION_QUEUE.md` に集約。
3. **action-queue**: `_ACTION_QUEUE.md` を派生生成。reflected:false=14件を patch→required_materials→ratify 順で表示。
4. **label→next_action 固定**: PASS/PASS_WITH_NOTES=ratify, MODIFY_REQUIRED=patch, NEED_MORE=required_materials, FAIL=reject。
5. **backfill**: 25件すべてに owner_digest_5line + claude_rethink_prompt + loop_state を付与。
6. **検収ログ**: `_VERIFY_20260608_GPTQUEUELOOPIMPL.md`（status/dry-run/apply/idempotency/action-queue/TEST-1〜6）。
7. **CLI 実装**: Project-codex `tools/gpt_audit/alo_gpt_audit.py`（依存ゼロ）。
   status/close/close-all/action-queue/lint。TEST-1〜6 を unittest 化（12件 PASS）。

## 3. 反映キュー現況

- patch(2): ccguard v0.1.2、本件
- required_materials(2): quasijudicial v0.4、legallibbiblio v0.5
- ratify(10): claudehead v1.1 / matterevent v0.5.1 / codexgov / statusregistry v0.2 / canonicalindex /
  caselink DM / codexprogress v0.2 / lawtime v0.2.1 / sessionaudit / toclegalref v0.2
- requeue/反映済(11)

## 4. 見てほしい点

§front-matter の review_scope / self_doubt / questions_for_gpt を参照。
特に「.json 配列を機械台帳正本とする運用」「loop_state/reflected の付与判断」「監査ループ検収として閉じるか」。

想定ラベル: GPTQUEUELOOPIMPL_PASS_WITH_NOTES（実装は通るが運用規約の確認が残る想定）。
