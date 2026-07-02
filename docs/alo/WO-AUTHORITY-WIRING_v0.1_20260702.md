# WO-AUTHORITY-WIRING v0.1 — 昇格済authorityへのconsumer配線＋durability fold（producer向け）

- wo_id: WO-AUTHORITY-WIRING-V01-20260702
- from: head (CC) / to: periodical/d1law pipeline producer (Mac・L4-COVERAGE-LIFT担当と同一)
- priority: 中（昇格済みだが consumer 未配線＝下流精度はまだ上がっていない）
- owner GO: canonical昇格は済(2026-07-01/02)。本WOは配線＋durability。実行は producer（build_authority_v15.py を所有し L4-COVERAGE-LIFT 進行中のため衝突回避）。

## 背景（重要・フォーク検出済）
- journal v15 は **2つ存在した**: producer版(l4cov・6/27・held8誌のNCID解決) と head版(NORMALIZE341/MERGE7/税理ISSN)。
- head が**決定論統合済** → `casename:artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v15.csv`(bd28b62・924行・両者反映)。
- **ただし reconciled は一回性ファイル**。producer が `build_authority_v15.py` を再実行すると head の NORMALIZE/MERGE/税理 が消える＝durability無し。
- 判例側: `d1law_dl/判例_identity_keys_dedup_canonical_20260702.csv`(211,988行・dedup614+court化け15復元)。元2ファイル不変。

## タスク

### 1. durability fold（build_authority_v15.py に head変更を取り込む）
`l4cov/tools/periodical/build_authority_v15.py` に、head の段1/段2確定分を**追加ルールとして**取り込む:
- NORMALIZE 341（誌名末尾補完・`journal_apply_changelog_20260701.csv` に全 before/after）
- MERGE_TO_EXISTING 7（実在誌統合・article_count合算）
- ISSN_RESOLVED 1（税理→0514-2512）
入力changelog: `casename:artifacts/periodical/journal_apply_changelog_20260701.csv`。
これで v15 が**再生成可能**になり、producerの8 NCID解決 + head の名前正規化が**1スクリプトから出る**。出力が reconciled(924行・bd28b62)と一致することを検証。

### 2. consumer 配線
- **article join** `tools/periodical/run_article_join_dryrun.py`: 参照を v14 → v15 へ。
- **L5 build** `artifacts/periodical/l5_feasibility_build.py`: 判例入力を旧2ファイル(20260605+backfill) → `判例_identity_keys_dedup_canonical_20260702.csv` へ。
- 各worktree複製は正本ブランチ(magazine)を更新→producer同期。

### 3. 回帰・payoff測定（read-only再実行）
- L5 を新判例authorityで再ビルド → **court化け15復元による court_miss 改善数**を測定・report（これが今回の判例修正の payoff）。
- article join を v15 で再実行 → 誌解決の被覆/精度差分（8 NCID + 341正規化の効果）。
- dedup(判例ID重複0/identity_key重複=DISTINCT6) と v15(dup-ISSN18) が下流で破綻しないこと。

## 受入基準
- build_authority_v15.py 再実行の出力 = reconciled v15(924行・8NCID+税理+341正規化)に一致。
- consumer 2本が新authorityを参照・エラーなく完走。
- L5 court_miss が復元15分だけ改善（悪化ゼロ）。想定外の悪化は停止して head へ。

## 安全（厳守）
- 元d1law2ファイル・v14 は不変（rollback保全）。判例dedup/v15 は既存の別名で共存。
- canonical/DB/外部公開の新規昇格は無し（本WOは配線＋durability＝既昇格分の反映のみ）。
- L4-COVERAGE-LIFT 進行中のため、build_authority_v15.py 改変は既存8 NCIDを壊さない（99.28%不変原則を継承）。
- 迷いは NEEDS_DECISION で head へ。
