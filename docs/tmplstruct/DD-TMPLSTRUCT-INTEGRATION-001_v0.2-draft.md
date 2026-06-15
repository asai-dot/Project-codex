# DD-TMPLSTRUCT-INTEGRATION-001 v0.2: 書式構造2系統の統合（監査 DDTMPLINTEG_PASS_WITH_NOTES 反映）

> **id**: DD-TMPLSTRUCT-INTEGRATION-001 / **version**: v0.2-draft / **supersedes**: v0.1-draft（監査参照点として凍結保持）
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / date: 2026-06-15
> **gate**: 設計のみ（DDL・DB書込み・SF write・MCP公開・accepted化なし）
> **改訂理由**: GPT監査 `DDTMPLINTEG_PASS_WITH_NOTES`（2026-06-13）の必須修正 N1–N5 を反映。owner ratify 済（2026-06-15）。
> **役割**: 本DDは **上位調停層（stack contract）**。MEANING-001（L1-L3 層別仕様）と FORMOBJ-001 v1.1（L4 層別仕様）を**即時 supersede せず**併存させる。統合DD v1.0 の canonical 化は L2-L4 が安定してから。

---

## 0. 結論（監査確定）

2系統は**重複ではなく相補**。統合形は **L1–L4 の単一スタック**。
```text
MEANING-001 = L1/L2/L3 の背骨
  L1 form observation / restorable profile（不変）
  L2 controlled vocabulary / clause_type / semantic_type / anchor（seed→accepted）
  L3 semantic overlay / concept_uri / sf_binding / relations（版管理）
FORMOBJ-001 = L4 design knowledge
  L4 clause_design_knowledge / baseline / push-pull / favors_role / grounded_from
```
- FORMOBJ P3 を MEANING L3 に**潰し込まない**。**L4 独立層**として分離（監査Q1=PASS）。
- 接合キーは独自語彙でなく **shared_term_registry の L2 term_id を参照**（fork禁止）。
- **HOLD継続**：DDL / DB canonical write / SF write / MCP publication / concept_uri accepted化 / L4 accepted化 / 自動legal-effect確定。

## 1. 層モデルの対応（P-model ↔ L-model）

| 統合層 | 内容 | FORMOBJ | MEANING | 調停 |
|---|---|---|---|---|
| **L1 形式** | 観察事実。document_hash で不変 | P1＝snapshot/canonical（L1製造工程） | L1 form（restorable_profile_v0.2.1） | L1を正本。FORMOBJ S2/S3 は L1 を生成する製造工程 |
| **L2 型** | 統制語彙。seed→candidate→accepted | P2 の function暫定タグ＝`seed` | L2 schema（clause_type/semantic_type、anchor、status） | L2を正本。FORMOBJ「暫定タグ」＝MEANING `seed` |
| **L3 束縛overlay** | concept_uri/sf_binding/legal_effect/relations | （無し） | L3 semantic overlay | MEANING L3 をそのまま採用 |
| **L4 設計知識** ★ | baseline＋押し引き＋favors_role、解説接地 | **P3→L4** | （legal_effectを空けていた領域） | FORMOBJ を L4 として新設。L2 term_id をキーに接続 |

**L3 と L4 の責務分離（監査Q1）**：
- **L3＝外延的束縛**（slot/term を concept_uri・sf_binding・relation・legal_effect候補へ接続）。
- **L4＝内包的設計知識**（なぜその条項か・どう締めるか・どちらに有利か・どの解説に根拠があるか）。
- 同じテーブル/同じ status で混ぜると SF field binding と契約条項の規範的判断が混線する。ゆえに **L4 独立層**。

## 2. 接合キー：L4 は L2 term_id を参照（N1）

旧 v0.1 の「`clause_function ≡ clause_type`（完全同義）」は実装上**強すぎる**ため撤回。

```text
N1 修正後:
  L4 clause_function は L2 canonical term_id を参照しなければならない。
  L4 は当該 term_id に scope された design_knowledge_profile を追加してよい。
  L4 は別語彙の名前空間を作ってはならない（fork禁止）。
```
粒度差は L4 側のフィールドで吸収（監査Q2）:
```text
design_knowledge:
  term_id                  # L2 canonical term
  design_scope             # clause | clause_family | option_axis | party_role | procedure_form
  applies_to_document_type
  applies_to_party_role
  narrower_term_ref        # 必要時のみ。別語彙でなく registry 内の下位term
```
例: L2 `payment` に対し、L4 で `payment_timing` / `late_payment_interest` / `setoff` / `withholding` を下位・局面として扱える。

## 3. 検証思想：共通framework・目的分離（N2）

L2接地と L4接地は同じ「接地」ファミリーだが**同一metricで扱わない**。

```text
L2 anchor authority:  term/concept の恒等性を支える接地
  例: e-Gov定義条 / alo-kg definition_article / JLT対訳 / 辞書項目
L4 grounded_from:     normative/design knowledge を支える接地
  例: 解説書 / 条項例解説 / 実務本 / 法令趣旨 / 判例 / 一問一答
```
共通の evidence object は持ってよいが `evidence_purpose` を分ける:
```text
evidence_purpose:
  identity_anchor      # L2用。term/conceptの恒等性
  design_rationale     # L4用。なぜその条項か
  legal_basis          # 法令・判例根拠
  drafting_guidance    # 書き方・条項例
  observed_variation   # 書式観測。仮説生成のみ（accepted化しない）
```
→ 共通テーブル/共通構造は可、**同一gate値化は不可**。

