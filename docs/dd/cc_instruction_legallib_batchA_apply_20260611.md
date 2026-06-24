> ⛔ **WITHDRAWN 2026-06-11**: GPT strategy `LEGALLIBJOIN_STRATEGY_V03_1_FIRST` により Batch A 本適用は実行しない（v0.3.1 一本化）。本書は evidence として保全。停止通知 = Box `cc_instruction_legallib_batchA_apply_20260611_WITHDRAWN.md`。

# INSTRUCTION: legallib 接合 Batch A 本適用 + Hold B/C レビュー材料生成（Mac CC 宛）

- 宛先: Mac Claude Code セッション / 発信: web CC（番頭）/ 2026-06-11
- 前提: GPT v2監査 `DDJOIN_V02_PASS_WITH_NOTES` = **APPLY_PARTIAL (Batch A のみ先行)**
- repo: asai-dot/Project-codex / branch claude/legallib-integration-design-Jgrtf / head c512bc0
- 承認パッケージ: `handoff/legallib_dryrun_v2_20260611/`（branch に commit 済）

## STEP 0: 最新 pull
```bash
cd Project-codex && git fetch origin && git checkout claude/legallib-integration-design-Jgrtf && git pull
```

## STEP 1【本番書き込み】Batch A のみ apply（734件 = create215 + overwrite正delta519）
```bash
python scripts/legallib_join_apply.py \
  --resolver <resolver出力> --legallib-dir <legallib_dl> \
  --toc-dir <app/data/toc> --books <books.json> \
  --policy data/toc_merge_policy_legallib.json \
  --only-isbns handoff/legallib_dryrun_v2_20260611/approved_isbns_batchA.txt \
  --backup-dir <backup_dir> \
  --log <apply_log.jsonl> \
  --commit
```
- **必ず `--only-isbns` と `--backup-dir` を付ける**（P0-1: 無いと overwrite で exit 1 / P1: rollback）。
- 期待: written≈734（create215 + overwrite519）。refused_protected / needs_approval が出たら記録。
- **コミット前ゲート（apply ログ冒頭に記録）**: 入力sha256 / write_candidates.csv hash /
  policy版 / converter版1.1.0 / batch=A / 件数 / backup パス。

## STEP 1-verify
- `app/data/books.json` の hasToc 整合は既存パイプラインで（別途）。
- 不変条件: 保護overwrite違反0 / blocked・review・defer・identity は未書込であることを apply ログで確認。

## STEP 2【書き込みゼロ】Hold B/C の diff レビュー材料を生成（web が判断するため）
Hold = `hold_negative_delta_B.csv`(78件, -1〜-49) + `hold_negative_delta_C.csv`(131件, ≤-50)。
これらの overwrite 候補について、旧/新ノードの diff を出す:
```bash
# v2 dryrun の overwrites_bundle (sample_overwrites.jsonl 等) から Hold の ISBN だけ抽出し、
python scripts/render_proposed_diff.py \
  --bundle <hold_overwrites_bundle.jsonl> \
  --out handoff/legallib_dryrun_v2_20260611/hold_overwrite_diff.md
```
- 入力 bundle は v2 全数 dryrun の `overwrites_bundle.jsonl`。Hold B/C の ISBN(209件) だけに
  絞った `hold_overwrites_bundle.jsonl` を作って渡してOK（旧existing_nodes + 新new_nodes 入り）。
- 4段ジャンプ警告6件の book_id も該当すれば併記。

## STEP 3: 戻す（handoff へ commit）
- `apply_log.jsonl`（STEP1 実績）/ `hold_overwrite_diff.md`（STEP2）を
  `handoff/legallib_dryrun_v2_20260611/` に commit・push。
- backup_dir の中身は戻さない（大きい/ローカル保持）。

→ STEP2 の `hold_overwrite_diff.md` が戻ったら、web 側で enrich/replace を仕分け、
  Hold B/C のうち承認できる分を Batch B/C として追加承認する。

## スコープ外 / 守秘
journal接合・proposed戻し。Batch B/C の commit は web 承認前は禁止。守秘: 設計・件数のみ。
