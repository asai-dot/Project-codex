# _ACTION_QUEUE — GPT監査 反映キュー（派生ビュー）

- generated_at_jst: 2026-06-08
- source: handoffs/gpt_ometsuke/_AUDIT_LEDGER.jsonl (Box, canonical) / tools/gpt_audit/_AUDIT_LEDGER.jsonl (git)
- generator: tools/gpt_audit/backfill_seed_20260608.py + alo-gpt-audit action-queue
- rule: GPT_PRO_AUDIT_LANE_DESIGN v0.3 §D / GPT_PRO_AUDIT_LOOP_RULE v0.1 §8,§11
- 原則: `reflected:false` が残る限り監査は閉じていない。退避済み(processed)でも反映済みではない。

## 反映待ち（reflected:false） 14件 / 反映・requeue済 11件 / 全25件

### next_action = patch（MODIFY → 修正して再投函）

#### 20260605_ccguard_v0.1.1_G0  `[G0_MODIFY_REQUIRED]`
- loop_state: **returned** / target_queue: patch_queue / ratify_required: False / requeue_expected: True
- blocking_before_ratify:
  - shell起動/eval/encoded payload/heredoc を deny/ask する rule+fixture
  - mcp__* unknown は defer ではなく ask、mutating verb は deny/ask
  - Box/GDrive mutation は path 無しでも ask 以上
  - SQL resolver に project ref allowlist + alo-connect hard-deny
  - G3 live dry-run（実Claude Code + managed settings）実測
- owner_digest_5line:
  ```
  監査: ccguard v0.1.1 安全ガード G0
  結論: MODIFY_REQUIRED
  理由: shell/SQL迂回余地・unknown tool fail-open・G3未実施
  次アクション: Claudeが v0.1.2 でbypass群を閉じG3実測
  Owner確認: 不要（accepted/本番昇格はG3後）
  ```
- claude_rethink_prompt: v0.1.1 は fixture では前進したが本番 guard には早い。v0.1.2 で shell/eval/heredoc/encoded、mcp unknown=ask、Box/GDrive mutation=ask、SQL project ref allowlist+alo-connect hard-deny を実装し、G3 live dry-run を 通してから再レビューに回すこと。
- result_file_id: 2266430431171

#### 20260608_queueaudit_loop_GPTQUEUE_REVIEW  `[GPTQUEUE_MODIFY_REQUIRED]`
- loop_state: **requeued** / target_queue: patch_queue / ratify_required: False / requeue_expected: True
- blocking_before_ratify:
  - to_gpt直下の.processed.mdを物理退避（完了: processed/へ移動・suffix除去）
  - _AUDIT_LEDGER.jsonl/action-queueを実体化（完了: 本pass）
  - from_gpt RESULT群をnext_action_type付きでbackfill（完了: 25件）
  - dry-run/apply/idempotencyログ添付（完了: _VERIFY_20260608）
  - GPTQUEUELOOPIMPL_REQUEST.md で再投函（本pass）
- owner_digest_5line:
  ```
  監査: queueaudit ループ実装の再監査
  結論: MODIFY_REQUIRED
  理由: キュー空確認はOKだがaction ledger未実体化・processed物理退避未完了
  次アクション: Claudeが台帳/action-queue/退避を実装し再投函（本passで実施）
  Owner確認: 不要
  ```
- claude_rethink_prompt: 本passで実装: (1).processed.md を processed/へ物理退避しsuffix除去、(2)_AUDIT_LEDGER.jsonl を25件backfill、(3)_ACTION_QUEUE.md 生成、(4)dry-run/apply/idempotency検収ログ、(5)GPTQUEUELOOPIMPL_REQUEST 再投函。reflected は GPT 再監査が PASS したら true 化する。
- result_file_id: 2270920897721

### next_action = required_materials（NEED_MORE → 資料補充）

#### 20260605_quasijudicial_v0.4_DDCASESOURCE  `[DDCASESOURCE_NEED_MORE]`
- loop_state: **returned** / target_queue: material_queue / ratify_required: False / requeue_expected: True
- need_more_type: material_absent
- missing_materials:
  - DD-CASE-SOURCE-CASEID_v0.4_closure_20260604.md
  - DD-CASE-001_individual_judgment_canonical_node_draft_v0.1.md
  - alo_source_registry_seed_v0.1_20260604.jsonl
  - registry_negative_test.py
  - 31_case_layer_quasi_judicial_patch_draft_v0.2.md
