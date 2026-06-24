---
request_id: 20260615_DD-LITID-001-ATTR_attr_observation_layer
decision_id: DD-LITID-001 追補（属性観測層 + 決定的projection）
request_type: 設計監査 (DESIGN gate)
topic: biblio attribute observation layer / thin-to-thick projection / 採用値の正しさ
作成日: 2026-06-15
監査対象: docs/2026-06-15_dd-litid-001_addendum_attr_observation_layer.md
source_hash: sha256:a1ba62f3d200245fcfb78cc582b5764176caa8cefe22470c26de698985f2afc5
source_commit: d01da92 (branch claude/library-data-reanalysis-7fg7ib)
親設計: DD-LITID-001 v0.2-draft（DESIGN_PASS_WITH_NOTES / Box 2275006797196）
supersedes: null
result_expected_filename: 20260615_DD-LITID-001-ATTR_attr_observation_layer_RESULT.md
status: queued（Box `to_gpt/` 投函済 2026-06-15）
box_review_request_file_id: 2286086385325
box_現物ファイルID: 2286087523073（追補doc現物・同 to_gpt/）
gate: DESIGN。**DDL適用・既存移行・backfill・データ更新・本番書込は対象外。**
---

# GPT Pro お目付け役 監査依頼: DD-LITID-001 追補「属性観測層 + projection」

## 0. 独立監査の要請（迎合不要）

本追補は **DD-LITID-001 v0.2 への査読(同familyのClaude作)→そのClaudeによる設計提案** という経路で生まれた。
**起案者と査読者が同family＝blind spot を共有し独立監査が成立しない。** 前提を疑い、結論ありきの追認を避け、
load-bearing な欠陥を厳しく指摘してほしい。「採用方向でよい」だけの返答は不要。

## 1. 趣旨（何を解こうとしているか）

DD-LITID-001 は **「どう同定するか(identity)」** は厚いが、**「同定後に各ソースの薄い属性を
どう積層して1つの正しい正規値にするか(projection)」** が手薄、という査読指摘(R1〜R10)への設計回答。

owner の基本線（本追補に反映済み）:
- **「厚さ」と「正しさ」を分離**。コーパスが厚いこと自体は価値でない。地層(観測)から
  **出所付きで採用する1つの正規値**が本体。薄くても綺麗な1値が正しければそれでよい。
- **Stage1（綺麗な層別観測DB＋採用値抽出）を先に、Stage2（重み付け関数）を後に**。並行しない。
- **AIが捏造できない構造**: 採用値は必ず実観測に接地（観測なき値は存在不可）。

## 2. 確定済み前提（変更不可・監査の枠）

- DD-LITID-001 v0.2 は採用方向（DESIGN_PASS_WITH_NOTES 済）。本追補はその §5 への**追補**であり置換でない。
- `fingerprints` を同一性解決の横断正本とし二重正本を作らない（前回監査の must_fix）。
- 版を束ねない（DDL-20260428-01）。raw保全（データ落とすな）。購読由来メタの rights gate。
- 本追補の実装(DDL/backfill)は本監査の対象外。**設計の可否のみ**。

## 3. 提案要旨（対象docの要点。詳細は source_hash の現物）

1. TOC の `toc_observations`（多観測→決定的projection）を **scalar/分類属性にも対称適用**:
   新 `biblio_item_attr_observations`（append-only・provenance付き）＋ 決定的 projection で
   **1属性=1採用値（canonical）**。`biblio_item` の scalar 列は観測からの**派生（キャッシュ）**に格下げ。
2. **採用値は必ず obs_id に接地**（`gate_adopted_value_grounded`）＝anti-hallucination。
3. **採用ポリシー**: cardinality=single は priority_profile→recency で1値。**単独権威観測でも採用可**。
   provenance_group 畳み後に値が割れたら **disputed で人手へ**（多数決しない）。
4. **重み(field_confidence)は Stage2 へ繰り延べ**。Stage1 は「値＋出所＋agreement＋conflict」まで。
5. 分類は `attr_scheme`(NDC/NDLC/件名/vendor:*) で**併存**・multi・**work rollup**（R2/R7/R8）。
6. `medium_origin`(digital/paper_scan) を**全観測共通**の出所事実に（R5）。
   `held_by_office`/`shelf_locator`/`fulltext_access`(none|shelf|local_pdf=自炊PDF) を昇格属性に（R9）。
7. 時点(R3): 取得時点(append-only/supersedes)＋主張時点(observed_at)。版valid-timeはitem粒度に委ねる。

## 4. 特に厳しく監査してほしい点（前提を疑え）

1. **第3の正本を作っていないか（最重要）**: `fingerprints`(SoT)・`toc_observations` がある上に
   `biblio_item_attr_observations` を足すのは、前回 must_fix「二重正本を作らない」に反しないか。
   属性観測は既存 observation/fingerprint 基盤に**畳むべき**ではないか。新テーブルが正当化される線引きは。
