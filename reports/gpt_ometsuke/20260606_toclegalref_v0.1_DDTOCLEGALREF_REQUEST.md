---
request_id: 20260606_toclegalref_v0.1_DDTOCLEGALREF
topic: toclegalref
gate: DDTOCLEGALREF
source_hash: sha256:15f3025b29619e60330d05738e51147a692f9f8651b919f4bf23b7c21ff45ff1
supersedes: null
result_expected_filename: 20260606_toclegalref_v0.1_DDTOCLEGALREF_RESULT.md
status: draft   # ← まだ queued ではない。Box to_gpt/ には未配置（owner 承認後に配置）
---

# ⚠ DRAFT — まだ投函していません（リポジトリ内ステージのみ）

この REQUEST は **Project-codex リポジトリ内に用意した投函レディ草案**です。
Box `handoffs/gpt_ometsuke/to_gpt/` には**配置していません**。投函は owner 承認後。

## 投函前チェックリスト（PROTOCOL v0.2 準拠）
- [ ] 親 **DD-LAWTIME-001 が accepted**（本 DD は depends_on。親未accept での投函は順序違反）
- [ ] **現物を Box `docs/alo/` にアップロード**（`DD-TOCLEGALREF_draft_v0.1.md`）。DDCASESOURCE は現物 Box 不在で blocked になった → 同じ轍を踏まない
- [ ] `source_hash` を Box 上の現物の実 sha256 と一致させる（現値 = 本リポジトリ版の sha256）
- [ ] `to_gpt/` に同一 topic+gate の REQUEST が無いか確認（重複投函禁止）
- [ ] front-matter `status: draft → queued` に変更し、現物を本文に同梱して `to_gpt/` へ配置

---

# REQUEST: DD-TOCLEGALREF-001 GPT Pro お目付け役レビュー

- request_type: 規範新設(T2)方向性レビュー＋設計監査（accept 前クロスレビュー）
- gate: **DDTOCLEGALREF** / 結果先頭行ラベル: `DDTOCLEGALREF_PASS / DDTOCLEGALREF_PASS_WITH_NOTES / DDTOCLEGALREF_MODIFY_REQUIRED / DDTOCLEGALREF_FAIL / DDTOCLEGALREF_NEED_MORE`
- requested_verdict: ① bib_toc 由来の文献→条文/判例参照を**既存 alo_edges に供給する方向**（新スキーマを作らない）が妥当か ② edge_type/assertion_mode/weight/evidence の写像が link layer 仕様に過不足なく適合しているか ③ accept 可否＋必須修正

## 決定の要旨
`biblio.bib_toc`（bencom-library, 552,544 ノード／条文参照 10,211・判例参照 2,042）から条文・判例参照をルール抽出し、**新スキーマを作らず**既存 `alo_edges` に
**文献(commentary)→条文(statute)=`interprets`** ／ **文献→判例(case)=`evaluates`** として供給する。`assertion_mode=vendor_implicit`、`assertion_confidence=NULL`（llm専用）、確信度 tier→`weight`(high1.0/med0.7, low除外)、Gate-5 evidence 必須、NFC URI。判例は事件番号欠落で canonical case URI 不能 → `needs_case_uri` 解決候補として保留。

## 番頭/producer の自己申告（独立検証してほしい）
- A: 文献→条文を `interprets`、文献→判例を `evaluates` に写像（35_link_layer §2.2/§6）。この選択が妥当か（`compares`/`review_chain` の方が適切な層があるか）。
- B: tier を `weight` に載せ `assertion_confidence` を NULL にした（同列は llm_inferred 専用制約）。この回避が設計意図に反しないか。
- C: 判例を edge 化せず解決候補に留めた判断（cases.canonical_uri が事件番号必須）。解決規則（court_code 正規化・元号→西暦・同日複数事件）の盲点。
- D: `bencom-library` を alo_source_priority に priority=50/append/is_canonical=false で登録する提案の妥当性。
- E: as_of=pub_year（年粒度）の proxy が DD-LAWTIME と整合するか。

## 特に問う論点
1. 「新スキーマを作らず alo_edges 供給」の方向是非（既存層への過剰結合 / 文献層 work URI 未解決のまま先行する是非）。
2. precision-first（裸の条番号 ~9,600 ノードを推測補完しない）方針の妥当性。recall を捨てて良いか。
3. low tier 除外（医療法人→医療法 等の複合語誤検出）の境界。medium の供給可否。
4. 依存順序：DD-LAWTIME-001 accept 前に本 DD を進める是非。
5. accept 可否＋ v0.2 で閉じるべき必須修正。

## 現物（queue 時に同梱）
- 本体: `DD-TOCLEGALREF_draft_v0.1.md`（source_hash 上記）
- 参考成果物（Project-codex リポジトリ `out_real/`）: `alo_edges_export.jsonl`(interprets 49) / `alo_edge_evidence_export.jsonl` / `alo_pointers_export.jsonl` / `alo_case_ref_candidates.jsonl`(25) / `alo_edges_export_summary.json`（Gate-5 PASS）/ `legal_link_quality_metrics.csv`

## 出力形式
gpt_review_output（先頭行=5ラベル / status / accepted_now / normal_findings / adversarial_findings / required_patches / final_gate ＋各判断に確度＋反証条件）。原文未取得なら context_sufficiency=partial を明示。
