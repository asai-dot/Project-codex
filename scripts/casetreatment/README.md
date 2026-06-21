# casetreatment — 判例引用 treatment 候補抽出器（DD-LAWSUBTRANS-001 Phase 4 producer）

日本語の判決文・文献テキストから判例引用を検出し、その**扱い（treatment relation,
DD §2.6 citator 統制語彙）**を定型句ルールで分類して **candidate として**出力する。

```
python -m scripts.casetreatment TEXTFILE --doc-id <id> \
    [--source-type court|scholar|treatise|practitioner] --out out/
```

出力: `out/case_treatment_candidates_<run>.jsonl` ＋ gate 結果付き summary。**DB書込みゼロ。**

## citator の教訓（設計の根拠）

- **citator は自分の声で「この判例は死んだ」と言わない**。treating authority が何を
  したかを、帰属＋抜粋付きで報告する（Shepard's/KeyCite/BCite 共通）。本抽出器も
  `quoted_text`（評価窓の原文）＋ `span` ＋ `pattern_id` を必ず携行する。
- **Hellyer (Law Libr. J. 110:449, 2018)**: 編集者付き商用 citator 3社でも negative
  treatment の判定一致は **15%**。→ 全行 `assertion_status='candidate'`、
  `claim_support_eligible=false` 固定（gate で強制）。
- **LEXA (Galgani+, 2015)**: 手作りルール72本が ML 基線を上回った。**ルール先行**は
  この分野の実証された定石。NN/LLM 系も treatment 細分類は 67–79% 止まり
  （Demir & Canbaz, NLLP@EMNLP 2025）。
- **KeyCite 特許群** (US 8,145,675 等) も中核は **cue 動詞＋近接規則**＋編集確認。
  Casetext SmartCite は Bluebook 逆接 signal（but see 等）を高精度 cue に使った。
  本実装の「定型句→candidate→curator 昇格」はこの業界標準の写し。

## 抽出設計

1. **引用文法**（precision-first 正規表現）: 裁判所トークン（フル形「最高裁…大法廷
   判決」／融合略記「最判/最大決/東京高判」）＋元号日付＋(法廷)＋(判決/決定)＋
   (判例集 巻号頁)。**裸の「裁判所＋日付」は引用と認めない**（dispo か reporter か
   融合略記が必要）。事件番号（令和N年(受)第N号）は窓内から併取。
   ※米国系では Free Law Project **eyecite** が同役（5,000万引用で検証）。
2. **評価窓**: 引用を含む文＋次の1文。**cue は引用と同一文を優先**し、なければ次文
   （Zhang & Koppaka ICAIL 2007 / Sadeghian AI&Law 2018 の sentence-level 規律）。
3. **cue→treatment**（主要定型句、最高裁起案定型に基づく）:
   - 「事案を異にし（本件に適切でない）」「趣旨を判示したものではない」→ **distinguished**
   - 「と同旨」「の趣旨に徴し/照らし」「当裁判所の判例とするところ」→ **followed**
   - 「（判例を）変更すべき」「抵触する限度で…変更」→ **overruled**
     （判例変更は大法廷専権＝裁判所法10条3号。法廷情報は手続アンカーとして citation に保持）
   - 「法改正により…前提を欠く/妥当しない」→ **superseded_by_statute**（citator 同様に隔離カテゴリ）
   - 「と相反する判断」「判例違反」→ **called_into_doubt**（low）
   - 「射程外」「限定的に解す」→ **limited** ／ 文献系「批判が強い」→ **criticized**
   - cue なし（「参照」含む）→ **cited**（中立 default。citator の neutral と同じ）
4. **当事者主張の抑制**: 「所論は…」「上告理由」「論旨は」の窓で 相反/変更 系 cue が
   出た場合、それは**主張の叙述であって裁判所の treatment ではない**ため `cited` に
   降格（`pattern_id` に `+argued_party_suppressed` を残す）。
5. **確度方針**: ルール抽出は **medium が上限**（`gate_no_high_confidence_from_rules`）。
   high への昇格は curator/review-event（DD T6）の仕事。Paxton AI citator の
   「per-label P/R を公開する」透明性モデルに倣い、pattern_id 単位で精度を測れる形にしてある。

## gates

`gate_treatment_all_candidate_status` / `gate_treatment_no_claim_support` /
`gate_treatment_domain` / `gate_treatment_has_evidence_span` /
`gate_strong_treatment_requires_cue`（overruled 等は明示 cue 必須）/
`gate_no_high_confidence_from_rules`

## 制約・次段

- 日本語の判例 treatment 自動抽出は**公開研究の空白領域**（調査でも直接の先行なし）。
  本実装は precision-first の最小核。recall 拡張（ML/LLM）は**ルール層の上に**載せる。
- 引用先の canonical case URI 解決（31_case_layer 事件番号解決）は別タスク。それまで
  edge 化しない（DD-TOCLEGALREF と同じ遮断）。
- 法務省 民事判決情報データベース（2026年度運用開始予定、年約20万件）が将来の基盤。
