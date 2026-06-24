# WORKER_TASK_PACKET — CASELINK: 実 D1-LIC 5,475 で評釈→判例リンク corpus dry-run

> 正本: `asai-dot/Project-codex` ブランチ `claude/precedent-object-progress-gwb47u` の
> `docs/WORKER_TASK_PACKET_caselink_corpus_dryrun_20260625.md` ＋ `scripts/case_link_corpus_dryrun.py` /
> `scripts/case_citation_span.py` / `scripts/case_link_{extract,map,eval}.py`。
> ワーカーは本ブランチを pull して実行すること。本ファイルが指示の正本。

```yaml
task_id: WORKER_20260625_CASELINK_CORPUS_DRYRUN_001
executor: claude-worker   # Mac CC（実 D1-LIC 5,475 解説コーパスと D1/リーガルライブラリー認証を持つ唯一の実行者）
permission_tags: [read-only, no-production-db-write, no-DDL, no-stance-column-apply-HOLD, no-canonical-promotion, no-accepted-edge, no-Box-delete]
output_path: _claude_dispatch/from_worker/20260625_caselink_corpus_dryrun_RESULT.md
upload_target: (任意・owner判断) Box CODEX/handoff
stop_condition: one-pass-complete | needs_decision | blocked | budget_exhausted | max_turns
```

## 意味づけ（owner）
DD-CASELINK-001 **accepted v1.0** の GO「read-only corpus dry run」。雑誌・文献の**本文**から評釈と判例を
**型付きエッジ**で繋ぐ設計が、実 D1-LIC でどれだけ **auto(evaluates) vs review(compares)** に振れ、
実 **evaluates 精度**がどうかを初めて実データで測る。「評釈と判例を丁寧に繋いで意味層を厚くする」の実証一歩。
**read-only**。alo_edges への実 write・canonical 昇格・stance 列 DDL は **HOLD**（別 GO 案件）。

## 手順（bounded・順に）
1. ブランチ pull → harness green 確認: `python3 scripts/test_case_citation_span.py` / `test_case_link_map.py` / `test_case_pipeline_e2e.py`（全 PASS が前提。FAIL なら blocked 報告）。
2. **D1-LIC 5,475 解説レコードを入力スキーマへ整形** → `caselink_corpus_d1lic_5475.jsonl`（1行=1記事）:
   ```json
   {"article_id":"...","article_type":"commentary|note|article",
    "masthead_citation":"令和3年(ワ)第123号"(D1-LIC crosswalk の対象判例があれば/無ければ省略),
    "is_formal_review":true(正式評釈シリーズのみ),"body_text":"解説本文プレーンテキスト"}
   ```
   - `article_type`: 書誌 genre から分類（評釈/判例研究→`commentary` / 判例紹介・解説→`note` / 論文・論説→`article`）。判別不能は `note`。
   - `masthead_citation`: D1-LIC crosswalk の**対象判例**(構造化済み)を入れる。これが auto(vendor_explicit)路の入力。
3. **分布 dry-run**: `python3 scripts/case_link_corpus_dryrun.py --corpus caselink_corpus_d1lic_5475.jsonl > dryrun_report.json`。
   → `articles / edges_emitted / route_distribution(auto vs review) / edge_type_counts / stance_counts` を取得。
4. **精度サンプル（stretch・可能なら）**: ランダム **N=100** 記事を抽出し、D1-LIC crosswalk or 人手で**正解エッジ**(記事→判例,役割,stance)を付け `caselink_gold_sample.jsonl`（`app/data/case_identity/case_link_gold_template.jsonl` と同形の `expected_edges`）。`case_link_eval.py` の GOLD を差し替えて **evaluates/compares precision・stance 正解率**を出す。目標: evaluates/review_chain=0.97 / compares=0.90 / stance=0.85。
5. **span 取りこぼしメモ**: 正規表現(`case_citation_span.CITATION_RE`)で拾えない/誤検出した引用書式の実例を **≤20件** 列挙（書式の型だけ。本文丸写し不要）。
6. `output_path` に §7 schema で報告。

## Forbidden
- **stance 列 DDL の適用 / alo_edges への実 write / canonical 昇格 / accepted edge 化**（すべて HOLD＝別 owner GO + Wave57 MAP_UPDATE 案件。番頭の領分）。
- 本番DB書込 / DDL / SF書戻 / Box ファイル削除。
- `case_link_*` や `case_vocab` の**設計改変**（語彙・写像則の変更は番頭＝remote Claude の領分。取りこぼしは §5 で**報告**するに留める）。
- 実案件個人情報の露出（解説本文に依頼者/個人特定情報があれば匿名化 or 除外し needs_decision）。

## 完了後
番頭(remote Claude)が `dryrun_report` と precision を読み、repo 側で:
(a) route 閾値/方針の調整、(b) **span 検出器の取りこぼし対応**（正規表現拡張・符号正規化強化）、
(c) 必要なら DD v0.3 反映 or 正典反映パッチの微調整、(d) 結果を整合監査ドキュメントへ記録。
production 反映（stance 列ほか）は引き続き別 GO で。
