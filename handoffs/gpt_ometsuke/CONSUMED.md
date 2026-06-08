# CONSUMED — GPT RESULT に対する Claude の採用判断ビュー

> **自動生成。手で編集しない。** 出典は v0.3 監査レーン台帳 `_AUDIT_LEDGER.jsonl`。
> 再生成: `python3 tools/gpt_audit/consumed_view.py build`
> これは v0.3 レーンへの **派生ビュー追加** であり、別の状態システムではない。

- generated_at: 2026-06-08T11:20:06+09:00
- source_ledger: `tools/gpt_audit/_AUDIT_LEDGER.snapshot.jsonl` (正本は Box `_AUDIT_LEDGER.jsonl` file_id 2271040382325)

## 要約

消費済 RESULT **25** 件 / うち **未反映 6** 件 (= 読んだが設計反映・再投函・資料補充が未完。`reflected:false`)。

| 判断の読み替え | next_action_type |
|---|---|
| 採用 | ratify / none |
| 採用(要修正) | patch (MODIFY_REQUIRED) |
| 保留(資料補充) | required_materials (NEED_MORE) |
| 不採用 | reject (FAIL) |

## 未反映 — 読んだが反映/再投函/資料補充が未完

| request_id | label | 判断 | GPT結論(要旨) | 反映内容 / 次アクション |
|---|---|---|---|---|
| `20260605_ccguard_v0.1.1_G0` | `G0_MODIFY_REQUIRED` | 採用(要修正) | MODIFY_REQUIRED: shell/SQL迂回余地・unknown tool fail-open・G3未実施 | v0.1.2 で bypass群(shell/eval/heredoc/encoded, mcp unknown=ask, Box/GDrive mutation=ask, SQL allowlist+alo-connect hard-deny)を閉じ G3 live dry-run 後に再レビュー |
| `20260605_quasijudicial_v0.4_DDCASESOURCE` | `DDCASESOURCE_NEED_MORE` | 保留(資料補充) | NEED_MORE: 対象正本5点が Box(docs/alo) 不在で内容監査不能 | [material_absent] 対象5点を Box 復旧→source_hash 埋め→status:queued で再投函(資料復旧ルート) |
| `20260606_legallibbiblio_v0.5_INGEST` | `INGEST_NEED_MORE` | 保留(資料補充) | NEED_MORE: 生JSON未確認が ingest blocker | [evidence_unverified] 生JSON3サンプル+確定mapping+dry-run diff0 evidence を添えて差分再投函 |
| `20260607_canonicalindex_v0.1_DDINDEXDISPO` | `DDINDEXDISPO_PASS_WITH_NOTES` | 採用 | PASS_WITH_NOTES(案二採用): 状態SoTを design_decisions Generated Index へ一本化 | ALO_CANONICAL_INDEX を superseded marker化 + registry v0.2.1 §5.3 pointer patch 後に ratify。full refresh も部分追記もしない |
| `20260607_sessionaudit_SESSIONAUDIT` | `SESSIONAUDIT_PASS_WITH_NOTES` | 採用 | PASS_WITH_NOTES: process discipline OK。台帳保留は破損防止の正しい分離 | DD正本台帳(design_decisions/90_/DD_REGISTRY.json/ALO_CANONICAL_INDEX) reconciliation を P0/P1 起票。大型正本への手差し編集はしない |
| `20260608_queueaudit_loop_GPTQUEUE_REVIEW` | `GPTQUEUE_MODIFY_REQUIRED` | 採用(要修正) | MODIFY_REQUIRED: action ledger未実体化・processed物理退避未完了 | 台帳/action-queue/退避を実装し GPTQUEUELOOPIMPL_REQUEST で再投函。GPT再監査PASSで reflected化 |

## ratify待ち — 反映済・浅井判断待ち

