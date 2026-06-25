# TOC_ACCURACY_DIAGNOSIS_20260625 — 文献TOC検索精度の診断と効果順レバー

```yaml
doc_id: TOC-ACCURACY-DIAGNOSIS-20260625
status: diagnosis + lever ranking（レバー#2はPR化、#1は ratify待ち、#3はHOLD）
created_at: 2026-06-25 JST
author: Claude（浅井さん指示「TOC精度に効く向上策を効く順に」）
gate: 診断は SET なし read-only SELECT のみ（DB mutation 0 / mint 0 / DDL 0）。
      適用は別途 ratify。
supabase_project: nixfjmwxmgugiiuqfuym
target: biblio.toc_nodes（552,544ノード / 3,802書 = 現状 bencom のみ）
```

## 1. 診断（read-only 実測 2026-06-25）

`biblio.toc_nodes` の充足率と索引現況を実測:

| 指標 | 実測 | 判定 |
|---|---|---|
| 総ノード / distinct書 | 552,544 / 3,802 | — |
| **embedding** | **0 / 552,544（100% NULL）** | ❌ 意味検索が完全に死んでいる |
| print_page | 552,544（100%） | ✅ |
| path_text | 552,544（100%）, avg 48.9字 | ✅ 階層パス文脈が完備・高品質 |
| parent_toc_node_id | 509,176（92.2%） | ✅ 欠落8%は全て depth=1 ルート（depth>1の孤児=0） |
| title 空 | 0 | ✅ |
| depth 分布 | {1:43,368 / 2:144,094 / 3:216,736 / 4:148,346} | ✅ 階層整合 |

索引現況（`biblio.toc_nodes`）:
- `toc_nodes_title_trgm`: GIN trgm on **`title`（葉ノードのベタ見出しのみ）**
- `embedding` にベクトル索引なし（embedding が空なので当然）
- **`path_text` に索引なし** ← トピック語が住む列が無索引

拡張: `vector 0.8.0`（HNSW可）/ `pg_trgm 1.6`。日本語形態素FTS（pg_bigm/pgroonga）は未導入。

**所見**: 構造（ページ・パス・階層・見出し）は実質欠陥ゼロ。精度の穴は2点に集約される
—— (A) embedding が一切生成されていない、(B) 索引が葉 title のみでパス文脈を拾えない。

## 2. 効果順レバー

| 順 | レバー | 効果 | 外部依存 | 状態 |
|---|---|---|---|---|
| **1** | **embedding backfill（path_textを1536次元で埋込）+ HNSW索引** | 意味/概念検索が 0→1（現在 完全死） | 要 OpenAI 等の埋込API | ratify待ち（下記4） |
| **2** | **path_text の trgm GIN索引** | リテラル/トピック検索の recall・速度↑ | なし（純DDL・可逆） | **本PRでツール化** |
| 3 | TOC重複の除去（重複書誌→重複TOC） | 冗長ヒット減・網羅性の正確化 | なし | HOLD（biblio_item mint 連動） |

## 3. レバー#2（本PRで提出 — 実行はratify後）

トピック語は葉 `title` ではなく親階層 `path_text` 側にある:

```
title     = "§§329-332(西原道雄)"
path_text = "第8章 先取特権 > 第3節 先取特権の順位 > §§329-332(西原道雄)"
```

既存索引は title のみ → 「先取特権」で当たらない。path_text を索引対象にするだけで
当たる。path_text は葉 title を末尾に含むため **title 索引の上位互換**（recall低下なし）。

**実測 recall 改善**（read-only）:

| トピック | title索引のみ | path_text | 増分 |
|---|---:|---:|---:|
| 先取特権 | 313 | 483 | +170（+54%） |
| 債権者代位 | 235 | 476 | +241（+103%） |

成果物: `tools/toc_search_index/`（`migration_toc_path_text_trgm.sql` / `README.md`）。
適用は無停止 CONCURRENTLY 推奨。可逆。

## 4. レバー#1（最大効果・ratify待ち）

embedding が 100% NULL のため、意味検索は現在まったく動かない。これが断トツの最大レバー。
ただし2つのゲートがある:

1. **外部ベンダー依存**: 列が `vector(1536)` ＝ OpenAI `text-embedding-3-small` 系の器。
   Anthropic に埋め込みAPIは無く、生成には OpenAI 等のキーが要る。「embedding生成／
   外部ベンダー処理」は前WO（WO-BIBREC-FPDRYRUN-RECFIX-20260618）で明示的に HOLD 指定
   されていた項目。→ ベンダー選定とキーは owner 判断。
2. **本番backfill**: 552,544行への UPDATE＝不可逆な本番書き込み。lionbolt と同様 ratify 必要。

コスト試算: path_text avg 49字 ≈ 35トークン/ノード、×552k ≈ 19Mトークン。
text-embedding-3-small @ $0.02/1M ≈ **$0.4 程度**（全corpus）。コストは事実上無視できる。

埋込の**入力は path_text を採用すべき**（ベタ title ではなく階層パス全体）。レバー#2と
同じ理由で、文脈付きの方が retrieval 品質が高い。実行 GO の際は backfill ツール
（OpenAI クライアント + 冪等 UPDATE WHERE embedding IS NULL + HNSW索引 + 検索スモークテスト）を
lionbolt と同じ「ツール+migrationをPR、実行はratify後」様式で用意する。

> 浅井さん判断: 2026-06-25 時点で **embeddingは保留、索引（#2）だけ先に**。本ドキュメントは
> #1 を実行可能な状態の一歩手前（診断・入力設計・コスト確定）まで固定し、GO待ちとする。

## 5. 再現性

- 診断は全て read-only SELECT（`biblio.toc_nodes` への count/分布/サンプル）。DB mutation 0。
- 主要クエリ:
  - 充足: `count(embedding) / count(print_page) / count(path_text) / parent深度別`
  - 索引: `pg_indexes WHERE tablename='toc_nodes'`、`pg_extension`
  - recall: `count(*) WHERE title ILIKE '%t%'` vs `... path_text ILIKE '%t%'`
