# DD: 判例評釈パース（人↔判例 3ホップの結線）v1 (2026-06-26)

- status: 設計のみ（read-only調査に基づく）。本番書込は HOLD。**判例DBレイヤ作成(DDL)の下流**。
- 親: `DD_case_layer_prereq_v1`（判例レイヤ前提）/ `DD_author_model_resolution_v1`（authority person/publication）
- 既存調査: 判例抽出は `d1law_ingest.py`/`extract_hanrei.py` が運用中（68,080/249,863=27.25% 抽出済, Box CSV）。
  **ただし canonical CSV 列に【判例評釈】は無く、評釈の構造化パースは未着手**＝本DDが埋める。

---

## 0. 何を作るか（genuinely 未着手の部分）

D1-Law判例RTFの **【判例評釈】フィールド**（JSONLで約57%充足）を分解し、
**person →(評釈著者)→ publication(評釈) →(対象判例)→ case** の3ホップを結線する。
直接の person→case エッジは設計上作らない（文献経由が正本, 判例レイヤ仕様 §6）。

```
authority.person ──claim── authority.publication(評釈) ──edge── cases
   △ 評釈者名の名寄せ        △ 誌名・巻号頁→刊行物         △ 対象判例の同定
```

## 1. 入力（既存資産）

- 判例RTF/CSV: `判例＿DLfromD1law`(folder 360757479930)、`extract_hanrei.py` 出力。
- 【判例評釈】生テキスト例（RTF内）: `田原睦夫・民商法雑誌 87巻4号512頁` のような **「氏名・誌名 巻号頁」** が改行区切りで**複数**並ぶ。
- 突合先: `authority.person`(著者) / `authority.publication`(刊行物) / cases(判例, ※DDL適用後)。

## 2. パース仕様（1評釈 = 1レコードに分解）

各判例の【判例評釈】テキストを行分割 → 各行を次に分解:

| 抽出項目 | 例 | 正規表現/規則(草案) |
|---|---|---|
| 評釈者名(複数可) | 田原睦夫 | 先頭〜区切り(`・`/`／`/全角空白)。共著は複数 |
| 掲載誌名 | 民商法雑誌 | 区切り後〜巻号の前 |
| 巻 | 87 | `(\d+)巻` |
| 号 | 4 | `(\d+)号` |
| 開始頁 | 512 | `(\d+)頁` |
| 年(あれば) | 2018 | `（(\d{4})）` |
| 評釈種別 | 判例評釈/判例研究/解説 | RTFの form_category 由来 |

出力中間: `hyoshaku_flat`（1行=評釈者×評釈×判例）。列: case_ref(対象判例) / hyoshaku_author_raw / serial_title_raw / volume / issue / page / year / raw_line / parse_confidence。

## 3. 3ホップの結線（各ホップは claim+evidence で候補→裁定）

### H1. 評釈 → 対象判例（case_ref）
- 評釈は判例RTF内に在る＝**その判例レコードに属する**。case_ref = 当該判例の canonical_uri（DDL適用後の cases.canonical_uri）。これは構造的に確実（同一RTF/判例ID内）。

### H2. 評釈著者 → person
- `hyoshaku_author_raw`(氏名) → `authority.person` を **氏名+yomi正規化**で突合。
- 既存同定パイプライン（publication_author_claim と同型）を流用。hard ID は評釈テキストに無い→**氏名のみ＝同名多発** → trust_tier 低め、name_only は candidate固定（自動accept禁止）。
- 名寄せは `resolution_log` 記録。

### H3. 評釈 → publication（刊行物の1記事として）
- `serial_title_raw`+巻号頁 → 既存 `authority.publication`(または刊行物マスタ)に**評釈記事**として登録/突合。
- 誌名は表記ゆれ吸収（NFC・略称）。誌名→serial の解決は既存の雑誌レイヤ(ISSN/誌マスタ)を使う。
- 評釈記事の publication_type = `case_comment`。

### 結線エッジ
- person→publication: `publication_author_claim`（H2の著者同定）。
- publication→case: **新エッジ**（仕様書の `alo_edges` evaluates/review_chain 相当 = 「この文献はこの判例の評釈」）。判例レイヤ仕様 §6 の literature_ref/evaluates を使う。

## 4. 落とし穴（器側ゲートで防ぐ）

1. **複数評釈/複数著者**：1判例に評釈N件、1評釈に共著者M名 → flat展開で取りこぼさない。`parse_confidence` で行分解の確からしさを保持。
2. **氏名のみ＝同名衝突**：hard ID不在。name_only は candidate止まり、auto-merge禁止。著者の活動年(判決年近傍)で補強。
3. **誌名表記ゆれ**：略称・旧称・全半角。誌マスタ(ISSN)突合＋未解決は保留レーン。
4. **57%しか評釈が無い**：評釈なし判例は人↔判例リンクが立たない（正常）。網羅性の線はOwner合意。
5. **依存順序**：H1は cases.canonical_uri が前提＝**判例レイヤDDL適用が先**（`DD_case_layer_prereq` §6-1）。それ未了なら hyoshaku_flat までで止め、case_ref は判例ID(decision_external_id)で保持。

## 5. 段取り（HOLD規律）

1. (read-only) サンプル数百判例の【判例評釈】を抽出し、§2パーサの precision/recall 計測（行分解・氏名/誌名/巻号の取り出し率）。
2. `hyoshaku_flat` を staging 生成（本番書込なし）。
3. 判例レイヤDDL適用後、H1で case_ref を canonical_uri に解決。
4. H2/H3 を claim+evidence で候補生成 → dry-runレポート（同定率・同名衝突率）。
5. Owner ratify → publication_author_claim ＋ publication→case エッジを本投入。

**HOLD（ratifyまで）**: authority.*/cases 本番書込 / 評釈著者の canonical昇格 / publication→case エッジ確定。
**依存**: 判例レイヤDDL（`DD_case_layer_prereq`）。それが無いと3ホップは閉じない。

## 6. 未確認（次に潰す）

- 【判例評釈】の実フォーマットの揺れ（区切り・年表記・「・」の著者区切りvs誌名内）→ サンプル実測でパーサ確定。
- 誌名→serial(ISSN)解決の既存マスタの所在・カバレッジ。
- publication→case エッジの格納先（既存 alo_edges 相当が本番にあるか＝判例レイヤDDLと一体で決まる）。
