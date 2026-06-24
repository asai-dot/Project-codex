# Project Codex — 知識グラフ：文献↔判例↔法令 / RAG（Fork 2 / KG スレッド）

ALOが自前で握る**引用グラフ**を作る。商用2サービス（リーガル＝文献→法令／ベンコム＝文献→判例）の
強みを吸い、着地は**ALOが構築できる公開アンカー**（e-Gov法令／裁判所HTML）＋内部PDで固める。
最終的に ③RAG「事務所ライブラリに聞く」が、文献パッセージ＋根拠判例＋根拠法令の**3レーン出典**で答える。

> 人間ビューワー（4図書館横断検索・ジャンプ・目次/引用コピー）は別スレッド：
> branch `claude/toc-search-rag-tLcyb` / PR #6。**互いのファイルは触らない。**
> 本スレッドの担当範囲は [`docs/THREAD_SCOPE.md`](docs/THREAD_SCOPE.md)。

> このスレッドは**人間ビューワー**（4図書館横断検索・ジャンプ・目次/引用コピー）を担当。
> 知識グラフ（文献↔判例↔法令の引用グラフ・判例の正本キー・採取・RAG）は別スレッドへフォーク済み：
> branch `claude/kg-lit-precedent-rag` / PR #11。**互いのファイルは触らない。**

---

## 中核

| ファイル | 役割 |
|----------|------|
| [`src/case_identity.py`](src/case_identity.py) | 判例の**正本キー**（和暦・事件番号・裁判所）。略記 `最大判`／leala `令和４年（ワ）`／`extract_case_refs` で raw_text から地名込み再抽出 |
| [`src/case_deeplink.py`](src/case_deeplink.py) + [`config/case_sources.json`](config/case_sources.json) | 判例の**3層着地**（内部PD → 裁判所HTML → ベンコムオンランプ） |
| [`scripts/harvest_precedents.py`](scripts/harvest_precedents.py) | ベンコム precedents ページ → 引用レコード |
| [`scripts/validate_case_refs.py`](scripts/validate_case_refs.py) | 実OPACへ一括適用で被覆率/衝突を検証（`--from-raw`） |
| [`docs/literature_precedent_graph.md`](docs/literature_precedent_graph.md) | **本設計の主資料**（§1-11） |

## クイックスタート

```bash
npm test    # = python3 tests/test_case_lane.py（56チェック）

# 実OPACへの一括適用（本番env、raw_text地名込み再抽出）
python3 scripts/validate_case_refs.py opac_parsed/ext_opac_articles.jsonl --from-raw
```

## 到達点（fork時点）

- 判例の**正本キー**は ALO未整備だったので本スレが提供（`case_spine` は案件＝別物と確認済）。
- 既存資産に接続：OPAC/CiNii の case_citations **17,259件**・`docket_raw`、D1KOS `article_cites_case`
  レビューレーン、`opac_parse.py` の `case_ref_text`。規律一致（`claim_scope=cites` / `pending_review`）。
- 被覆率実証：旧 case_ref_text=40% → `--from-raw`（raw_text 地名込み再抽出）=**100%**（代表サンプル）。

## ロードマップ

詳細・次の一手は [`docs/THREAD_SCOPE.md`](docs/THREAD_SCOPE.md)。本番フル17,259件の `--from-raw` 実走 →
ベンコム実採取 → `docket_raw` 突合 → e-Gov法令/裁判所HTML着地 → 時点警告 → ③RAG。

スキーマは [`schema/supabase_schema.sql`](schema/supabase_schema.sql)（`case_citations` / `law_citations` /
pgvector）。全体設計は [`docs/architecture.md`](docs/architecture.md) §7。