- owner_digest_5line:
  ```
  監査: quasijudicial v0.4（準司法コーパス）
  結論: NEED_MORE（対象正本5点がBox不在）
  理由: docs/alo に監査対象が無く内容監査不能
  次アクション: 5ファイルをBox復旧→status:queued→source_hash埋め再投函
  Owner確認: 不要（資料復旧タスク）
  ```
- claude_rethink_prompt: 内容議論に入らない。対象5点を Box docs/alo にアップロードし実体ID・sha1 を REQUEST に入れ、front-matter を status: queued に戻して再投函する資料復旧ルート。
- result_file_id: 2268867415119

#### 20260606_legallibbiblio_v0.5_INGEST  `[INGEST_NEED_MORE]`
- loop_state: **returned** / target_queue: material_queue / ratify_required: False / requeue_expected: True
- need_more_type: evidence_unverified
- missing_materials:
  - legallib raw JSON 3サンプル（通常/索引あり/深いTOC）
  - 確定 mapping table（top-level/author/TOC/index）
  - --dry-run --limit 3 の出力例
  - 既存 asai-bookshelf/bencom 差分0 test
  - 再実行 diff 0 test
- owner_digest_5line:
  ```
  監査: legallibbiblio v0.5（蔵書ingest）
  結論: NEED_MORE（生JSON未確認がingest blocker）
  理由: loader入力の実shapeが未確定のままPASS不可
  次アクション: 生JSON3サンプル+dry-run evidenceを添えて再投函
  Owner確認: 不要（資料補充ルート）
  ```
- claude_rethink_prompt: 設計方向は良いが ingest gate は資料不足。実物3冊のJSONサンプルと確定mapping、dry-run diff0 evidence を出せば差分再監査で PASS_WITH_NOTES まで上がる。
- result_file_id: 2269719016248

### next_action = ratify（PASS/PASS_WITH_NOTES → blocking反映後 Owner ratify）

#### 20260605_claudehead_v1.1_DDCLAUDEHEAD  `[DDCLAUDEHEAD_PASS_WITH_NOTES]`
- loop_state: **ratify_wait** / target_queue: approval_queue / ratify_required: True / requeue_expected: False
- blocking_before_ratify:
  - 第二instance=hand/capacity(planner含む,head/auditorでない)へ表現修正
  - cost lane: Google alias $0 と Anthropic $400/月を分離記述
  - §E に v1.0/F5 fallback path 参照と head落ち時の可否を明記
  - 「canonical兄弟」→「companion/pending related」へ弱化
- owner_digest_5line:
  ```
  監査: claudehead v1.1（第二Anthropic）
  結論: PASS_WITH_NOTES
  理由: A-1公理(容量増≠監査独立)は採用可。軽微notesのみ
  次アクション: 4点反映後 浅井ratifyで accepted 化
  Owner確認: ratify必要
  ```
- claude_rethink_prompt: 再T2不要。blocking 4点（role label, cost lane分離, F5 fallback参照, canonical兄弟弱化）を accepted body に反映し、浅井ratifyで v1.1 accepted 化。
- result_file_id: 2268831609533

#### 20260605_matterevent_v0.5.1_DDMATTEREVENT  `[DDMATTEREVENT_PASS_WITH_NOTES]`
- loop_state: **ratify_wait** / target_queue: approval_queue / ratify_required: True / requeue_expected: False
- blocking_before_ratify:
  - v0.5.1-integrated migration SQL を1本に統合（v0.3 annex/v0.5 canonical を直接当てない）
  - old-snippet exclusion test (S2) を通す
  - canonical index で v0.5.1 を優先パッチと明示
- owner_digest_5line:
  ```
  監査: matterevent v0.5.1（動的スキーマ）
  結論: PASS_WITH_NOTES（migration-ready）
  理由: P-1〜P-4をdry-runで機構検証済み。v0.6不要
  次アクション: v0.5.1-integrated migration pack 作成、五宝miniパイロット
  Owner確認: 本番DDLは浅井GO必要
  ```
