# ORCH-LOCAL-CLASSIFY-PILOT — Worker 実行レポート（ブロッカー報告）

```yaml
report_for: ORCH-LOCAL-CLASSIFY-PILOT_order_20260624.md
worker: Worker Claude Code (bg job d86610ad)
date: 2026-06-25 (JST)
branch: claude/magazine-object-analysis-seg9cr
authority: read-only 派生のみ。canonical/DB/外部公開なし。
status: BLOCKED — 規格を満たす成果物(article_type_local_pilot_v0.1.csv)を生成できず。garbage は push しない判断。
```

## 結論（先に）
発注どおり `LIMIT=2000 ./tools/run_local_classify.sh` を着手したが、**現環境では監査に通る
パイロット成果物を生成できない**。原因は下記2点。既知garbageの push は害なので行わず、head判断を仰ぐ。

## 観測した事実（証拠）

### 1. 同一発注が多数のジョブで重複実行され、単一GPUがデッドロック
- 実行時、`run_local_classify.sh` / `dispatch_local.sh` 系プロセスが **同時に27個** 走っていた。
- ollama サーバ自体は健全（`/api/tags` が 22ms で 200）。しかし生成キューが27プロセスで奪い合いになり、
  モデルのロード/アンロードが連続発生（`ollama ps` が恒常的に `Stopping...`）。
- 兄弟ジョブの中間出力はいずれも未完成: `1行` / `41行` / `146行`（目標2000行）。**どのジョブも完走できていない。**
- 結果、5行のプローブですら qwen2.5 / qwen3-nt:30b とも 3分超で応答せずタイムアウト。
- **→ 私が更にランナーを足すと悪化するだけ。重複の直列化は head（または owner）でないと解消できない。**

### 2. モデル auto-detect が qwen2.5 を選び、全件「その他」になる
- `run_local_classify.sh` の auto-detect は `ollama list` の先頭 qwen を拾うため **qwen2.5:latest(7.6B)** を選択。
- これで実際に chunk1(400行) を回した結果: 整形済み出力 **101行/400（被覆率≈25%）**、かつ
  **全件「その他」**。例: 明らかな判例研究タイトル
  「…の効力を抵当権者に対抗することができるか（令和５．１１．２７最高二小判）＜最高裁時の判例 民事＞」も「その他」。
- 規格外0 / 正規表現クロスチェック≥85% / 分布サニティ の **全基準で不合格確実**。
- 原因2つ: (a) 400行バッチで出力が途中で切れる（被覆不足）, (b) 7Bモデルが分類せず既定値に倒れる（品質崩壊）。
- 本プロジェクトの正規「ローカルちゃん」は **qwen3:30b**（`localchan-dispatch` skill 記載）。auto-detect の qwen2.5 は誤選択。

## head への提案（再パイロットの修正点）
1. **重複ランナーを停止して1本に直列化。** 最大のボトルネック。27プロセスが互いを餓死させている。
2. **モデルを明示:** `OLLAMA_MODEL=qwen3:30b LIMIT=2000 ./tools/run_local_classify.sh`
   （auto-detect の qwen2.5 は使わない）。
3. **CHUNK を縮小:** `CHUNK=40`〜`50`（400は出力が切れる）。30bモデルなら小バッチで完走見込み。
4. **スクリプト恒久修正(推奨):** `run_local_classify.sh` の auto-detect を「qwen2.5優先」ではなく
   「30b優先 もしくは 明示必須（未指定ならabort）」へ。誤モデルでの空振りパイロットを防ぐ。

## 私が行った/行っていないこと
- 行った: 専用 worktree(`job-d86610ad-classify`, detached@8e244fc) を切って read-only でドライ実行・検証。
  入力 `article_join_dryrun_v0.1.csv`(302,131行) は既存 worktree からコピー（git管理外）。
- 行っていない: **garbage CSV の commit/push はしない。** canonical/DB/外部公開 への書込なし。force-push なし。
  他ジョブのプロセスは kill していない（自分の起こしたランナー17210のみ停止）。

## 受入基準との対応
- `article_type_local_pilot_v0.1.csv`: **未生成**（上記理由）。出力スキーマ `article_id,type,source` は未充足。
- 代わりに本レポートを成果物として返す（read-only 派生、規約準拠）。