| request_id | label | 判断 | GPT結論(要旨) | 反映内容 / 次アクション |
|---|---|---|---|---|
| `20260605_claudehead_v1.1_DDCLAUDEHEAD` | `DDCLAUDEHEAD_PASS_WITH_NOTES` | 採用 | PASS_WITH_NOTES: A-1公理(容量増≠監査独立)採用可。軽微notesのみ | blocking 4点(role label, cost lane分離, F5 fallback参照, canonical兄弟弱化)を accepted body に反映済。浅井 ratify で v1.1 accepted化 |
| `20260605_matterevent_v0.5.1_DDMATTEREVENT` | `DDMATTEREVENT_PASS_WITH_NOTES` | 採用 | PASS_WITH_NOTES(migration-ready): P-1〜P-4 を dry-run で機構検証済 | v0.5.1-integrated migration pack 反映済。本番DDL は浅井GO必要(五宝miniパイロット) |
| `20260606_codexgov_v0.1_IMPL` | `IMPL_PASS_WITH_NOTES` | 採用 | IMPL_PASS_WITH_NOTES: clean-only/環境分離/candidate物理ブロック整合 | governance基盤は ratify可。legaldb は landing/candidate維持し promotion block 外さない |
| `20260606_statusregistry_v0.2_DDSTATUS` | `DDSTATUS_PASS` | 採用 | PASS(owner_ratify_ready): v0.1 の self-consistency 欠陥 P0-PATCH 1-5 全CLOSED | 浅井 ratify 後 accepted。candidate段階では Generated Index に backfill しない |
| `20260607_caselink_CASELINKDM` | `CASELINKDM_PASS_WITH_NOTES` | 採用 | CASELINKDM_PASS_WITH_NOTES: 非破壊差分として採用可 | 方向 ratify可。confirmed alias 根拠必須と再学習除外を DB CHECK で物理化してから P2 DDL |
| `20260607_codexprogress_v0.2_DDPROGRESS` | `DDPROGRESS_PASS_WITH_NOTES` | 採用 | PASS_WITH_NOTES: runtime dashboard として採用可。v0.1 の5点CLOSED | N1(manifest検証をprobe前に強制)反映済。観測dashboard扱い(正本状態表ではない) |
| `20260607_lawtime_v0.2.1_DDLAWTIME` | `DDLAWTIME_PASS_WITH_NOTES` | 採用 | PASS_WITH_NOTES(design採用可): v0.2 の N1-N4 を CLOSED | design として浅井 ratify。production DDL は P1-P5 notes + D6 executable gates 後 |
| `20260607_toclegalref_v0.2_DDTOCLEGALREF` | `DDTOCLEGALREF_PASS_WITH_NOTES` | 採用 | PASS_WITH_NOTES: 危険(強edge意味/temporal先取り)を安全側に閉鎖 | candidate toc_signal(claim_support不可)として link layer に入れる限り採用可。production昇格は N1-N4 gate 後 |

## 反映済(後続へ) — 反映の上で新 version に置換

| request_id | label | 判断 | GPT結論(要旨) | 反映内容 / 次アクション |
|---|---|---|---|---|
| `20260605_lawtime_v0.1_DD` | `DDLAWTIME_MODIFY_REQUIRED` | 採用(要修正) | MODIFY_REQUIRED | v0.2 / v0.2.1 で消化済 |
| `20260605_statusregistry_v0.1_DDSTATUS` | `DDSTATUS_MODIFY_REQUIRED` | 採用(要修正) | MODIFY_REQUIRED | v0.2 (DDSTATUS_PASS) で閉鎖済 |
| `20260606_caselink_CASELINK` | `CASELINK_PASS_WITH_NOTES` | 採用 | PASS_WITH_NOTES | 実装は CASELINKDM(20260607) へ引き継ぎ |
| `20260606_codexprogress_v0.1_DDPROGRESS` | `DDPROGRESS_PASS_WITH_NOTES` | 採用 | PASS_WITH_NOTES | v0.2 で消化済 |
| `20260606_legaldb_v0.5_DESIGN` | `DESIGN_MODIFY_REQUIRED` | 採用(要修正) | MODIFY_REQUIRED | v0.5.1→v0.6 で再投函済 |
| `20260606_toclegalref_v0.1_DDTOCLEGALREF` | `DDTOCLEGALREF_MODIFY_REQUIRED` | 採用(要修正) | MODIFY_REQUIRED | v0.2 で消化済 |
| `20260607_lawtime_v0.2_DDLAWTIME` | `DDLAWTIME_PASS_WITH_NOTES` | 採用 | PASS_WITH_NOTES | v0.2.1 で N1-N4 を閉じ済 |
| `20260607_legaldb_v0.5.1_DESIGN` | `DESIGN_MODIFY_REQUIRED` | 採用(要修正) | MODIFY_REQUIRED(F4 lawtime依存) | v0.6 で再投函済 |
| `20260607_purchaserec_v0.1_DESIGN` | `DESIGN_MODIFY_REQUIRED` | 採用(要修正) | MODIFY_REQUIRED | v0.2 で再投函済 |
| `20260607_queueaudit_GPTQUEUE` | `GPTQUEUE_PASS_WITH_NOTES` | 採用 | PASS_WITH_NOTES | loop review(20260608) で MODIFY、後続で実装 |

## 反映済

| request_id | label | 判断 | GPT結論(要旨) | 反映内容 / 次アクション |
|---|---|---|---|---|
| `20260605_matterevent_v0.5.1_DDMATTEREVENT_REQUEST` | `DDMATTEREVENT_PASS_WITH_NOTES` | 採用 | PASS_WITH_NOTES(重複保存) | REQUEST_RESULT 名の重複保存。正本は result_file_id 2266769629679 に統合 |
