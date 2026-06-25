# ORCH-LOCAL-CLASSIFY-PILOT — Worker Claude Code 発注: 記事種別分類 パイロット(2000件)を回す

```yaml
order: ORCH-LOCAL-CLASSIFY-PILOT
from: Cloud Code Web (codex, head)
to: Worker Claude Code（Mac上、Ollama/QEN を実行できる）
authority: read-only 派生生成。canonical/DB/外部公開なし。
spec: artifacts/periodical/ORCH-LOCAL-ARTICLE-TYPE_order_20260624.md（種別定義・監査基準の正本）
```

## やること（そのまま実行）— ★run-report反映の修正版
**前提: storm(重複ジョブ)が停止し1本に直列化されていること。** 並走はGPUを奪い合い逆効果。
1. `git pull origin claude/magazine-object-analysis-seg9cr`（competition安全sync）
2. パイロット実行（**HTTP版ドライバ・qwen3:30b・小チャンク**。ollama CLIは本機でcrashするためHTTP経路）:
   ```
   OLLAMA_MODEL=qwen3:30b LIMIT=2000 CHUNK=15 TIMEOUT=600 python3 tools/run_local_classify_http.py
   ```
   （resume対応＝中断しても続きから。CLI版 run_local_classify.sh は本機では不可）
3. 出力 `artifacts/periodical/article_type_local_pilot_v0.1.csv` を commit して push。**force-push禁止**。

## 注意
- 入力は `artifacts/periodical/article_join_dryrun_v0.1.csv`（article_id, title）。
- ollama が起動していること（`ollama list` が応答する）。応答しなければ `ollama serve` を促す。
- これはパイロット。全量(30万件)は head 監査合格後に LIMIT を外して別途。

## 返却後
head(codex) が `tools/periodical/audit_article_type.py` で受入検査（規格外0 / 正規表現クロスチェック≥85% / 分布サニティ）。
合格 → 全量GO。不合格 → プロンプト調整して再パイロット。
