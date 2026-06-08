# QUEUE_INDEX — GPT お目付け役 監査キュー 現在状態台帳

> **自動生成。手で編集しない。** 真実は `QUEUE_EVENTS.jsonl`。
> 再生成: `python3 tools/gpt_audit/queue.py build`

- generated_at: 2026-06-08T11:01:39+09:00
- source: `handoffs/gpt_ometsuke/QUEUE_EVENTS.jsonl`
- protocol: `handoffs/gpt_ometsuke/PROTOCOL.md` (GPT_OMETSUEKE_QUEUE_PROTOCOL v0.2)
- Box 正本との対応: QUEUE_EVENTS.jsonl ⇔ `_AUDIT_LEDGER.jsonl` / QUEUE_INDEX.md ⇔ `_ACTION_QUEUE.md` (PROTOCOL.md §crosswalk)

## 件数分類 (状態報告)

全 **25** 件 / 未済 **14** 件 / closed **11** 件

| 状態 | 件数 | 意味 |
|---|---|---|
| 未監査 | 0 | REQUEST はあるが GPT RESULT 未着 |
| 未消費 | 0 | RESULT はあるが Claude が読んで判断していない |
| 未反映 | 6 | 消費済だが設計反映/再投函/資料補充が未完 |
| 浅井判断待ち | 8 | 反映済だが浅井先生の ratify 待ち |
| closed | 11 | 反映 (+ratify) まで到達し閉じた / 後続に置換 |

## 未監査 — GPT 返答待ち

_(該当なし)_

## 未消費 — Claude 取り込み待ち

_(該当なし)_

## 未反映 — Claude 作業待ち (patch / 資料補充 / 再投函)

| request_id | topic | label | next_action | 最終更新 |
|---|---|---|---|---|
| `20260605_ccguard_v0.1.1_G0` | ccguard | `G0_MODIFY_REQUIRED` | v0.1.2 で bypass群(shell/eval/heredoc/encoded, mcp unknown=ask, Box/GDrive mutation=ask, SQL project ref allowlist + alo-connect hard-deny) を閉じ G3 live dry-run 後に再レビュー | 2026-06-08 |
| `20260608_queueaudit_loop_GPTQUEUE_REVIEW` | queueaudit | `GPTQUEUE_MODIFY_REQUIRED` | 本pass で台帳/action-queue/退避を実装し GPTQUEUELOOPIMPL_REQUEST で再投函。GPT 再監査 PASS で reflected 化 | 2026-06-08 |
| `20260605_quasijudicial_v0.4_DDCASESOURCE` | quasijudicial | `DDCASESOURCE_NEED_MORE` | [material_absent] 対象5点を Box 復旧 → source_hash 埋め → status:queued で再投函 (資料復旧ルート) | 2026-06-08 |
| `20260606_legallibbiblio_v0.5_INGEST` | legallibbiblio | `INGEST_NEED_MORE` | [evidence_unverified] 生JSON3サンプル + 確定mapping + dry-run diff0 evidence を添えて差分再投函 | 2026-06-08 |
| `20260607_canonicalindex_v0.1_DDINDEXDISPO` | canonicalindex | `DDINDEXDISPO_PASS_WITH_NOTES` | ALO_CANONICAL_INDEX を superseded marker 化 + registry v0.2.1 §5.3 pointer patch 後に ratify。full refresh も部分追記もしない | 2026-06-08 |
| `20260607_sessionaudit_SESSIONAUDIT` | sessionaudit | `SESSIONAUDIT_PASS_WITH_NOTES` | DD正本台帳(design_decisions/90_/DD_REGISTRY.json/ALO_CANONICAL_INDEX) reconciliation を P0/P1 起票。大型正本への手差し編集はしない | 2026-06-08 |

## 浅井判断待ち — ratify 待ち

