# CLAUDE.md — このリポジトリで動く全 Claude Code が従う規約

## AIチーム組織とルーティング（必読・正本: docs/alo/AGENT_ORG_AND_ROUTING.md）

構造: **ヘッド**（設計・決定・ルーティング・受入検査）→ **ハンド3種**（ワーカーちゃん=Worker Claude Code /
コーデックス=Codex / ローカルちゃん=QEN・Ollama）→ 全成果物を **GPT Pro が監査**。

**ルーティング規約（ユーザーがハンドを名指ししたら、そのハンドを開いて仕事を渡す）:**
ユーザーの口語指示（「起こして」「仕事ふって」「仕事回して」「投げて」等）はすべて下記の発注アクションにマップする。
**発注書が明示されなければ「今振る発注書」ポインタ `artifacts/periodical/ORCH-CURRENT.txt` の先頭行を使う**
（引数なしで各スクリプトを叩けば自動でそれを投下する）。ユーザーが新しい仕事を口頭で述べたら、
ヘッドが ORCH-*.md 発注書を起こし、ORCH-CURRENT を更新してから投下する。

- 「ワーカーちゃん起こして／仕事ふって／回して」→ `./tools/trigger_worker.sh [発注書]`（引数省略=ORCH-CURRENT。遠隔発注、watcherが起動）。Mac即時なら `./tools/wake_worker.sh [発注書]`
- 「コーデックスに仕事振って」→ `./tools/wake_codex.sh <発注書>`（CONFIG確認）
- 「ローカルちゃんに仕事振って」→ **処理できるサイズに切り分けてから** `./tools/dispatch_local.sh <チャンク>`（CONFIG確認）
- ヘッドはフェーズ進行に応じて `ORCH-CURRENT.txt` を最新の発注書へ更新し続ける。

原則:
- ハンドへの発注書は入出力・受入基準・read-only/dry-run を明記。成果物は commit→push。
- ファイル名前空間: `P##`=Mac Cloud Code の誌解決専用 / `ORCH-*`,`DD-*`,`WO-*`=ヘッドの設計・発注。
- ヘッドは成果物を受入検査し、必要なら GPT Pro 監査へ。ローカルちゃんへは必ずチャンク分割。
- Cloud Web からの間接起動: `.worker_trigger` を push → Mac 常駐 `tools/worker_watch.sh` が自動起動。

## データ所在
データの所在は AI_READY atlas を最初に見る: `docs/alo/AI_READY_DATA_LOCATOR_LATEST.md`
（機械索引 `AI_READY_DATA_LOCATOR_INDEX_LATEST.tsv` はローカル正本）。atlas は参照専用、
move/delete/DB書込/外部公開は別途 exact owner GO。

## ゲート
canonical 昇格・DB投入・accepted edge 化・外部公開・生payload取込は owner(asai@asai-lo.com) GO 必須。
external_share_allowed=false は不変。
