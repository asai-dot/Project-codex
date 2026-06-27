---
worker_task_id: W-20260626-501
status: queued
priority: P1
owner: claude-code-worker
created_at: 2026-06-26
request: docs/WORKER_TASK_PACKET_caselink_corpus_dryrun_20260625.md
goal: magazine の判例評釈 subset(artifacts/periodical/article_type_local_*.csv の type=判例評釈)を入力に CASELINK engine で評釈→判例リンク dry-run を1回行い、route(auto/review)・edge_type・stance 分布と(可能ならN=100で)実 evaluates 精度を出す
mode: implementation
requires_systems:
  - branch claude/precedent-object-progress-gwb47u の scripts/case_link_*.py, case_citation_span.py, case_vocab.py
  - branch claude/magazine-object-analysis-seg9cr の artifacts/periodical/article_type_local_*.csv + 記事本文/fulltext層
depends_on:
  - magazine 記事種別分類(判例評釈 subset)が生成済であること
allowed_paths:
  - _claude_dispatch/from_worker/
  - artifacts/caselink/
allowed_actions:
  - read_files(magazine article_type csv, 記事本文/fulltext層)
  - ensure_engine(precedent-object-progress ブランチから scripts/case_link_*・case_citation_span・case_vocab・app/data/case_identity を取得)
  - run scripts/case_link_corpus_dryrun.py
  - write deliverable(dry-run report)
forbidden_actions:
  - production_db_write
  - salesforce_write
  - box_write_move_rename_delete
  - raw_source_mutation
  - ai_estimate_as_human_decision
  - pii_in_general_artifact
  - human_gate_bypass
  - fill_unknown_with_generalities
  - stall_whole_run_waiting_for_input
exit_criteria:
  - dry-run report(articles/edges_emitted/route_distribution/edge_type_counts/stance_counts)を出力している
  - 判例評釈 subset が未生成なら blocked(探した場所・件数を明記)
  - stance列DDL/alo_edges実write/canonical昇格/accepted edge化を一切していない(HOLD)
  - RESULT を done/ または blocked/ に書く
deliverables:
  - _claude_dispatch/from_worker/20260625_caselink_L5_dryrun_RESULT.md
max_attempts: 2
result_expected_filename: W-20260626-501_RESULT.md
---

# Task — CASELINK L5: magazine 判例評釈 subset で評釈→判例リンク dry-run

詳細発注は `docs/WORKER_TASK_PACKET_caselink_corpus_dryrun_20260625.md`（正本）。RECONCILE ratified に基づき「magazine L5 は新規実装せず CASELINK engine を呼ぶ」。

## 手順
0. **engine 準備**: runner は worker-task-queue ブランチで動くため、CASELINK engine が無ければ `git fetch origin claude/precedent-object-progress-gwb47u` →`git checkout origin/claude/precedent-object-progress-gwb47u -- scripts/case_link_extract.py scripts/case_link_map.py scripts/case_link_eval.py scripts/case_citation_span.py scripts/case_vocab.py app/data/case_identity/` で取得（read-only 取得・既存ファイルを壊さない）。`python3 scripts/test_case_citation_span.py` green 確認。
1. magazine の `artifacts/periodical/article_type_local_*.csv`(type=判例評釈)を特定。**未生成なら blocked**。
2. 判例評釈 article_id → 記事本文(fulltext層/article_meta)を join し、入力スキーマ `{article_id, article_type:"commentary", masthead_citation?, is_formal_review?, body_text}` の `caselink_L5_input.jsonl` を作る（**正規化キー/本文のみ・PIIは匿名化**）。
3. `python3 scripts/case_link_corpus_dryrun.py --corpus caselink_L5_input.jsonl` → 分布レポート。
4. 可能なら N=100 に正解エッジを付け `case_link_eval` で実 precision。
5. span 取りこぼし ≤20件メモ。
6. RESULT(先頭 `WORKER_PASS` または `WORKER_BLOCKED`)を `_result_template.md` 形式で書き complete/block。

## Do Not
stance列DDL適用・alo_edges実write・canonical昇格・accepted edge化（全HOLD・別GO）。case_link_*/case_vocab の設計改変（番頭領分・不足は RESULT に報告）。

---
## HEAD OPS 準拠(本タスク共通)
本タスクは `docs/HEAD_OPS_CASELINK_SILVER_LOOP_20260627.md` の規律に従う。要点:
- **サブエージェント許可**: chunked work(500-1000件単位の並列)・independent search(入力場所特定)・adversarial verify(自己refute)で `Agent` を使ってよい。HOLD境界の判断は singleton(分散しない)。allowed_paths/forbidden_actions はサブエージェントも継承。
- **self-check**: RESULT 末尾に必須メトリクス節を出す:
  ```
  ## MERTRICS_JSON
  {"records_in":N,"records_processed":N,"elapsed_sec":N,
   "key_metrics":{...task固有...},
   "subagent_calls":N,"halts":N,"blocked_reason":null|str}
  ```
- **STOP gate**: §9 のいずれかに該当したら自走停止 → head に判定依頼(部分実行でOK、強行しない)。EMERGENCY(forbidden違反/PII露出/捏造数値疑惑)は即時 blocked + owner 通知。
- **RESULT 構造**: `WORKER_PASS|WORKER_PASS_WITH_NOTES|WORKER_BLOCKED|WORKER_FAIL`(先頭行) → 要約3行 → 主要メトリクス → 完了/未完了内訳 → 次手提案(head が hold/ から該当タスクを queue するため)。
- **検収**: head は HEAD_OPS §3.2 の self-check 値を見て label を確定し、PASS で対応する hold/W-NNN を queue へ。
