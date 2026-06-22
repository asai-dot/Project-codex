# RECONCILIATION — 既存 NDL/蔵書パイプラインに寄せる（再発明の撤回）

- 作成日: 2026-06-20
- 経緯: 当初ここに R1/R2/R3 のオフライン照合スクリプトを新規作成したが、**他スレ（事務所スクリプト群）に
  同等資産が既存**と判明したため、新規スクリプトは撤回（git 履歴には残置）。本書は既存資産への対応表と再利用方針。
- 監査整合: FORWARD_ROADMAP v0.3 WS-R/WS-A/WS-B。**reuse > rebuild**。

## 1. 既存資産（Box `scripts/` ＝ 事務所自動化コードベース）

| 既存 script | 役割 | 私の(撤回した)再発明 |
|---|---|---|
| `ndl_normalize.py` | ISBN noise除去 / **ISBN10→13 / checkdigit** / NFC / 全角半角 / `isbn_status`分類。target に **`ndl_isbn_index.csv`** あり | `isbn_util.py`, `r2`の正規化 |
| `ndl_integrate.py` | ISBN で蔵書突合し **`alo:book:isbn:{isbn13}` URI 生成**、NDC320-329 法律書サブセット | `r3_coverage.py` の蔵書突合 |
| `ndl_pipeline.py` | normalize→enrich→integrate オーケストレータ | `run_all.sh` |
| `match_titles_to_ndl.py` | **no-ISBN の title→NDL exact/contains/fuzzy 照合**。正規化で**版/刷を除去**（EDITION_RE） | 1,101件 no-ISBN generator 構想 |
| `google_books_isbn_recovery.py` | no-ISBN レコードの **ISBN 復元** | （未着手だが構想と重複） |
| `enrich_ndl_publisher.py` | OpenBD で publisher 補完 | — |
| `opac_ndl_overlay_analysis.py` / `opac_temporal_*` | OPAC 突合・時系列 | — |
| `bookshelf_pdf_match.py` / `export_bookshelf_master.py` | 蔵書PDF突合 / master 書き出し | — |
| `build_object_links_from_ndl_matches.py` | NDL match → object link | — |

**重要**: `ndl_integrate.py` が生成する `alo:book:isbn:{isbn13}` は、現 DB `biblio.bib_records.bib_id` と同形式。
＝ **今の bib_records（asai-bookshelf, ndl 76.7%）はこの既存パイプラインの出力**。R4 lineage 仮説は事実上ここで裏取れる。

## 2. 撤回したもの（git 履歴に残置・HEAD から除去）

`isbn_util.py` / `r1_probe.py` / `r2_build_index.py` / `r3_coverage.py` / `selftest.py` / `run_all.sh` /
`README.md`(旧) / `RUNBOOK_local.md`(旧)。
※ selftest は PASS していたが、機能が既存と重複のため不採用。

## 3. 残置（再利用可能な新規・データのみ）

- `input/cohortA_isbn.tsv`（5,397, DB由来 read-only スナップショット）
- `input/cohortA_noisbn.tsv`（1,127, 同）
→ 既存 `ndl_integrate.py` の `books.json` / `bookshelf_master` と役割が重なる。**どちらを正とするか §5 で要確認**。

## 4. 再利用方針（rebuild しない）

- **WS-R（オフライン索引）**: 新規作成せず、`ndl_normalize.py --target index`（`ndl_isbn_index.csv`）を
  **16.7GB の `ndl_all_records_*.csv`** に向ける運用に寄せる。差分は「入力ファイル名/パスの差し替え」程度のはず。
- **WS-A2（421 穴埋め）**: `ndl_integrate.py` の shelf 突合 + `google_books_isbn_recovery.py` を再走。
- **WS-B1（1,101 no-ISBN）**: `match_titles_to_ndl.py`（版/刷除去済）を再利用。新規 generator は作らない。
- v0.3 の監査ガード（candidate≠confirmed / lineage / no egress / Q1 非循環）は、既存出力を**そのまま confirmed 扱い
  しない**形で上に被せる（既存は match までで、adjudication は別途）。

## 5. owner / local に確認したいこと

1. 既存 `scripts/` 一式の所在（Asai PC / Box）と、`ndl_all_records_*.csv`(16.7GB) が `ndl_normalize.py` の
   harvest 入力（`ndl_isbn_index.csv` 等）の元データか。**重複生成を避けるため**。
2. `books.json` / `bookshelf_master*.json`（既存）と 本 DB `bib_records`/本 `input/*.tsv` のどれを cohort-A の正とするか。
3. 既存 `ndl_*_normalized.csv` / `ndl_shelf_integrated.csv` の最新版が Box にあるか（あれば R3 被覆は再走不要で読むだけ）。

→ 上記が分かれば、**新規コードゼロで** WS-A1/A2/B1 の read-only 計測に入れる見込み。