## 4. L4 status 規律（N3）

L4 にも `seed/candidate/accepted/deprecated` を課す（MEANING L2 昇格規律と整合）。ただし `source_diversity ≥ 2` **だけでは弱い**。
```text
L4 seed:      1書式/1抽出の観察。助言に使わない
L4 candidate: grounded_from あり（解説/実務書≥1）。owner未確定。単一書籍はここ止まり
L4 accepted:  grounded_from あり＋source独立性確認＋未解決矛盾なし＋scope明示＋owner/reviewer ratify
L4 deprecated: 法改正・新解説・owner判断・より良い知識で更新
```
**L2参照品質の連動（N5）**：L4 は seed/candidate の L2 term を参照してよいが、**L4 が accepted になるには、参照先 L2 term が最低 candidate かつ label-cohesion / anchor-quality レビュー通過**（または owner override の明示）。

## 5. ガバナンス：上位調停層として併存（N4）

即時 supersede は早い（理由: MEANING は独自論点を持ち design PASS 済／FORMOBJ は L4 領域を持つ／SEED_IMPL が REVISION_REQUIRED でL2 anchor品質が未安定／即統合canonical化は未安定部まで巻き込む）。
```text
DD-TMPLSTRUCT-INTEGRATION-001 : upper arbitration / stack contract（本DD）
DD-TMPLSTRUCT-MEANING-001     : layer spec for L1-L3
DD-FORMOBJ-001 v1.1          : layer spec for L4（用語patch済）
```
将来 L2/L3/L4 が十分安定したら、統合DD v1.0 を canonical とし下位DDを reference archive に移す。

## 6. SEED_IMPL REVISION_REQUIRED を前提条件に取り込む（N5）

MEANING SEED 監査の指摘は L4 の term 参照品質に影響するため無視しない:
- `inline_iu` を正式 anchor-rate gate から除外（authoritative_anchor と weak_observation_anchor を分離）。
- `ja_labels` の凝集性（synonym のみ。related/example/party/event を別フィールドへ）。
- → これらが未解決の L2 term を L4 accepted の参照先にしない。

## 7. 必須修正 notes 反映状況

| note | 内容 | 反映 |
|---|---|---|
| N1 | `≡` を「L4→L2 term_id 参照」に緩める | §2（＋FORMOBJ v1.1 §2.3） |
| N2 | L2接地とL4接地を purpose 分離 | §3（＋FORMOBJ v1.1 grounded_from.evidence_purpose） |
| N3 | L4 accepted 条件を強化（独立性・矛盾なし・scope・ratify） | §4（＋FORMOBJ v1.1 §4.2） |
| N4 | FORMOBJ/MEANING を即 deprecate しない | §5 |
| N5 | SEED_IMPL REVISION を前提条件化 | §6（＋§4 L2参照品質連動） |

## 8. 新設ゲート（統合スタック共通）
- `gate_no_vocab_fork` — function_ref/term_id は shared_term_registry の term_id のみ。
- `gate_l4_keyed_by_l2` — L4 は L2 term_id をキーに持つ。未登録キーでの L4 生成禁止。
- `gate_layer_immutability` — L4/L3 を改訂しても L1/L2 を再生成しない。
- `gate_l2l4_grounding_separation` — identity_anchor と design_rationale を同一gate値にしない。
- `gate_l4_accepted_requires_l2_candidate` — L4 accepted は参照先 L2 term ≥ candidate＋品質レビュー通過（or owner override）。

## 9. 次の小さな起票（監査の next 指示）
1. **FORMOBJ 用語patch**（P3→L4 ほか）→ **完了**（`DD-FORMOBJ-001_v1.1-draft.md`）。
2. **MEANING への L4 参照点追記**（legal_effect の空欄を「L4 design knowledge が埋める」と明記）→ Mac側 canonical のため**patch文を用意し連携**（本DD §10）。
3. **shared_term_registry の L4 FK 設計**（小さく）→ `shared_term_registry_v0.1-draft.md`。

## 10. MEANING への追記 patch（Mac側連携用・本セッションでは直接編集しない）
MEANING-001 は別セッション（Mac側）の PASS 済 canonical。並行canonical禁止・越権回避のため**直接編集せず**、以下の追記文を連携する:
> **追記（L4 参照点）**: 本DDの L3 overlay が持つ `legal_effect` は *候補タグ* に留め、条項の規範的設計知識（なぜ/押し引き/有利不利/根拠解説）は **L4 design knowledge（DD-FORMOBJ-001 v1.1）** が `shared_term_registry.term_id` をキーに供給する。L3 は外延的束縛、L4 は内包的設計知識として責務分離する。

## 11. 改訂履歴
- **v0.2-draft（2026-06-15・本版）**：監査 `DDTMPLINTEG_PASS_WITH_NOTES` の N1-N5 反映。term_id参照化、evidence_purpose分離、L4 accepted強化、併存ガバナンス、SEED_IMPL前提化、MEANING連携patch文。owner ratify 済。
- v0.1-draft（2026-06-12）：監査提出版（凍結・参照点）。
