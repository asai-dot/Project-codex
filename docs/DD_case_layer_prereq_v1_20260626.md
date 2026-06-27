# DD: 判例レイヤ投入の前提（cases未作成の事実整理）v1 (2026-06-26)

- status: 設計・前提整理（read-only調査に基づく）。本番DDL/書込は HOLD。
- 親: `MATERIALS_ORGANIZATION_OVERVIEW`（cases記述の訂正） / 02_ALO_判例レイヤ技術仕様書 v1.4 / `DD_author_model_resolution_v1`
- 目的: 人↔判例の前提＝判例レイヤの現状を実DB+Boxで確定し、投入の段取りとgapを明示する。

---

## 1. 認識訂正（重要）

- **`dynamic.cases` は判例テーブルではない。** Salesforce同期の**案件(matter)テーブルで1,017行**（sf_record_type/id, case_label, case_type, status, client_party_id, box_folder_url, sf_raw 等）。court/decision_date/case_number 等の判例列は無い。
- **判例(hanrei)レイヤのテーブルは本番に存在しない（DDL未適用）。** 仕様書v1.4/v1.5の `cases / case_annotations / alo_pointers / term_occurrence / decision_external_ids / alo_source_priority / casebundle_evidence` 等は全schema横断検索でヒットせず。
- → `OVERVIEW` の「dynamic.cases=0＝判例未投入」は表現が誤り。正しくは **「判例レイヤのスキーマ自体が未作成」**。埋める前に**DDL適用が先**。

## 2. 元データの所在・規模（Box, 揃っている）

| 材料 | 所在 | 規模 |
|---|---|---|
| D1-Law判例 RTF（全フィールド） | `…/02＿判例レイヤー/判例＿DLfromD1law`(folder 360757479930) | **約52.5GB**、母集団 **249,863件**（民事セレクション契約） |
| CSV サマリ | 同上 `判例一覧.csv` / `d1_lic_case_source_crosswalk_stable_v0.csv` | 9列基本メタ / クロスウォーク7.5MB |
| JSONL化 仕様＋サンプル | `花岡/legal-db/01_jsonl_conv/`, `花岡/20260607/01_jsonl_conv/` | 仕様書＋ADR。実変換 RTF92/CSV466/JSONL179件（裁判年月日分解済） |
| 判例骨格 case_spine | `…/alo-kg/case_spine`(folder 376420754269) | ~718KB |
| 目次語彙 d1law_taikei | 本番DB schema `d1law_taikei` | alo_terms **49,733** / labels 149,199 / relations 38,910（投入済） |

## 3. ターゲット設計（仕様書 v1.4/v1.5 要点）

- **URI**: `alo:case:jp:{court_code}:{YYYY-MM-DD}:{case_number_norm}`、`fn_generate_case_uri_v1()` で決定的生成＋CHECK。
- **同一性と解釈の分離**: `cases`（事件の同一性：canonical_uri[UQ]/court_code/decision_date/case_number_norm/disposition/case_type/full_text）＋ `case_annotations`（ソース別 headnote/taxonomy_paths[jsonb]/pointer_uri/review_status）。
- 本文参照=`alo_pointers`(char単位)、語彙紐付け=`term_occurrence`、外部ID=`decision_external_ids`(D1-Law 8桁)、ソース優先度=`alo_source_priority`(D1-Law=canonical)。
- RTF→DBマッピングは仕様書5章で確定（【判例ID】→decision_external_ids、【要旨】→annotations.headnote+taxonomy、【裁判年月日等】→cases、【審級関連】→alo_edges[appeal_chain]、【本文】→full_text+pointers）。

## 4. gap（投入前に要解決）

1. **判例レイヤDDL未適用**（最優先・SE/花岡レーン）。投入先schema名も未確定。
2. **「裁判年月日等」複合フィールドの分解未実装** — court_code正規化辞書（"最高裁判所大法廷"→コード）＋case_number_norm（全角→半角）。**3要素が揃わないと canonical_uri 生成不可**。
3. **要旨の法編パス→term_ids 参照先未確定** — 仕様は `ndlsh_terms` 記述だが、本番実在は `d1law_taikei.alo_terms`。対応付け方針の決定が要る。
4. **全量変換未済** — サンプル92/466/179件どまり。249,863件のRTF→JSONL→raw投入の本走行は未着手（原資52GB）。

## 5. 人↔判例の繋ぎ方（3ホップ。直接エッジは設計上なし）

```
authority.person  ──(評釈著者の名寄せ claim)──▶  authority.publication(評釈)  ──(評釈→対象判例)──▶  cases
```
- データ源は有：RTFの **【判例評釈】**フィールド（"氏名・誌名 巻号頁"、JSONLで約57%充足）。著者側=`authority.person`/`serving.publication_author_claim_current`、文献側=`authority.publication` は既存。
- **不足**: ①評釈テキストのパース（氏名・誌名・巻号頁→著者/publication/case_uri に分解、複数評釈は改行区切り）②**case ↔ publication エッジ**（「この文献はこの判例の評釈」関係の表/edge）が未実装 ③評釈著者名→person の claim 生成（既存同定パイプライン流用可、接続部が未整備）。

## 6. 次の一手（順序）

1. 判例レイヤ **DDL適用**（cases/case_annotations/alo_pointers/term_occurrence/decision_external_ids/source_priority）— SEレーン。
2. RTF→JSONL の **裁判年月日等 分解パイプライン**＋court_code/case_number正規化辞書 → canonical_uri 生成。
3. 小バッチ dry-run（数百件）→ ゲート → Owner ratify → 全量(249,863)投入。
4. 評釈パース → case↔publication エッジ → 評釈著者 claim で **人↔判例(3ホップ)** 開通。
