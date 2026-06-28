# CLAUDE.md — このリポジトリで動く全 Claude Code が従う規約

## 実行権限ルーター（正本: alo_ai_router/）
全AIは ALO-MODEL-ROUTER v0.1 に従う。task_type/cog_level/risk_level/mutation_power/data_zone/author_family で
何を書けるかが機械的に決まる。worker は draft_write 上限。processed化/canonical_write は head/controller のみ。
UNKNOWN は fail closed。詳細: `alo_ai_router/README.md`, `alo_ai_router/FREEZE_NOTE_v0.1.md`

## AIチーム組織とルーティング（必読・正本: docs/alo/AGENT_ORG_AND_ROUTING.md）

構造: **ヘッド**（設計・決定・ルーティング・受入検査）→ **ハンド3種**（ワーカーちゃん=Worker Claude Code /
コーデックス=Codex / ローカルちゃん=QEN・Ollama）→ 全成果物を **GPT Pro が監査**。

**ルーティング規約（ユーザーがハンドを名指ししたら、そのハンドを開いて仕事を渡す）:**
ユーザーの口語指示（「起こして」「仕事ふって」「仕事回して」「投げて」等）はすべて下記の発注アクションにマップする。
**発注書が明示されなければ「今振る発注書」ポインタ `artifacts/periodical/ORCH-CURRENT.txt` の先頭行を使う**
（引数なしで各スクリプトを叩けば自動でそれを投下する）。ユーザーが新しい仕事を口頭で述べたら、
ヘッドが ORCH-*.md 発注書を起こし、ORCH-CURRENT を更新してから投下する。

**汎用オーケストレーション基板 `.claude-orch/`** がプロジェクト共通の発注経路。
雑誌に限らず判例・法令・語彙など他オブジェクトのスレでも同じ仕組みで使える（詳細: `.claude-orch/README.md`）。
- `./tools/trigger_worker.sh <発注書>`              → 旧仕様(legacy・後方互換、雑誌用)
- `./tools/trigger_worker.sh <発注書> <channel>`    → 新仕様(複数チャネル並行、例 hanrei/horei/vocab)
- 発注書ファイル名は `ORCH-*.md` 必須（暴発防止）。ブランチは `ORCH_BRANCH` env で変更可。

- 「ワーカーちゃん起こして／仕事ふって／回して」→ `./tools/trigger_worker.sh [発注書]`（引数省略=ORCH-CURRENT。遠隔発注、watcherが起動）。Mac即時なら `./tools/wake_worker.sh [発注書]`
- 「コーデックスに仕事振って」→ `./tools/wake_codex.sh <発注書>`（CONFIG確認）
- 「ローカルちゃんに仕事振って」→ **処理できるサイズに切り分けてから** `./tools/dispatch_local.sh <チャンク>`（CONFIG確認）
- ヘッドはフェーズ進行に応じて `ORCH-CURRENT.txt` を最新の発注書へ更新し続ける。

原則:
- ハンドへの発注書は入出力・受入基準・read-only/dry-run を明記。成果物は commit→push。
- ファイル名前空間: `P##`=Mac Cloud Code の誌解決専用 / `ORCH-*`,`DD-*`,`WO-*`=ヘッドの設計・発注。
- ヘッドは成果物を受入検査し、必要なら GPT Pro 監査へ。ローカルちゃんへは必ずチャンク分割。
- Cloud Web からの間接起動: `.worker_trigger` を push → Mac 常駐 `tools/worker_watch.sh` が自動起動。
- **【厳守】共有ブランチへ `git push --force`/`-f` は禁止。** 必ず `git pull --rebase` 後に通常 push。
  force-push は他AIのコミットを消す（実際に ORCH-CURRENT 機能が一度消失した）。競合時は rebase で解消する。
- **【厳守】ワーカーCC起動前に `/login` を完了しておく。** 未ログインだと `Not logged in` で即死し、
  watcher が消費push失敗で60秒毎に乱launchする storm が起きる（実害あり、2026-06-27 発生）。
  watcher の storm防止 lock は導入済み（同内容トリガで二度起動しない）が、根本予防は事前ログイン。
- 急ぐ時は手動 `./tools/wake_worker.sh` が最も安全（watcher経由よりリスクが小さい）。

## データ所在
データの所在は AI_READY atlas を最初に見る: `docs/alo/AI_READY_DATA_LOCATOR_LATEST.md`
（機械索引 `AI_READY_DATA_LOCATOR_INDEX_LATEST.tsv` はローカル正本）。atlas は参照専用、
move/delete/DB書込/外部公開は別途 exact owner GO。

## ゲート
canonical 昇格・DB投入・accepted edge 化・外部公開・生payload取込は owner(asai@asai-lo.com) GO 必須。
external_share_allowed=false は不変。
