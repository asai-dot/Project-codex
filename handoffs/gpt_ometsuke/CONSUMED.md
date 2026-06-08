# CONSUMED — GPT RESULT に対する Claude の採用判断記録

> **自動生成。手で編集しない。** 真実は `QUEUE_EVENTS.jsonl` の CONSUMED イベント。
> 再生成: `python3 tools/gpt_audit/queue.py build`

- generated_at: 2026-06-08T11:01:39+09:00
- 目的: GPT RESULT を Claude が **読んだだけでなく、採用/不採用/反映内容まで** 記録し、
  「読んだのに反映していない」「不採用にした理由が残っていない」事故を潰す。

記録 **25** 件。

## `20260605_ccguard_v0.1.1_G0`

- result_label: `G0_MODIFY_REQUIRED`
- result_file_id (Box): `2266430431171`
- 判断: **採用**
- 反映状態: 未反映 / ratify: 不要
- 現在状態: **未反映**
- GPT結論(要旨): MODIFY_REQUIRED: shell/SQL迂回余地・unknown tool fail-open・G3未実施
- 反映内容/次アクション: v0.1.2 で bypass群(shell/eval/heredoc/encoded, mcp unknown=ask, Box/GDrive mutation=ask, SQL project ref allowlist + alo-connect hard-deny) を閉じ G3 live dry-run 後に再レビュー

## `20260605_claudehead_v1.1_DDCLAUDEHEAD`

- result_label: `DDCLAUDEHEAD_PASS_WITH_NOTES`
- result_file_id (Box): `2268831609533`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 要・未
- 現在状態: **浅井判断待ち**
- GPT結論(要旨): PASS_WITH_NOTES: A-1公理(容量増≠監査独立)採用可。軽微notesのみ
- 反映内容/次アクション: blocking 4点(role label, cost lane分離, F5 fallback参照, canonical兄弟弱化)を accepted body に反映済。浅井 ratify で v1.1 accepted 化

## `20260605_lawtime_v0.1_DD`

- result_label: `DDLAWTIME_MODIFY_REQUIRED`
- result_file_id (Box): `—`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 不要
- 現在状態: **closed**
- GPT結論(要旨): MODIFY_REQUIRED
- 反映内容/次アクション: v0.2 / v0.2.1 で消化済
- 後続: `20260607_lawtime_v0.2.1_DDLAWTIME` に置換

## `20260605_matterevent_v0.5.1_DDMATTEREVENT`

- result_label: `DDMATTEREVENT_PASS_WITH_NOTES`
- result_file_id (Box): `2266769629679`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 要・未
- 現在状態: **浅井判断待ち**
- GPT結論(要旨): PASS_WITH_NOTES(migration-ready): P-1〜P-4 を dry-run で機構検証済
- 反映内容/次アクション: v0.5.1-integrated migration pack 反映済。本番DDL は浅井GO必要 (五宝miniパイロット)

## `20260605_matterevent_v0.5.1_DDMATTEREVENT_REQUEST`

- result_label: `DDMATTEREVENT_PASS_WITH_NOTES`
- result_file_id (Box): `—`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 不要
- 現在状態: **closed**
- GPT結論(要旨): PASS_WITH_NOTES(重複保存)
- 反映内容/次アクション: 正本 record に統合済

## `20260605_quasijudicial_v0.4_DDCASESOURCE`

- result_label: `DDCASESOURCE_NEED_MORE`
- result_file_id (Box): `2268867415119`
- 判断: **保留 (資料補充)**
- need_more_type: `material_absent`
- 反映状態: 未反映 / ratify: 不要
- 現在状態: **未反映**
- GPT結論(要旨): NEED_MORE: 対象正本5点が Box(docs/alo) 不在で内容監査不能
- 反映内容/次アクション: 対象5点を Box 復旧 → source_hash 埋め → status:queued で再投函 (資料復旧ルート)

## `20260605_statusregistry_v0.1_DDSTATUS`

- result_label: `DDSTATUS_MODIFY_REQUIRED`
- result_file_id (Box): `—`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 不要
- 現在状態: **closed**
- GPT結論(要旨): MODIFY_REQUIRED
- 反映内容/次アクション: v0.2 (DDSTATUS_PASS) で閉鎖済
- 後続: `20260606_statusregistry_v0.2_DDSTATUS` に置換

## `20260606_caselink_CASELINK`

