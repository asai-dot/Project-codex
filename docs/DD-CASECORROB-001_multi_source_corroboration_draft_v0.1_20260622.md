# DD-CASECORROB-001 — 多源コロボレーション（独立源の一致で精度を上げる）**draft v0.1**

- 起票: 2026-06-22 JST ／ 番頭: Claude Code (remote)
- lifecycle: **draft / candidate**（GPT Pro 独立監査 未了 → DDCASE ゲート）
- domain: CASE（判例精度・③多源コロボ）
- parent: `DD-CASE-001`(accepted v1.0, merge禁止/edge) / `DD-CASEID-001`(accepted v1.0, 35層 fingerprints/external_ids)
- related: `DD-CASEEVAL-001`(計測) / `DD-CASEBIND-001`(②ガード・G3拡張) / `DD-CASE reality_check`(D1-LIC 5,475 / OPAC accepted edge 0)
- 実装: `scripts/case_corroborate.py` / `scripts/test_case_corroborate.py`

> **目的**: 独立源の一致で confidence を上げ、不一致を review に出す。**源の種類で効かせ方を分離**し、**コロボは決して merge を生まない**（CASE-001 AN-2: 関係は edge）。`DD-CASEEVAL` の precision を、誤統合を増やさずに底上げする打ち手。**設計のみ・read-only**。

---

## 0. スコープと原則
reality_check の確定（**「LIC data_no を canonical case にしてはならない」「OPAC accepted edge 0」**）を厳守。コロボレーションは **confidence 付与と review 振り分け**に限り、canonical 昇格・auto-merge はしない（HOLD）。

## 1. 決定 — 源の種類で3層に分離

| 層 | 源の例 | link_type | 効かせ方 |
|---|---|---|---|
| **L1 identity** | 判例DB間（D1-Law / NII / 最高裁HP / 下級裁HP …）の自然キー一致 | `caselaw_same_case` | **同一性の補強**。独立判例源が ≥2 一致＝`multi_source_agree`。採番が割れていれば **`conflict_review`**（false split か crosswalk 誤りの疑い）。**merge はしない**（②G1 を尊重、forum跨ぎは特に） |
| **L2 annotation** | D1-LIC crosswalk（解説誌→事件、resolved 5,475） | `literature_about_case` | **要旨/評釈 source の補強**＝`annotation_corroboration`。case_annotation candidate を attach（canonical 化は別ゲート）。**識別ではない** |
| **L3 relation** | OPAC/CiNii 引用（事件→事件、accepted edge 0） | `case_cites_case` | **関係 edge 候補**＝`relationship_edge_candidate`（review-first）。同一 case_key なら `self_citation_anomaly`。**merge はしない** |

- **identity confidence**: `distinct_caselaw_sources` の数で `multi_source_agree / single_source / non_caselaw_only`。②ガードの Tier B review の **優先度付け**に使う（合意が多い候補を先に人手確認）。
- **conflict は宝**: `caselaw_same_case` 主張に対し採番が割れている＝**取りこぼし（false split）検出**の信号。review に出して recall を後追いで回収（precision を落とさずに）。
- **未知 link_type は fail-closed**。

## 2. DD-CASEEVAL / DD-CASEBIND との結線
- ②ガードは false_merge=0 を保証するが **recall を犠牲**にする（split寄り）。③コロボは **その犠牲を review 経由で安全に回収**する装置：`conflict_review`＝「同一の可能性が高いのに割れている」候補を人手へ。
- コロボは `assignment` を**書き換えない**（test で merge 不発生を確認）。precision を守ったまま recall 改善の“当たり”を作る。
- 効果計測は `DD-CASEEVAL`：実 gold で「コロボ由来 review を反映後の recall 改善」と「false_merge_rate 不変（=0 維持）」を測る。

## 3. why / alternatives_rejected
- **why 源種別で分離**: 解説誌 crosswalk（L2）や引用（L3）を identity（L1）と混ぜると、「事件に言及」を「同一事件」と誤読し false-merge を生む（reality_check の禁止事項）。種別を分けて **L2/L3 は永久に非merge** とする。
- **rejected**: crosswalk を identity key 化（reality_check 禁止＝却下）。引用を accepted edge に直昇格（OPAC accepted 0・review-first＝却下）。多源一致で auto-merge（②G1 を破る＝却下、confidence 付与に留める）。

## 4. verification（現状）
- deterministic_self_verification = **fixture-level done**: `test_case_corroborate.py` green（exit 0）。L1/L2/L3 分離・`conflict_review` 検出・**コロボが merge を生まない**ことを確認。
- corpus-level = **Mac CC**（D1-LIC 5,475 / OPAC 1,648 worksheet を実 link 化、`DD-CASEEVAL` で recall改善 vs false_merge を計測）。
- independent_meaning_audit = **未了**（DDCASE ゲートへ）。owner_approval = 未了。

## 5. follow-up
- ②G3 を source 横断へ強化（同一 case_key の外部ID合意を identity confidence に反映）。
- L2 annotation candidate の canonical 選択（`is_canonical` 源優先）＝④/L2 eval へ。
- L3 edge 候補の review-first lane（OPAC P1 1,648）と接続、accepted edge gate。
- conflict_review の処理優先度を identity confidence で決める運用。
