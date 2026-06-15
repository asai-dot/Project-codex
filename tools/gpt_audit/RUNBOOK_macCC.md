# RUNBOOK — Mac Claude Code 向け: 実 Box で監査ループを回す

対象: 単一書き手の Mac (Box Drive 同期済み)。`alo-gpt-audit` を実 `gpt_ometsuke/`
レーンに対して実行し、GPT Pro 監査の帰り便（退避・台帳・action-queue）を回す。

> 大原則:
> - **承認不要**なのは「監査の帰り便」だけ（RESULT 保存 / processed 退避 / 台帳 /
>   route カード）。**accepted/canonical 化・index backfill・本番 DB・SF 書戻し・
>   外部送信は実行しない**（owner-gated）。
> - **単一書き手**で実行する（複数マシンから同時に `--apply` しない）。
> - 必ず **dry-run → 目視 → `--apply`** の順。

---

## 0. 前提を取得（最新コードを pull）

```bash
cd ~/path/to/Project-codex
git fetch origin claude/gpt-pro-audit-loop-g0FyC
git checkout claude/gpt-pro-audit-loop-g0FyC
git pull origin claude/gpt-pro-audit-loop-g0FyC
```

（main へマージ済みなら `git checkout main && git pull` でよい）

---

## 1. Box 同期パスを特定して root に設定

`gpt_ometsuke` の Box 上の位置（pathCollection 実測）:
`すべてのファイル / 浅井 / claude / handoffs / gpt_ometsuke`

Box Drive の標準マウントなら:

```bash
# まず候補を探す（環境で名称が違うことがある）
ls -d ~/Library/CloudStorage/Box-Box 2>/dev/null || ls -d ~/Box 2>/dev/null

export ALO_GPT_AUDIT_ROOT="$HOME/Library/CloudStorage/Box-Box/浅井/claude/handoffs/gpt_ometsuke"

# 確認（to_gpt / from_gpt / _AUDIT_LEDGER.jsonl が見えるはず）
ls "$ALO_GPT_AUDIT_ROOT"
```

見つからない場合:

```bash
find ~/Library/CloudStorage ~/Box -maxdepth 6 -type d -name gpt_ometsuke 2>/dev/null
```

> 実行前に Box Drive が**同期完了**していること（クラウドのみのプレースホルダだと
> 読めない／空に見える）。`from_gpt/` の RESULT が全部ローカルに落ちているか確認。

---

## 2. 現況確認（読み取りのみ・安全）

```bash
ALO=tools/gpt_audit/alo_gpt_audit.py

python3 $ALO status -v        # answered_not_processed / missing_result / bad_label
python3 $ALO health           # レーン全体の健全性
python3 $ALO lint             # 未回答 REQUEST の preflight（任意）
```

期待（2026-06-07 観測時点）:
- active = 2（lawtime v0.2 / toclegalref v0.2、いずれも `missing_result` = GPT 回答待ち）
- 旧式 `*_REQUEST.processed.md` = 2（後述 §4 で relocate）

---

## 3. 帰り便を回す（dry-run → apply）

```bash
# 3-1) まず dry-run（何も動かさない。退避予定とカード予定を表示）
python3 $ALO close-all

# 3-2) 表示内容を目視確認したら実行（承認不要）
python3 $ALO close-all --apply

# 3-3) 冪等性の確認：もう一度 --apply しても「退避対象 0 件」になる
python3 $ALO close-all --apply
```

`--apply` がやること（すべて承認不要）:
1. RESULT 済み REQUEST を `to_gpt/processed/` へ退避（三点照合・bad label/未回答は触らない）
2. `_AUDIT_LEDGER.jsonl` に追記
3. `result_label` → `next_action_type` で `patch_queue/` `material_queue/`
   `approval_queue/` `rejected_queue/` にカード作成

---

## 4. 旧式その場退避ファイルの relocate（one-off, 承認不要）

旧運用で `to_gpt/` 直下に残った `*_REQUEST.processed.md` を `processed/` へ移す:

```bash
cd "$ALO_GPT_AUDIT_ROOT/to_gpt"
mkdir -p processed
for f in *_REQUEST.processed.md; do
  [ -e "$f" ] || continue
  # ".processed.md" を ".md" に戻して processed/ へ
  mv -n "$f" "processed/${f%.processed.md}.md"
done
cd -
python3 $ALO status -v   # 旧式 = 0 になるか確認
```

> 対応 RESULT が `from_gpt/` にあることは §2 health で確認済み。`mv -n` で上書き回避。

---

## 5. Claude の次手（action-queue を読む）

```bash
python3 $ALO action-queue     # reflected:false = まだ反映していない監査結果
python3 $ALO owner-digest     # Owner へ返す 5 行サマリ
```

`action-queue` の各項目に対し Claude が実施:
- `next_action=patch` → GPT 指摘を反映し**新 version**で再 REQUEST（元 REQUEST は復活させない）
- `next_action=required_materials` → 不足資料を Box 復旧 → 再投函
- `next_action=ratify` → blocking を反映後、**Owner ratify を依頼**（昇格は要承認）
- `next_action=reject` → 別案を起票

反映が終わった項目は「反映済み」にする（台帳に append、承認不要）:

```bash
python3 $ALO reflect <request_id> --apply
python3 $ALO action-queue     # 反映済みは消える。reflected:true まで監査は閉じない
```

---

## 6. やってはいけないこと（owner-gated）

以下はこのツールでは実行しない。Owner ratify / 所定 T2 ゲートを経ること:

- DD を accepted / canonical に昇格
- design_decisions / Generated Index への backfill
- 本番 DB 投入・DDL 適用
- Salesforce 書戻し・外部送信・公開

要否に迷ったら: `python3 $ALO gate-check <operation>`（owner-gated は exit 2）。

---

## 7. 典型セッション（Owner「監査を回して」への一括応答）

```bash
export ALO_GPT_AUDIT_ROOT="$HOME/Library/CloudStorage/Box-Box/浅井/claude/handoffs/gpt_ometsuke"
ALO=tools/gpt_audit/alo_gpt_audit.py

python3 $ALO status -v          # 1) 溜まり確認
python3 $ALO close-all          # 2) dry-run
python3 $ALO close-all --apply  # 3) 退避＋台帳＋振分け（承認不要）
python3 $ALO action-queue       # 4) Claude の次手
python3 $ALO owner-digest       # 5) Owner へ 5 行で返す
```

これで「返答で終わらず、Claude 再思考まで回る」1 周が完了する。
詳細は `tools/gpt_audit/README.md`。
