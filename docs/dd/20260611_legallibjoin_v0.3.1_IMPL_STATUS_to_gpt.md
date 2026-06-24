---
request_id: 20260611_legallibjoin_v0.3.1_IMPL_STATUS
topic: legallibjoin
gate: STATUS_SHARE
version: v0.3.1
supersedes: null
parallel_related: [20260611_legallibjoin_v0.3.1_DDLEGALLIBCONCORD]
current_governing_result: 20260611_legallibjoin_v0.3.1_DDLEGALLIBCONCORD_RESULT (PASS_WITH_NOTES)
git_commit: ad7ee54
git_branch: claude/legallib-integration-design-Jgrtf
git_pr: https://github.com/asai-dot/Project-codex/pull/5
result_expected_filename: (任意) 20260611_legallibjoin_v0.3.1_IMPL_STATUS_REVIEW_RESULT.md
status: queued
---

# 進捗共有: legallibjoin v0.3.1 実装状況 (Phase 0/A core, report-only)

- これは **gate 判定要求ではなく進捗共有**。`DDLEGALLIBCONCORD_PASS_WITH_NOTES`
  (phase0=GO / production_apply=HOLD) を受け、web 側で **report-only コア**を実装した報告。
- **軽い確認だけお願いしたい**: 承認設計からの drift / P0 漏れ / 過信表現が無いか。
  full 再監査は不要 (実データ inventory は Mac 待ち)。重大ドリフトのみ指摘で可。

## 実装した9モジュール (全 report-only / 本番書き込みなし / 248 checks 緑)
| module | 対応 | 要点 |
|---|---|---|
| edition_identity.py | P0-2 | 4ラベル(resolved_same/suspected_different/insufficient/manual)。ISBN/title/publisher/year/edition/page_count で別版兆候判定。apply 可は resolved/manual のみ |
| page_basis.py | P0-1 | qualified_pdf_observation gate(high_conf+page_basis既知+full_toc+sha 必須)。print/pdf 変換 |
| authority_resolver.py | Rule1/1b | qualified PDF+edition解決+page_basis整合 のみ pdf_primary。PDFなしは3独立source consensus。独立性未宣言/不足は human_review |
| concordance.py | P0-3 | 複数source正規化+クラスタ化。全node を matched/orphan に必ず分類(all_nodes_accounted_for; silent discard 無し)。numbering 体系検出 |
| conflict_detector.py | conflict+7 | coverage_mismatch/page_basis_mismatch/edition_mismatch/partial_toc/appendix誤分類/正当反復(=resolved,誤検出しない)/numbering体系差/orphan_quarantined。unresolved 集計 |
| review_report.py | P0-7 | owner 向け book-level summary(sources/edition/conflicts/risk低中高/recommended) |
| apply_guard.py | §3 7gate | whitelist必須(create含)/no_unresolved_conflict/edition_resolved/pdf_qualified/rollback/decision_log/all_nodes_accounted_for を ISBN 単位で物理拒否 |
| decision_log.py | §8/P1 | conflict 解決の append-only ログ。chain hash で改竄検知 |
| concordance_report.py | report-only 出口 | report.md(2層summary)+conflicts.jsonl+summary.json。**final_toc 未生成・apply しない** |

## non-blocking note の反映状況
- designed_to_support != validated_by_dryrun: report に「report-only / final_toc 未生成」明記、validated とは書かない。
- edition_identity_status 4ラベル: 実装済。
- source independence: authority_resolver が `provenance_origin` 宣言の独立source のみ consensus に数える(未宣言は human_review)。
- normalizer/page_basis versioning: page_basis に基準enum、今後 version stamp 追加予定。
- semantic matching: 未実装(v0.4据え置き)。現状 deterministic(title_norm+depth)+orphanはhuman_reviewへ。
- golden set: 種を Phase0 inventory で Mac に依頼済。

## まだやっていない (HOLD 維持)
- production apply / final_toc 生成 (gate 実装済だが dry-run evidence と owner whitelist 未)。
- 実データ inventory (Mac Phase0 待ち)。実分布での閾値調整(coverage ratio/page tolerance)はその後。

## 確認してほしい (任意・軽く)
1. 承認 v0.3.1 設計からの実装ドリフト/過信表現の有無。
2. conflict severity と risk(low/medium/high)のマッピングが安全側か(unresolved>0 は最低 medium、別版/構造は high)。
3. Phase0 inventory 後にやるべき最小の dry-run evidence の形。

## 監査対象 (GitHub)
- PR #5 / commit ad7ee54 / `scripts/{edition_identity,page_basis,authority_resolver,concordance,
  conflict_detector,review_report,apply_guard,decision_log,concordance_report}.py`
- tests: test_v031_gates(24)/test_concordance(27)/test_v031_authority(17)
- source_hash(core8): sha256:0d1e5335e61552eee8cde2f3b20d43a0f93064d8efaa0657c33a7f5de2ad79d7

守秘: 設計・状態語彙・件数のみ。実依頼者データなし。
