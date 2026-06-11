# DDLEGALLIBCONCORD v0.3.1 — legallib 接合 concordance 設計（P0 7点反映）

- supersedes(production apply 判断): v0.2 (`DDJOIN` / `overwrite_simple` lane)
- parallel_related: `20260611_legallibjoin_v03_concordance_DDLEGALLIBCONCORD_v1.0`（v0.3 原案）
- 反映元監査: `from_gpt/20260611_legallibjoin_v03_concordance_DDLEGALLIBCONCORD_AUDIT_RESULT.md`
  (`DDLEGALLIBCONCORD_MODIFY_REQUIRED`) §11 の P0 7点 + 戦略 `LEGALLIBJOIN_STRATEGY_V03_1_FIRST`
- 状態: draft（投函前 owner 同期）

## 0. 位置づけ
複数資料（legallib / lion / bencom / 生PDF 等）の TOC を **concordance（対応付け）**して、
矛盾を可視化し、**owner 承認 ISBN のみ** final_toc を本適用する。v0.2 の単一ソース
`overwrite_simple` は廃し、v0.2 のコード資産（F1 children 再帰 / F2 有効ISBN gate /
F3 構造ガード / provenance / 943候補 / bencom 保護 evidence）は **baseline / whitelist seed /
evidence** として継承（apply list ではない）。

## 1. アーキテクチャ（層分離・採用）
```
NORMALIZATION → (EDITION IDENTITY) → CONCORDANCE MATCHING → CONFLICT DETECTION
→ AUTHORITY RESOLUTION → MERGE(final_toc) → DECISION LOG → APPLY GUARD(whitelist)
```
各 source の raw 差は Normalization が吸収、Matching は対応関係のみ、Resolution は採否のみ。
最初は **`concordance_report_only`**（merge/apply なし）から作る。

## 2. P0 反映（監査 §11 の7点）

### P0-1 PDF は ground truth ではなく `qualified_pdf_observation`
- 生PDF絶対視を廃止。PDF は「抽出された TOC observation」。authority=pdf_primary は
  **high_confidence かつ edition一致かつ page_basis整合**のときのみ。低信頼/部分/基準不明は
  `pdf_observed_not_ground_truth` → consensus か human_review。
- observation metadata: `extraction_method(manual|ocr|llm|publisher_pdf_toc)` /
  `extraction_confidence` / `page_basis(print_page|pdf_page|unknown)` / `coverage(full|partial|unknown)` /
  `extractor` / `source_sha256`。

### P0-2 edition / manifestation identity gate（P0昇格・接合前）
- 「答えは一つ」は **同一 edition/manifestation 確認後のみ**成立。接合前に
  ISBN / source_book_key / title_norm / publisher_norm / year / edition / page_count で
  同一性を解決。未解決は apply 禁止。page差/階層差は「別版の兆候」かもしれず conflict と区別。

### P0-3 conflict completeness の言い換え
- 「見つからなかった矛盾なし」は廃止。定義は
  **`all_nodes_accounted_for` = 全入力node・全候補edgeが matched/conflict/orphan/quarantined/
  dropped_with_reason のいずれかに分類され、silent discard が無い**。意味的conflictの全検出は保証しない。

### P0-4 unresolved conflict のある ISBN は apply 不可
- unresolved conflict が1件でもある ISBN は whitelist に入らない（hard gate）。

### P0-5 全 write に owner whitelist 必須（hard gate）
- `create` を含め final_toc apply は **owner 承認 ISBN whitelist 必須**。CLI が物理的に拒否
  （v0.2 P0-1 を全write へ拡張）。

### P0-6 orphan は削除せず `quarantined_with_reason`
- 対応先のない node（特に detail）は drop せず理由付きで quarantine。後で復活可能に。

### P0-7 owner 用 book-level conflict summary
- conflict.jsonl 直読は非現実的。book単位サマリ + node単位detailの2層。
```
ISBN / title
sources: legallib 104 / lion 98 / bencom 104 / pdf 104
conflicts: 3 unresolved / 12 resolved / 0 edition_mismatch
risk: medium
recommended: approve only if 3 unresolved are stamped
```

## 3. Conflict / quarantine パターン（6 + 追加7）
既存6 + 追加: edition_mismatch_suspected / page_basis_mismatch / partial_toc_source /
appendix_or_table_misclassified / coverage_mismatch / same_heading_repeated_legitimately
（正当反復をduplicate誤検出しない）/ numbering_scheme_changed（第1章/第一章/一/Ⅰ/Article 1）。

## 4. 複数一致（採用の定義・P0）
- PDFあり: `qualified high-confidence PDF + 1 source`。
- PDFなし: **3 独立 source**（同一二次由来は consensus と見なさない・独立性 metadata 必須）。

## 5. Safety Gates（物理強制・apply_guard.py）
1 all_nodes_accounted_for / 2 no_unresolved_conflict_in_apply / 3 edition_identity_resolved /
4 pdf_observation_qualified / 5 whitelist_required_for_all_writes / 6 conflict_report_reviewable /
7 rollback_bundle_complete（old_toc/new_toc/concordance graph/conflict decisions/source hashes）。

## 6. フェーズ（report-only から）
- Phase 0 source inventory / sample profiling / parser success histogram（1-2週）
- Phase A deterministic normalization のみ（2-3週）
- Phase B matching（semantic embedding なし）（2週）
- Phase C conflict report UX + owner review loop（2週）
- Phase D apply gate / rollback / dry-run（2週）
- semantic matching は v0.4 defer（その間 recall 不足は review に倒す。自動merge率を上げない）。

## 7. modules / coverage
modules: `normalize_{source}.py` / `page_basis.py` / `edition_identity.py` / `concordance.py` /
`conflict_detector.py` / `authority_resolver.py` / `review_report.py` / `decision_log.py` / `apply_guard.py`。
coverage: unit(各conflict型/各parser/page基準変換) / integration(既知conflict 10冊seed) /
golden(PDF observation high/medium/low) / regression(unresolved conflict は apply whitelist に到達不可)。

## 8. apply log / decision_log
apply log に: isbn / book_identity_cluster_id / edition_identity_status / old・new_toc_sha256 /
concordance_version / normalizer_versions / source_hashes / conflict_ids / resolution_decision_ids /
approved_by / approved_at / rollback_path。
conflict 解決は `decision_log.jsonl`（誰が・どの conflict を・どの根拠で、append-only）。

## 9. owner 要件整合（designed_to_support であり validated ではない）
矛盾を解く=conflict分類+review UX / 答えは一つ=edition identity 解決後のみ /
原点PDF正規化=PDF quality gate / きれいな構造=tree validation + no silent drop /
安全接合=whitelist + rollback + zero unresolved conflict gate。

## 10. 次
本 v0.3.1 を `DDLEGALLIBCONCORD` 再監査へ投函（投函前に Mac/web 内輪同期＝新規約#1）。
PASS_WITH_NOTES が出れば Phase 0 から実装着手。
