# INGEST SPEC — raw_intake 受け渡しプロトコル / Phase 0 メタ契約 v0.2

- 作成日: 2026-06-18（v0.1）／改訂 2026-06-18（v0.2）
- 対象: DD-LITID-PLAN 4ルート書籍 版同定パイプライン Phase 0（メタ契約）＋ Phase 1（raw 投入）
- 状態: **Phase 0 契約確定**。raw 投入は本契約充足後（監査 GO 範囲内）。DDL/実装/backfill/本番突合は HOLD。
- 関連: DD-LITID-PLAN_4route_edition_resolution_v0.1_20260618.md
- 監査: 20260618_..._RESULT.md = DESIGN_PASS_WITH_NOTES（GPT-5.5 Thinking, 2026-06-18）

## v0.2 改訂の趣旨（監査 must_fix 5件の畳み込み）

| # | must_fix | 反映箇所 |
|---|---|---|
| 1 | 投入前に raw_intake 契約（出所/権利/媒体/snapshot/route id 等）を確定 | §2 manifest 拡張・§7-A 必須フィールド契約 |
| 2 | no-ISBN は bengo4 のみ／legallib は ISBN 持ち、と本文修正 | §0・§7（DD本体へも反映予定） |
| 3 | bengo4 no-ISBN は別レーン `bengo4_noisbn_shadow` | §5・§7-B |
| 4 | `unresolved_holding` / `unresolved_access` を一級市民で先に定義 | §7-C |
| 5 | リンク状態 confirmed/candidate/rejected/superseded を定義、confirmed 暗黙変更禁止 | §7-D |

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
  "source":            "lionbolt | bengo4 | legallib | self_scan",
  "source_system":     "LION BOLT | bengo4.com | legallibrary | self_scanner",
  "fetched_at":        "2026-06-10T05:00:00+09:00",   // = capture_timestamp
  "account":           "owner正規契約アカウント",
  "fetch_method":      "api | scrape | colophon_ocr",
  "acquisition_path":  "subscription_api | authenticated_scrape | physical_cut_scan",
  "source_location":   "https://... | box://folder_id | local://mac/path",  // source_url/location
  "rights_class":      "owned | subscription_access | mixed",                // rights/access class
  "medium_origin":     "digital | paper_scan",
  "route_local_id":    "book_id | content_id | legallib_book_id | scan_id",  // = key_field の native名
  "key_field":         "isbn | content_id",
  "toc_origin":        "publisher_html | own_ocr | unknown",
  "extractor_version": "bengo4_catalog.py@<hash> 等",   // = parser_version
  "record_count":      4490,
  "files":             [{"name": "...", "sha256": "...", "bytes": 0}],  // raw_hash=sha256
  "evidence_locator":  "box://file_id or path#anchor （後で証拠に辿れる位置）",
  "notes":             "47-5/規約遵守、本文不含 等"
}
```

- `toc_origin` は independence_flag（同一出版社TOC再配信の二重計上回避）に直結。
- `source_location` / `evidence_locator` / `extractor_version`（=parser_version）/ `acquisition_path`
  / `rights_class` は **取得時にしか残らない出所**。append-only でも未捕捉は永久に戻らない（監査 must_fix #1）。
- 投入は本 manifest の全必須フィールドが埋まったバッチのみ受け付ける（§7-A の契約ゲート）。

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

## 5. 取り込み順序（Phase 0 契約充足後）

レーンは **ISBN持ち** と **bengo4 no-ISBN** で物理的に分ける（監査 must_fix #3）。

1. **ISBN→NDL レーン**: 自所(ISBN取得分) / LION BOLT / legallib を raw へ。封筒は REPORT/sha256 から自動。
   ISBN→bibid で O(n) 縮約。read-only dry-run から。
2. legallib フル版を Mac から `raw_intake/legallib/` にドロップ → **field-profile 監査（§7-A ゲート）通過後**に 1 へ合流。
3. **`bengo4_noisbn_shadow` レーン（別）**: 弁コムは TOC主証拠＋独立証拠2本。ISBN→NDL レーンに混ぜない。
   independence は origin_publisher / content_hash / URL pattern / extractor lineage で判定。
4. 着地しない自所裁断（奥付欠落等）は **`unresolved_holding`** に保持（§7-C）。強制 edition 着地はしない。

## 6. 未確定（次工程）
- legallib フル版の実フィールド（ISBN形式/TOC構造）は本体ドロップ後に field-profile 監査で確認（§7-A 投入前ゲート）。
- 弁コム HTML ページの安定性（URL+capture_timestamp を証拠保持できるか）。
- 弁コム page_count は native に無く TOC 末ページからの推定要否を Phase 2 で判断。
- 加除式/ルーズリーフの NDL bibid 粒度不足時の表現（exception lane、should_fix）。

## 7. Phase 0 メタ契約（監査 must_fix 畳み込み・投入前に確定）

### 7-A. raw_intake 必須フィールド契約ゲート（must_fix #1）
各バッチは §2 manifest の下記を**全て**埋めた場合のみ ingest 受理:
`source, source_system, fetched_at(capture_timestamp), account, fetch_method, acquisition_path,
source_location, rights_class, medium_origin, route_local_id, key_field, toc_origin,
extractor_version(parser_version), record_count, files[].sha256(raw_hash), evidence_locator`。
legallib フル版は**ドロップ後 field-profile 監査**（ISBN形式・TOC構造・キー充足率）を通すまで投入保留。

### 7-B. レーン分離（must_fix #2, #3）
- **事実訂正**: no-ISBN は **bengo4 のみ**。自所/LION BOLT/legallib は ISBN 持ち（legallib はフル版検証保留）。
- `isbn_ndl_lane`（3ルート）と `bengo4_noisbn_shadow`（弁コム専用）を分離。混在禁止。

### 7-C. 未解決レコードを一級市民で先に定義（must_fix #4）
- `unresolved_holding`: 自所所有だが edition 未確定（奥付欠落・改訂未記載）。証拠付きで保持、後着地。
- `unresolved_access`: オンライン閲覧可だが edition 未確定。
- いずれも edition への**強制着地を禁止**。所有/アクセスのカウントには出すが edition カウントには出さない。

### 7-D. リンク状態と confirmed 不変則（must_fix #5）
- 状態: `candidate` / `confirmed` / `rejected` / `superseded`。
- `confirmed` は**暗黙変更禁止**。閾値再較正で揺れる場合は versioned evidence ＋ 明示的な
  re-evaluation event を記録し、`superseded` 経由でのみ遷移（silent mutation 不可）。
- カウント表示は confirmed edition / candidate work / access / holding を**分離表示**（collapse 禁止）。

### 7-E. GO/HOLD（監査 final_gate 準拠）
- **GO**: Phase 0 契約ドラフト（本書）/ raw_intake スケルトン設計 / field-profile 監査スクリプト / read-only dry-run 計画。
- **HOLD**: DDL・実装・backfill・本番突合・canonical promotion・serving・embedding・外部公開。
