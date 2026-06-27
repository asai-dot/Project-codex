# .claude-orch/ — 汎用オーケストレーション基板

このディレクトリは「ヘッド(Claude Code)→ ワーカー(Claude Code) の遠隔発注」を
**雑誌オブジェクトに限らず**全プロジェクト共通で使うための基板です。

## 使い方

### 1. ヘッドが発注（任意の場所で）
```
./tools/trigger_worker.sh <発注書パス>
```
発注書は `ORCH-*.md` で始まる相対パスならどこでもOK（旧仕様の `artifacts/periodical/ORCH-*.md` も互換）。

### 2. watcher が拾ってワーカーを起動
- Mac 側で `./tools/install_worker_watch.sh` を一度実行（launchd常駐）。
- watcher は `.claude-orch/triggers/*.trigger` と旧 `artifacts/periodical/.worker_trigger` の**両方**を監視。
- トリガを検知 → `wake_worker.sh` でワーカー起動 → トリガを `.claude-orch/consumed/` へ移動して消費。

### 3. 出力を head が監査
出力は発注書で指定したパス。head セッション側で監査スクリプト（オブジェクトごと）を回す。

## チャネル
- 並行発注は `.claude-orch/triggers/<channel>.trigger`（例: `magazine.trigger`, `hanrei.trigger`）。
- watcher は全 `*.trigger` を1サイクルで全部拾う。
- 同じ channel に重複投下されたら最新が勝つ（古いものは consumed へ）。

## トリガファイル形式
1行目: 発注書パス（`ORCH-*.md` で始まる相対パス）。
2行目以降: 任意のメタ（`branch:` を書くと watcher がそのブランチに切替えてから起動）。
