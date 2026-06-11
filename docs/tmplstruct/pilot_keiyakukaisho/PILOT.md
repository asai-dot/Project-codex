# P0 パイロット — 契約解消の法律実務（自炊600dpi × ポイントOCR）

**対象**: 契約解消の法律実務（中央経済社・14式・所蔵・自炊4点完備）
**自炊 01_全体**: Box file_id `2150796103179`（40MB・248ページ・西村由布さんスキャン）
**bencom bib_id**: `NOBN_20220726_契約解消の法律実務_01`（bib_toc 140行・頁0〜248）

## 方針ロック（owner決定 2026-06-11）
- **基準＝うちの自炊600dpi画像**（高画質。将来精度が出る）。bencomページ画像は使わない。
- **本丸（会社議事録/会社法務書式集第3版/企業労働法書式編）は再自炊で画像を揃える前提**。

## このパイロットで判明した重要点
1. **骨格はDBに既存**: `biblio.bib_toc` に章節〜小見出しが**頁付き4階層**で入っている（目次OCR不要）。
   - 注: `page` は **スキャンPDFのページ順（表紙=0）**。→ PDFの1-based頁 = `bib_toc.page + 1`。
2. **14式は独立した目次ノードではない**: 本書の書式（モデル契約書・合意書・解除通知例）は
   **ケーススタディ本文に埋め込み**で、TOCに「書式」見出しが立っていない。
   → 式の所在は「bencomの書式リスト or 本文のポイントOCRでの書式検出」で取る必要がある。
3. **画像取得はMac側必須**: リモート環境の Box `get_preview_page` は空(0byte)を返す（40MB/小ファイルとも）。
   → `tools/pointocr_pilot.py` は Box の **PNG representation** を直接取得して vision に渡す設計。

## 書式を含む頁（bib_toc から特定したポイントOCR対象）
| 書式 | 章/位置 | bib_toc頁 | **PDF頁(1-based)** |
|---|---|---|---|
| 共同研究開発のモデル契約書 | 第2章 第5 ⑵ | 157–166 | **158–167** ←最も明確な書式 |
| 解除通知の例 | 第1章 第3 2⑴ | 60–69 | **61–70** |
| 売買・合意書作成のポイント | 第2章 第1 5 | 91–93 | 92–94 |
| 各ケースの合意書/契約書例 | 第2章 各節 | 散在 | 章頁から範囲指定 |

## 実行（Mac/ワーカー）
```bash
export BOX_TOKEN=...          # Box APIトークン
export ANTHROPIC_API_KEY=...  # Claude APIキー
python tools/pointocr_pilot.py \
  --box-file-id 2150796103179 \
  --title "契約解消の法律実務" \
  --pages 158-167,61-70 \
  --out out/keiyakukaisho
# → out/keiyakukaisho/pNNN.json（式ごとの構造JSON: blocks/clauses/blanks/notes）
```

## 検証の見どころ（実証ポイント）
- 600dpi画像→vision OCRで、**モデル契約書の条項番号・空欄・署名欄・別紙参照**が
  リーガルライブラリー全文OCRより明確に拾えるか（p158–167で判定）。
- `bib_toc.page+1` のページ対応が実画像と一致するか（最初の1〜2頁で校正）。
- 拾った書式が、tmplstruct の式境界（14式）と整合するか。

## 出力スキーマ（form 1件）
`form_title / form_kind / page_from-to / blocks[heading|party|recital|clause|item|signature|date|attachment|note] / blanks / clause_count / notes`
（`tools/pointocr_pilot.py` の SCHEMA と同一）

## 次
1. Mac側で上記コマンド実行 → p158–167 の出力JSONをこのフォルダにコミット（生品質を実物確認）。
2. 良ければ S5（tmplstruct スキーマ反映）を確定し、所蔵×式数の多い順に展開。
3. 並行して本丸3冊の**再自炊指示**（`スキャンルール.txt`準拠の4点）を発注。