2. **Stage1/Stage2 分離の罠**: 重み付けを後回しにして観測層を先に作ると、後で Stage2 設計時に
   Stage1スキーマへ手戻りする failure mode はないか。逆に「重みなしの採用値」は本当に意味があるか
   （重み抜きの projection が中途半端な確定をしないか）。**順序自体に地雷**はないか。
3. **単独権威観測での採用は安全か**: 「NDL 1件だけで採用可」は、NDLの誤り（同名異本誤付与・
   分類誤り）をそのまま正しい値として確定するリスクがある。corroboration を必須にしない判断の failure mode は。
4. **disputed の運用破綻**: 「割れたら人手へ」は、出版社表記ゆれ・年/頁の定義差で **disputed が大量発生**し
   人手レビューが詰まらないか。disputed を作りすぎない/自動解消する設計が要らないか。
5. **anti-hallucination 主張の実効性**: 「採用値は観測接地」はDB層の不変条件にすぎず、
   **serving/LLM が誤って引用・合成する**のは別問題ではないか。`gate_adopted_value_grounded` は
   どこで・どう強制すれば実効があるか。正規化値（norm）や derived 値は「観測なき値」に当たり過剰制約にならないか。
6. **provenance_group の運用可能性**: 二重計上回避の全体が「同一供給元の再配信を検出できる」前提に乗る。
   弁コム×legallib の同一出版社TOC/メタを**実際にどう判定**するのか。判定が不確実なら no_double_count は名目倒れでは。
7. **work-rollup の早すぎ問題**: 分類を work層で合議する案は、work_id が candidate/late な段階で
   **誤 work マージが全版の分類を汚染**する。分類は work 確定(promotion)まで item 留めにすべきでは。
8. **scalar の派生化(キャッシュ列)移行**: `biblio_item` scalar を canonical の派生にすると、
   現行 `app/booklib.py`・serving の既存consumerを壊さないか。determinism gate だけで十分か。
9. **rights 漏れ**: 購読由来メタを attr_observations→canonical→serving と流す経路で、
   gated/購読由来値が rights_profile を失って漏れる経路はないか。
10. **過剰設計の疑い**: attr_registry 駆動（attr_key×scheme×cardinality×rollup×priority）は
    一般化しすぎていないか。雑誌/記事(DD-PERIODICAL)・著者名寄せと整合するか、別物に割れないか。

## 5. owner 決定待ち（監査の所見が欲しい項目）

対象doc §9 の7決定（観測層採用／scalar派生化／分類multi・work rollup／重みStage2／自所保有属性／
medium_origin必須／厚さと正しさの分離）。各々への賛否と条件。

## 6. 期待する判定

- `DESIGN_PASS` / `DESIGN_PASS_WITH_NOTES` / `MODIFY_REQUIRED` / `HOLD`

## 7. 返答フォーマット

```text
status: DESIGN_PASS | DESIGN_PASS_WITH_NOTES | MODIFY_REQUIRED | HOLD

verdict_summary:

accepted_now:
- 属性観測層(attr_observations)＋projection:
- 厚さ/正しさ分離・採用値=観測接地:
- Stage1先行/Stage2重み後回し:
- 分類 multi・work rollup・NDCピボット:
- medium_origin / 自所保有属性:

adversarial_findings:        # §4の各点に対する独立批判（迎合不要）
- 二重正本リスク:
- Stage順序の罠:
- 単独権威採用の危険:
- disputed運用破綻:
- anti-hallucination実効性:
- provenance_group運用可能性:
- work-rollup早すぎ:
- scalar派生化の移行安全:
- rights漏れ:
- 過剰設計:

must_fix:
should_fix:
risks:

gate_decisions:              # 提案ゲートの妥当性
- gate_adopted_value_grounded:
- gate_attr_obs_append_only:
- gate_attr_projection_deterministic:
- gate_provenance_group_no_double_count:
- gate_attr_conflict_surfaced:
- gate_no_scalar_second_sot:

owner_decisions:             # §9の7決定への所見
- ...

open_questions:
recommended_next_steps:
final_gate: PASS | PASS_WITH_NOTES | MODIFY_REQUIRED | HOLD | FAIL
```

## 8. 監査上の注意（本パックで許可されないこと）

production DB変更／DDL適用／backfill／canonical promotion／自動accepted化／embedding投入／
外部公開・頒布／本文再配布 ── いずれも本監査では許可しない。本件は**設計可否のみ**。

## 9. banto 自己申告

- 本件は設計提案・監査依頼のみ。DB/スキーマ/既存データ/TOC/OCR/embedding は変更していない。
- 対象docは Claude（リモート）が DD-LITID-001 v0.2 を査読し、その指摘に自ら回答する形で起案した。
  **起案と査読が同family**であることを明示し、独立監査を依頼する（§0）。
- 実装(DDL/backfill)は本依頼の射程外。観測層は append-only 設計ゆえ既存破壊を意図しない。
- ライブ実測の根拠: biblio に現在 asai-bookshelf(ndc 5,503/ndlc 5,020)＋bencom 3,802 のみ投入、
  LION BOLT/legallib 未投入（=同定前）。これは設計根拠であり、移行ゲートでは再実測が必要。
