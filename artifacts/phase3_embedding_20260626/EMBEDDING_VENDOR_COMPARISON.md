# Phase 3 — embedding ベンダー比較表

```yaml
doc_id: PHASE3-EMBEDDING-VENDOR-COMPARISON-20260626
status: comparison（owner 選定材料。実行は別途 ratify）
created_at: 2026-06-26 JST
author: Claude
gate: 本ファイルは情報整理。価格・仕様は本ファイル末尾の参照時点。実発注前に最新を再確認すること。
target: biblio.toc_nodes.embedding（vector(1536), 552,544行 + 後続 lionbolt 236k/legallib 想定）
input_text: path_text（avg 48.9字 = 約35トークン/ノード）
related:
  - artifacts/toc_accuracy_20260625/TOC_ACCURACY_DIAGNOSIS_20260625.md
  - artifacts/corpus_roadmap_20260626/NEXT_STEPS_20260626.md
```

## 0. 前提（DB側の制約）

- 列の型は **`vector(1536)`**。**1536次元を出すモデル**でないと列スキーマを変えるマイグレーションが要る
- 入力テキスト = `path_text`（既存）。avg 49字 ≈ **35トークン/ノード**（日本語含み）
- 想定対象ノード数（全ソース揃った時）:
  - 弁コム 552,544 + lionbolt 236,674 + legallib 約500,000* = **約 1,300,000 ノード**
  - = 約 **45M 入力トークン**（×35）
- *legallib 投入後の実数で更新。スコープに「全部」「lionboltまで」「弁コムだけ」の3案あり

## 1. 候補ベンダー比較

### 1.1 OpenAI（推奨・既存スキーマ整合）

| モデル | 次元 | 価格 (USD / 1M tok) | 多言語 | 備考 |
|---|---:|---:|---|---|
| `text-embedding-3-small` | **1536** | $0.020 | ◎ | **既存列と同次元・最安**。本命 |
| `text-embedding-3-large` | 3072 (1536に縮小可) | $0.130 | ◎+ | 1536に切り詰めて使えば列スキーマ不変。精度↑（評価で +20%級）|
| `text-embedding-ada-002` | 1536 | $0.100 | ○ | 旧モデル。3-small に劣る。非推奨 |

3-large は出力次元を縮約（`dimensions=1536`）で 1536 にできる。これも列変更不要。

**コスト試算**（全1.3M ノード = 45M token）:
- 3-small: 45 × $0.020 = **$0.90**
- 3-large(1536縮約): 45 × $0.130 = **$5.85**

### 1.2 Voyage AI（精度評価で高評価・列変更要）

| モデル | 次元 | 価格 (USD / 1M tok) | 多言語 | 備考 |
|---|---:|---:|---|---|
| `voyage-3` | 1024 | $0.060 | ◎ | 日本語含む精度はOpenAI 3-large に比肩 |
| `voyage-3-large` | 1024 / 2048 | $0.180 | ◎+ | 多くの retrieval ベンチで上位 |

**列を `vector(1024)` に変えるマイグレーションが必要**（既存552k分の embedding は今は全NULL なので破棄影響なし）。

コスト: 45M × $0.060 = **$2.70**（voyage-3）

### 1.3 Cohere

| モデル | 次元 | 価格 (USD / 1M tok) | 多言語 | 備考 |
|---|---:|---:|---|---|
| `embed-multilingual-v3.0` | 1024 | $0.10 | ◎ | 多言語特化。日本語OK |
| `embed-multilingual-light-v3.0` | 384 | $0.10 | ○ | 軽量・低次元 |

列スキーマ変更要。コスト: 45M × $0.10 = $4.50

### 1.4 自前 / オンプレ（参考のみ）

- `intfloat/multilingual-e5-large` (1024次元)
- `pkshatech/GLuCoSE-base-ja`
- GPU/CPU 推論コスト・運用面でこのフェーズには不向き。将来オプション

## 2. 判定マトリクス

| 軸 | OpenAI 3-small | OpenAI 3-large(1536) | Voyage-3 | Cohere multi-v3 |
|---|---|---|---|---|
| 列スキーマ変更 | **不要** | 不要 | **必要(1024)** | 必要(1024) |
| 初回 backfill コスト（1.3M ノード） | **$0.90** | $5.85 | $2.70 | $4.50 |
| 日本語法律ドメイン精度 | 良 | **最良** | 良〜最良 | 良 |
| API SLA・運用実績 | **最大** | 最大 | 良 | 良 |
| ベンダーロックイン | OpenAI 依存 | OpenAI 依存 | Voyage 依存 | Cohere 依存 |
| 再生成リスク | 低（安価） | 中 | 中 | 中 |

## 3. 推奨

**第1案: OpenAI `text-embedding-3-small`**（コスト・スキーマ整合・運用安定の総合勝ち）
- 列既存の `vector(1536)` をそのまま使える → Phase 3 のマイグレーションは index 追加のみ
- 全コーパス backfill が **$1未満**でできる → 試行錯誤しても安い
- 精度評価で不足なら 3-large(1536縮約) に**列変更なしで**乗り換え可能（同じ次元）

**第2案: OpenAI `text-embedding-3-large` 出力次元1536**（精度勝負したい場合）
- $5.85 で 3-small より明確に精度↑
- 列スキーマは同じ
- 法律ドメインで「微妙な節の意味差」を拾いたいときに

**回避**: Voyage / Cohere は精度メリットが「列変更コスト + ロックイン」を上回らない限り見送り。3-small で評価して足りなければ 3-large へ。

## 4. 実装メモ（owner GO 後）

1. `OPENAI_API_KEY` を Mac 側ローダ環境に設置（DB側ではなくバッチ側）
2. backfill ツール `tools/toc_embedding_backfill/`:
   - 入力: `path_text` of `toc_nodes WHERE embedding IS NULL`
   - バッチサイズ: 100ノード/req（OpenAIの 8191 token入力上限内に収まる）
   - レート制限: tier 次第。3-small は 5000 RPM / 5M TPM が一般的
   - 冪等: 既に embedding 入っている行は skip
   - 進捗: バッチごとに `count(*) WHERE embedding IS NOT NULL` を出す
3. backfill 完了後に HNSW 索引:
   ```sql
   CREATE INDEX CONCURRENTLY toc_nodes_embedding_hnsw
     ON biblio.toc_nodes USING hnsw (embedding vector_cosine_ops);
   ```
4. 検索クエリ例:
   ```sql
   SELECT book_id, path_text, 1 - (embedding <=> :q_emb) AS sim
   FROM biblio.toc_nodes ORDER BY embedding <=> :q_emb LIMIT 20;
   ```

## 5. 全段ratify ゲート（再掲）

- A. ベンダー/モデル選定（本ファイルで第1案推奨）
- B. APIキー owner 用意
- C. Phase 1 (legallib投入) / Phase 2 (シルバー射影) PASS 後でないと **対象ノード集合が確定しない**
- D. Phase 3 自体の DDDESIGN 監査（コスト・スコープ・冪等性）

---

## 6. 参照（変動するので運用前に再確認）

- OpenAI: https://openai.com/api/pricing/ (Embeddings 段)
- Voyage: https://docs.voyageai.com/docs/pricing
- Cohere: https://cohere.com/pricing

価格は本ファイル作成時点の確認値。発注前に再取得すること。