- result_label: `CASELINK_PASS_WITH_NOTES`
- result_file_id (Box): `—`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 不要
- 現在状態: **closed**
- GPT結論(要旨): PASS_WITH_NOTES
- 反映内容/次アクション: 実装は CASELINKDM(20260607) へ引き継ぎ
- 後続: `20260607_caselink_CASELINKDM` に置換

## `20260606_codexgov_v0.1_IMPL`

- result_label: `IMPL_PASS_WITH_NOTES`
- result_file_id (Box): `2269703399814`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 要・未
- 現在状態: **浅井判断待ち**
- GPT結論(要旨): IMPL_PASS_WITH_NOTES: clean-only/環境分離/candidate物理ブロック整合
- 反映内容/次アクション: governance基盤は ratify可。legaldb は landing/candidate維持し promotion block 外さない

## `20260606_codexprogress_v0.1_DDPROGRESS`

- result_label: `DDPROGRESS_PASS_WITH_NOTES`
- result_file_id (Box): `—`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 不要
- 現在状態: **closed**
- GPT結論(要旨): PASS_WITH_NOTES
- 反映内容/次アクション: v0.2 で消化済
- 後続: `20260607_codexprogress_v0.2_DDPROGRESS` に置換

## `20260606_legaldb_v0.5_DESIGN`

- result_label: `DESIGN_MODIFY_REQUIRED`
- result_file_id (Box): `—`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 不要
- 現在状態: **closed**
- GPT結論(要旨): MODIFY_REQUIRED
- 反映内容/次アクション: v0.5.1→v0.6 で再投函済
- 後続: `20260607_legaldb_v0.5.1_DESIGN` に置換

## `20260606_legallibbiblio_v0.5_INGEST`

- result_label: `INGEST_NEED_MORE`
- result_file_id (Box): `2269719016248`
- 判断: **保留 (資料補充)**
- need_more_type: `evidence_unverified`
- 反映状態: 未反映 / ratify: 不要
- 現在状態: **未反映**
- GPT結論(要旨): NEED_MORE: 生JSON未確認が ingest blocker
- 反映内容/次アクション: 生JSON3サンプル + 確定mapping + dry-run diff0 evidence を添えて差分再投函

## `20260606_statusregistry_v0.2_DDSTATUS`

- result_label: `DDSTATUS_PASS`
- result_file_id (Box): `2269658306240`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 要・未
- 現在状態: **浅井判断待ち**
- GPT結論(要旨): PASS(owner_ratify_ready): v0.1 の self-consistency 欠陥 P0-PATCH 1-5 全CLOSED
- 反映内容/次アクション: 浅井 ratify 後 accepted。candidate段階では Generated Index に backfill しない

## `20260606_toclegalref_v0.1_DDTOCLEGALREF`

- result_label: `DDTOCLEGALREF_MODIFY_REQUIRED`
- result_file_id (Box): `—`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 不要
- 現在状態: **closed**
- GPT結論(要旨): MODIFY_REQUIRED
- 反映内容/次アクション: v0.2 で消化済
- 後続: `20260607_toclegalref_v0.2_DDTOCLEGALREF` に置換

## `20260607_canonicalindex_v0.1_DDINDEXDISPO`

- result_label: `DDINDEXDISPO_PASS_WITH_NOTES`
- result_file_id (Box): `2270473891101`
- 判断: **採用**
- 反映状態: 未反映 / ratify: 要・未
- 現在状態: **未反映**
- GPT結論(要旨): PASS_WITH_NOTES(案二採用): 状態SoTを design_decisions Generated Index へ一本化
- 反映内容/次アクション: ALO_CANONICAL_INDEX を superseded marker 化 + registry v0.2.1 §5.3 pointer patch 後に ratify。full refresh も部分追記もしない

## `20260607_caselink_CASELINKDM`

- result_label: `CASELINKDM_PASS_WITH_NOTES`
- result_file_id (Box): `2269842057063`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 要・未
- 現在状態: **浅井判断待ち**
- GPT結論(要旨): CASELINKDM_PASS_WITH_NOTES: 非破壊差分として採用可
- 反映内容/次アクション: 方向 ratify可。confirmed alias 根拠必須と再学習除外を DB CHECK で物理化してから P2 DDL

## `20260607_codexprogress_v0.2_DDPROGRESS`