| request_id | topic | label | next_action | 最終更新 |
|---|---|---|---|---|
| `20260605_claudehead_v1.1_DDCLAUDEHEAD` | claudehead | `DDCLAUDEHEAD_PASS_WITH_NOTES` | blocking 4点(role label, cost lane分離, F5 fallback参照, canonical兄弟弱化)を accepted body に反映済。浅井 ratify で v1.1 accepted 化 | 2026-06-08 |
| `20260605_matterevent_v0.5.1_DDMATTEREVENT` | matterevent | `DDMATTEREVENT_PASS_WITH_NOTES` | v0.5.1-integrated migration pack 反映済。本番DDL は浅井GO必要 (五宝miniパイロット) | 2026-06-08 |
| `20260606_codexgov_v0.1_IMPL` | codexgov | `IMPL_PASS_WITH_NOTES` | governance基盤は ratify可。legaldb は landing/candidate維持し promotion block 外さない | 2026-06-08 |
| `20260606_statusregistry_v0.2_DDSTATUS` | statusregistry | `DDSTATUS_PASS` | 浅井 ratify 後 accepted。candidate段階では Generated Index に backfill しない | 2026-06-08 |
| `20260607_caselink_CASELINKDM` | caselink | `CASELINKDM_PASS_WITH_NOTES` | 方向 ratify可。confirmed alias 根拠必須と再学習除外を DB CHECK で物理化してから P2 DDL | 2026-06-08 |
| `20260607_codexprogress_v0.2_DDPROGRESS` | codexprogress | `DDPROGRESS_PASS_WITH_NOTES` | N1(manifest検証をprobe前に強制)反映済。観測dashboard扱い (正本状態表ではない) | 2026-06-08 |
| `20260607_lawtime_v0.2.1_DDLAWTIME` | lawtime | `DDLAWTIME_PASS_WITH_NOTES` | design として浅井 ratify。production DDL は P1-P5 notes + D6 executable gates 後 | 2026-06-08 |
| `20260607_toclegalref_v0.2_DDTOCLEGALREF` | toclegalref | `DDTOCLEGALREF_PASS_WITH_NOTES` | candidate toc_signal(claim_support不可)として link layer に入れる限り採用可。production昇格は N1-N4 gate 後 | 2026-06-08 |

## closed — 反映済 / 後続置換

| request_id | topic | label | next_action | 最終更新 |
|---|---|---|---|---|
| `20260605_lawtime_v0.1_DD` | lawtime | `DDLAWTIME_MODIFY_REQUIRED` | v0.2 / v0.2.1 で消化済 | 2026-06-08 |
| `20260605_matterevent_v0.5.1_DDMATTEREVENT_REQUEST` | matterevent | `DDMATTEREVENT_PASS_WITH_NOTES` | 正本 record に統合済 | 2026-06-08 |
| `20260605_statusregistry_v0.1_DDSTATUS` | statusregistry | `DDSTATUS_MODIFY_REQUIRED` | v0.2 (DDSTATUS_PASS) で閉鎖済 | 2026-06-08 |
| `20260606_caselink_CASELINK` | caselink | `CASELINK_PASS_WITH_NOTES` | 実装は CASELINKDM(20260607) へ引き継ぎ | 2026-06-08 |
| `20260606_codexprogress_v0.1_DDPROGRESS` | codexprogress | `DDPROGRESS_PASS_WITH_NOTES` | v0.2 で消化済 | 2026-06-08 |
| `20260606_legaldb_v0.5_DESIGN` | legaldb | `DESIGN_MODIFY_REQUIRED` | v0.5.1→v0.6 で再投函済 | 2026-06-08 |
| `20260606_toclegalref_v0.1_DDTOCLEGALREF` | toclegalref | `DDTOCLEGALREF_MODIFY_REQUIRED` | v0.2 で消化済 | 2026-06-08 |
| `20260607_lawtime_v0.2_DDLAWTIME` | lawtime | `DDLAWTIME_PASS_WITH_NOTES` | v0.2.1 で N1-N4 を閉じ済 | 2026-06-08 |
| `20260607_legaldb_v0.5.1_DESIGN` | legaldb | `DESIGN_MODIFY_REQUIRED` | v0.6 で再投函済 | 2026-06-08 |
| `20260607_purchaserec_v0.1_DESIGN` | purchaserec | `DESIGN_MODIFY_REQUIRED` | v0.2 で再投函済 | 2026-06-08 |
| `20260607_queueaudit_GPTQUEUE` | queueaudit | `GPTQUEUE_PASS_WITH_NOTES` | loop review(20260608) で MODIFY、本pass で実装 | 2026-06-08 |
