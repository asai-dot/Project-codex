# drafterintent — 立法担当者解説コネクタ（DD-LAWSUBTRANS-001 Phase 3 producer）

逐条解説・一問一答・立案担当者解説・所管庁資料・国会審議録から、**条文に対する
「実質変更の有無に関する立案者の主張」**を抽出し、**tier-2 の substantive_change_assertion
candidate（T2）＋ evidence pointer（T5）**として出力する。

```
python -m scripts.drafterintent TEXTFILE --doc-id <id> \
    [--source-hint 一問一答|逐条解説|国会審議|通達] \
    [--law-work-id W] [--locator p.123] [--source-uri URI] --out out/
```

出力: `out/drafter_evidence_<run>.jsonl`（T5）＋ `out/drafter_substantive_assertions_<run>.jsonl`（T2）
＋ gate 結果付き summary。**DB書込みゼロ。**

## 設計原則（DD §2.4 / §4 / §5、監査 PASS_WITH_NOTES 反映）

- **立法担当者意図は説得的だが拘束力なし**（調査: 日本では判例は立法担当者解説に通常言及
  しないが、立法意図を一問一答・逐条解説に求めうる。判例・学説とは別クラス）。
  → 全行 `source_tier=2`、**tier 1（official_legal_data＝官報/改正法令）は出さない**（それは
  DD-LAWTIME の管轄。gate `gate_drafter_source_tier_2`）。
- **accepted へ自動昇格しない**: 全行 `assertion_status='candidate'`、`claim_support_eligible=False`、
  確度は **medium 上限**（high 禁止）。accepted 化は curator/review-event の仕事（DD T6 ＋ gate
  `accepted_requires_review_event`）。立案担当者解説が「実質変更なし」と言っても、判例・学説が
  反対しうる（DD gate `drafter_intent_not_sole_truth`）ため、ここでは候補に留める。
- **解説テキストが何を述べたかだけを根拠にする**（DD ingest no-auto-generation policy）。
  改正の存在や textual_delta だけからは何も生成しない。cue が無ければ assertion を作らない
  （gate `gate_drafter_change_requires_cue`）。
- **citator 流儀**: 自分の声で意味変化を断じない。出典スパン（`quoted_text`＋`source_span_hash`）を
  必ず携行（gate `gate_drafter_assertion_has_evidence`）。

## 抽出設計

1. **条文参照パーサ**: `[改正後の|改正前の|新|旧|現行][法令名]第N条[第N項][第N号]`、枝番
   「第三条の二」→ `art:3-2`。**漢数字・全角数字を arabic に正規化**（`kanji_to_int`、千百十対応）。
   path は lawdelta / DD-LAWTIME と同じ `art:709` / `art:415:para:2:item:1` 形式。
   新旧マーカーから `revision_side`（before/after/current）を hint 化（lawname が「旧民法」を
   飲み込む場合も prefix 全体を見て判定）。
2. **source_type 推論**: 国会/審議/答弁→`legislative_record`、通達/所管庁/ガイドライン→
   `ministry_commentary`、それ以外（一問一答/逐条解説/部会資料）→`legislative_drafter`。全 tier 2。
3. **窓**: 参照を含む文＋次の1文。cue は**同一文を優先**し、なければ次文。
4. **cue → change_type**（precision-first、DD §2.1 語彙）:
   - 「実質的な変更はない」「従来の取扱いを変更するものではない」「確認的に規定」→ **no_substantive_change**（`confirmatory=True`）
   - 「明確化」「明文化」「文言を整理」→ **wording_clarification**
   - 「新たに〜を要件とした」「要件を加え」→ **requirement_added** ／「要しないこととした」→ **requirement_removed**
   - 「効果/効力を改め」→ **effect_changed** ／「対象を拡大」→ **scope_expansion** ／「対象を限定」→ **scope_reduction**
   - 「規律を改め」「取扱いを変更するものである」→ **substantive_change_unspecified**
   - 「創設的な規定」「新たに設けた/規定」→ **substantive_change_unspecified**（`confirmatory=False`）
   - cue なし（単なる言及）→ **assertion を作らない**
   - **確認的(=既存法の宣言、変更なし) vs 創設的(=新法の創設)** の日本の起案概念を `confirmatory`
     フラグで保持。
5. **確度方針**: ルール抽出は medium 上限（Paxton 流の per-pattern 精度測定を可能にするため
   `pattern_id` を携行）。high 昇格は review-event の仕事。

## gates

`gate_drafter_all_candidate_status` / `gate_drafter_no_claim_support` /
`gate_drafter_source_tier_2`（tier1=官報系を出さない）/ `gate_drafter_change_type_domain` /
`gate_drafter_assertion_has_evidence` / `gate_drafter_change_requires_cue` /
`gate_no_high_confidence_from_rules` / `gate_drafter_assertion_has_article_path`

## 下流接続（DD §6 Phase 4 へ）

本 producer の T2 candidate は、Phase 4（判例・学説による評価）の `counter_assertion` 候補と
突き合わせて **dispute** を形成する。例: 立案担当者「実質変更なし(no_substantive_change)」 ⇄
学説「要件変更(requirement_changed)」 → `disputed` → claim_support 不可（DD gate）。
canonical work URI 解決（lawtime/30_law_layer）が付くまで law_work_id は NULL 可（candidate のまま）。

## 制約

- 解説本文の入力前提（PDF/HTML からの本文抽出は別段。raw 保持は ALO 編成指針 L0 の役割）。
- 確度・cue は fixture 検証値。実解説コーパスでの precision 測定と閾値確定は production gate（DD §7）。