- result_label: `DDPROGRESS_PASS_WITH_NOTES`
- result_file_id (Box): `2270064515801`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 要・未
- 現在状態: **浅井判断待ち**
- GPT結論(要旨): PASS_WITH_NOTES: runtime dashboard として採用可。v0.1 の5点CLOSED
- 反映内容/次アクション: N1(manifest検証をprobe前に強制)反映済。観測dashboard扱い (正本状態表ではない)

## `20260607_lawtime_v0.2.1_DDLAWTIME`

- result_label: `DDLAWTIME_PASS_WITH_NOTES`
- result_file_id (Box): `2270935890940`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 要・未
- 現在状態: **浅井判断待ち**
- GPT結論(要旨): PASS_WITH_NOTES(design採用可): v0.2 の N1-N4 を CLOSED
- 反映内容/次アクション: design として浅井 ratify。production DDL は P1-P5 notes + D6 executable gates 後

## `20260607_lawtime_v0.2_DDLAWTIME`

- result_label: `DDLAWTIME_PASS_WITH_NOTES`
- result_file_id (Box): `—`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 不要
- 現在状態: **closed**
- GPT結論(要旨): PASS_WITH_NOTES
- 反映内容/次アクション: v0.2.1 で N1-N4 を閉じ済
- 後続: `20260607_lawtime_v0.2.1_DDLAWTIME` に置換

## `20260607_legaldb_v0.5.1_DESIGN`

- result_label: `DESIGN_MODIFY_REQUIRED`
- result_file_id (Box): `—`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 不要
- 現在状態: **closed**
- GPT結論(要旨): MODIFY_REQUIRED(F4 lawtime依存)
- 反映内容/次アクション: v0.6 で再投函済
- 後続: `20260607_legaldb_v0.6_DESIGN` に置換

## `20260607_purchaserec_v0.1_DESIGN`

- result_label: `DESIGN_MODIFY_REQUIRED`
- result_file_id (Box): `—`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 不要
- 現在状態: **closed**
- GPT結論(要旨): MODIFY_REQUIRED
- 反映内容/次アクション: v0.2 で再投函済
- 後続: `20260607_purchaserec_v0.2_DESIGN` に置換

## `20260607_queueaudit_GPTQUEUE`

- result_label: `GPTQUEUE_PASS_WITH_NOTES`
- result_file_id (Box): `—`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 不要
- 現在状態: **closed**
- GPT結論(要旨): PASS_WITH_NOTES
- 反映内容/次アクション: loop review(20260608) で MODIFY、本pass で実装
- 後続: `20260608_queueaudit_loop_GPTQUEUE_REVIEW` に置換

## `20260607_sessionaudit_SESSIONAUDIT`

- result_label: `SESSIONAUDIT_PASS_WITH_NOTES`
- result_file_id (Box): `2269851722287`
- 判断: **採用**
- 反映状態: 未反映 / ratify: 要・未
- 現在状態: **未反映**
- GPT結論(要旨): PASS_WITH_NOTES: process discipline OK。台帳保留は破損防止の正しい分離
- 反映内容/次アクション: DD正本台帳(design_decisions/90_/DD_REGISTRY.json/ALO_CANONICAL_INDEX) reconciliation を P0/P1 起票。大型正本への手差し編集はしない

## `20260607_toclegalref_v0.2_DDTOCLEGALREF`

- result_label: `DDTOCLEGALREF_PASS_WITH_NOTES`
- result_file_id (Box): `2270358722334`
- 判断: **採用**
- 反映状態: 反映済 / ratify: 要・未
- 現在状態: **浅井判断待ち**
- GPT結論(要旨): PASS_WITH_NOTES: 危険(強edge意味/temporal先取り)を安全側に閉鎖
- 反映内容/次アクション: candidate toc_signal(claim_support不可)として link layer に入れる限り採用可。production昇格は N1-N4 gate 後

## `20260608_queueaudit_loop_GPTQUEUE_REVIEW`

- result_label: `GPTQUEUE_MODIFY_REQUIRED`
- result_file_id (Box): `2270920897721`
- 判断: **採用**
- 反映状態: 未反映 / ratify: 不要
- 現在状態: **未反映**
- GPT結論(要旨): MODIFY_REQUIRED: action ledger 未実体化・processed 物理退避未完了
- 反映内容/次アクション: 本pass で台帳/action-queue/退避を実装し GPTQUEUELOOPIMPL_REQUEST で再投函。GPT 再監査 PASS で reflected 化
