# ORCH-LOCAL-CLASSIFY-PILOT — Worker 実行レポート (2026-06-25)

発注書: `artifacts/periodical/ORCH-LOCAL-CLASSIFY-PILOT_order_20260624.md`
仕様正本: `artifacts/periodical/ORCH-LOCAL-ARTICLE-TYPE_order_20260624.md`
権限: read-only 派生生成（canonical/DB/外部公開なし）。

## 結論（先に）
発注どおりの `LIMIT=2000 ./tools/run_local_classify.sh` は **このMacでは実行不能**。原因は2つ:

1. **ollama CLI が native crash**（`ollama run` / `ollama list` とも）。
   `libmlx … mlx_random_key` → `mlx::core::metal::Device` 初期化で `objc_exception_throw`。
   発注書の経路 `run_local_classify.sh → dispatch_local.sh → ollama run` は全チャンクで落ち、
   出力が空になる。
2. **マシン過負荷**。本オーダーが remote-trigger 経由で **重複起動**（`classify-pilot-*`
   worktree が約15本、すべて同一オーダー）。単一GPUのollama daemonを奪い合い、
   load average が 58→92→99 と上昇。1回の推論すら完了しないことがある。

ollama **daemon の HTTP API (`/api/generate`) は正常**（推論可能）。
そこで CLI 経路を HTTP 経路に置換するドライバを実装し、発注仕様（同じ10種別・LIMIT・
出力ファイル名/スキーマ・`source=qen`）を保ったまま実行した。

## 実装した回避策（成果物）
- `tools/run_local_classify_http.py`
  - `run_local_classify.sh` と同一の10種別・LIMIT・出力（`artifacts/periodical/article_type_local_pilot_v0.1.csv`、
    スキーマ `article_id,type,source`、`source=qen`）。
  - id echo の代わりに **行番号で整列**（idが長くモデルが復元失敗するため、番号→idを内部写像）。
  - **チェックポイント** `artifacts/periodical/.classify_pilot_ckpt.jsonl` に逐次追記 → 中断/再実行で resume。
  - タイムアウト/失敗行は **その他に偽装せず未分類のまま残し**、resume で再挑戦（監査の分布健全性を汚さない）。
  - モデル: `qwen2.5`（発注書ドライバの fallback と同じ。`ollama list` が落ちる本機では自動検出が
    この既定値に落ちるため、挙動を一致させた）。`qwen3-nt:30b` は thinking 型で遅く、本パイロットには不適。

## 検証
- クリーンな先頭40件サンプルで HTTP 経路が **規格内ラベルのみ** を出力することを確認（整列 20/20×2 chunk）。
  例: `issn:0448-0791#1602#p115 抵当不動産…令和5.11.27最高二小判 → 判例評釈`。
- ただし qwen2.5(7B) は バッチ時に `その他` を多めに付ける傾向（40件中25件）。
  head 監査の「分布サニティ」次第では、より大きいQENモデル/プロンプト調整での再パイロットを推奨。

## 本実行の状態
`LIMIT=2000 CHUNK=15 TIMEOUT=600 python3 tools/run_local_classify_http.py` をバックグラウンド実行中。
**load≈99 の過負荷下では1チャンクの完了に分単位**かかり、全2000件の完了は現実的時間内に保証できない。
（resume 対応のため、負荷が下がれば続きから自動進行する。）

## head への推奨（重要）
1. **重複ジョブの集約**: `classify-pilot-*` の重複 worktree/ジョブを1本に絞る。並列はGPUを奪い合い逆効果。
2. 1本に絞った状態で `tools/run_local_classify_http.py` を回せば、2000件は短時間で完了見込み。
3. ollama CLI の crash は環境側の不具合（MLX/Metal）。CLI 依存の `dispatch_local.sh` / `run_local_classify.sh`
   は本機では HTTP 版に置き換えて運用するのが安全。
4. 完了後、`tools/periodical/audit_article_type.py` で受入検査（規格外0 / 正規表現クロスチェック≥85% / 分布サニティ）。
