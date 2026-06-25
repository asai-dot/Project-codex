# toc_search_index — TOC検索精度レバー#2（path_text trgm 索引）

TOC精度向上の **read-only 診断**で確定したボトルネックのうち、外部ベンダー依存ゼロで
即適用できる打ち手。`biblio.toc_nodes.path_text`（階層パス文脈、100%充足）に
trigram GIN 索引を張り、リテラル/トピック検索の recall と速度を上げる。

- **状態**: NOT APPLIED（owner ratify 後に適用）。本番DB未接触。
- **可逆**: `DROP INDEX` で完全撤去可。
- **コスト**: 外部API不要。索引構築のみ（552k行・数十秒〜1分、~100–200MB）。

## なぜ効くか

`toc_nodes` は構造完備（page/path_text/階層すべて100%）だが、既存の trgm 索引は
葉ノードの**ベタ見出し `title` だけ**。トピック語は親階層の `path_text` 側にある。

```
title     = "§§329-332(西原道雄)"
path_text = "第8章 先取特権 > 第3節 先取特権の順位 > §§329-332(西原道雄)"
```

→ 「先取特権」検索は title 索引では当たらない。path_text を索引対象にすると当たる。
path_text は葉 title を末尾に含むので **title 索引の上位互換**（recall 低下なし）。

## 実測 recall 改善（read-only, 2026-06-25）

| トピック | title索引のみ | path_text | 増分 |
|---|---:|---:|---:|
| 先取特権 | 313 | 483 | +170 (+54%) |
| 債権者代位 | 235 | 476 | +241 (+103%) |

## 適用

`migration_toc_path_text_trgm.sql` 参照。推奨は無停止の CONCURRENTLY を
execute_sql（autocommit）で:

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS toc_nodes_path_text_trgm
  ON biblio.toc_nodes USING gin (path_text gin_trgm_ops);
```

## このレバーの守備範囲と限界

- **できる**: リテラル/部分一致/曖昧（trgm類似度）でのトピック検索の recall・速度向上。
- **できない**: 概念検索（「民法90条まわりの議論」のような語が一致しない検索）。
  それは**レバー#1 = embedding backfill（vector(1536)）**の領分で、外部埋め込みAPI
  と本番backfillのため別途 ratify 待ち。診断と順位付けは
  `artifacts/toc_accuracy_20260625/TOC_ACCURACY_DIAGNOSIS_20260625.md` を参照。