- claude_rethink_prompt: v0.6 は作らない。v0.5 canonical + v0.5.1 patch + dry-run を統合した migration pack を1本作り、古い断片(v0.3 annex/v0.5)を混ぜない。SF writeback/会計射影/外部LLM送出は禁止のまま五宝1文書から段階パイロット。
- result_file_id: 2266769629679

#### 20260606_codexgov_v0.1_IMPL  `[IMPL_PASS_WITH_NOTES]`
- loop_state: **ratify_wait** / target_queue: approval_queue / ratify_required: True / requeue_expected: False
- blocking_before_ratify:
  - service_role bypass を README で運用ゲート化（手元scriptからINSERTしない）
  - prod受入に validated_at/by/row_hash/source/gate_run_id を必須化検討
  - legaldb-candidate-status.md に current_design_gate_result を持たせ追従
- owner_digest_5line:
  ```
  監査: codexgov v0.1（静的RDBガバナンス基盤）
  結論: IMPL_PASS_WITH_NOTES（採用可）
  理由: clean-only/環境分離/candidate物理ブロックは整合
  次アクション: legaldbはlanding/candidate維持しpromotion block外さない
  Owner確認: governance基盤はratify可 / legaldb昇格は不可
  ```
- claude_rethink_prompt: ガバナンス基盤は採用可。legaldb v0.5系は landing-only/promotion blocked を維持。service_role運用の明文化と current_design_gate_result 追跡を追記。
- result_file_id: 2269703399814

#### 20260606_statusregistry_v0.2_DDSTATUS  `[DDSTATUS_PASS]`
- loop_state: **ratify_wait** / target_queue: approval_queue / ratify_required: True / requeue_expected: False
- owner_digest_5line:
  ```
  監査: statusregistry v0.2（状態語彙・差分再監査）
  結論: PASS（owner_ratify_ready）
  理由: v0.1のself-consistency欠陥(P0-PATCH 1-5)を全CLOSED
  次アクション: 浅井ratify後 accepted。candidate段階ではbackfillしない
  Owner確認: ratify必要
  ```
- claude_rethink_prompt: 差分再監査 PASS。浅井ratify で accepted 化。ratify までは design_decisions/Generated Index へ backfill しない運用を維持。
- result_file_id: 2269658306240

#### 20260607_canonicalindex_v0.1_DDINDEXDISPO  `[DDINDEXDISPO_PASS_WITH_NOTES]`
- loop_state: **returned** / target_queue: approval_queue / ratify_required: True / requeue_expected: False
- blocking_before_ratify:
  - ALO_CANONICAL_INDEX_20260605 を superseded/historical snapshot marker 化
  - DD-STATUS-REGISTRY-001 v0.2.1 SoT pointer patch（§5.3のみ）作成
  - v0.2.1 を owner ratify で accepted
  - full refresh / 部分追記はしない
- owner_digest_5line:
  ```
  監査: canonicalindex 処分判断
  結論: PASS_WITH_NOTES（案(二)採用）
  理由: 状態SoTを design_decisions Generated Index へ一本化が妥当
  次アクション: index退役表示 + registry v0.2.1 narrow pointer patch
  Owner確認: 処分はratify可
  ```
- claude_rethink_prompt: 「触らない」で止めない。ALO_CANONICAL_INDEX を superseded marker 化し、DD-STATUS-REGISTRY v0.2.1 で §5.3 SoT pointer のみ差し替え、owner ratify。full refresh も部分追記もしない。
- result_file_id: 2270473891101

#### 20260607_caselink_CASELINKDM  `[CASELINKDM_PASS_WITH_NOTES]`
- loop_state: **ratify_wait** / target_queue: approval_queue / ratify_required: True / requeue_expected: False
- blocking_before_ratify:
  - party_alias confirmed に confirmed_by/at/evidence_strength/review_basis 必須+CHECK
  - inference_log に training_eligible/training_disposition（既定false）
  - enum migration idempotency（rejected/superseded 既存時）
