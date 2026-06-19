# DD-XMODAL-001 v0.4 — cross-modal triangulation & 生きたコーパス（PASS_WITH_NOTES 反映・ratify候補）candidate

> **id**: DD-XMODAL-001 / **version**: candidate v0.4 / **supersedes**: v0.3
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-19 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/学習/embedding/OCR は HOLD。
> **改訂理由（v0.3→v0.4）**: GPT Pro 再監査 `DDXMODAL_PASS_WITH_NOTES`（RESULT Box 2295556105320）の非blocking notes 2点を反映。**致命傷（D軸一枚岩）は v0.3 で解消・是認済**。本 v0.4 は notes 反映＝**owner ratify 候補**。
> **承継**: v0.3 §1（D0/D1/D2 三分割）・§3（confirmed に D2＋独立2源）・§4 ストレステスト・§5 ゲート・§6 既存/白地分離・5ガードレール・inventory-probe は**不変**。本ファイルは notes 差分を追加。

---

## 0. 監査履歴
- v0.2 = `DDXMODAL_MODIFY_REQUIRED`（D軸過大独立主張）→ v0.3 で D0/D1/D2 分割。
- v0.3 = `DDXMODAL_PASS_WITH_NOTES`（致命傷解消・D1 を独立票にしない点を評価）→ 本 v0.4 で notes 2点反映。

## 1. notes 反映①：external_source_families の registry 化（G_XMODAL_EXTERNAL_FAMILY_REGISTRY）
`confirmed` の必要条件 `external_source_count ≥ 2` を**生のソース数で数えない**。同一系統（同じ D1-Law 系／同じ OCR エンジン／同じ編集源／同じ出版社系）から来たものを「独立2源」と誤計上すると、corpus 規模の自己一致になる。
```text
external_source_family_registry        # 統制レジストリ（人手管理）
  family_id / family_kind∈{statute_text, legal_dictionary, classification_scheme,
    commentary_publisher, ocr_engine, editorial_source, court_db}
  independence_notes
# confirmed 判定は DISTINCT family_id を数える（同 family の複数源は1票）
d2_evidence(... , external_source_family_id -> registry)
```
→ `external_source_count` は **DISTINCT registered family** で計算。未登録 family は independent と見なさない（possible 止まり）。

## 2. notes 反映②：possible_reason を機械可読に（G_XMODAL_POSSIBLE_REASON_REQUIRED）
`confirmed` を D2 で絞ると possible が増える。**なぜ possible 止まりか**を機械可読に保持し、次アクション（D2 補充／人手／granularity 精緻化）を一意化：
```text
agreement_signal(... , decision, possible_reason∈{
   no_d2_evidence,            # D2 未取得（外部証拠なし）
   single_external_family,    # 外部源が1 family のみ（registry 判定）
   low_label_model_prob,      # 相関補正後の確率が中間帯
   abstain_majority,          # 主要 view が abstain
   granularity_mismatch,      # 章一致だが unit/bbox 不一致（ストレステスト#3）
   external_taxonomy_conflict # 外部分類同士が不一致（#4）
})
```

## 3. ゲート（v0.3 ＋ 追加2本）
v0.3 既存（D_AXIS_SPLIT / NO_EXTERNAL_OVERCLAIM / DEPENDENCY_GRAPH_REQUIRED / EXTERNAL_EVIDENCE_REQUIRED_FOR_CONFIRMED / LAW_SNAPSHOT_REQUIRED / NO_VT_CONFIRMATION / HUMAN_PROMOTION_ONLY ＋ 基底）に加え：
- **G_XMODAL_EXTERNAL_FAMILY_REGISTRY**：external_source_count は統制レジストリの DISTINCT family で数える。
- **G_XMODAL_POSSIBLE_REASON_REQUIRED**：possible は machine-readable な possible_reason を必須。

## 4. 不変（v0.3 承継）
D0(prior)/D1(mapper, T結合=非独立)/D2(外部証拠)。confirmed に D2＋独立2 family。view_assertion の dependency_refs/mapper_version/independence_class。D観測の law_snapshot/source_version/valid_at。ストレステスト5本。既存/白地分離。5ガードレール。inventory-probe（knowledge_yield に D2率）。

## 5. loop_state
`DDXMODAL_PASS_WITH_NOTES`（非blocking）→ notes 反映済 → **owner ratify 候補**。HOLD：DDL/DB/mint/Box mutation/学習/embedding/OCR。
