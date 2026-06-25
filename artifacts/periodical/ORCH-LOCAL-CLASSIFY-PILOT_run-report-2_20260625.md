# ORCH-LOCAL-CLASSIFY-PILOT — Worker 実行レポート #2（根本原因の追加特定 + ドライバ修正）

```yaml
report_for: ORCH-LOCAL-CLASSIFY-PILOT_order_20260624.md
supersedes_context: ORCH-LOCAL-CLASSIFY-PILOT_run-report_20260625.md（前報の続報）
worker: Worker Claude Code (bg job 617bf5c1)
date: 2026-06-25 (JST)
branch: claude/magazine-object-analysis-seg9cr
authority: read-only 派生のみ。canonical/DB/外部公開なし。force-push なし。
status: PARTIAL — ドライバの致命バグを修正し再実行可能化。ただし GPU 重複実行(storm)継続中の
        ため、規格を満たす pilot CSV の生成は head/owner による storm 解消後に実施が必要。
```

## 結論（先に）
1. **新たに根本原因を特定して恒久修正した**: `run_local_classify.sh` の最終正規化が
   `grep -P`（PCRE）に依存していたが、**macOS の BSD grep / 本機には -P が無い**（GNU grep も
   `ggrep` も未インストール）。このため**モデル出力が正しくても整形段で必ず 0 行**になり、
   全ジョブが空 CSV に終わっていた。前報の「101行/400・全件その他」も、この grep 失敗と
   モデル誤選択が重なった結果と整合する。→ awk 一本の移植版に置換し、本機で動作検証済み。
2. **storm は継続中**: 実行時点で `run_local_classify.sh` 系ドライバが **5本**同時稼働、
   旧スクリプト（`grep -P`版）のため**全て 0 行で終わる運命**だが、qwen2.5 を 100% GPU で
   奪い合っており、新規の重い推論を足すと前報同様デッドロックを悪化させる。
3. 既知 garbage / 空 CSV は push しない方針を維持。head/owner 判断を仰ぐ。

## このコミットで行った修正（`tools/run_local_classify.sh`）
- **(A) 移植性バグ修正（最重要）**: `grep -P '^\S+\t\S+' | awk ...` →
  BSD/GNU 双方で動く `awk -F'\t'` 一本に統一。タブ区切り2列・前後空白除去・空行除去。
  検証: `A001\t判例評釈` 等のサンプルで `article_id,type,qen` を正しく出力、説明文行や
  タブ無し行は除去（規格外0 に寄与）。
- **(B) モデル auto-detect 修正**: 先頭 qwen（=qwen2.5, 7B）を拾う実装が「全件その他」の
  一因。**30b 優先**（`qwen*30b` → `qwen3` → 任意qwen → 既定 `qwen3:30b`）へ変更。
  正規の「ローカルちゃん」は qwen3:30b（localchan-dispatch skill）。
- **(C) CHUNK ガイド追記**: 30b は 400行で出力が切れる実測のためコメントで CHUNK=40〜50 を推奨。

## 現環境の証拠（観測）
- `ollama list`: qwen2.5:latest / qwen3-nt:30b / qwen2.5-coder:32b / qwen3:30b / qwen3-vl:4b。
- `which grep` は claude ラッパ→`command grep`（BSD）。`ggrep` 無し → `-P` 不可を確認。
- `ollama ps`: qwen2.5:latest を 100% GPU でロード中。
- 同一発注のドライバ（`run_local_classify.sh` / `run_local_classify_http.py`）が複数 bg job で
  並走（観測時 5本前後、ピークは前報の27本）。いずれも未完。

## 受入基準を満たす再実行手順（storm 解消後・1本に直列化して実行）
```
# 1) 重複ドライバを停止（head/owner のみ・他ジョブ kill 判断）。
# 2) 単一プロセスで実行（30b・小チャンク）:
OLLAMA_MODEL=qwen3:30b LIMIT=2000 CHUNK=40 ./tools/run_local_classify.sh
# 出力: artifacts/periodical/article_type_local_pilot_v0.1.csv（列: article_id,type,source=qen）
```
- 完了後 head 監査: 規格外0 / 正規表現クロスチェック≥85% / 分布サニティ
  （`tools/periodical/audit_article_type.py`）。

## 私が行った / 行っていないこと
- 行った: 専用 worktree（detached@origin tip 3ed587c）で read-only 検証、ドライバの移植性
  バグ修正と auto-detect 修正、awk 整形の単体検証。本レポートと修正を commit/push。
- 行っていない: **他ジョブのプロセスは kill していない**（cross-job・不可逆のため owner/head 判断）。
  GPU 競合下での重い pilot 推論は**意図的に走らせていない**（storm 悪化回避）。
  garbage/空 CSV の push なし。canonical/DB/外部公開なし。force-push なし。

## head/owner への依頼（ボトルネックは storm の解消）
- 重複ドライバ群の停止（直列化）は head/owner のみが安全に実施可能。停止後、上記コマンドを
  **1本だけ**回せば規格 CSV を生成できる見込み（ドライバ側の技術ブロッカーは本コミットで解消済み）。
- 許可があれば本ワーカーが「重複停止 → 単一実行 → 監査用 CSV 生成 → push」まで実施する。
