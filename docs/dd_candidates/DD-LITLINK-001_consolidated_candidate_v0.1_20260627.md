# DD-LITLINK-001 v0.1（凍結候補）— 文献リンク層（signal→candidate→edge・所有境界・独立性 leaf binding）candidate

> **id**: DD-LITLINK-001 / **version**: candidate v0.1（**consolidated freeze candidate**・初の凍結候補）/ **formalizes**: cleaned design record `02_LIT_DESIGN_RECORD_CLEANED_20260615`（Box 2286222789037）§6 文献link・§7 CaseBundle 扱い（latest-pointer の DD-LITLINK-001 を単一凍結候補に確定）
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-27 JST
> **lifecycle**: candidate（**設計のみ**）。DDL/DB/mint/OCR/embedding/edge promotion/alo_edges export 本番反映/Box mutation は **HOLD**。
> **depends_on（pin）**: **DD-LITID-001 v0.5**（source/asset 同定の正本・accepted・content_hash 4b8f4a57…・RESULT 2312578962778）/ **DD-INDEP-LINEAGE-001 v0.1**（独立性 lineage 正本・accepted・content_hash a7856be1…・RESULT 2306834650821）。
> **consumed by**: DD-XDOC-001 v0.9（§8 OWNERSHIP_NO_REDEF が lit_link を所有境界の一種として参照・本 DD は定義を供給）。
> **責務境界**: 本 DD は「文献が**何を参照するか**（link/edge）」のみ所有。「**どの本が同じ本か**（identity）」は DD-LITID-001 が正本（再定義しない）。

---

## 0. 射程（凍結する範囲）
文献（biblio_item/chunk）から **法令・判例・語彙・他文献・書式/手続** への**接続 signal の所有・候補・export 境界**を凍結する。identity・属性は LITID（§依存）、独立カウントは INDEP leaf（§4）に委譲し、本 DD はリンクのライフサイクルと所有境界のみを規律する。

## 1. 3層モデル（raw signal → candidate → accepted edge）
cleaned record §6 を凍結。**生 signal と accepted edge を強さで混ぜない**。
```text
lit_link_signal        -- raw source から抽出した接続 signal（観測・append-only）
  signal_id ; from_ref(biblio_item|chunk|toc_node) ; to_target_ref(law|case|vocab|lit|form)
  signal_kind ; source_system ; provenance_group ; raw_payload_ref ; observed_at ; rights_profile
lit_link_candidate     -- resolver 状態・allowed usage を持つ候補（可逆）
  candidate_id ; from_ref ; to_resolved_ref? ; resolver_status ; allowed_usage ; supporting_signals[]
  independence_assessment_ref   -- §4 leaf binding（corroboration の独立カウント）
alo_edges export       -- reviewed かつ accepted かつ resolver 済みのものだけ
  edge_id ; from_ref ; to_ref ; edge_kind ; acceptance_ref ; export_scope
```
- **append-only**：signal は削除しない（再取得は新 signal）。candidate は resolver_status で状態遷移（resolved/disputed/rejected）・履歴保持。
- **export ゲート**：alo_edges へ出すのは **reviewed ∧ accepted ∧ resolved** のみ（生 signal や未解決 candidate を edge にしない）。
- **G_LITLINK_THREE_TIER**：signal→candidate→edge を畳まない（生 signal を直接 edge にしない）。**G_LITLINK_EXPORT_ACCEPTED_ONLY**：alo_edges は reviewed+accepted+resolved のみ。

## 2. signal 強度差別化（同じ強さで扱わない）
cleaned record §6：**TOC / NDLSH / D1分類 / OPAC評釈 / 本文明示引用 / LLM suggestion を同一強度にしない**。
```text
signal_kind（typed・強さ順は policy が持つ・本 DD は分類のみ固定）:
  explicit_citation      -- 本文明示引用（最強・原典に接地）
  structured_classification -- NDLSH / NDC / NDLC / D1分類（構造化・出所明確）
  toc_reference          -- 目次由来の参照
  editorial_annotation   -- OPAC評釈・解説由来
  llm_suggestion         -- LLM 提案（最弱・単独で edge にしない）
```
- **G_LITLINK_SIGNAL_KIND_TYPED**：signal は typed。**llm_suggestion 単独で accepted edge にしない**（人手 or 強 signal の裏付け必須）。
- 強さの数値・閾値は **Stage2（重み付け）へ繰延**（LITID と同じ段階分離・本 DD は分類と順序原則のみ固定）。

## 3. 所有境界（XDOC OWNERSHIP_NO_REDEF 整合）
XDOC v0.9 §8 が区別する3種の所有を**侵さない**：
| 所有 | 意味 | 所有 DD |
|---|---|---|
| `block_ref` | 文書内の明示参照（cross_doc 含む） | LAYOUT |
| **`lit_link`** | **文献→外部（法令/判例/語彙/他文献/書式）の link** | **本 DD（LITLINK）** |
| `xdoc_alignment` | 文書間の推定整列 | XDOC |
- **G_LITLINK_OWNERSHIP_NO_REDEF**：lit_link は block_ref（明示参照）・xdoc_alignment（推定整列）を再定義しない。本 DD は文献→外部 reference のみ所有。

