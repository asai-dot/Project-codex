# legallib_ingest — Legal Library 法律ライブラリ投入ローダ（SCAFFOLD）

> 状態: **SCAFFOLD（実投入は2つの前提条件後）**
> 1. legallib メタの DB staging 完了（`_stg_legallib_raw` に 4,052 行）
> 2. Phase 2 DDDESIGN 監査 PASS（`gpt_ometsuke/from_gpt` の RESULT 着）
>
> 本ファイルは Phase 1 の地ならし。dry-run 経路のみ完成、apply 経路はスタブ。

## 設計（lionbolt と同枠 + legallib 固有差分）

| 観点 | lionbolt | legallib |
|---|---|---|
| 主キー | book_id（ISBN+内部ID） | book_id（**内部のみ・ISBN無し**） |
| 識別 | ISBN13 で横断キー | **fingerprint v1 のみ**（title+publisher+year） |
| 目次構造 | flat `toc.items[]`（level属性付き） | **levelツリー `toc[]`**（再帰DFS で flatten 必要） |
| 形式分離 | monograph 主 | 官報/パブコメ混在 → `form_type` でタグ |
| ページ数 | `page_count` あり | 多くは無い（`physical=null` 既定） |
| URL | book_url_template あり | 不明 |

## 主要関数（実装済み）

- `norm_isbn` / `norm_str` / `norm_key`：FP v1 と同じ正規化
- `parse_pub_year`：`pub_year_raw` 文字列から年抽出（"2019年" 等）
- `detect_form_type`：publisher 空 + 「官報」「パブリックコメント」で分類
- `to_bib_record`：bib_id mint + 既存 schema に整形
- `to_toc_rows`：levelツリーを深さ優先で `(ordinal, level, page, text)` に flatten
- `fingerprint_v1`：既存 FP と同形（突合用）

## dry-run（DB非接触）

```bash
python tools/legallib_ingest/load_legallib.py \
    --input ~/alo-ai/work/legallib_dl/legallib_toc_full.jsonl \
    --out artifacts/legallib_ingest_dryrun_$(date +%Y%m%d) \
    [--existing-fingerprints existing_fp.tsv]
```

出力: `SUMMARY.json`（件数・form_type分布・FP突合があれば `DEDUP_REPORT.json`）

## 投入（Phase 1 着手時に追加するもの）

- `migration_legallib.sql`（lionbolt の `migration_lionbolt.sql` を雛形に）
  - `library_sources` に legal-library 1行
  - staging `_stg_legallib_bib` / `_stg_legallib_toc`
  - `biblio.fn_legallib_upsert(p_loader_version, p_source_hash)`
- 本 `load_legallib.py` の `--apply` 経路を psycopg2 で実装
  - lionbolt 同様 `\copy` で staging → `SELECT fn_legallib_upsert(...)` を呼ぶ
- mint / canonical promotion は **HOLD**（DD-LITID）

## スコープ外

- biblio_item mint / 横断 dedup 確定（HOLD）
- embedding 生成（Phase 3）
- toc_nodes シルバー射影（Phase 2 / 監査PASS後にこの bib_id を流す）
