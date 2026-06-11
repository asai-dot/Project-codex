# 詳細目次の出どころ — LION BOLT 経由（弁コムとは別）／DB投入は未了

## 結論
- **詳細TOCは「LION BOLT」経由で取得済み**。弁コムライブラリー(bengo4)とは**別サービス**。
  - LION BOLT＝株式会社サピエンスの法律書全文検索（著作権法47条の5、25,049冊）。
  - 取得済みコーパス: **書誌＋構造化詳細目次（ページ範囲＋階層レベル付き）**。
  - 規模: 22,844冊の書誌、うち **目次あり4,433冊／264,555項目**（`toc.items[].level / startHeadlinePage / endHeadlinePage`）。
  - 置き場: Box `LIONBOLT_法律書カタログ_20260610/`（catalog_dedup.jsonl 64MB ほか）。
- **ただしDB投入はドライランのみ（未反映）**。`lionbolt_dryrun_summary_20260611.json` = `DRYRUN_COMPLETED_NO_DB_WRITES`（264,555行→toc_nodes、ddl/data writes=false、toc_source=lionbolt）。
  → だから現DBの `biblio.bib_toc`（3,802冊）には**弁コム(bencom)由来しか無く**、LIONBOLT分（全書含む）はまだ見えない。

## TOCの3系統（粒度の整理）
| 系統 | 出どころ | 収録 | 頁/階層 | DB状態 |
|---|---|---|---|---|
| bencom TOC | 弁コムライブラリー | 3,802冊（出典本=これ） | 頁＋4階層 | **bib_toc に投入済** |
| **LION BOLT TOC** | LION BOLT(サピエンス) | **4,433冊**（より広い） | **ページ範囲＋階層** | **ドライラン・未投入** |
| codex_ocr TOC | 自炊02_目次のOCR | 自前スキャン分 | 総目次のみ・頁なし・ノイズ | Box app/data/toc に断片 |

## 契約書式実務全書の件（実確認）
LIONBOLT INDEX(22,844冊)を照合した結果：
- **第3版が収録・目次あり**：
  - `9784324107508` 第1巻 993p／**TOC 283項目**
  - `9784324107515` 第2巻 988p／**TOC 290項目**
  - `9784324107522` 第3巻 820p／**TOC 542項目**（いずれも `source_type=scan, has_toc=True`、ページ範囲付き）
- **旧版（第2版 9784324096970/987/994）はLIONBOLT未収録**。自炊(996MB等)とBoxのcodex_ocr総目次は**この旧版**。
- 当事務所は**新旧2版とも所蔵**。

→ 全書をやるなら **「LIONBOLT第3版TOC（頁範囲付き）＋第3版の現物/スキャン」**が筋。
  目次を画像OCRで起こし直す必要はない（第3版基準にすれば既に構造化済み）。

## 効いてくる含意
1. **本丸/出典本の骨格はLIONBOLTで一気に揃う可能性**：4,433冊分の頁範囲付きTOCが未投入で眠っている。
   → **LIONBOLTドライランを本投入（toc_nodes化）**すれば、tmplstructの「骨格」調達が激変する。
2. ポイントOCRの設計は不変（骨格＝TOC、中身＝書式頁のvision OCR）。骨格の供給源にLIONBOLTが加わるだけ。
3. 版の使い分け: 詳細TOCが揃うのは**新しい版**が多い（LIONBOLTはOCR対象が新しい本中心）。正規化は**新版基準**が有利。

## 次アクション候補
- **A. LIONBOLT本投入**：ドライランをレビュー（quarantine: depth_gap 69 / first_row_depth_gt_1 600）し、toc_nodes へ本ロード → 4,433冊のTOCをDBで使える状態に。
- **B. 出典本×LIONBOLT突合**：175出典本のうちLIONBOLTにTOCがある冊を洗い出し（弁コムbib_tocと重複/補完を確認）。
- **C. 全書は第3版基準**でLIONBOLT TOC＋第3版スキャンに切替（旧版自炊はアーカイブ扱い）。
