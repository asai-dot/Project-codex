# alo-gpt-audit — GPT Pro お目付け役 監査レーン CLI

`handoffs/gpt_ometsuke/`（Box）の GPT Pro 監査レーンを回す依存ゼロ Python CLI と、
その台帳・反映キューの実体。

## 設計正本

- GPT_PRO_AUDIT_LANE_DESIGN v0.3 (Box:2269736541410)
- GPT_PRO_AUDIT_LOOP_RULE v0.1 (Box:2270127270632)
- ALO_GPT_AUDIT_ROUTE_RULES v0.1 (Box:2269686181805)
- PROTOCOL.md (Box:2266009787864)

中核原則（不変）: **フォルダ位置を状態にする。`to_gpt/` 直下は未回答だけ。**
退避は「GPT 照会1回分は回答済み」という pipeline 状態にすぎず、artifact lifecycle の
accepted 化（Owner ratify 経由）とは別軸。

## レーン構成（root 配下）

```
to_gpt/              未回答 REQUEST だけが直下に残る
to_gpt/processed/    回答済み REQUEST の物理退避先（名前ではなく場所で状態を表す）
from_gpt/            GPT Pro が返す RESULT
_AUDIT_LEDGER.jsonl  派生台帳（SoT はフォルダ位置。台帳は控え）
```

## CLI

```bash
# root は Box Drive 同期パス、または fixture ディレクトリ
export ALO_GPT_AUDIT_ROOT=/path/to/handoffs/gpt_ometsuke

python3 alo_gpt_audit.py status              # 三点照合でレーン状態
python3 alo_gpt_audit.py close-all           # answered_not_processed を一括退避（既定 dry-run）
python3 alo_gpt_audit.py close-all --apply    # 実退避（REQUEST→processed, suffix除去, 台帳追記）
python3 alo_gpt_audit.py close <request_id>   # 単一退避
python3 alo_gpt_audit.py action-queue        # reflected:false の反映キュー
python3 alo_gpt_audit.py build-ledger        # フォルダ状態から台帳再生成（人手項目は引継ぎ）
python3 alo_gpt_audit.py lint [request_id]    # REQUEST preflight（T2 必須メタ）
```

`result_label → next_action_type`（固定）:

| label | next_action | queue |
|---|---|---|
| PASS / PASS_WITH_NOTES | ratify | approval_queue |
| MODIFY_REQUIRED | patch | patch_queue |
| NEED_MORE | required_materials | material_queue |
| FAIL | reject | rejected_queue |

## 検収（TEST-1〜6, lane design v0.3 §H）

```bash
python3 tests/test_alo_gpt_audit.py    # 12件（TEST-1..6 + 補助）
```

- TEST-1 status / TEST-2 dry-run / TEST-3 execute / TEST-4 idempotency /
  TEST-5 missing-result / TEST-6 bad-label。

## 台帳の実体（2026-06-08 backfill）

- `backfill_seed_20260608.py` — from_gpt RESULT 全25件の機械生成 seed（全フィールド・provenance）。
- `_AUDIT_LEDGER.generated.jsonl` — 上記の出力（全フィールド版 jsonl, git 正本）。
- `_AUDIT_LEDGER.json` — Box 用の機械可読台帳（配列形・lean）。Box `_AUDIT_LEDGER.json`(2271020613373) と一致。
- `_ACTION_QUEUE.md` — 反映キュー派生ビュー（digest/rethink/blocking 付き）。Box(2271025917499) と一致。
- `_VERIFY_20260608_GPTQUEUELOOPIMPL.md` — 検収ログ。Box(2271029433015) と一致。
- `20260608_gptqueueloop_GPTQUEUELOOPIMPL_REQUEST.md` — GPT 再投函 REQUEST。Box to_gpt(2271031113115)。

### Box の `.jsonl` 制約

Box MCP は `.jsonl` 拡張子を書けない（`json` は可）。このため Box 側の機械台帳は
`_AUDIT_LEDGER.json`（配列形）で提供し、全フィールド版 jsonl は git に常設する。
旧 Box `_AUDIT_LEDGER.jsonl`(2269735330886) は superseded 表示にし、backup を
`ledger/_AUDIT_LEDGER_pre20260608_backup.jsonl`(2270958229506) に保全済み。
