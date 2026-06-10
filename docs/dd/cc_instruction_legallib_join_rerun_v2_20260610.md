# INSTRUCTION v2: legallib 接合 全数ドライラン再実行 + 本適用ゲート（Mac CC 宛 / dispatch）

- 宛先: Mac Claude Code セッション
- 発信: web CC（番頭）/ 2026-06-10
- 前回: `cc_instruction_legallib_join_handoff_20260608.md`（初回ドライランは完了済 commit 4a7bea1）
- 今回: **DDJOIN/DDJOINAUDIT 監査反映後（F1ネスト修正・F3構造ガード・P0-1 whitelist強制）で全数を回し直す**
- 正本: repo `docs/handoff_mac_session_legallib_join.md` / 監査記録 `docs/dd/2026061*`

## なぜ再実行が必須か
- 旧 `4a7bea1` の `overwrites_bundle.jsonl` は **F1(ネスト children)修正前**生成 → legallib の深い目次が欠落。
- v0.2 で **F3 構造ガード**（status=simple でも depth>1/parent/階層path/page あれば保護）を追加 → overwrite 判定が変わる（overwrite↓ / route_human_review↑）。
- よって旧 counts/bundle は本適用に使えない。**最新コードで作り直す。**

## STEP 0: 最新ブランチ
```bash
cd Project-codex
git fetch origin && git checkout claude/legallib-integration-design-Jgrtf
git pull   # head 2b4a712 (F1+v0.2+P0-1 入り)
```

## STEP 1: preflight（F2 契約が効く）
```bash
python scripts/validate_resolver.py --resolver <resolver出力> --expect "1839,305,616"
python scripts/inspect_legallib_dir.py --legallib-dir <legallib_dl> --json   # nested:true を確認
```
- **F2**: `auto_accept` で ISBN 空/不正があると **hard error**。出たら resolver 側で「対象なし→`bucket=defer_new`」に振り直してから再実行。

## STEP 2: 全数ドライラン（書き込みゼロ・最新 converter）
```bash
python scripts/legallib_join_dryrun.py \
  --resolver <resolver出力> --legallib-dir <legallib_dl> \
  --toc-dir <app/data/toc> --books <books.json> \
  --policy data/toc_merge_policy_legallib.json \
  --out build/legallib_dryrun_v2
```
L1 self-verify: exit 0 / report.md「不変条件違反 0 ✅」/ `identity_review.jsonl` 件数記録 /
旧比(overwrite1525)より overwrite が減り review が増えていること（F3が効いた証拠）。

## STEP 3: overwrite の diff レビュー（本適用前 P0-3）
```bash
python scripts/render_proposed_diff.py --bundle build/legallib_dryrun_v2/overwrites_bundle.jsonl \
  --out build/legallib_dryrun_v2/overwrite_diff.md
```
- `replace`（旧タイトルが新に無い）は **原則 human_review**。`enrich`（旧⊆新）は承認しやすい。

## STEP 4: 戻す（handoff へコミット）
`handoff/legallib_dryrun_v2_<日付>/` に小さいものだけ:
`report.md` / `actions.jsonl` / `overwrites_bundle.jsonl` / `review_bundle.jsonl` /
`review_queue.jsonl` / `identity_review.jsonl` / `defer_staging.jsonl` / `overwrite_diff.md` /
`pipeline_snapshot_*`。**proposed/・books.json・legallib_dl は戻さない。**

## 本適用は STEP 5（別途・人手承認後のみ）
- web 側で `overwrite_diff.md` を見て **承認 ISBN を `approved_isbns.txt`** に確定 → その後：
```bash
python scripts/legallib_join_apply.py --resolver ... --legallib-dir ... --toc-dir ... --books ... \
  --only-isbns approved_isbns.txt --backup-dir <backup> --log <applylog> --commit
```
- **P0-1**: overwrite を含む `--commit` は `--only-isbns` **必須**（無いと exit 1）。create は承認不要だが、安全のため create も approved に入れる運用推奨。
- **P1**: `--backup-dir` で overwrite 前に旧ファイル退避（rollback 用）。
- ドライラン段階では絶対に `--commit` しない。

## スコープ外
journal(雑誌)接合 / proposed 等の戻し / スクリプト改修PR（番頭領分）。守秘: 設計・件数のみ。
