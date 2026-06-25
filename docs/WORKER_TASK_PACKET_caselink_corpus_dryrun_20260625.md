# WORKER_TASK_PACKET — CASELINK L5: magazine 判例評釈 subset で評釈→判例リンク dry-run（統合版・正本ratified）

> 正本: `asai-dot/Project-codex` ブランチ `claude/precedent-object-progress-gwb47u` の本ファイル ＋
> `scripts/case_link_corpus_dryrun.py` / `case_citation_span.py` / `case_link_{extract,map,eval}.py`。
> **入力は magazine ブランチの判例評釈 subset**（RECONCILE_caselink_linkboot_magazine_20260625.md ratified に基づく）。
> ワーカーは本ブランチを pull して実行。RECONCILE で「magazine L5 は新規実装せず本 engine を呼ぶ」と確定済。

```yaml
task_id: WORKER_20260625_CASELINK_L5_DRYRUN_002
executor: claude-worker   # Mac CC（magazine成果物 + D1-LIC + 認証を持つ実行者）
permission_tags: [read-only, no-production-db-write, no-DDL, no-stance-column-apply-HOLD, no-canonical-promotion, no-accepted-edge, no-Box-delete]
output_path: _claude_dispatch/from_worker/20260625_caselink_L5_dryrun_RESULT.md
stop_condition: one-pass-complete | needs_decision | blocked | budget_exhausted | max_turns
depends_on: magazine の記事種別分類 (artifacts/periodical/article_type_local_v0.1.csv, 判例評釈ラベル)
```

## 意味づけ（owner ratified 2026-06-25）
3レイヤ正本確定: **magazine=上流(記事↔号/種別) / CASELINK=L5判例リンクengine / LINKBOOT=法令リンク**。
本タスクは **magazine(上流) → CASELINK(L5 engine)** を一本で繋ぐ**単一**dry-run。二重実装・二重コーパス整形を作らない。**read-only**。stance列DDL・alo_edges実write・canonical昇格は HOLD。

## 手順（bounded・順に）
1. `git pull origin claude/precedent-object-progress-gwb47u` → harness green 確認（`python3 scripts/test_case_citation_span.py` 他）。
2. **入力＝magazine の判例評釈 subset を取得**:
   - magazine ブランチ(`claude/magazine-object-analysis-seg9cr`)から `artifacts/periodical/article_type_local_v0.1.csv`(type=判例評釈 の行) と、対応する記事メタ/本文(`build/labeled_v0.2.1/article_meta_labeled.jsonl` 等)を read-only で参照。
   - **classify がまだ pilot で 判例評釈 subset が未確定なら blocked 報告**（magazine L5 上流待ち）。pilot 分だけでも回す場合は件数を明記。
3. **入力スキーマへ整形** `caselink_L5_input.jsonl`（1行=1記事）:
   `{"article_id","article_type":"commentary"(判例評釈),"masthead_citation":<対象判例 court/date/事件 があれば。D1-LIC crosswalk or タイトル/書誌から>,"is_formal_review":<正式評釈シリーズ>,"body_text":<記事本文>}`
4. **dry-run**: `python3 scripts/case_link_corpus_dryrun.py --corpus caselink_L5_input.jsonl > L5_dryrun_report.json`
   → `articles / edges_emitted / route_distribution(auto vs review) / edge_type_counts / stance_counts`。
5. **精度サンプル（stretch）**: N=100 に正解エッジ(記事→判例,役割,stance)を付け `case_link_eval.py` で evaluates/compares precision・stance 正解率。目標 evaluates/review_chain=0.97 / compares=0.90 / stance=0.85。
6. **span 取りこぼしメモ** ≤20件（`case_citation_span.CITATION_RE` で拾えない引用書式の型）。
7. `output_path` に報告（件数・分布・精度・取りこぼし・blocked 有無）。

## Forbidden
- stance 列 DDL 適用 / alo_edges 実 write / canonical 昇格 / accepted edge 化（全 HOLD＝別 owner GO + Wave57 MAP_UPDATE）。
- magazine の上流成果物への書込み（read-only 参照のみ）。
- `case_link_*` / `case_vocab` の設計改変（番頭領分。取りこぼしは §6 で報告のみ）。
- **新たな評釈→判例抽出器を別実装すること**（＝RECONCILE 違反。必ず本 engine を使う）。
- 実案件個人情報の露出（あれば匿名化 or 除外し needs_decision）。

## 完了後
番頭(remote Claude=head)が report を読み、(a) route 閾値/span 拡張、(b) magazine head と L5 接続点(HANREI-TARGET→case_link_extract の masthead 入力)の確定、(c) 結果を RECONCILE/整合監査へ記録。production 反映(stance列ほか)は別 GO。
