# alo-gpt-audit

GPT Pro 目付け役 監査レーン (`gpt_ometsuke/`) の **行き・帰り・完了処理**を機械化する単一書き手 CLI。
設計書: `GPT_PRO_AUDIT_LANE_DESIGN_v0.2_20260606.md` (Box file_id 2269085336900) の実装。

> 設計仕様 v0.3（語彙アライン + 反映キュー）は [`docs/GPT_PRO_AUDIT_LANE_DESIGN_v0.3_20260607.md`](docs/GPT_PRO_AUDIT_LANE_DESIGN_v0.3_20260607.md)。
> 正本は Box (`gpt_ometsuke/`, file_id 2269736541410)。本リポジトリのものは mirror。

## 中核ルール

> `to_gpt/` 直下は、GPT がまだ答えていない REQUEST だけにする。
> RESULT を返したら、元 REQUEST は必ず `to_gpt/processed/` へ退避する。

状態の SoT は **フォルダ位置とファイル実体**。台帳 (`_AUDIT_LEDGER.jsonl` / `.md`) はそこから派生する控え。

## レーン構成

| folder | 役割 | 中身 |
|---|---|---|
| `<root>/to_gpt/` | GPT 未回答の ACTIVE REQUEST | `*_REQUEST.md` |
| `<root>/from_gpt/` | RESULT 正本アーカイブ | `*_RESULT.md` |
| `<root>/to_gpt/processed/` | 退避済み REQUEST の控え | RESULT 作成後の元 REQUEST |

`<root>` は Box folder `gpt_ometsuke/` (387373370306) を Box Drive で同期したローカル実パス。
GPT が毎回 Box をいじるのではなく、**最後の 1 プロセス (Mac CC / 単一書き手)** が退避を実行する。

## インストール

```bash
cd tools/gpt_audit
pip install -e .
```

`pip` を使わず単体実行も可能:

```bash
PYTHONPATH=src python -m alo_gpt_audit status --root /path/to/gpt_ometsuke
```

## 使い方

root は `--root` または環境変数 `ALO_GPT_OMETSUKE_ROOT` で指定する。

```bash
export ALO_GPT_OMETSUKE_ROOT="$HOME/Library/CloudStorage/Box/.../gpt_ometsuke"

# 1) レーン状態の確認 (読み取りのみ)
alo-gpt-audit status
alo-gpt-audit status --json

# 2) 1 件を退避 (検証 + 移動 + 台帳追記)
alo-gpt-audit close 20260605_quasijudicial_v0.4_DDCASESOURCE

# 3) answered_not_processed を一括退避 (既定 dry-run。--apply で実行)
alo-gpt-audit close-all
alo-gpt-audit close-all --apply

# 4) 反映キュー: RESULT を消化するための next_action を表示
alo-gpt-audit action-queue
alo-gpt-audit action-queue --json

# 5) REQUEST の preflight 検査 (scope境界 / target_mode / source_hash)
alo-gpt-audit lint
alo-gpt-audit lint --strict   # 警告があれば exit 1
```

## 台帳派生の運用コマンド (owner-digest / reflect / gate-check / health / consumed)

`close` 時に台帳 (`_AUDIT_LEDGER.jsonl`) は enrich され、`event` / `ts` (JST iso) /
`verdict` / `loop_state` / `owner_digest_5line` / `claude_rethink_prompt` /
`queue` / `approval_required_to_act` を 1 行に持つ。以下のコマンドはこの台帳を
派生ビューとして読む (request_id ごと後勝ち、`reflected:false` かつ
`loop_state != closed` を未消化とみなす)。

```bash
# Owner 向け 5 行サマリ。既定は未消化 (action_queue) のみ、--all で reflected 済みも。
alo-gpt-audit owner-digest
alo-gpt-audit owner-digest --all

# RESULT を反映済みにする (reflected:true を append-only 追記)。既定 dry-run。
# next_action が none/reject なら loop_state=closed、それ以外は reflected。
alo-gpt-audit reflect <request_id>
alo-gpt-audit reflect <request_id> --apply

# 操作の承認要否。承認不要は exit 0、owner-gated / 未知は exit 2 (安全側)。
alo-gpt-audit gate-check status          # -> 0
alo-gpt-audit gate-check production_db    # -> 2

# レーン health report (lane_status 内訳 / 未反映 action item / route queue サイズ)。
alo-gpt-audit health
alo-gpt-audit health --json

# 台帳から CONSUMED.md (消化状態ビュー) を <root>/CONSUMED.md に生成 / 検査。
# check は generated_at 行を無視して比較し、ドリフトがあれば exit 1。
alo-gpt-audit consumed build
alo-gpt-audit consumed check
alo-gpt-audit consumed build --ledger /path/to/_AUDIT_LEDGER.jsonl --generated-at 2026-06-22T00:00:00+09:00
```

`consumed` は台帳を消化状態 (`未反映` / `ratify待ち` / `反映済(後続へ)` /
`反映済` / `closed`) 別に並べた Markdown を `<root>/CONSUMED.md` へ書き出す。
入力台帳は既定で `<root>/_AUDIT_LEDGER.jsonl` (`--ledger` で上書き可)。

