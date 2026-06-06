# alo-gpt-audit

GPT Pro 目付け役 監査レーン (`gpt_ometsuke/`) の **行き・帰り・完了処理**を機械化する単一書き手 CLI。
設計書: `GPT_PRO_AUDIT_LANE_DESIGN_v0.2_20260606.md` (Box file_id 2269085336900) の実装。

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

テストフィクスチャは 2026-06-06 時点の実 Box 状態を再現する
(真の `answered_not_processed` は quasijudicial の 1 件のみ、
再投函済みの statusregistry v0.2 / legaldb v0.5.1 は `active`)。
