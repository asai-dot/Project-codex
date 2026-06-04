# A1 実相談検索観測ベースライン — 方法 (baseline_method.md)

> **これは検索ベンチ（評価）ではない。観測装置である。**
> Stage1 では「この相談なら何を引くべきか」を一切判断しない。実相談テキストに対し、現状DBが**実際に何に反応するか**だけを記録する。
> 正解率評価ではなく、`biblio.bib_terms`（語彙↔蔵書の橋）投入前の **before スナップショット**。

## 1. 目的
実相談テキストをそのまま投げたとき、現状の語彙(`biblio.terms` 554)・書誌(`bib_records`)・目次(`bib_toc`)が
どこで反応するかを観測する。bib_terms 投入後に同一スクリプトで再走し、差分で橋の価値を実測する。

## 2. 入力（決定的スナップショット）
- SF leala `leala__Consultation__c` 230件（org=`alo-prod`）。使用列 `Id, Name, leala__CaseOutline__c, ALO_Inferred_CaseCategory__c`。
  → `~/alo-ai/work/searchbench_a1/consultations_raw.json`（**PIIあり・非コミット**）。
- 語彙 `biblio.terms` 554（全 `scheme=jp_statutory_definition`）→ `build/search_bench/terms_554_snapshot.json`（法定定義語・非PII・コミット）。
- 構造事実: `bib_terms=0`, `bib_records=10,326`, `bib_toc=555,887`（Supabase `nixfjmwxmgugiiuqfuym`, read-only SELECT）。

## 3. クエリ表現（A層・生成のみ・推定なし）
- 単位 = 実相談1件（230件全件。top-N で隠さない）。
- `matter_type_from_name` = `Name` を「＿/_」で分割した**最終セグメント**（依頼者prefixを除去）。区切り無は `no_delimiter`。
- 末尾の intake channel カッコ（法テラス/京都弁護士会/当番弁護/国選弁護/遺言・相続センター/ひまわりほっとダイヤル 等）を
  **matter・概要の双方からマッチ前に除去**（「（京都弁護士会）」→語『弁護士会』のような経路ノイズの誤計上を防ぐ）。
- `query_text_private` = matter ＋ 事案概要（計算用・非コミット）。
- 正規化: `original / NFC / match(NFKC＋空白記号除去)`。保存・表示は original/NFC、マッチのみ match 空間。

## 4. 観測指標（B層・仮説を置かない）
**指標A term presence** — 554 term が query_text に部分文字列として実在するか。一枚岩にせず4区分:
- `non_stop_term_hit`（本体到達候補）/ `stoplist_only_hit` / `short_term_hit`（≤2字）/ `compound_embedded_hit`（長い既マッチ語に内包）
- 各 match に `match_field(matter_type|case_outline|both) / start_pos / end_pos / context_window / match_type` を付与（owner 目視用）。
- stoplist 2本立て: `manual_stoplist`（会社/株式/請求/手続… 高頻度低弁別）＋ `data_driven_stoplist`（230件中 出現率>10%）。目的は除外でなく**本体とノイズの分離**。

**指標B book_reach_via_terms** — `bib_terms=0` → 語彙経由の蔵書到達は**構造的に全件0**（失敗でなく before 基準）。

**指標C raw full-text probe（参考・語彙橋ではない）** — matter フレーズで `bib_toc`/`bib_records` を ILIKE。
出力名は必ず `raw_toc_probe_hit_count / raw_record_probe_hit_count`（`book_reach` と混同しない）。汎用フレーズ（法律相談/企業法務）は除外。

**結果分類 failure_or_outcome_class**: `non_stop_term_hit / stoplist_only_hit / raw_probe_hit_but_no_term_hit /
no_term_no_raw_probe / noise_record`。特に `raw_probe_hit_but_no_term_hit` ＝蔵書側に材料があるのに語彙橋が無い＝bib_terms 投入の最優先領域。

## 5. PII ガードレール
- 依頼者名・電話・メール・住所をコミット対象に出さない。`*_report_safe` は PII 検出時 `[PIIのため表示抑制]`、区切り無 matter は `[区切り無・表示抑制]`（保守的・過剰抑制側）。
- 非コミット（`.gitignore`）: `consultations_raw.json` / `*private*` / `*raw*` / `*probe*`。
- read-only のみ。DB 書き込み無し。

## 6. 禁止事項（Stage1 で作らない）
相談ごとの「正解分野/引くべき本・条文・用語」、Claude による要約・法律構成推定・検索クエリ拡張、gold 本体。
**成果物に `expected_* / target_* / should_reach_* / relevant_* / gold_*` 等の非空列・見出しが出たら失敗**（スクリプトが自己検査）。
gold は Stage2 で owner が監修する（`owner_review_scaffold_*.md` は空欄台紙のみ）。

## 7. 再現
```
# 1) SF 取得（private）
sf data query --target-org alo-prod \
  --query "SELECT Id, Name, leala__CaseOutline__c, ALO_Inferred_CaseCategory__c FROM leala__Consultation__c" \
  --json > ~/alo-ai/work/searchbench_a1/consultations_raw.json
# 2) 語彙/構造スナップショット = build/search_bench/terms_554_snapshot.json（MCP SELECT 由来）
# 3) 指標C = build/search_bench/raw_probe_results.json（MCP ILIKE 由来、phrase→{toc_hits,record_hits}）
# 4) 観測実行（冪等・決定的）
python3 docs/search_bench/measure_consultation_reach.py --asof 20260605
```
冪等・決定的（乱数/実行時日付不使用、基準日は `--asof`）。再実行で `a1_summary.json` は同一。
