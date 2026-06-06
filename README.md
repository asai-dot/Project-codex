# Project-codex — Fork 1: legallib 詳細TOC × canonical 接合

legallib の詳細目次（TOC）を本番ブックJSON（canonical, `app/data/toc/isbn_*.json`）へ
**安全に接合**するための実装設計とツール群。検収「既存の人手/NDL TOC を1件も劣化させない／
誤マージ0」を**コードの不変条件**として固定している。

設計の全体像 → [`docs/fork1_legallib_join_design.md`](docs/fork1_legallib_join_design.md)

## 構成

| パス | 役割 |
|---|---|
| `scripts/legallib_to_canonical.py` | ① legallib `{l,p,t,level}` → 本番ノード変換器（`parent_toc_node_id` を level 入れ子から再構築） |
| `scripts/legallib_join_policy.py` | ② `toc_source` 優先順位ポリシー + simple-only 上書きゲート |
| `scripts/legallib_join_dryrun.py` | ③ auto_accept 新規分の**書き込みゼロ**ドライラン diff CLI |
| `scripts/legallib_join_apply.py` | 本適用器（**dry-run 既定**・書き込み直前にゲート再適用で保護対象を物理的に上書き不可） |
| `data/toc_merge_policy_legallib.json` | 拡張優先順位ポリシー（既存に `ndl` / `legallib` を追加） |
| `scripts/validate_resolver.py` | preflight: resolver 出力の契約検証（Mac 着手前に fail-fast） |
| `scripts/inspect_legallib_dir.py` | preflight: `legallib_dl/*.json` のスキーマ点検 |
| `scripts/render_proposed_diff.py` | 下流: `overwrites_bundle.jsonl` → 旧/新 TOC 差分 markdown |
| `scripts/triage_review_queue.py` | 下流: `review_bundle.jsonl` → 保護衝突をタイトル類似度でトリアージ |
| `tests/test_legallib_join.py` / `tests/test_handoff_tools.py` | 検収テスト（72 + 26 = 98 checks・stdlib のみ） |
| `.github/workflows/ci.yml` | CI（compile + 全テスト + ドライラン素振り） |
| `docs/handoff_mac_session_legallib_join.md` | Mac セッションへの発注書（preflight→dryrun→戻す物） |
| `docs/fork1_roadmap_after_join.md` | 接合の前後と「その先」のロードマップ |
| `docs/merge_engine_integration_design.md` | legallib を `merge_toc_updates.py` へ統合する設計（回帰ゼロの段階移行） |

## クイックスタート（実データ不要）

```bash
# 検収テスト
python tests/test_legallib_join.py            # → 72 passed, 0 failed
python tests/test_handoff_tools.py            # → 26 passed, 0 failed

# 同梱フィクスチャでドライラン素振り
python scripts/legallib_join_dryrun.py --demo --out build/legallib_dryrun_demo
cat build/legallib_dryrun_demo/report.md
```

## 実データでの実行

resolver 出力（`auto_accept` / `human_review` / `defer_new`）と
`legallib_dl/*.json` は `~/alo-ai/` 側（本リポジトリ外）にある。

```bash
python scripts/legallib_join_dryrun.py \
  --resolver     ~/alo-ai/work/legallib_dl/resolver_decisions.jsonl \
  --legallib-dir ~/alo-ai/work/legallib_dl \
  --toc-dir      app/data/toc \
  --books        app/data/books.json \
  --out          build/legallib_dryrun
```

`build/legallib_dryrun/report.md` の **「不変条件違反 0 件 ✅」** が、
非simple（人手/NDL/出版社/PDF目次）を1件も上書きしていない機械的証明。
本番 `app/data/toc/` は**一切変更されない**（ドライラン）。

要件・前提・依存は Python 3.9+ 標準ライブラリのみ。
