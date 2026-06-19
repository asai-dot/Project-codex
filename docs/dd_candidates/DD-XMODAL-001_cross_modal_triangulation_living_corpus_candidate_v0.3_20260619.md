# DD-XMODAL-001 v0.3 — cross-modal triangulation & 生きたコーパス（D軸を D0/D1/D2 に分割）candidate

> **id**: DD-XMODAL-001 / **version**: candidate v0.3 / **supersedes**: v0.2
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-19 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/学習/embedding/OCR は HOLD。
> **改訂理由（v0.2→v0.3）**: GPT Pro 監査 `DDXMODAL_MODIFY_REQUIRED`（RESULT Box 2295468896935）反映。**approach は是認**（印刷TOC＝第3独立軸でない、は正しい）。ただし「D軸＝artifact から真に独立」は危険＝**上等な自己循環（外部語彙で飾った自己一致）**を生む。must-fix の核＝**D軸を D0/D1/D2 に分割**。
> **承継**: v0.2 の §2 既存/白地分離・§5 5ガードレール・§8 inventory-probe は不変。本ファイルは差分を上書き。

---

## 0. 監査反映サマリ（must-fix）
| # | GPT must-fix | v0.3 反映 |
|---|---|---|
| 1 | D軸を D0/D1/D2 に分割（独立性を正しく階層化） | §1 |
| 2 | 「artifact から真に独立」と言い切らない | §1・G_XMODAL_NO_EXTERNAL_OVERCLAIM |
| 3 | involves_external だけでは不足→3種＋source count/families | §2 |
| 4 | view_assertion に依存関係・mapper版・independence_class | §2 |
| 5 | confirmed には D2（外部証拠照合）必須 | §3・G_XMODAL_EXTERNAL_EVIDENCE_REQUIRED_FOR_CONFIRMED |
| 6 | D軸に法令版時点（law_snapshot/valid_at） | §2・G_XMODAL_LAW_SNAPSHOT_REQUIRED |
| 7 | 依存グラフ明示（転置できた≠検証できた／STAM 依存明示） | §2・G_XMODAL_DEPENDENCY_GRAPH_REQUIRED |

## 1. ★D軸の三分割（v0.3 の核）
v0.2 は D を一枚で「真に独立」とした。これは誤り。OCR 由来の写像は T に依存する。正しくは：
```text
D0 = external doctrine ontology / taxonomy     （文書外の prior。材料として独立）
     法令体系・法律用語辞典・D1分類・要件事実体系・research_unit 等
D1 = artifact-to-doctrine mapper               （本文/画像/OCR → どの D0 node か推定）
     入力が OCR なら T と依存。★完全独立ではない
D2 = external evidence corroboration           （条文原文・辞典定義・複数 doctrine source と内容照合）
     ★ここまで来て初めて validation と呼べる
```
- **独立なのは D0（材料）と D2（外部証拠）**。**D1 は T と結合**（OCR 入力）。
- ∴ 「V+T 一致＋D1 着地」は**検証でない**（OCR 誤読が doctrine mapping を誘導し false validation になりうる）。**confirmed には D2 が要る**。

## 2. 派生レイヤ語彙（v0.3 改）
```text
view_assertion(unit_id, axis∈{V_visual,T_textual,D0_prior,D1_mapper,D2_evidence},
  predicted_label, view_confidence, abstain,
  input_source_family,        # この観測の入力が何由来か（image/ocr_text/external_corpus…）
  dependency_refs,            # 依存する他観測（例 D1 → 当該 T observation）
  mapper_version,             # D1 mapper / 照合器の版
  independence_class∈{root_image, ocr_derived, external_prior, external_evidence},
  correlation_group)          # V_visual,T_textual,D1_mapper = "artifact_coupled" / D0,D2 = "external"
agreement_signal(unit_id, pattern, label_model_prob, decision∈{confirmed,possible,rejected},
  external_prior_involved,    # D0
  external_mapping_involved,  # D1
  external_evidence_involved, # D2 ★confirmed の必要条件
  external_source_count, external_source_families)
# D 観測（特に D2）は法令版時点を持つ
d_axis_obs(... , law_snapshot_id, source_version, valid_at)
derived_candidate(... , kind∈{correction,toc_node,form_variant,work_expression,research_unit}, status=proposed…)
view_accuracy(axis, task, m_prob, u_prob, weight, correlation_group)
```