## 4. ★独立性＝DD-INDEP-LINEAGE-001 leaf へ binding（LITID §4 と同型）
同一 edge を支持する複数 signal の **corroboration（独立裏取り）**は、leaf 正本で数える。同一供給元の signal 再配信を独立票にしない。
```text
# 正本は leaf（DD-INDEP-LINEAGE-001 §5）。LITLINK は写像して consume（独自定義しない）。
signal の provenance_group → leaf same_origin_collapse_key   （同一供給元 signal を1票へ collapse）
signal の source_lineage   → leaf upstream_lineage_id
corroboration_count        = leaf content_independent 準拠（同一 group 内一致は多数決にしない）
独立性 pin: id=DD-INDEP-LINEAGE-001 / version=v0.1 / content_hash=a7856be1… / acceptance_ref=RESULT 2306834650821
```
- **G_LITLINK_INDEP_SOURCE_LEAF**：edge corroboration の独立カウント正本は leaf。**G_LITLINK_PROVENANCE_NO_DOUBLE_COUNT**：同一供給元 signal を独立2票にしない。**G_LITLINK_UNKNOWN_LINEAGE_CONSERVATIVE**：不明系譜 signal だけで edge を強めない（leaf note5）。

## 5. CaseBundle ゲート（文献 link は evidence でない）
cleaned record §7 を凍結：文献 chunk/link は CaseBundle で **supporting_analysis / counter_analysis / research_lead** であって **evidence ではない**。
- **G_LITLINK_NO_EVIDENCE**：lit_link を CaseBundle evidence へ直接入れない。claim_support_eligible=false（派生・非 canonical）。

## 6. resolver / allowed usage（rights 継承）
- `resolver_status`：to_target を実体（law_id/case_id/vocab_id/item_id）へ解決した状態（unresolved/candidate/resolved/disputed/rejected・可逆）。
- `allowed_usage`：signal の rights_profile を継承（購読由来 signal の利用範囲が edge/export まで漏れない）。
- **G_LITLINK_RIGHTS_INHERITED**：signal→candidate→edge→export で rights が閉じる。

## 7. ゲート一覧
THREE_TIER / EXPORT_ACCEPTED_ONLY / SIGNAL_KIND_TYPED / OWNERSHIP_NO_REDEF / **INDEP_SOURCE_LEAF / PROVENANCE_NO_DOUBLE_COUNT / UNKNOWN_LINEAGE_CONSERVATIVE** / NO_EVIDENCE / RIGHTS_INHERITED。

## 8. 受入試験（全自動 PASS が条件）
1. 生 signal を直接 alo_edges export にしない（reviewed+accepted+resolved のみ）。
2. llm_suggestion 単独では accepted edge にならない（強 signal or 人手の裏付け必須）。
3. lit_link が block_ref / xdoc_alignment を再定義しない（所有境界）。
4. **同一供給元（provenance_group）の signal 再配信が corroboration 2票にならない**（§4・leaf 準拠）。
5. 不明系譜 signal だけで edge を強めない（leaf note5）。
6. lit_link が CaseBundle evidence に入らない（supporting_analysis 止まり）。
7. signal の rights_profile が edge/export まで継承され閉じる。
8. signal/candidate が append-only・resolver_status 遷移が履歴保持（可逆）。

## 9. owner 決定事項（要 ratify）
1. 本 v0.1 を DD-LITLINK-001 の凍結正本とし、cleaned record §6/§7 を formalize 完了とするか。→ 推奨：そうする。
2. signal_kind の分類粒度（5種）で十分か（書式/手続 link を別 kind にするか）。→ 推奨：v0.1 は5種・必要なら addendum。
3. 強さ重み（signal_kind の数値順位・閾値）を Stage2 へ繰延（推奨：LITID と同じ段階分離）。

## 10. GO / HOLD / loop_state
- **GO**：v0.1 凍結 design ratify／leaf・LITID pin 整合（§4・§依存）／DDLITLINK 監査投函。**凍結後に RECONCILE v0.3 §7 の最後の TBD（DD-LITLINK-001）を実値化 → Phase1 dependency gate 緑化**。
- **HOLD**：DDL/DB/mint/OCR/embedding/edge promotion/alo_edges export 本番反映/Box mutation。
- loop_state = **freeze candidate（v0.1・signal→candidate→edge 凍結・独立性を leaf へ binding・所有境界 XDOC 整合）→ DDLITLINK 監査 → owner ratify で入口 DD 凍結完了**。これで実データ投入前ゲートの入口 DD（LITID+LITLINK）が揃う。
