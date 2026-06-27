# ORCH-STORM-STOP — periodical classify storm の安全停止 ＆ 単一実行（owner が Mac で実行する手順書）

```yaml
order: ORCH-STORM-STOP
from: head (remote Claude, Cloud)
to: owner（Mac で手実行。Cloud からはプロセス kill 不可のため）
authority: 重複ドライバ停止は cross-job・不可逆ゆえ owner のみ。本書は手順提示。
gate: read-only診断 → owner判断kill → 単一classify実行(read-only派生生成)。DB/canonical/外部公開なし。
goal: classify storm(重複ドライバ+GPU競合)を解消し、article_type_local CSV を1本だけ生成する。
unblocks: WORKER_20260625_CASELINK_L5_DRYRUN_002（magazine 判例評釈subset → CASELINK engine）
durable_fix: ブランチ claude/t8-runner-flock-fix（flock で重複launch を恒久防止）を後で merge 推奨。
```

## 原則（安全第一）
- **盲目的 kill 禁止**。まず診断して PID を特定 → **owner が「残す/止める」を判断** → graceful(`TERM`) → 確認 → 止まらない時のみ `KILL`。
- **止めない**: `ollama serve`（デーモン本体）/ Box 同期(`.Box_*`)/ 他フォークの claude エージェントで storm と無関係なもの / `worker_watch`（常駐watcher。必要なら最後に）。
- **止める対象**: 重複起動した **classify ドライバ**（`run_local_classify.sh` / `dispatch_local.sh` の多重ループ）と、それにぶら下がる `ollama run`（ドライバ停止で連鎖終了）。
- データ削除なし・force-push なし・canonical/DB 変更なし。停止は再実行で復帰可能。

## STEP 1 — 診断（read-only。まず現状を見る）
```
echo "===== classify/dispatch ドライバ ====="
ps aux | grep -E "run_local_classify|dispatch_local|run_local|classify" | grep -v grep
echo "===== ollama (run と serve を区別) ====="
ps aux | grep -E "ollama" | grep -v grep
echo "===== 走っている claude エージェント(止めてはいけない他job確認) ====="
claude agents 2>/dev/null
echo "===== worker_watch 常駐 ====="
ps aux | grep -E "worker_watch" | grep -v grep
echo "===== GPU/負荷(任意) ====="
ps aux | sort -nrk3 | head -8
```
→ 出力を head(私)に貼れば、**どれが重複/犯人で、どれを残すべきか**を一緒に判定します（迷ったら貼ってから止める）。

## STEP 2 — owner 判断 → graceful 停止（重複ドライバのみ）
判定後、**止めると決めた PID だけ** TERM：
```
# 例: 重複している run_local_classify / dispatch_local の PID を1つずつ
kill -TERM <PID>            # ← STEP1 で特定した重複ドライバの PID
sleep 3
ps aux | grep -E "run_local_classify|dispatch_local" | grep -v grep   # 残存確認
```
- `ollama serve`（デーモン）は**残す**。重複していた `ollama run` はドライバ停止で消える。
- TERM で残るゾンビのみ最後の手段 `kill -KILL <PID>`。
- **claude agents に出た他job（例: HIGHHOLD-INGEST のワーカー）は storm と無関係なら触らない。**

## STEP 3 — storm 解消の確認
```
ps aux | grep -E "run_local_classify|dispatch_local|classify" | grep -v grep   # ≤1 本(or 0)
ps aux | grep "ollama run" | grep -v grep                                       # 競合 run が消えている
```
classify ドライバが 0〜1、`ollama run` の多重が解消＝storm 解消。

## STEP 4 — 単一実行で分類 CSV を生成（直列・1本だけ）
```
cd ~/Project-codex
git checkout claude/magazine-object-analysis-seg9cr && git pull origin claude/magazine-object-analysis-seg9cr
OLLAMA_MODEL=qwen3:30b LIMIT=2000 CHUNK=40 ./tools/run_local_classify.sh
```
- まず **LIMIT=2000 の pilot** で規格 CSV が出るか確認（run-report 準拠）。OK なら全量は `LIMIT` を外す/増やして再実行。
- 出力: `artifacts/periodical/article_type_local_pilot_v0.1.csv`（列 `article_id,type,source=qen`）。

## STEP 5 — head 監査（規格チェック）
```
wc -l artifacts/periodical/article_type_local_pilot_v0.1.csv
python3 tools/periodical/audit_article_type.py 2>/dev/null || echo "(audit script を head が用意)"
```
合格基準（magazine 規約）: 規格外ラベル=0 / 正規表現クロスチェック≥85% / 分布サニティ（判例評釈・論説が一定割合）。

## 完了後 → CASELINK L5 を1回回す（storm 解消の果実）
`article_type_local_*.csv`（type=判例評釈）が出たら、上流→L5 を一本で：
```
cd ~/Project-codex && git fetch origin claude/precedent-object-progress-gwb47u
git worktree add ../pc-caselink claude/precedent-object-progress-gwb47u
cd ../pc-caselink
claude --bg --permission-mode bypassPermissions "発注書 docs/WORKER_TASK_PACKET_caselink_corpus_dryrun_20260625.md を実行。入力=magazine の article_type_local_*.csv(判例評釈) → CASELINK engine で dry-run。read-only厳守、stance列DDL/alo_edges実write/canonical昇格は禁止。結果を _claude_dispatch/from_worker/20260625_caselink_L5_dryrun_RESULT.md に commit&push。"
```

## ロールバック / 失敗時
- 止めすぎた → 各ドライバは再実行で復帰（`./tools/run_local_classify.sh` 等）。データ損失なし。
- classify が再 storm 化 → `claude/t8-runner-flock-fix`（flock 排他）を merge してから再実行。
- 迷ったら STEP1 の出力を head に貼る。**不可逆判断は owner、precise 化は head。**