## 反映キュー (action-queue) — 監査の出口を閉じる

退避 (`processed/`) は **「GPT 照会 1 回分は回答済み」** を意味するだけで、
**「設計に反映済み」ではない**。RESULT が返っただけで止まると「赤入れをもらった
だけ」事故になる。`action-queue` は from_gpt の全 RESULT を読み、ラベルから
次アクションを導出して反映キュー (Box フォルダを増やさず台帳派生ビュー) を出す。

| RESULT label | next_action_type | flags |
|---|---|---|
| `PASS` / `PASS_WITH_NOTES` | `ratify` | `ratify_required` (PASS_WITH_NOTES は `blocking_before_ratify` を ratify 前に反映必須) |
| `MODIFY_REQUIRED` | `patch` | `requeue_expected` |
| `NEED_MORE` | `required_materials` | `requeue_expected`, `need_more_type`, `missing_materials` |
| `FAIL` | `reject` | — |

RESULT 本文に次の任意項目があれば抽出して表示する (§2 PASS_WITH_NOTES 粒度 / §5 NEED_MORE 細分):

```yaml
need_more_type: material_absent|context_insufficient|evidence_unverified|ambiguity_owner
missing_materials:
  - ...
blocking_before_ratify:    # PASS_WITH_NOTES でも ratify 前に必須の修正
  - ...
```

退避済み (`processed_done`) の RESULT も消化対象として出し続ける — ここが
「監査結果が返っただけで設計に反映されない」事故を防ぐ要。

## lint — REQUEST preflight (監査スコープ境界 §4 / target_mode §6)

T2 監査 (accepted化・規範新設・本番投入前) の REQUEST が、揃っているべき
front-matter キーを持つか検査する (advisory。`--strict` で exit 1)。

```yaml
review_scope:          # include / exclude。exclude が特に重要 (確定事項を蒸し返さない)
regression_anchors:    # 矛盾してはいけない accepted/canonical の Box ID
decision_requested:    # PASS可否 / accepted化可否 / backfill可否
target_mode:           # inline_embedded | box_hash_locked | box_pointer_only
source_hash:           # T2 は box_hash_locked 推奨 (unresolved を弾く)
```

## lane status (三点照合 §6)

`A`=to_gpt直下にある / `B`=from_gpt に RESULT あり / `C`=processed にある。

| lane_status | A | B | C | 意味 / 処理 |
|---|---|---|---|---|
| `active` | ✓ | ✗ | ✗ | queued・GPT 未回答 (正常な待ち) |
| `blocked_active` | ✓ | ✗ | ✗ | `blocked/superseded/cancelled` で待ち |
| `answered_not_processed` | ✓ | ✓ | ✗ | **close 対象** (RESULT あり・未退避) |
| `duplicate_in_processed` | ✓ | ✓ | ✓ | 重複 → 同内容なら集約、差異なら要人間確認 |
| `processed_without_result` | ✓ | ✗ | ✓ | 事故 → 自動処理せず人間確認 |

## close の検証 (§5 完了条件)

1. `from_gpt/<result_expected_filename>` が存在する
2. RESULT 先頭行が `<gate>_{PASS,PASS_WITH_NOTES,MODIFY_REQUIRED,FAIL,NEED_MORE}` のいずれか
3. RESULT 本文の `request_id` が REQUEST と一致 (不一致は拒否 / 欠落は警告)
4. 元 REQUEST を `to_gpt/processed/` へ移動
5. 台帳へ追記

`NEED_MORE` / `MODIFY_REQUIRED` でも退避する。これは「案件完了」ではなく
「その GPT 照会 1 回分は回答済み」を意味する (§7, §8)。`blocked` + `NEED_MORE` も退避対象。

## テスト

```bash
cd tools/gpt_audit
PYTHONPATH=src python -m pytest -q
```

テストフィクスチャは 2 系統:

- `lane_root`: 2026-06-06 時点の**実 Box 状態**を再現
  (真の `answered_not_processed` は quasijudicial の 1 件のみ、
  再投函済みの statusregistry v0.2 / legaldb v0.5.1 は `active`)。
- `design_lane_root`: 設計書 §13 の**理想シナリオ** (answered=4, processed 空)。
  検収テスト用。

### 検収テスト (TEST-1〜6)

`tests/test_acceptance.py` が Mac CC 実装の受け入れ基準を固定する:

| test | 内容 |
|---|---|
| TEST-1 status | answered_not_processed が正しく数えられる |
| TEST-2 dry-run | 退避予定が表示され、NEED_MORE/MODIFY_REQUIRED も対象。何も動かさない |
| TEST-3 execute | REQUEST が processed へ移動、to_gpt 直下は 0、from_gpt RESULT は残る |
| **TEST-4 idempotency** | **再実行で二重移動・二重台帳追記しない (no-op)** |
| TEST-5 missing-result | RESULT のない REQUEST は移動しない |
| TEST-6 bad-label | 先頭行が不正な RESULT は移動しない |
