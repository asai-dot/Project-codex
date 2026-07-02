# ORCH-AUTHORITY-WIRING order 20260702 — 昇格済authorityのconsumer配線＋durability fold（producer実行）

- orch_id: ORCH-AUTHORITY-WIRING-20260702 / channel: wiring
- 親WO: `docs/alo/WO-AUTHORITY-WIRING_v0.1_20260702.md`（branch: claude/t10-d1-full-sweep, commit 20d8ec3）
- 実行者: **producer（build_authority_v15.py 所有・L4-COVERAGE-LIFT 担当）**。head の段1/段2は受入合格済・canonical昇格済。本発注は配線＋durability（新規昇格なし）。
- 種別: 既昇格分の反映。新規 canonical/DB/外部公開 なし。判例元2ファイル・v14 は不変（rollback保全）。

## 前提（フォーク統合済）
- journal v15 は head が producer版(l4cov 6/27・held8誌NCID)と head版(NORMALIZE341/MERGE7/税理ISSN)を**決定論統合済** → `casename:artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v15.csv`(bd28b62・924行)。
- reconciled は**一回性ファイル**＝build_authority_v15.py 再実行で head 変更が消える。本発注で durability を確保。

## タスク

### 1. durability fold（最優先）
`l4cov/tools/periodical/build_authority_v15.py` に head の確定分を追加ルールとして取り込み、**再実行で reconciled(924行) と一致する**ようにする:
- NORMALIZE 341 / MERGE_TO_EXISTING 7 / 税理ISSN 0514-2512（入力 changelog: `casename:artifacts/periodical/journal_apply_changelog_20260701.csv`）
- 既存の producer 8 NCID解決・99.28%不変原則は壊さない。
- **L4-COVERAGE-LIFT が未コミット変更を持つ場合は触らず停止して head へ**（衝突回避）。

### 2. consumer 配線
- `tools/periodical/run_article_join_dryrun.py`: v14 → v15 参照へ。
- `artifacts/periodical/l5_feasibility_build.py`: 判例入力を `20260605.csv`+`backfill6yr_20260617.csv` → `/Users/yuta/alo-ai/work/d1law_dl/_parsed_hanrei/判例_identity_keys_dedup_canonical_20260702.csv` へ。
- 正本ブランチ(magazine)を更新。

### 3. 回帰・payoff測定（read-only再実行）
- L5 を新判例authorityで再ビルド → **court化け15復元による court_miss 改善数**を測定・report（判例修正の payoff）。
- article join を v15 で再実行 → 8 NCID+341正規化の被覆/精度差分。

## 受入基準
- build_authority_v15.py 再実行出力 = reconciled v15(924行・8NCID+税理+341正規化)に一致。
- consumer 2本が新authority参照でエラーなく完走。
- L5 court_miss は改善のみ（悪化ゼロ）。想定外の悪化/差分は停止して head へ。

## 出力（成果物・commit/push）
- 更新済 `build_authority_v15.py` ＋ 生成 v15（reconciled一致の検証ログ）
- 配線済 consumer 2本
- `authority_wiring_regression_report_20260702.md`（court_miss改善数・article join差分・破綻なし確認）

## 安全（厳守）
- 判例元2ファイル・v14 不変。新規昇格なし。read-only再実行の測定のみ。
- L4-COVERAGE-LIFT 進行中との衝突回避（未コミットあれば停止）。
- 継続性: RESULT に read_log_commit/read_digest_id/read_standing_ids を記載。迷いは NEEDS_DECISION で head へ。
