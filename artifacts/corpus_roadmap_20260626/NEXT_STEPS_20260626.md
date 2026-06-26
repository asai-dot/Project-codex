# NEXT_STEPS_20260626 — 文献TOCコーパス これからの工程（legallib突合の後）

```yaml
doc_id: CORPUS-NEXT-STEPS-20260626
status: roadmap（思考メモ。実行は各フェーズで ratify / 接続確立後）
created_at: 2026-06-26 JST
author: Claude（浅井さん指示「そのあとの作業考えておいて」）
context: legallib_meta を staging へ \copy 待ち（Mac接続未確立で中断中）
```

## 現状スナップショット（このスレで実測確定）

| 層 | 中身 | 件数 |
|---|---|---|
| bib_records | asai 6,524 + 弁コム 3,802 + lionbolt 22,844 | 33,170冊 |
| bib_toc（正準・フラット） | 弁コム 552,544 + lionbolt 236,674 | 789,218ノード |
| toc_nodes（リッチ層: path_text+embedding枠） | **弁コムのみ** | 552,544（embedding 100% NULL） |
| legallib | staging 待ち。カタログ 4,052冊 / 662,717ノード（ISBN無し） | DB未投入 |
| 事務所PDF | 611本（has_toc=0、TOC未抽出） | TOC 0 |

ボトルネックは2つ: **(A) embedding が全く無い**（意味検索が死） / **(B) リッチ層が弁コムしか無い**（lionbolt/legallibが検索高度化の外）。

---

## Phase 0 — legallib 突合の数字が出た直後の判断（最優先）

\copy で 4,052 行が staging に入ったら、私が read-only で：
- `title_norm | publisher_norm | pub_year` fingerprint（既存FP v1）で 33,170冊と突合
- **正味ユニーク冊数** と 重複内訳（どのソースと衝突か）

判断分岐:
- **ユニーク多い** → full 投入の価値大 → Phase 1 へ
- **重複多い** → ユニーク部分集合のみ投入 or 全投入＋重複は review queue 行き
- **官報/パブコメ等（publisher空）** は本来ユニーク。`form_type` でタグ分離し、"書籍"のユニーク数を水増ししないよう別勘定

> 注: legallib は **ISBN無し**。横断キーは fingerprint のみ。publisher空グループは title+year に縮退するので別集計。

## Phase 1 — legallib 投入（lionbolt と同枠 / mint は HOLD）

- `tools/legallib_ingest/load_legallib.py`（lionbolt ローダ派生）。差分=
  - ISBN無し → fingerprint識別のみ / `authors_raw` / `pub_year_raw` パース
  - `toc[]`（levelツリー＋`toc_node_count`）→ `bib_toc(bib_id,ordinal,level,page,text)` へ平坦化
  - 官報/パブコメを `form_type` でタグ
- `library_sources` に `legal-library` 1行 / `bib_id='legallib:'+book_id` / `source='legal-library'`
- dedup は **レポートのみ**、biblio_item mint は HOLD。PR提出 → ratify後に実行
- 実行は Mac（124MB全文jsonlを読む）。**※先に Mac→DB 接続(DSN)を一度きちんと通す**（後述）

## Phase 2 — リッチ層(toc_nodes)の統一【精度の前提工事・効果大】

現状 toc_nodes は弁コムのみ。lionbolt(236k)も legallib(投入後)も `bib_toc` にはあるが
path_text/embedding枠を持つ toc_nodes に**射影されていない** → 精度レバーが効かない。

- `bib_toc` の (ordinal, level) 階層から **path_text を生成**（祖先たどり）して toc_nodes へ射影
- lionbolt → 次に legallib。これで検索対象が全ソース ~1M+ ノードに
- これは **DB内処理**（外部依存なし）。SQLは私がオフラインで先に書ける

## Phase 3 — 精度レバー（統一層の上で、効く順）

1. **path_text trgm 索引**（PR済 `tools/toc_search_index/`）→ apply。全ソースを literal/トピック検索可に（実測 recall +54〜103%）
2. **embedding backfill**（vector(1536), OpenAI text-embedding-3-small, path_text入力）→ **意味検索 0→1**。最大レバー。プロバイダ/キー＋ratify待ち（owner保留中、コスト~$0.4）
3. （任意）HNSW索引で ANN 高速化

## Phase 4 — 4種類目: 事務所PDFのTOC抽出

- 611本（=自分の実蔵書、関連度100%）が has_toc=0。OCR/構造抽出で TOC を起こし asai-bookshelf に付与
- 別パイプライン（OCR）で工数大。価値は「自分が持ってる本の中身が引ける」= 高い。別途スコープ設計

## 横断・ガバナンス（HOLD / 並行）

- **biblio_item mint & 横断dedup収斂（DD-LITID）**: 4カタログの重複を正準itemに統合する本丸。fan-out/fingerprint成果が全部ここに効く。owner ratify 待ち
- **RLS advisory**: toc_nodes 等が anon 露出（PostgREST公開スキーマ次第）。コーパス拡大で重要度↑。公開スキーマ確認→ポリシー設計
- **弁コム未ロード 688冊**（TOC-rich）: Mac側 source/loader 調査
- **Mac→DB 接続の確立**: 毎回の Mac側ロードで再発する。セッションプーラ
  `host=aws-0-ap-northeast-1.pooler.supabase.com port=5432 dbname=postgres user=postgres.nixfjmwxmgugiiuqfuym sslmode=require` ＋ DBパスワードを一度 `.pgpass`/env に固定すると以後ノーストレス

---

## 私がオフラインで先に進められるもの（Mac/DB不要）

- ✅ 本ロードマップ（これ）
- ○ **Phase 2 の射影SQL**（bib_toc→toc_nodes path_text生成）を先に書いてPR下書き。schema既知で書ける
- △ load_legallib.py は **toc[]の実構造を見てから**（meta しか見ていない）。雛形scaffoldまでは可
- ✅ legallib突合クエリ（staging前提）の用意 — 入った瞬間に走らせる形で控え済み
