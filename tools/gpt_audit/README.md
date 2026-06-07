# alo-gpt-audit — GPT Pro 監査ループ運用ツール

GPT Pro お目付け役の監査を「**返答で終わらせず、Claude の再思考まで回す**」ための
依存ゼロ Python CLI。Owner が「監査を回して」「回しといて」「監査溜まってない？」と
言ったときに動く、`gpt_ometsuke/` レーンの行き・帰り・**反映**処理を担う。

## 正本 (canonical references)

- `GPT_PRO_AUDIT_LOOP_RULE_v0.1_20260607.md`
- `GPT_PRO_AUDIT_LANE_DESIGN_v0.3_20260607.md`
- `GPT_PRO_AUDIT_LANE_APPROVAL_RULE_v0.1_20260606.md`

## 設計原則 (v0.2 から不変)

> **フォルダ位置を状態にする。`to_gpt/` 直下は未回答 REQUEST だけ。**
> RESULT を返したら REQUEST を `to_gpt/processed/` へ退避する。
> **だが退避は反映ではない。** `reflected:true` と lifecycle の `accepted`
> (Owner ratify 経由) に到達して、監査は初めて閉じる。

## レーン構造 (root = `gpt_ometsuke/`)

```
gpt_ometsuke/
├── to_gpt/                 # REQUEST 置き場。直下 = 未回答だけ
│   ├── *_REQUEST.md        #   active (未回答)
│   └── processed/          #   退避済み REQUEST (回答 1 回分は済)
├── from_gpt/               # RESULT 置き場 (*_RESULT.md)
├── approval_queue/         # next_action=ratify のカード
├── patch_queue/            # next_action=patch のカード
├── material_queue/         # next_action=required_materials のカード
├── rejected_queue/         # next_action=reject のカード
└── _AUDIT_LEDGER.jsonl     # 監査台帳 (append-only。SoT はフォルダ位置、台帳は派生控え)
```

## インストール / 実行

依存なし (Python 3.9+)。root は Box Drive 同期パスを指す。
実 Box で回す手順は **`RUNBOOK_macCC.md`** (Mac 単一書き手向け) を参照。

```bash
export ALO_GPT_AUDIT_ROOT="$HOME/Library/CloudStorage/Box-Box/.../gpt_ometsuke"
python3 tools/gpt_audit/alo_gpt_audit.py status
# または --root で明示
python3 tools/gpt_audit/alo_gpt_audit.py --root /path/to/gpt_ometsuke status
```

> **単一書き手**で実行すること (退避とリネームの競合を避ける)。

## コマンド

| コマンド | 役割 | 承認 |
|---|---|---|
| `status [-v]` | 三点照合でレーン状態 (読取) | 不要 |
| `close <id> [--apply]` | 1 件 close (退避+台帳+route)。既定 dry-run | 不要 |
| `close-all [--apply]` | answered を一括 close。既定 dry-run | 不要 |
| `action-queue` | `reflected:false` の一覧 = Claude の次手 | 不要 |
| `owner-digest [--all]` | Owner 5 行サマリ | 不要 |
| `reflect <id> [--apply]` | RESULT を反映済みにする (`reflected:true`) | 不要 |
| `lint` | REQUEST preflight (T2 必須キー) | 不要 |
| `health [--json]` | 監査レーン health report | 不要 |
| `gate-check <op>` | 操作の承認要否を判定 | — |

## 監査ループ (理想形)

```
Owner: 「監査を回して」「監査溜まってない？」
  ↓ (GPT Pro が REQUEST を監査し from_gpt に RESULT)
alo-gpt-audit status        # 未回答 / answered_not_processed / bad_label を確認
  ↓
alo-gpt-audit close-all --apply
  # 1) answered REQUEST を to_gpt/processed/ へ退避  (承認不要)
  # 2) _AUDIT_LEDGER.jsonl に追記                    (承認不要)
  # 3) result_label -> next_action_type で振分けカード作成 (承認不要)
  ↓
alo-gpt-audit action-queue  # Claude が読む: patch / 資料補充 / 再投函 / ratify待ち / reject
  ↓ (Claude が patch / 再投函 等を実施)
alo-gpt-audit reflect <id> --apply   # reflected:true。ループが 1 周閉じる
  ↓
alo-gpt-audit owner-digest  # Owner には 5 行サマリだけ返す
```

## result_label → next_action_type (LOOP_RULE §3)

