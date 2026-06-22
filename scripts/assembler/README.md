# assembler — dispute 形成器（DD-LAWSUBTRANS-001 中核オーケストレータ）

3 producer（`drafterintent`=tier-2立案担当者、`casetreatment`/学説=tier-3判例・tier-4学説）の
出力を束ね、**同一条文に対する主張の衝突を検出して dispute を構成**する。DDの中核思想
（立法担当者意図を重く扱うが絶対視しない／真として自動確定しない）を実際に動かす部品。

```
python -m scripts.assembler --run-id RUN --out out/ \
    --drafter out/drafter_substantive_assertions_*.jsonl \
    --interpretation court_scholar_interpretation.jsonl \
    [--treatment out/case_treatment_candidates_*.jsonl --bindings bindings.json]
```

出力（すべて JSONL＋summary、**DB書込みゼロ**）:
- `resolved_assertions_<run>.jsonl` — 各 assertion ＋ assembler 算出の `current_status` /
  `counter_assertion_id` / `dispute_id` / `claim_support_eligible`
- `assertion_review_events_<run>.jsonl` — **append-only T6**（dispute 処分を `review_basis` 付きで記録）
- `disputes_<run>.jsonl` — dispute グループ（target / 継続側 / 変化側 / tiers / basis）

## stance 射影（衝突検出の核）

各 assertion を「その条文の**意味・法理は継続したか/変わったか**」の粗い stance に射影:

| stance | 由来（DD §2.1/§2.2/§2.6） |
|---|---|
| `continues` | no_substantive_change / wording_clarification ／ interpretation_continues ／ followed/applied/approved/relied_upon |
| `changed` | scope_*/requirement_*/effect_changed/… / substantive_change_unspecified ／ interpretation_discontinued/newly_established ／ overruled/abrogated/disapproved/**superseded_by_statute** |
| `qualified` | interpretation_modified ／ distinguished/limited/questioned/criticized/called_into_doubt/… |
| `neutral` | cited/considered/explained |
| `disputed` | change_type/transition_type が自己申告 disputed |

## dispute 形成規則

- **グループ化**: 条 root（`art:415:para:1` → `art:415`）。`law_work_id` がある場合は将来 strict 化。
- **成立条件**: 同一グループに **継続側（continues）と 変化側（changed/qualified/disputed）が両方存在**。
  片側のみ・neutral のみ・自己申告 disputed 単独では dispute を作らない（gate `dispute_two_sided`）。
- **処分**: 衝突メンバは `current_status='disputed'`、相互に `counter_assertion_id`、
  **append-only review-event**（`decided_by=assembler`、`review_basis` に
  「T2:legislative_drafter:no_substantive_change vs T3:court:interpretation_discontinued」等の
  機械可読理由＝Wikidata P2241/P7452 相当）。
- **勝者を選ばない**: tier で自動決着しない（DD §2.4。立法担当者意図は説得的だが拘束力なし、
  判例は適用上の解釈、学説は評価——どれも自動で truth にしない）。`counter_assertion_id` は
  単一FK制約のための代表ポインタにすぎず、全体像は dispute グループが持つ。
- **claim_support は決して付与しない**: 全 assertion `claim_support_eligible=False`。accepted 化は
  人手 review-event（`review_basis` 必須）の専権（gate `assembler_never_accepts` /
  `accepted_requires_review_event`）。

## gates（DD §4）

`gate_disputed_blocks_claim`（counter あり ⇒ claim_support false ∧ status disputed）/
`gate_claim_support_requires_accepted`（accepted ∧ counter なし ∧ lawtime_resolved のときだけ true 可）/
`gate_assembler_never_accepts` / `gate_no_self_counter` / `gate_dispute_two_sided` /
`gate_review_event_has_basis` / `gate_disputed_has_dispute_and_counter`

## E2E（fixture デモ）

`drafterintent`（一問一答）→ assembler に court/scholar 解釈を合流させると:

```
art:415  T2 立案担当者: no_substantive_change (continues)
         T3 裁判所:     interpretation_discontinued (changed)
         T4 学説:       interpretation_modified (qualified)
   => dispute。全員 disputed、claim_support=false、勝者なし。
```

これは GPT 議論 §8 の「OK 出力」（形式的には改正、立案担当者解説は変更なしと説明、文献は要件変更と
評価、裁判例は旧枠組みを参照 → reviewed candidate として扱う）の機械化である。Phase 5（MCP 出口）は
この `disputes_*.jsonl` + `resolved_assertions_*.jsonl` を**両論併記**でレンダリングするだけでよい。

## casetreatment との接続（bindings）

`casetreatment` は判例→判例の treatment が中心なので、ある treatment を**条文/法理の target に束ねる**
curator binding（`{dedup_key: {article_path, law_work_id?, doctrine_label?}}`）を与えたときだけ
provision-level の interpretation assertion になる。未束ねの treatment は assembler に渡さない
（過剰生成を避ける。canonical case/work URI 解決後に束ねる運用）。

## 制約

- グループ化は条 root の v0.1 ヒューリスティック。項・号粒度や law_work 跨ぎの厳密化は次版。
- stance 射影は粗い二項対立への単純化。「新設だが法理は継続」のような両立ケースも現状は dispute として
  surface する（**見落とすより人手レビューに上げる**安全側）。確度・閾値の較正は production gate。