- owner_digest_5line:
  ```
  監査: caselink データモデル差分(DM)
  結論: CASELINKDM_PASS_WITH_NOTES（非破壊差分として採用可）
  理由: party_alias/link_policy/non_matter_type 方向は妥当
  次アクション: confirmed alias条件と再学習除外をDBで強制してP2 DDL
  Owner確認: 方向ratify可 / 実装はP2 DDL review
  ```
- claude_rethink_prompt: v0.3非破壊差分として採用可。実装順は enum保証→inference_log拡張→party_alias→link_policy→non_matter_type。confirmed alias の根拠必須と rejected/superseded の training除外を DB CHECK で物理化してから P2 DDL。
- result_file_id: 2269842057063

#### 20260607_codexprogress_v0.2_DDPROGRESS  `[DDPROGRESS_PASS_WITH_NOTES]`
- loop_state: **ratify_wait** / target_queue: approval_queue / ratify_required: True / requeue_expected: False
- blocking_before_ratify:
  - N1: dashboard one-shot route でも manifest不正時は probe前に止める
- owner_digest_5line:
  ```
  監査: codexprogress v0.2（進捗dashboard差分）
  結論: PASS_WITH_NOTES（runtime dashboardとして採用可）
  理由: v0.1の6点中5点CLOSED。F4はone-shot経路のみ未閉
  次アクション: N1(manifest検証をprobe前に強制)を小修正
  Owner確認: ratify可（N1反映推奨）
  ```
- claude_rethink_prompt: pipeline_dashboard.py --root 経路でも validate_manifest をprobe前に呼び、errorなら return 1。N1反映で前回F4も完全閉鎖。正本状態表でなく観測dashboard扱い。
- result_file_id: 2270064515801

#### 20260607_lawtime_v0.2.1_DDLAWTIME  `[DDLAWTIME_PASS_WITH_NOTES]`
- loop_state: **ratify_wait** / target_queue: approval_queue / ratify_required: True / requeue_expected: False
- blocking_before_ratify:
  - P1: article_path_json の扱いを明記（v0.2.1はlaw_revision_id解決までがscope）
  - P2: edge_id 型を alo_edges PK に合わせFK化 / gate_temporal_eval_edge_exists
  - P3: repeal_and_reenact→abolish_and_replace の rename map
  - P4: gate_claim_support_requires_resolved_lawtime
  - P5: gate_succession_event_group_consistency
- owner_digest_5line:
  ```
  監査: lawtime v0.2.1（法令時間モデル）
  結論: PASS_WITH_NOTES（design採用可）
  理由: v0.2のN1-N4をCLOSED。v0.5.1の自称v0.2.1を正規ラインに再接地
  次アクション: owner ratify。production DDLはP1-P5+D6 gate後
  Owner確認: ratify可（designとして）
  ```
- claude_rethink_prompt: DD-LAWTIME v0.2.1 を design として owner ratify。これで legaldb の F4 依存先が 確定する。production DDL は P1-P5 notes と D6 executable gates を満たしてから。
- result_file_id: 2270935890940

#### 20260607_sessionaudit_SESSIONAUDIT  `[SESSIONAUDIT_PASS_WITH_NOTES]`
- loop_state: **returned** / target_queue: approval_queue / ratify_required: True / requeue_expected: False
- blocking_before_ratify:
  - DD_LEDGER_RECONCILIATION タスク起票（design_decisions/90_/DD_REGISTRY.json/ALO_CANONICAL_INDEX 4点）
  - accepted artifact の暫定索引を非破壊sidecar/queue cardで補う
  - 大型正本への手差し編集はしない
- owner_digest_5line:
  ```
  監査: sessionaudit（番頭session process監査）
  結論: PASS_WITH_NOTES（process discipline OK）
  理由: 台帳保留は破損防止の正しい分離。ただしfollow-up要明示化
  次アクション: DD台帳reconciliation を P0/P1 タスク化
  Owner確認: 不要（reconcileタスク化のみ）
  ```
- claude_rethink_prompt: 本passの監査レーン台帳(_AUDIT_LEDGER.jsonl)整備とは別に、DD正本台帳(design_decisions.md/90_/DD_REGISTRY.json/ALO_CANONICAL_INDEX)の reconciliation を 明示P0/P1で起票。accepted済 claudehead v1.1/matterevent の索引可視性を短期で補う。大型正本への手差し編集はしない。
- result_file_id: 2269851722287