| result_label | next_action_type | queue | loop_state(初期) | Owner |
|---|---|---|---|---|
| `*_PASS` | ratify | approval_queue | ratify_wait | ratify必要 |
| `*_PASS_WITH_NOTES` (blocking 無) | ratify | approval_queue | ratify_wait | ratify必要 |
| `*_PASS_WITH_NOTES` (blocking 有) | **patch** | patch_queue | returned | 判断必要 |
| `*_MODIFY_REQUIRED` | patch | patch_queue | returned | 不要 |
| `*_NEED_MORE` | required_materials | material_queue | returned | 不要/判断 |
| `*_FAIL` / `*_REJECT` | reject | rejected_queue | returned | 判断必要 |

`*_ESCALATE_OWNER` は `NEED_MORE` (need_more_type=ambiguity_owner) として扱う。

## 三点照合 (DESIGN v0.3 §I) — 二重回答防止

REQUEST ↔ RESULT の対応を次の優先順で確定する:

1. `result_expected_filename` (front-matter) == RESULT ファイル名 — 最強・言語非依存
2. ファイル名規約 (`_REQUEST.md` → `_RESULT.md`)
3. `request_id` が RESULT 本文/ファイル名に含まれ、かつ gate 一致

いずれも満たさない → `missing_result` (移動しない)。
RESULT 先頭行が `<GATE>_<VERDICT>` でない → `bad_label` (移動しない)。

## 承認不要 / 承認必要 (APPROVAL_RULE)

**このツールが行うのは「監査の帰り便 = 承認不要な事務」だけ。**

- 承認不要: RESULT 保存 / REQUEST の processed 退避 / 台帳追記 / action queue 更新。
- 承認必要 (**このツールは絶対に実行しない**): DD accepted/canonical 化、Generated
  Index backfill、本番 DB 投入・DDL、SF 書戻し、外部送信・公開。

`gate-check <op>` で要否を判定できる (owner-gated は exit code 2)。

## 台帳 (`_AUDIT_LEDGER.jsonl`) 1 レコードの項目

append-only JSONL。`reflect` も新イベント行として追記し、`action-queue` は
request_id ごとに最新行 (後勝ち) で状態を判定する。

```json
{
  "ts": "2026-06-07T20:00:00+09:00",
  "event": "close",
  "request_id": "...", "request_filename": "...", "result_filename": "...",
  "result_label": "DDX_MODIFY_REQUIRED", "verdict": "MODIFY_REQUIRED", "gate": "DDX",
  "next_action_type": "patch", "ratify_required": false, "requeue_expected": true,
  "need_more_type": null, "reflected": false,
  "blocking_before_ratify": [], "missing_materials": [],
  "owner_digest_5line": "監査: ...\n結論: ...\n...",
  "claude_rethink_prompt": "[DDX] MODIFY: ...",
  "loop_state": "returned",
  "queue": "patch_queue", "approval_required_to_act": false
}
```

`loop_state`: `returned`(返却・未反映) → `reflected`(反映済) / `requeued`(再投函) /
`ratify_wait`(PASS で ratify 待ち) → `closed`(反映済かつ次アクション無)。

## テスト / 検収 (DESIGN v0.3 §H)

```bash
python3 -m unittest discover -s tools/gpt_audit/tests -v
```

| test | 内容 |
|---|---|
| TEST-1 status | answered_not_processed を正しく数える |
| TEST-2 dry-run | 退避予定表示・NEED_MORE/MODIFY も対象・何も動かさない |
| TEST-3 execute | REQUEST→processed、to_gpt 直下 answered=0、RESULT 残置 |
| TEST-4 idempotency | 再実行で二重移動・二重台帳・二重カードなし |
| TEST-5 missing-result | RESULT 無し REQUEST は移動しない |
| TEST-6 bad-label | 先頭行が不正な RESULT は移動しない |
| + action-queue | `reflected:false` が出る / reflect で消える |
| + classification | PASS→ratify / MODIFY→patch / NEED_MORE→materials / blocking→patch |
| + approval | owner-gated は実行されない (exit 2) |
| + owner-digest | 5 行 |
| + ledger-fields | LOOP_RULE 必須項目すべて |

## デモ / 成果物生成

```bash
python3 tools/gpt_audit/demo_run.py   # artifacts/ に dry-run / 実行 / health を生成
```

生成物: `artifacts/DRYRUN_demo_4items.txt`, `artifacts/EXEC_demo_4items.txt`,
`artifacts/HEALTH_demo_lane.md`。実レーン観測は `artifacts/HEALTH_real_lane_20260607.md`。

## 原則文

> 監査は一回の返答ではなく、Claude の再思考まで含む品質改善ループである。
> Owner の短い合図で REQUEST を拾い、GPT Pro が別 family 監査を返し、Claude が
> それを読んで次の仕事を始める。Owner には 5 行サマリだけを返し、詳細は Box 上の
> 監査記録 (`_AUDIT_LEDGER.jsonl` / action queue) に残す。
