#!/usr/bin/env python3
"""QUEUE_EVENTS.jsonl を 2026-06-08 の実状態でブートストラップする一回限りのスクリプト.

出典: Box `handoffs/gpt_ometsuke/_ACTION_QUEUE.md` (generated_at 2026-06-08) と
`_AUDIT_LEDGER.jsonl`。全 25 件 (反映待ち14 / 反映・requeue済11) を v0.2 の
イベントモデルに移し替える。元イベントの正確な発生時刻は失われているため、
REQUEST_CREATED は request_id の日付プレフィクスを、それ以外は移行時刻
(2026-06-08T09:00:00+09:00) を用いる。

実行すると QUEUE_EVENTS.jsonl を **上書き生成** する。通常運用ではこの後は
queue.py append でイベントを足していく。再シードが必要なときだけ再実行する。
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EVENTS_PATH = os.path.normpath(
    os.path.join(HERE, "..", "..", "handoffs", "gpt_ometsuke", "QUEUE_EVENTS.jsonl")
)

BOOT_TS = "2026-06-08T09:00:00+09:00"


def req_ts(request_id: str) -> str:
    d = request_id[:8]
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}T09:00:00+09:00"


# 各 record の最終状態を宣言し、最小イベント列に展開する。
# fields: rid, topic, gate, label, rf(result_file_id), disp, req_refl, refl,
#         ratify, ratified, superseded_by, closed_reason, need_more_type,
#         owner(=GPT結論要旨), claude(=反映内容/次アクション)
RECORDS = [
    # ---- 未反映 (6) -------------------------------------------------------
    dict(rid="20260605_ccguard_v0.1.1_G0", topic="ccguard", gate="G0",
         label="G0_MODIFY_REQUIRED", rf="2266430431171", disp="adopt",
         req_refl=True, refl=False, ratify=False, ratified=False,
         owner="MODIFY_REQUIRED: shell/SQL迂回余地・unknown tool fail-open・G3未実施",
         claude="v0.1.2 で bypass群(shell/eval/heredoc/encoded, mcp unknown=ask, Box/GDrive mutation=ask, SQL project ref allowlist + alo-connect hard-deny) を閉じ G3 live dry-run 後に再レビュー"),
    dict(rid="20260608_queueaudit_loop_GPTQUEUE_REVIEW", topic="queueaudit", gate="GPTQUEUE",
         label="GPTQUEUE_MODIFY_REQUIRED", rf="2270920897721", disp="adopt",
         req_refl=True, refl=False, ratify=False, ratified=False,
         owner="MODIFY_REQUIRED: action ledger 未実体化・processed 物理退避未完了",
         claude="本pass で台帳/action-queue/退避を実装し GPTQUEUELOOPIMPL_REQUEST で再投函。GPT 再監査 PASS で reflected 化"),
    dict(rid="20260605_quasijudicial_v0.4_DDCASESOURCE", topic="quasijudicial", gate="DDCASESOURCE",
         label="DDCASESOURCE_NEED_MORE", rf="2268867415119", disp="defer",
         req_refl=True, refl=False, ratify=False, ratified=False,
         need_more_type="material_absent",
         owner="NEED_MORE: 対象正本5点が Box(docs/alo) 不在で内容監査不能",
         claude="対象5点を Box 復旧 → source_hash 埋め → status:queued で再投函 (資料復旧ルート)"),
    dict(rid="20260606_legallibbiblio_v0.5_INGEST", topic="legallibbiblio", gate="INGEST",
         label="INGEST_NEED_MORE", rf="2269719016248", disp="defer",
         req_refl=True, refl=False, ratify=False, ratified=False,
         need_more_type="evidence_unverified",
         owner="NEED_MORE: 生JSON未確認が ingest blocker",
         claude="生JSON3サンプル + 確定mapping + dry-run diff0 evidence を添えて差分再投函"),
    dict(rid="20260607_canonicalindex_v0.1_DDINDEXDISPO", topic="canonicalindex", gate="DDINDEXDISPO",
         label="DDINDEXDISPO_PASS_WITH_NOTES", rf="2270473891101", disp="adopt",
         req_refl=True, refl=False, ratify=True, ratified=False,
         owner="PASS_WITH_NOTES(案二採用): 状態SoTを design_decisions Generated Index へ一本化",
         claude="ALO_CANONICAL_INDEX を superseded marker 化 + registry v0.2.1 §5.3 pointer patch 後に ratify。full refresh も部分追記もしない"),
    dict(rid="20260607_sessionaudit_SESSIONAUDIT", topic="sessionaudit", gate="SESSIONAUDIT",
         label="SESSIONAUDIT_PASS_WITH_NOTES", rf="2269851722287", disp="adopt",
         req_refl=True, refl=False, ratify=True, ratified=False,
         owner="PASS_WITH_NOTES: process discipline OK。台帳保留は破損防止の正しい分離",
         claude="DD正本台帳(design_decisions/90_/DD_REGISTRY.json/ALO_CANONICAL_INDEX) reconciliation を P0/P1 起票。大型正本への手差し編集はしない"),
    # ---- 浅井判断待ち (8) -------------------------------------------------
    dict(rid="20260605_claudehead_v1.1_DDCLAUDEHEAD", topic="claudehead", gate="DDCLAUDEHEAD",
         label="DDCLAUDEHEAD_PASS_WITH_NOTES", rf="2268831609533", disp="adopt",
         req_refl=True, refl=True, ratify=True, ratified=False,
         owner="PASS_WITH_NOTES: A-1公理(容量増≠監査独立)採用可。軽微notesのみ",
         claude="blocking 4点(role label, cost lane分離, F5 fallback参照, canonical兄弟弱化)を accepted body に反映済。浅井 ratify で v1.1 accepted 化"),
    dict(rid="20260605_matterevent_v0.5.1_DDMATTEREVENT", topic="matterevent", gate="DDMATTEREVENT",
         label="DDMATTEREVENT_PASS_WITH_NOTES", rf="2266769629679", disp="adopt",
         req_refl=True, refl=True, ratify=True, ratified=False,
         owner="PASS_WITH_NOTES(migration-ready): P-1〜P-4 を dry-run で機構検証済",
         claude="v0.5.1-integrated migration pack 反映済。本番DDL は浅井GO必要 (五宝miniパイロット)"),
    dict(rid="20260606_codexgov_v0.1_IMPL", topic="codexgov", gate="IMPL",
         label="IMPL_PASS_WITH_NOTES", rf="2269703399814", disp="adopt",
         req_refl=True, refl=True, ratify=True, ratified=False,
         owner="IMPL_PASS_WITH_NOTES: clean-only/環境分離/candidate物理ブロック整合",
         claude="governance基盤は ratify可。legaldb は landing/candidate維持し promotion block 外さない"),
    dict(rid="20260606_statusregistry_v0.2_DDSTATUS", topic="statusregistry", gate="DDSTATUS",
         label="DDSTATUS_PASS", rf="2269658306240", disp="adopt",
         req_refl=True, refl=True, ratify=True, ratified=False,
         owner="PASS(owner_ratify_ready): v0.1 の self-consistency 欠陥 P0-PATCH 1-5 全CLOSED",
         claude="浅井 ratify 後 accepted。candidate段階では Generated Index に backfill しない"),
    dict(rid="20260607_caselink_CASELINKDM", topic="caselink", gate="CASELINKDM",
         label="CASELINKDM_PASS_WITH_NOTES", rf="2269842057063", disp="adopt",
         req_refl=True, refl=True, ratify=True, ratified=False,
         owner="CASELINKDM_PASS_WITH_NOTES: 非破壊差分として採用可",
         claude="方向 ratify可。confirmed alias 根拠必須と再学習除外を DB CHECK で物理化してから P2 DDL"),
    dict(rid="20260607_codexprogress_v0.2_DDPROGRESS", topic="codexprogress", gate="DDPROGRESS",
         label="DDPROGRESS_PASS_WITH_NOTES", rf="2270064515801", disp="adopt",
         req_refl=True, refl=True, ratify=True, ratified=False,
         owner="PASS_WITH_NOTES: runtime dashboard として採用可。v0.1 の5点CLOSED",
         claude="N1(manifest検証をprobe前に強制)反映済。観測dashboard扱い (正本状態表ではない)"),
    dict(rid="20260607_lawtime_v0.2.1_DDLAWTIME", topic="lawtime", gate="DDLAWTIME",
         label="DDLAWTIME_PASS_WITH_NOTES", rf="2270935890940", disp="adopt",
         req_refl=True, refl=True, ratify=True, ratified=False,
         owner="PASS_WITH_NOTES(design採用可): v0.2 の N1-N4 を CLOSED",
         claude="design として浅井 ratify。production DDL は P1-P5 notes + D6 executable gates 後"),
    dict(rid="20260607_toclegalref_v0.2_DDTOCLEGALREF", topic="toclegalref", gate="DDTOCLEGALREF",
         label="DDTOCLEGALREF_PASS_WITH_NOTES", rf="2270358722334", disp="adopt",
         req_refl=True, refl=True, ratify=True, ratified=False,
         owner="PASS_WITH_NOTES: 危険(強edge意味/temporal先取り)を安全側に閉鎖",
         claude="candidate toc_signal(claim_support不可)として link layer に入れる限り採用可。production昇格は N1-N4 gate 後"),
    # ---- closed: 後続置換 / 重複 (11) ------------------------------------
    dict(rid="20260605_lawtime_v0.1_DD", topic="lawtime", gate="DDLAWTIME",
         label="DDLAWTIME_MODIFY_REQUIRED", rf="", disp="adopt", req_refl=True, refl=True,
         ratify=False, ratified=False, superseded_by="20260607_lawtime_v0.2.1_DDLAWTIME",
         owner="MODIFY_REQUIRED", claude="v0.2 / v0.2.1 で消化済"),
    dict(rid="20260605_matterevent_v0.5.1_DDMATTEREVENT_REQUEST", topic="matterevent", gate="DDMATTEREVENT",
         label="DDMATTEREVENT_PASS_WITH_NOTES", rf="", disp="adopt", req_refl=False, refl=True,
         ratify=False, ratified=False, closed_reason="REQUEST_RESULT 名の重複保存。正本は result_file_id 2266769629679",
         owner="PASS_WITH_NOTES(重複保存)", claude="正本 record に統合済"),
    dict(rid="20260605_statusregistry_v0.1_DDSTATUS", topic="statusregistry", gate="DDSTATUS",
         label="DDSTATUS_MODIFY_REQUIRED", rf="", disp="adopt", req_refl=True, refl=True,
         ratify=False, ratified=False, superseded_by="20260606_statusregistry_v0.2_DDSTATUS",
         owner="MODIFY_REQUIRED", claude="v0.2 (DDSTATUS_PASS) で閉鎖済"),
    dict(rid="20260606_caselink_CASELINK", topic="caselink", gate="CASELINK",
         label="CASELINK_PASS_WITH_NOTES", rf="", disp="adopt", req_refl=True, refl=True,
         ratify=False, ratified=False, superseded_by="20260607_caselink_CASELINKDM",
         owner="PASS_WITH_NOTES", claude="実装は CASELINKDM(20260607) へ引き継ぎ"),
    dict(rid="20260606_codexprogress_v0.1_DDPROGRESS", topic="codexprogress", gate="DDPROGRESS",
         label="DDPROGRESS_PASS_WITH_NOTES", rf="", disp="adopt", req_refl=True, refl=True,
         ratify=False, ratified=False, superseded_by="20260607_codexprogress_v0.2_DDPROGRESS",
         owner="PASS_WITH_NOTES", claude="v0.2 で消化済"),
    dict(rid="20260606_legaldb_v0.5_DESIGN", topic="legaldb", gate="DESIGN",
         label="DESIGN_MODIFY_REQUIRED", rf="", disp="adopt", req_refl=True, refl=True,
         ratify=False, ratified=False, superseded_by="20260607_legaldb_v0.5.1_DESIGN",
         owner="MODIFY_REQUIRED", claude="v0.5.1→v0.6 で再投函済"),
    dict(rid="20260606_toclegalref_v0.1_DDTOCLEGALREF", topic="toclegalref", gate="DDTOCLEGALREF",
         label="DDTOCLEGALREF_MODIFY_REQUIRED", rf="", disp="adopt", req_refl=True, refl=True,
         ratify=False, ratified=False, superseded_by="20260607_toclegalref_v0.2_DDTOCLEGALREF",
         owner="MODIFY_REQUIRED", claude="v0.2 で消化済"),
    dict(rid="20260607_lawtime_v0.2_DDLAWTIME", topic="lawtime", gate="DDLAWTIME",
         label="DDLAWTIME_PASS_WITH_NOTES", rf="", disp="adopt", req_refl=True, refl=True,
         ratify=False, ratified=False, superseded_by="20260607_lawtime_v0.2.1_DDLAWTIME",
         owner="PASS_WITH_NOTES", claude="v0.2.1 で N1-N4 を閉じ済"),
    dict(rid="20260607_legaldb_v0.5.1_DESIGN", topic="legaldb", gate="DESIGN",
         label="DESIGN_MODIFY_REQUIRED", rf="", disp="adopt", req_refl=True, refl=True,
         ratify=False, ratified=False, superseded_by="20260607_legaldb_v0.6_DESIGN",
         owner="MODIFY_REQUIRED(F4 lawtime依存)", claude="v0.6 で再投函済"),
    dict(rid="20260607_purchaserec_v0.1_DESIGN", topic="purchaserec", gate="DESIGN",
         label="DESIGN_MODIFY_REQUIRED", rf="", disp="adopt", req_refl=True, refl=True,
         ratify=False, ratified=False, superseded_by="20260607_purchaserec_v0.2_DESIGN",
         owner="MODIFY_REQUIRED", claude="v0.2 で再投函済"),
    dict(rid="20260607_queueaudit_GPTQUEUE", topic="queueaudit", gate="GPTQUEUE",
         label="GPTQUEUE_PASS_WITH_NOTES", rf="", disp="adopt", req_refl=True, refl=True,
         ratify=False, ratified=False, superseded_by="20260608_queueaudit_loop_GPTQUEUE_REVIEW",
         owner="PASS_WITH_NOTES", claude="loop review(20260608) で MODIFY、本pass で実装"),
]


def expand(rec: dict) -> list:
    rid = rec["rid"]
    evs = []
    evs.append(dict(ts=req_ts(rid), event="REQUEST_CREATED", request_id=rid,
                    actor="claude", topic=rec["topic"], gate=rec["gate"]))
    if rec.get("label"):
        r = dict(ts=BOOT_TS, event="RESULT_RETURNED", request_id=rid, actor="gpt",
                 label=rec["label"])
        if rec.get("rf"):
            r["result_file_id"] = rec["rf"]
        if rec.get("need_more_type"):
            r["need_more_type"] = rec["need_more_type"]
        if rec.get("owner"):
            r["summary_owner"] = rec["owner"]
        evs.append(r)
    if rec.get("disp"):
        c = dict(ts=BOOT_TS, event="CONSUMED", request_id=rid, actor="claude",
                 disposition=rec["disp"], requires_reflection=rec["req_refl"],
                 ratify_required=rec["ratify"])
        if rec.get("need_more_type"):
            c["need_more_type"] = rec["need_more_type"]
        if rec.get("claude"):
            c["summary_claude"] = rec["claude"]
        evs.append(c)
    if rec.get("refl"):
        evs.append(dict(ts=BOOT_TS, event="REFLECTED", request_id=rid, actor="claude"))
    if rec.get("ratified"):
        evs.append(dict(ts=BOOT_TS, event="RATIFIED", request_id=rid, actor="asai"))
    if rec.get("superseded_by"):
        evs.append(dict(ts=BOOT_TS, event="REQUEUED", request_id=rid, actor="claude",
                        superseded_by=rec["superseded_by"]))
    if rec.get("closed_reason"):
        evs.append(dict(ts=BOOT_TS, event="CLOSED", request_id=rid, actor="claude",
                        reason=rec["closed_reason"]))
    return evs


def main() -> None:
    header = [
        "# QUEUE_EVENTS.jsonl — GPT お目付け役 監査キュー 状態変更ログ (append-only)",
        "# 真実はこのファイル。QUEUE_INDEX.md / CONSUMED.md は派生 (queue.py build で再生成)。",
        "# seed: tools/gpt_audit/seed_20260608.py  source: Box _ACTION_QUEUE.md @2026-06-08",
        "# 以後の追記は queue.py append で行い、行を書き換え/削除しない。",
    ]
    lines = list(header)
    for rec in RECORDS:
        for ev in expand(rec):
            lines.append(json.dumps(ev, ensure_ascii=False))
    with open(EVENTS_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {EVENTS_PATH} ({len(RECORDS)} records)")


if __name__ == "__main__":
    main()
