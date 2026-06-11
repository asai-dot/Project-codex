---
request_id: 20260611_legallibjoin_v0.3.1_DDLEGALLIBCONCORD
topic: legallibjoin
gate: DDLEGALLIBCONCORD
version: v0.3.1
supersedes: 20260611_legallibjoin_v03_concordance_AUDIT
parallel_related: [20260610_legallibjoin_v0.1_DDJOIN, 20260610_legallibjoin_analysis_v0.1_DDJOINAUDIT, 20260611_legallibjoin_v0.2_AUDIT]
withdrawal_effect: v0.2 production-apply lane は撤回維持。本v0.3.1がproduction apply判断のcurrent governing。
current_governing_result: pending
git_commit: 3021208
git_branch: claude/legallib-integration-design-Jgrtf
git_pr: https://github.com/asai-dot/Project-codex/pull/5
result_expected_filename: 20260611_legallibjoin_v0.3.1_DDLEGALLIBCONCORD_RESULT.md
status: draft   # 投函前に Mac/web 内輪同期 (新規約#1)。owner OK で queued へ。
---

# GPT Pro 設計監査(再)依頼: legallibjoin v0.3.1 concordance (P0 7点反映)

- gate: **DDLEGALLIBCONCORD** / version v0.3.1 / 起票 2026-06-11 / 番頭 web CC
- RESULT 先頭行: `DDLEGALLIBCONCORD_PASS` / `..._PASS_WITH_NOTES` / `..._MODIFY_REQUIRED` / `..._FAIL` / `..._NEED_MORE`
- 趣旨: v0.3 `DDLEGALLIBCONCORD_MODIFY_REQUIRED` の **P0 7点を反映した v0.3.1** が、実装着手
  (Phase 0) を許せる水準かの再監査。アーキテクチャは前回採用可。差分中心で見てほしい。

## 反映した P0 7点（前回 §11 対応）
1. PDF ground truth → **qualified_pdf_observation**（extraction_method/confidence/page_basis/
   coverage/source_sha256 の gate）。
2. **edition/manifestation identity gate を P0 昇格**（接合前。未解決は apply 禁止）。
3. conflict completeness → **all_nodes_accounted_for**（silent discard 無し。意味的全検出は非保証）。
4. **unresolved conflict のある ISBN は apply 不可**（hard gate）。
5. **全 write に owner whitelist 必須**（create 含む・CLI 物理拒否）。
6. orphan は削除せず **quarantined_with_reason**。
7. **owner 用 book-level conflict summary**（2層: book summary + node detail）。

加えて: conflict パターン +7（edition_mismatch / page_basis_mismatch / partial_toc /
appendix_misclassified / coverage_mismatch / legit repeated heading / numbering_scheme_changed）、
複数一致定義（PDF high+1 / PDFなし3独立source）、phase を report-only 起点に変更、
modules/coverage 目標、apply log + decision_log.jsonl を明記。

## 確認してほしい点
1. P0 7点が「実装着手を許す」水準で閉じているか。残る過信表現は。
2. edition identity gate の初期実装範囲（ISBN/title_norm/publisher/year/edition/page_count）で十分か。
3. `concordance_report_only` を Phase 0/A の唯一の出口にする段取りは妥当か。
4. v0.2 成果物（943候補・bencom保護 evidence・Batch A list）の whitelist seed 化の扱い。
5. PASS なら Phase 0 着手可か。

## 監査対象
- 設計: repo `docs/dd/20260611_legallibjoin_v0.3.1_concordance_DESIGN.md`（commit 3021208）
- 前回: `from_gpt/20260611_legallibjoin_v03_concordance_DDLEGALLIBCONCORD_AUDIT_RESULT.md`
- 戦略: `from_gpt/20260611_legallibjoin_strategy_clarification_RESULT.md` (V03_1_FIRST)
- 継承コード: `scripts/legallib_join_{policy,dryrun,apply}.py` / `legallib_to_canonical.py`(v1.1.0)

## 守秘
設計・状態語彙・件数レベルのみ。実依頼者データなし。
