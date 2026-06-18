# INGEST SPEC — raw_intake 受け渡しプロトコル v0.1

- 作成日: 2026-06-18
- 対象: DD-LITID-PLAN 4ルート書籍 版同定パイプライン Phase 1（raw 投入）
- 状態: 仕様確定（実投入は GPT 監査 OK 後）
- 関連: DD-LITID-PLAN_4route_edition_resolution_v0.1_20260618.md

## 0. 確定した前提（実データ観測 2026-06-18）

| ルート | Box現物 | 形式 | ISBN | TOC | 状態 |
|---|---|---|---|---|---|
| LION BOLT | `LIONBOLT_法律書カタログ_20260610` (388659455439) | catalog_dedup.jsonl 61MB | あり(ISBN-13) | 19% | Box済 |
| 弁コム(bengo4) | `弁コム法律書カタログ_20260610` (388913757182) | catalog.jsonl 505MB | 無し(content_id) | 100% | Box済(biblio投入3,802/4,490) |
| 自所(裁断) | colophon_* / opac_parsed* / scan_data | 奥付OCR ndjson + PDF | 混在 | — | OCR pipeline既存 |
| legallib | サンプルのみ(388957737218 等) | resolver sample | あり | 不明 | **本体Macローカル→Box未同期** |

**要点**: 無ISBNは弁コムのみ。他3ルートはISBNあり→NDL直結。no-ISBN同定機械は弁コム専用。
弁コムTOC=出版社HTML / LION BOLT TOC=自前OCR → 両者は独立出自（independence好材料）。

## 1. チャネル: Box `raw_intake/` ドロップ

Box Drive 同期パス配下に下記を作り、Mac の Finder からドロップ（単一書き手）。
大容量(505MB等)は MCP 経由不可のため、同期ローカル実体を ingest が直接読む。

```
raw_intake/
├── lionbolt/20260618/    catalog_dedup.jsonl  + manifest.json
├── bengo4/20260618/      catalog.jsonl        + manifest.json
├── legallib/20260618/    <Macフル版>.jsonl    + manifest.json   ← 唯一の新規ドロップ
└── self_scan/20260618/   colophon_meta.jsonl  + manifest.json   ← PDF本体は入れない
```

## 2. 🔴 manifest.json（不可逆メタの封筒・バッチ単位）

各 REPORT.md ＋ inputs_sha256.txt から**機械生成**（手書きしない）。取得時にしか残らない出所を固定。

```json
{
  "source":          "lionbolt | bengo4 | legallib | self_scan",
  "fetched_at":      "2026-06-10T05:00:00+09:00",
  "account":         "owner正規契約アカウント",
  "fetch_method":    "api | scrape | colophon_ocr",
  "extractor_version": "bengo4_catalog.py@<hash> 等",
  "rights_profile":  "subscription_terms | owned",
  "medium_origin":   "digital | paper_scan",
  "key_field":       "isbn | content_id",
  "toc_origin":      "publisher_html | own_ocr | unknown",
  "record_count":    4490,
  "files":           [{"name": "...", "sha256": "...", "bytes": 0}],
  "notes":           "47-5/規約遵守、本文不含 等"
}
```

`toc_origin` は independence_flag（同一出版社TOC再配信の二重計上回避）に直結。

## 3. ソース別フィールド → 共通 source_biblio_item マッピング

| 共通列 | LION BOLT | 弁コム | legallib | self_scan(奥付) |
|---|---|---|---|---|
| `src_native_id` | book_id | content_id | legallib_book_id | scan_id |
| `isbn` | isbn(13) | （無→enrichで後付） | isbn | 奥付抽出 or null |
| `title` | title | title.main | title | 奥付OCR |
| `author` | author | authors[] | author | 奥付OCR |
| `publisher` | publisher | publisher.name | publisher | 奥付OCR |
| `pub_date` | pub_date(ISO) | publication_date / release_date | pub_date | 奥付（年のみ多） |
| `page_count` | page_count | （TOC末ページから推定） | — | PDF総頁 |
| `toc_raw` | toc.items[] | toc_html + toc_nodes[] | （取得後） | — |
| `external_ids` | amazon/cinii/calil_url | precedents(lic_no) | — | — |
| `fetched_at` | manifest | レコード毎 fetched_at | manifest | scanned_at |

raw はソース忠実保持（append-only）。上記は派生ビュー用の対応表であり raw を上書きしない。

## 4. 自所 裁断PDF の扱い（PDF本体はレーンに入れない）

`self_scan/.../colophon_meta.jsonl` = 1行1PDF：
```json
{"path": "...", "filename": "...", "sha256": "...", "page_count": 0,
 "colophon_ocr_text": "...", "isbn_extracted": "9784...", "scanned_at": "...",
 "medium_origin": "paper_scan", "fulltext_access": "local_pdf"}
```
- 既存 colophon_ocr / colophon_ndl_results.json pipeline を流用。
- ISBN 取れたもの → ISBN→NDL 直結。取れない古書 → 書誌/TOC fingerprint へ。
- PDF 本体はローカル保持（権利・容量）。レーンにはメタのみ。

## 5. 取り込み順序（audit OK 後）

1. 既存3ソース（LION BOLT / 弁コム / 自所）を Box 現物から Supabase raw へ。封筒は REPORT/sha256 から自動。**即着手可・ノーリスク**。
2. legallib フル版を Mac から `raw_intake/legallib/` にドロップ → 同様に raw へ。
3. ISBN持ち3ルート → NDLハブ直結。弁コム(無ISBN)のみ TOC主証拠ルート。

## 6. 未確定（次工程）
- legallib フル版の実フィールド（ISBN/TOC構造）は本体ドロップ後に確認。
- 弁コム page_count は native に無く TOC 末ページからの推定要否を Phase 2 で判断。
