# legallib 接合 本適用 Batch A 承認パッケージ (DDJOIN_V02_PASS_WITH_NOTES 準拠)

- 由来: Box `20260611_legallibjoin_v0.2_AUDIT/write_candidates.csv` (943件) を delta で3分割
- GPT v2 監査: `DDJOIN_V02_PASS_WITH_NOTES` → **APPLY_PARTIAL (Batch A のみ先行)**

## 分割結果 (943 = 734 + 78 + 131)
| | 件数 | 内訳 | 扱い |
|---|--:|---|---|
| **Batch A (承認)** | **734** | create 215 + overwrite_simple(node_delta≥0) 519 | 本適用可 |
| Hold B | 78 | overwrite_simple node_delta −1〜−49 | spot review 後 |
| Hold C | 131 | overwrite_simple node_delta ≤−50 | 個別 review 必須 |

`approved_isbns_batchA.txt` に負delta overwrite は **0件** (検証済)。

## Mac での本適用コマンド (Batch A のみ)
```bash
git pull   # 最新ブランチ (apply の P0-1 whitelist 強制入り)
python scripts/legallib_join_apply.py \
  --resolver <resolver出力> --legallib-dir <legallib_dl> \
  --toc-dir <app/data/toc> --books <books.json> \
  --policy data/toc_merge_policy_legallib.json \
  --only-isbns handoff/legallib_dryrun_v2_20260611/approved_isbns_batchA.txt \
  --backup-dir <backup_dir> \
  --log <apply_log.jsonl> \
  --commit
```

## コミット前ゲート (GPT 必須・apply ログに記録すること)
- 入力 sha256 (resolver / legallib_dl) ・ dryrun report hash ・ write_candidates.csv hash
- policy version (toc_merge_policy_legallib) ・ converter version (1.1.0)
- batch=A / 件数=734 / rollback=backup-dir
- 維持すべき不変条件: 保護overwrite違反=0 / blocked・review・defer・identity は書かない

## 4段ジャンプ警告 (6件) と warning多行
- warning は level clamp のみ (tree健全) だが、4段ジャンプ6件 + warning多い上位は
  Batch A に混じる場合は個別確認。混じらなければ Hold 群と一緒に後送り。

## 残 (owner/別途)
- Hold B(78) / Hold C(131) は overwrite_diff (render_proposed_diff) で精査後に判断。
- F3(A) 上流 toc_status ラベル是正は別タスク。
