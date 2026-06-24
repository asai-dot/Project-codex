# ハンド起動ツール 一式

組織構造とルーティング規約: `docs/alo/AGENT_ORG_AND_ROUTING.md`（正本）。要約は `CLAUDE.md`。

## ハンドを開く（ヘッドの操作）
| ハンド | コマンド | 備考 |
|---|---|---|
| ワーカーちゃん (Worker Claude Code) | `./tools/wake_worker.sh [発注書]` | 既定=記事接合。`--bg`起動。**即利用可** |
| コーデックス (Codex) | `CODEX_CMD='...' ./tools/wake_codex.sh <発注書>` | CONFIG: `CODEX_CMD` を一度設定 |
| ローカルちゃん (QEN/Ollama) | `./tools/dispatch_local.sh "指示" [入力]` | CONFIG: `OLLAMA_MODEL`。**小さく切って渡す** |

発注書は `artifacts/periodical/ORCH-*.md`（入出力・受入基準・dry-run/read-only を明記）。

## Cloud Web からの間接起動（常駐watcher）
Mac で一度だけ常駐させる:
```
nohup ./tools/worker_watch.sh > ~/worker_watch.log 2>&1 &
```
以後、Cloud Web(私)が `artifacts/periodical/.worker_trigger` に発注書パスを1行書いて push すると、
watcher が拾って `wake_worker.sh` で自動起動し、トリガを消費する。→ Cloud Web からも「いつでも起こす」。

停止: `kill %1`（または `pkill -f worker_watch.sh`）。

## CONFIG を焼き込む（一度きり）
`~/.zshrc` 等に:
```
export CODEX_CMD='codex exec'        # ← Codex の実起動コマンドに合わせる
export OLLAMA_MODEL='qwen2.5'        # ← QEN の実モデル名に合わせる
```