## 3. confirmed 条件（v0.3 厳格化）
`decision=confirmed` には **`external_evidence_involved=true`（D2）かつ external_source_count ≥ 2（独立 family）** を必須。D0/D1 だけ・V+T だけ・単一外部源では **possible 止まり**（人手 or 追加 D2 へ）。conflict 解決の相関補正：V_visual・T_textual・**D1_mapper を同一 correlation_group（artifact_coupled）**として実効票を割り引く。D0/D2 のみ external。

## 4. ★ストレステスト（監査提示・設計で落とす）
1. **綺麗だが誤った版**：V=T=印刷TOC 一致でも旧版/誤版 → D2 の外部時点照合（law_snapshot/valid_at）で落とす。D0 mapping だけでは不可。
2. **OCR誤読が doctrine mapping を誘導**：T 誤読→D1 がもっともらしい概念に着地→false validation → D2 必須で遮断。
3. **法体系は正しいが本文箇所が違う**：章は売買でも当該 bbox は損害賠償 → granularity＋selector_ref（DD-LAYOUT の page_block 単位）で位置を縛る。
4. **外部分類自体の誤り**：D1-Law/外部 taxonomy も誤る → 単一外部源を神託化しない（external_source_count ≥ 2）。
5. **法改正・版違い**：D軸に law_snapshot_id / source_version / valid_at 必須。

## 5. ゲート（v0.2 ＋ 監査追加）
v0.2 既存（DERIVED/NO_CLAIM_SUPPORT/NO_SELF_LOOP/HUMAN_GATED/NO_RAW_MAJORITY/INDEP_REEXTRACT）に加え：
- **G_XMODAL_D_AXIS_SPLIT**：D を D0/D1/D2 に分けずに扱わない。
- **G_XMODAL_NO_EXTERNAL_OVERCLAIM**：D を「artifact から真に独立」と言わない（D1 は T 結合）。
- **G_XMODAL_DEPENDENCY_GRAPH_REQUIRED**：各観測は dependency_refs を持つ。STAM 転置できた≠検証できた、を明示。
- **G_XMODAL_EXTERNAL_EVIDENCE_REQUIRED_FOR_CONFIRMED**：confirmed には D2＋独立2源。
- **G_XMODAL_LAW_SNAPSHOT_REQUIRED**：D観測は法令版時点（law_snapshot/valid_at）。
- **G_XMODAL_NO_VT_CONFIRMATION**：V+T のみ（D2 無し）の一致を confirmed に昇格しない。
- **G_XMODAL_HUMAN_PROMOTION_ONLY**：正準化は人手のみ（新hub/新構造 auto=0）。

## 6. 不変（v0.2 承継）
既存/白地分離（2-of-3 機械は全引用。白地＝独立AI観測×安定アンカー×**外部体系＝D0/D2**×連続再評価の自己改訂ループ）／5ガードレール／inventory-probe（`knowledge_yield` に external_involved率＝D2率を含む）／2出力パス（correction→DD-PROOF の visual_reocr・doctrinal_external source_family／未知構造は候補）。

## 7. open items
O2 D1 mapper 実装・confidence／O3 visual_reocr・doctrinal_external の DD-PROOF source_family 接続／O5 work_expression↔FRBR/LRM（DD-LITID）／O6 knowledge_yield カーネル／O7 V-T-D1 相関の実測／O8 D2 の外部源 family 定義（条文原文/辞典/分類…）と最低源数。

## 8. loop_state / 一行
loop_state = **patched（v0.3）→ 再投函（再監査）候補**。HOLD：DDL/DB/mint/Box mutation/学習/embedding/OCR。
**一行**：第3軸は外部法律体系だが**一枚岩でない**。D0(prior)/D1(mapper, T結合)/D2(外部証拠照合) に割り、**confirmed には D2 を要求**することで「外部語彙で飾った自己一致」を構造的に禁じる。これが v0.2 の致命的穴の塞ぎ。