#### 20260607_toclegalref_v0.2_DDTOCLEGALREF  `[DDTOCLEGALREF_PASS_WITH_NOTES]`
- loop_state: **ratify_wait** / target_queue: approval_queue / ratify_required: True / requeue_expected: False
- blocking_before_ratify:
  - production promotion前: 弱い表示名(toc_signal/toc_mentions)定義
  - DD-LAWTIME ratify後 backfill条件を本文追加
  - medium quarantine 解除条件を gold set precision基準で定義
  - dedup_key を extraction_policy_id/major version 粒度へ
- owner_digest_5line:
  ```
  監査: toclegalref v0.2（蔵書TOC→link layer差分）
  結論: PASS_WITH_NOTES（design candidate として accept可）
  理由: v0.1の危険(強いedge意味/temporal先取り)を安全側に閉鎖
  次アクション: owner ratify。production昇格はN1-N4 gate後
  Owner確認: ratify可（designとして）
  ```
- claude_rethink_prompt: TOC由来参照は法律判断の根拠でなく candidate toc_signal(claim_support不可)として link layer に入れる限り accept可。owner ratify 後、production promotion 前に 弱い表示名・lawtime後backfill条件・medium解除閾値・dedup粒度を閉じる。
- result_file_id: 2270358722334

---

## 反映・requeue 済（参考 / action不要）

- 20260605_lawtime_v0.1_DD `[DDLAWTIME_MODIFY_REQUIRED]` — loop_state: requeued — 本RESULTは v0.2 / v0.2.1 で消化済み。lawtime の最新監査は v0.2.1 (DDLAWTIM…
- 20260605_matterevent_v0.5.1_DDMATTEREVENT_REQUEST `[DDMATTEREVENT_PASS_WITH_NOTES]` — loop_state: reflected — REQUEST_RESULT 名の重複保存。正本 matterevent RESULT (result_file_id …
- 20260605_statusregistry_v0.1_DDSTATUS `[DDSTATUS_MODIFY_REQUIRED]` — loop_state: requeued — v0.2 (DDSTATUS_PASS) で閉鎖済み。最新は statusregistry v0.2 を参照。…
- 20260606_caselink_CASELINK `[CASELINK_PASS_WITH_NOTES]` — loop_state: requeued — 説明レイヤ監査は CASELINKDM(20260607) の DM 差分監査へ引き継がれた。alias/旧姓は確定でな…
- 20260606_codexprogress_v0.1_DDPROGRESS `[DDPROGRESS_PASS_WITH_NOTES]` — loop_state: requeued — v0.2 (DDPROGRESS_PASS_WITH_NOTES, N1のみ残) で消化済み。最新は v0.2 参照。…
- 20260606_legaldb_v0.5_DESIGN `[DESIGN_MODIFY_REQUIRED]` — loop_state: requeued — v0.5.1 へ消化済み（さらに v0.6 を to_gpt に投函済み）。最新版を参照。…
- 20260606_toclegalref_v0.1_DDTOCLEGALREF `[DDTOCLEGALREF_MODIFY_REQUIRED]` — loop_state: requeued — v0.2 (DDTOCLEGALREF_PASS_WITH_NOTES) で消化済み。最新は v0.2 を参照。…
- 20260607_lawtime_v0.2_DDLAWTIME `[DDLAWTIME_PASS_WITH_NOTES]` — loop_state: requeued — v0.2.1 で N1-N4 を閉じ済み。lawtime 最新監査は v0.2.1 を参照。…
- 20260607_legaldb_v0.5.1_DESIGN `[DESIGN_MODIFY_REQUIRED]` — loop_state: requeued — v0.5.1 は v0.5 より大幅改善だが F4 の lawtime 依存が未確認 accepted を前提にして r…
- 20260607_purchaserec_v0.1_DESIGN `[DESIGN_MODIFY_REQUIRED]` — loop_state: requeued — books.json SoT・bookdx_*はread replica方針は妥当。RLS/private schema…
- 20260607_queueaudit_GPTQUEUE `[GPTQUEUE_PASS_WITH_NOTES]` — loop_state: requeued — queueaudit は状態確認としては妥当。loop review(20260608)で MODIFY_REQUIRE…
