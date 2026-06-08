#!/usr/bin/env python3
"""20260608 一括 backfill seed — from_gpt RESULT 全25件を _AUDIT_LEDGER.jsonl 化する。

GPT_PRO_AUDIT_LANE_DESIGN v0.3 §D + GPT_PRO_AUDIT_LOOP_RULE v0.1 §8/§11 の
台帳スキーマに、各 RESULT の result_label / next_action_type / reflected /
owner_digest_5line / claude_rethink_prompt / loop_state を埋める。

このファイルは「機械生成された台帳の出所（provenance）」として版管理する。
台帳本体（Box: _AUDIT_LEDGER.jsonl, file_id 2269735330886）は、これを実行して
得た jsonl で upload_file_version した派生控えである（SoT はフォルダ位置）。

loop_state の意味:
  returned    : RESULT 返却済み・未反映（Claude が次アクション未着手）
  requeued    : 後続 version を再投函済み（この RESULT の指摘は次版へ送られた）
  ratify_wait : blocking なし。Owner ratify 待ち
  reflected   : 反映済み（重複/消化済み）
  closed      : 反映済みかつ次アクションなし
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alo_gpt_audit import LedgerEntry  # noqa: E402

# request_id, result_label, req_file_id, res_file_id, reflected, loop_state,
# need_more_type, missing_materials, blocking_before_ratify, digest, rethink
ROWS = [
    dict(
        request_id="20260605_ccguard_v0.1.1_G0",
        result_label="G0_MODIFY_REQUIRED",
        request_file_id="2266001714138", result_file_id="2266430431171",
        reflected=False, loop_state="returned",
        blocking_before_ratify=[
            "shell起動/eval/encoded payload/heredoc を deny/ask する rule+fixture",
            "mcp__* unknown は defer ではなく ask、mutating verb は deny/ask",
            "Box/GDrive mutation は path 無しでも ask 以上",
            "SQL resolver に project ref allowlist + alo-connect hard-deny",
            "G3 live dry-run（実Claude Code + managed settings）実測",
        ],
        owner_digest_5line=(
            "監査: ccguard v0.1.1 安全ガード G0\n"
            "結論: MODIFY_REQUIRED\n"
            "理由: shell/SQL迂回余地・unknown tool fail-open・G3未実施\n"
            "次アクション: Claudeが v0.1.2 でbypass群を閉じG3実測\n"
            "Owner確認: 不要（accepted/本番昇格はG3後）"),
        claude_rethink_prompt=(
            "v0.1.1 は fixture では前進したが本番 guard には早い。v0.1.2 で "
            "shell/eval/heredoc/encoded、mcp unknown=ask、Box/GDrive mutation=ask、"
            "SQL project ref allowlist+alo-connect hard-deny を実装し、G3 live dry-run を "
            "通してから再レビューに回すこと。"),
    ),
    dict(
        request_id="20260605_claudehead_v1.1_DDCLAUDEHEAD",
        result_label="DDCLAUDEHEAD_PASS_WITH_NOTES",
        request_file_id="2266370634224", result_file_id="2268831609533",
        reflected=False, loop_state="ratify_wait",
        blocking_before_ratify=[
            "第二instance=hand/capacity(planner含む,head/auditorでない)へ表現修正",
            "cost lane: Google alias $0 と Anthropic $400/月を分離記述",
            "§E に v1.0/F5 fallback path 参照と head落ち時の可否を明記",
            "「canonical兄弟」→「companion/pending related」へ弱化",
        ],
        owner_digest_5line=(
            "監査: claudehead v1.1（第二Anthropic）\n"
            "結論: PASS_WITH_NOTES\n"
            "理由: A-1公理(容量増≠監査独立)は採用可。軽微notesのみ\n"
            "次アクション: 4点反映後 浅井ratifyで accepted 化\n"
            "Owner確認: ratify必要"),
        claude_rethink_prompt=(
            "再T2不要。blocking 4点（role label, cost lane分離, F5 fallback参照, "
            "canonical兄弟弱化）を accepted body に反映し、浅井ratifyで v1.1 accepted 化。"),
    ),
    dict(
        request_id="20260605_lawtime_v0.1_DD",
        result_label="DDLAWTIME_MODIFY_REQUIRED",
        request_file_id="2266019581395", result_file_id="2266776294262",
        reflected=True, loop_state="requeued",
        owner_digest_5line=(
            "監査: lawtime v0.1（法令時間モデル）\n"
            "結論: MODIFY_REQUIRED（→ v0.2/v0.2.1 で対応済み）\n"
            "理由: Work resolver/as_of unknown保持/Work粒度が未閉鎖\n"
            "次アクション: 後続 v0.2→v0.2.1 で再投函済み\n"
            "Owner確認: 不要（最新版 v0.2.1 を参照）"),
        claude_rethink_prompt=(
            "本RESULTは v0.2 / v0.2.1 で消化済み。lawtime の最新監査は v0.2.1 "
            "(DDLAWTIME_PASS_WITH_NOTES) を参照。"),
    ),
    dict(
        request_id="20260605_matterevent_v0.5.1_DDMATTEREVENT_REQUEST",
        result_label="DDMATTEREVENT_PASS_WITH_NOTES",
        request_file_id="2266081460902", result_file_id="2269856296342",
        reflected=True, loop_state="reflected",
        owner_digest_5line=(
            "監査: matterevent v0.5.1（重複RESULTファイル）\n"
            "結論: PASS_WITH_NOTES（_DDMATTEREVENT_RESULT.md と同内容の重複）\n"
            "理由: 同一監査の二重保存\n"
            "次アクション: 正本は 2266769629679 を参照\n"
            "Owner確認: 不要"),
        claude_rethink_prompt=(
            "REQUEST_RESULT 名の重複保存。正本 matterevent RESULT "
            "(result_file_id 2266769629679) に集約済みとして扱う。"),
    ),
    dict(
        request_id="20260605_matterevent_v0.5.1_DDMATTEREVENT",
        result_label="DDMATTEREVENT_PASS_WITH_NOTES",
        request_file_id="2266081460902", result_file_id="2266769629679",
        reflected=False, loop_state="ratify_wait",
        blocking_before_ratify=[
            "v0.5.1-integrated migration SQL を1本に統合（v0.3 annex/v0.5 canonical を直接当てない）",
            "old-snippet exclusion test (S2) を通す",
            "canonical index で v0.5.1 を優先パッチと明示",
        ],
        owner_digest_5line=(
            "監査: matterevent v0.5.1（動的スキーマ）\n"
            "結論: PASS_WITH_NOTES（migration-ready）\n"
            "理由: P-1〜P-4をdry-runで機構検証済み。v0.6不要\n"
            "次アクション: v0.5.1-integrated migration pack 作成、五宝miniパイロット\n"
            "Owner確認: 本番DDLは浅井GO必要"),
        claude_rethink_prompt=(
            "v0.6 は作らない。v0.5 canonical + v0.5.1 patch + dry-run を統合した "
            "migration pack を1本作り、古い断片(v0.3 annex/v0.5)を混ぜない。SF writeback/"
            "会計射影/外部LLM送出は禁止のまま五宝1文書から段階パイロット。"),
    ),
    dict(
        request_id="20260605_quasijudicial_v0.4_DDCASESOURCE",
        result_label="DDCASESOURCE_NEED_MORE",
        request_file_id="2266376727636", result_file_id="2268867415119",
        reflected=False, loop_state="returned",
        need_more_type="material_absent",
        missing_materials=[
            "DD-CASE-SOURCE-CASEID_v0.4_closure_20260604.md",
            "DD-CASE-001_individual_judgment_canonical_node_draft_v0.1.md",
            "alo_source_registry_seed_v0.1_20260604.jsonl",
            "registry_negative_test.py",
            "31_case_layer_quasi_judicial_patch_draft_v0.2.md",
        ],
        owner_digest_5line=(
            "監査: quasijudicial v0.4（準司法コーパス）\n"
            "結論: NEED_MORE（対象正本5点がBox不在）\n"
            "理由: docs/alo に監査対象が無く内容監査不能\n"
            "次アクション: 5ファイルをBox復旧→status:queued→source_hash埋め再投函\n"
            "Owner確認: 不要（資料復旧タスク）"),
        claude_rethink_prompt=(
            "内容議論に入らない。対象5点を Box docs/alo にアップロードし実体ID・sha1 を "
            "REQUEST に入れ、front-matter を status: queued に戻して再投函する資料復旧ルート。"),
    ),
    dict(
        request_id="20260605_statusregistry_v0.1_DDSTATUS",
        result_label="DDSTATUS_MODIFY_REQUIRED",
        request_file_id="2266319221274", result_file_id="2268789568134",
        reflected=True, loop_state="requeued",
        owner_digest_5line=(
            "監査: statusregistry v0.1（状態語彙）\n"
            "結論: MODIFY_REQUIRED（→ v0.2 で PASS 済み）\n"
            "理由: lifecycle列に非lifecycle語が混入する自己矛盾\n"
            "次アクション: v0.2 で P0-PATCH 反映済み\n"
            "Owner確認: 不要（最新 v0.2 を参照）"),
        claude_rethink_prompt=(
            "v0.2 (DDSTATUS_PASS) で閉鎖済み。最新は statusregistry v0.2 を参照。"),
    ),
    dict(
        request_id="20260606_caselink_CASELINK",
        result_label="CASELINK_PASS_WITH_NOTES",
        request_file_id="2269074954298", result_file_id="2269673250328",
        reflected=True, loop_state="requeued",
        owner_digest_5line=(
            "監査: caselink 説明レイヤ\n"
            "結論: PASS_WITH_NOTES（→ 実装は CASELINKDM へ）\n"
            "理由: 説明資料としては妥当。alias/巻戻し設計は候補特徴量化が必要\n"
            "次アクション: 後続 CASELINKDM(データモデル差分)で具体化済み\n"
            "Owner確認: 不要"),
        claude_rethink_prompt=(
            "説明レイヤ監査は CASELINKDM(20260607) の DM 差分監査へ引き継がれた。"
            "alias/旧姓は確定でなく候補特徴量、誤紐付け巻戻しは append-only ログで。"),
    ),
    dict(
        request_id="20260606_codexgov_v0.1_IMPL",
        result_label="IMPL_PASS_WITH_NOTES",
        request_file_id="2269094730430", result_file_id="2269703399814",
        reflected=False, loop_state="ratify_wait",
        blocking_before_ratify=[
            "service_role bypass を README で運用ゲート化（手元scriptからINSERTしない）",
            "prod受入に validated_at/by/row_hash/source/gate_run_id を必須化検討",
            "legaldb-candidate-status.md に current_design_gate_result を持たせ追従",
        ],
        owner_digest_5line=(
            "監査: codexgov v0.1（静的RDBガバナンス基盤）\n"
            "結論: IMPL_PASS_WITH_NOTES（採用可）\n"
            "理由: clean-only/環境分離/candidate物理ブロックは整合\n"
            "次アクション: legaldbはlanding/candidate維持しpromotion block外さない\n"
            "Owner確認: governance基盤はratify可 / legaldb昇格は不可"),
        claude_rethink_prompt=(
            "ガバナンス基盤は採用可。legaldb v0.5系は landing-only/promotion blocked を維持。"
            "service_role運用の明文化と current_design_gate_result 追跡を追記。"),
    ),
    dict(
        request_id="20260606_codexprogress_v0.1_DDPROGRESS",
        result_label="DDPROGRESS_PASS_WITH_NOTES",
        request_file_id="2269101887272", result_file_id="2269700668702",
        reflected=True, loop_state="requeued",
        owner_digest_5line=(
            "監査: codexprogress v0.1（進捗可視化）\n"
            "結論: PASS_WITH_NOTES（→ v0.2 で対応）\n"
            "理由: roundtrip keying/manifest drift が v0.1リスク\n"
            "次アクション: v0.2 で6点中5点閉鎖済み\n"
            "Owner確認: 不要（最新 v0.2 を参照）"),
        claude_rethink_prompt=(
            "v0.2 (DDPROGRESS_PASS_WITH_NOTES, N1のみ残) で消化済み。最新は v0.2 参照。"),
    ),
    dict(
        request_id="20260606_legaldb_v0.5_DESIGN",
        result_label="DESIGN_MODIFY_REQUIRED",
        request_file_id="2268717601893", result_file_id="2268874456060",
        reflected=True, loop_state="requeued",
        owner_digest_5line=(
            "監査: legaldb v0.5（静的DB設計）\n"
            "結論: MODIFY_REQUIRED（→ v0.5.1/v0.6 へ）\n"
            "理由: lawtime依存未閉鎖・識別子責務混同・treatment未定義\n"
            "次アクション: v0.5.1→v0.6 で再投函済み\n"
            "Owner確認: 不要（最新版を参照）"),
        claude_rethink_prompt=(
            "v0.5.1 へ消化済み（さらに v0.6 を to_gpt に投函済み）。最新版を参照。"),
    ),
    dict(
        request_id="20260606_legallibbiblio_v0.5_INGEST",
        result_label="INGEST_NEED_MORE",
        request_file_id="2269094301007", result_file_id="2269719016248",
        reflected=False, loop_state="returned",
        need_more_type="evidence_unverified",
        missing_materials=[
            "legallib raw JSON 3サンプル（通常/索引あり/深いTOC）",
            "確定 mapping table（top-level/author/TOC/index）",
            "--dry-run --limit 3 の出力例",
            "既存 asai-bookshelf/bencom 差分0 test",
            "再実行 diff 0 test",
        ],
        owner_digest_5line=(
            "監査: legallibbiblio v0.5（蔵書ingest）\n"
            "結論: NEED_MORE（生JSON未確認がingest blocker）\n"
            "理由: loader入力の実shapeが未確定のままPASS不可\n"
            "次アクション: 生JSON3サンプル+dry-run evidenceを添えて再投函\n"
            "Owner確認: 不要（資料補充ルート）"),
        claude_rethink_prompt=(
            "設計方向は良いが ingest gate は資料不足。実物3冊のJSONサンプルと確定mapping、"
            "dry-run diff0 evidence を出せば差分再監査で PASS_WITH_NOTES まで上がる。"),
    ),
    dict(
        request_id="20260606_statusregistry_v0.2_DDSTATUS",
        result_label="DDSTATUS_PASS",
        request_file_id="2269073758846", result_file_id="2269658306240",
        reflected=False, loop_state="ratify_wait",
        owner_digest_5line=(
            "監査: statusregistry v0.2（状態語彙・差分再監査）\n"
            "結論: PASS（owner_ratify_ready）\n"
            "理由: v0.1のself-consistency欠陥(P0-PATCH 1-5)を全CLOSED\n"
            "次アクション: 浅井ratify後 accepted。candidate段階ではbackfillしない\n"
            "Owner確認: ratify必要"),
        claude_rethink_prompt=(
            "差分再監査 PASS。浅井ratify で accepted 化。ratify までは design_decisions/"
            "Generated Index へ backfill しない運用を維持。"),
    ),
    dict(
        request_id="20260606_toclegalref_v0.1_DDTOCLEGALREF",
        result_label="DDTOCLEGALREF_MODIFY_REQUIRED",
        request_file_id="2269713772194", result_file_id="2269878208289",
        reflected=True, loop_state="requeued",
        owner_digest_5line=(
            "監査: toclegalref v0.1（蔵書TOC→link layer）\n"
            "結論: MODIFY_REQUIRED（→ v0.2 で PASS_WITH_NOTES）\n"
            "理由: edge意味が強すぎ・lawtime依存・src_uri暫定管理が未閉鎖\n"
            "次アクション: v0.2 で candidate隔離・temporal遮断を反映済み\n"
            "Owner確認: 不要（最新 v0.2 を参照）"),
        claude_rethink_prompt=(
            "v0.2 (DDTOCLEGALREF_PASS_WITH_NOTES) で消化済み。最新は v0.2 を参照。"),
    ),
    dict(
        request_id="20260607_canonicalindex_v0.1_DDINDEXDISPO",
        result_label="DDINDEXDISPO_PASS_WITH_NOTES",
        request_file_id="2270470784493", result_file_id="2270473891101",
        reflected=False, loop_state="returned",
        blocking_before_ratify=[
            "ALO_CANONICAL_INDEX_20260605 を superseded/historical snapshot marker 化",
            "DD-STATUS-REGISTRY-001 v0.2.1 SoT pointer patch（§5.3のみ）作成",
            "v0.2.1 を owner ratify で accepted",
            "full refresh / 部分追記はしない",
        ],
        owner_digest_5line=(
            "監査: canonicalindex 処分判断\n"
            "結論: PASS_WITH_NOTES（案(二)採用）\n"
            "理由: 状態SoTを design_decisions Generated Index へ一本化が妥当\n"
            "次アクション: index退役表示 + registry v0.2.1 narrow pointer patch\n"
            "Owner確認: 処分はratify可"),
        claude_rethink_prompt=(
            "「触らない」で止めない。ALO_CANONICAL_INDEX を superseded marker 化し、"
            "DD-STATUS-REGISTRY v0.2.1 で §5.3 SoT pointer のみ差し替え、owner ratify。"
            "full refresh も部分追記もしない。"),
    ),
    dict(
        request_id="20260607_caselink_CASELINKDM",
        result_label="CASELINKDM_PASS_WITH_NOTES",
        request_file_id="2269712726103", result_file_id="2269842057063",
        reflected=False, loop_state="ratify_wait",
        blocking_before_ratify=[
            "party_alias confirmed に confirmed_by/at/evidence_strength/review_basis 必須+CHECK",
            "inference_log に training_eligible/training_disposition（既定false）",
            "enum migration idempotency（rejected/superseded 既存時）",
        ],
        owner_digest_5line=(
            "監査: caselink データモデル差分(DM)\n"
            "結論: CASELINKDM_PASS_WITH_NOTES（非破壊差分として採用可）\n"
            "理由: party_alias/link_policy/non_matter_type 方向は妥当\n"
            "次アクション: confirmed alias条件と再学習除外をDBで強制してP2 DDL\n"
            "Owner確認: 方向ratify可 / 実装はP2 DDL review"),
        claude_rethink_prompt=(
            "v0.3非破壊差分として採用可。実装順は enum保証→inference_log拡張→party_alias→"
            "link_policy→non_matter_type。confirmed alias の根拠必須と rejected/superseded の "
            "training除外を DB CHECK で物理化してから P2 DDL。"),
    ),
    dict(
        request_id="20260607_codexprogress_v0.2_DDPROGRESS",
        result_label="DDPROGRESS_PASS_WITH_NOTES",
        request_file_id="2269973632030", result_file_id="2270064515801",
        reflected=False, loop_state="ratify_wait",
        blocking_before_ratify=[
            "N1: dashboard one-shot route でも manifest不正時は probe前に止める",
        ],
        owner_digest_5line=(
            "監査: codexprogress v0.2（進捗dashboard差分）\n"
            "結論: PASS_WITH_NOTES（runtime dashboardとして採用可）\n"
            "理由: v0.1の6点中5点CLOSED。F4はone-shot経路のみ未閉\n"
            "次アクション: N1(manifest検証をprobe前に強制)を小修正\n"
            "Owner確認: ratify可（N1反映推奨）"),
        claude_rethink_prompt=(
            "pipeline_dashboard.py --root 経路でも validate_manifest をprobe前に呼び、"
            "errorなら return 1。N1反映で前回F4も完全閉鎖。正本状態表でなく観測dashboard扱い。"),
    ),
    dict(
        request_id="20260607_lawtime_v0.2_DDLAWTIME",
        result_label="DDLAWTIME_PASS_WITH_NOTES",
        request_file_id="2270221638834", result_file_id="2270335369444",
        reflected=True, loop_state="requeued",
        owner_digest_5line=(
            "監査: lawtime v0.2（法令時間モデル再監査）\n"
            "結論: PASS_WITH_NOTES（→ v0.2.1 へ）\n"
            "理由: 7必須修正は設計上CLOSED。N1-N4は実装前修正\n"
            "次アクション: v0.2.1 で N1-N4 を反映済み\n"
            "Owner確認: 不要（最新 v0.2.1 を参照）"),
        claude_rethink_prompt=(
            "v0.2.1 で N1-N4 を閉じ済み。lawtime 最新監査は v0.2.1 を参照。"),
    ),
    dict(
        request_id="20260607_lawtime_v0.2.1_DDLAWTIME",
        result_label="DDLAWTIME_PASS_WITH_NOTES",
        request_file_id="2270929110363", result_file_id="2270935890940",
        reflected=False, loop_state="ratify_wait",
        blocking_before_ratify=[
            "P1: article_path_json の扱いを明記（v0.2.1はlaw_revision_id解決までがscope）",
            "P2: edge_id 型を alo_edges PK に合わせFK化 / gate_temporal_eval_edge_exists",
            "P3: repeal_and_reenact→abolish_and_replace の rename map",
            "P4: gate_claim_support_requires_resolved_lawtime",
            "P5: gate_succession_event_group_consistency",
        ],
        owner_digest_5line=(
            "監査: lawtime v0.2.1（法令時間モデル）\n"
            "結論: PASS_WITH_NOTES（design採用可）\n"
            "理由: v0.2のN1-N4をCLOSED。v0.5.1の自称v0.2.1を正規ラインに再接地\n"
            "次アクション: owner ratify。production DDLはP1-P5+D6 gate後\n"
            "Owner確認: ratify可（designとして）"),
        claude_rethink_prompt=(
            "DD-LAWTIME v0.2.1 を design として owner ratify。これで legaldb の F4 依存先が "
            "確定する。production DDL は P1-P5 notes と D6 executable gates を満たしてから。"),
    ),
    dict(
        request_id="20260607_legaldb_v0.5.1_DESIGN",
        result_label="DESIGN_MODIFY_REQUIRED",
        request_file_id="2269106646663", result_file_id="2269823581513",
        reflected=True, loop_state="requeued",
        blocking_before_ratify=[
            "DD-LAWTIME v0.2.1 accepted 証跡(Box ID/owner ratify/GPT result)を提示",
            "legal_anchor_lineage と既存 stable_locator_key の責務分界をDDL明文化",
            "treatment未reviewed edge を claim_support から除外する view/CHECK/gate",
        ],
        owner_digest_5line=(
            "監査: legaldb v0.5.1（静的DB設計差分）\n"
            "結論: DESIGN_MODIFY_REQUIRED\n"
            "理由: F4が未確認の『DD-LAWTIME v0.2.1 accepted』を前提（既存RESULTと矛盾）\n"
            "次アクション: lawtime v0.2.1 ratify証跡を添えv0.6で再投函（投函済み）\n"
            "Owner確認: 不要（v0.6 で再監査待ち）"),
        claude_rethink_prompt=(
            "v0.5.1 は v0.5 より大幅改善だが F4 の lawtime 依存が未確認 accepted を前提にして "
            "regression seed。lawtime v0.2.1 の ratify 証跡を確定させ、anchor lineage 制約整合を "
            "追記して v0.6 で再監査（v0.6 は既に to_gpt に投函済み）。"),
    ),
    dict(
        request_id="20260607_purchaserec_v0.1_DESIGN",
        result_label="DESIGN_MODIFY_REQUIRED",
        request_file_id="2270366612942", result_file_id="2270396655962",
        reflected=True, loop_state="requeued",
        blocking_before_ratify=[
            "RLS/private schema 決定（推奨 bookdx schema、publicならRLS+revoke+no SELECT policy）",
            "dedup強弱分離（ISBN/bencom_id強一致、title_normはreview candidate）",
            "load_run監査（source_hash/source_files/loader_version/loaded_at）",
        ],
        owner_digest_5line=(
            "監査: purchaserec v0.1（蔵書購入推薦DB）\n"
            "結論: DESIGN_MODIFY_REQUIRED（→ v0.2 へ）\n"
            "理由: RLS/露出面とdedup強弱が未決のままDDL不可\n"
            "次アクション: v0.2 で P0/P1 反映し再投函（投函済み）\n"
            "Owner確認: 不要（v0.2 で再監査待ち）"),
        claude_rethink_prompt=(
            "books.json SoT・bookdx_*はread replica方針は妥当。RLS/private schema と "
            "dedup強弱分離、load_run監査を反映した v0.2 で再監査（v0.2 は既に to_gpt 投函済み）。"),
    ),
    dict(
        request_id="20260607_queueaudit_GPTQUEUE",
        result_label="GPTQUEUE_PASS_WITH_NOTES",
        request_file_id="", result_file_id="2270471912644",
        reflected=True, loop_state="requeued",
        owner_digest_5line=(
            "監査: queueaudit（GPT監査キュー状態）\n"
            "結論: PASS_WITH_NOTES（→ loop review で MODIFY）\n"
            "理由: キュー空確認は妥当だが監査ループ実装検収としては狭い\n"
            "次アクション: loop review の指摘を本passで実装\n"
            "Owner確認: 不要（loop review を参照）"),
        claude_rethink_prompt=(
            "queueaudit は状態確認としては妥当。loop review(20260608)で MODIFY_REQUIRED と "
            "された通り、_AUDIT_LEDGER/action-queue/processed退避を本passで実装した。"),
    ),
    dict(
        request_id="20260607_sessionaudit_SESSIONAUDIT",
        result_label="SESSIONAUDIT_PASS_WITH_NOTES",
        request_file_id="2269112162165", result_file_id="2269851722287",
        reflected=False, loop_state="returned",
        blocking_before_ratify=[
            "DD_LEDGER_RECONCILIATION タスク起票（design_decisions/90_/DD_REGISTRY.json/ALO_CANONICAL_INDEX 4点）",
            "accepted artifact の暫定索引を非破壊sidecar/queue cardで補う",
            "大型正本への手差し編集はしない",
        ],
        owner_digest_5line=(
            "監査: sessionaudit（番頭session process監査）\n"
            "結論: PASS_WITH_NOTES（process discipline OK）\n"
            "理由: 台帳保留は破損防止の正しい分離。ただしfollow-up要明示化\n"
            "次アクション: DD台帳reconciliation を P0/P1 タスク化\n"
            "Owner確認: 不要（reconcileタスク化のみ）"),
        claude_rethink_prompt=(
            "本passの監査レーン台帳(_AUDIT_LEDGER.jsonl)整備とは別に、DD正本台帳"
            "(design_decisions.md/90_/DD_REGISTRY.json/ALO_CANONICAL_INDEX)の reconciliation を "
            "明示P0/P1で起票。accepted済 claudehead v1.1/matterevent の索引可視性を短期で補う。"
            "大型正本への手差し編集はしない。"),
    ),
    dict(
        request_id="20260607_toclegalref_v0.2_DDTOCLEGALREF",
        result_label="DDTOCLEGALREF_PASS_WITH_NOTES",
        request_file_id="2270226491058", result_file_id="2270358722334",
        reflected=False, loop_state="ratify_wait",
        blocking_before_ratify=[
            "production promotion前: 弱い表示名(toc_signal/toc_mentions)定義",
            "DD-LAWTIME ratify後 backfill条件を本文追加",
            "medium quarantine 解除条件を gold set precision基準で定義",
            "dedup_key を extraction_policy_id/major version 粒度へ",
        ],
        owner_digest_5line=(
            "監査: toclegalref v0.2（蔵書TOC→link layer差分）\n"
            "結論: PASS_WITH_NOTES（design candidate として accept可）\n"
            "理由: v0.1の危険(強いedge意味/temporal先取り)を安全側に閉鎖\n"
            "次アクション: owner ratify。production昇格はN1-N4 gate後\n"
            "Owner確認: ratify可（designとして）"),
        claude_rethink_prompt=(
            "TOC由来参照は法律判断の根拠でなく candidate toc_signal(claim_support不可)として "
            "link layer に入れる限り accept可。owner ratify 後、production promotion 前に "
            "弱い表示名・lawtime後backfill条件・medium解除閾値・dedup粒度を閉じる。"),
    ),
    dict(
        request_id="20260608_queueaudit_loop_GPTQUEUE_REVIEW",
        result_label="GPTQUEUE_MODIFY_REQUIRED",
        request_file_id="", result_file_id="2270920897721",
        reflected=False, loop_state="requeued",
        blocking_before_ratify=[
            "to_gpt直下の.processed.mdを物理退避（完了: processed/へ移動・suffix除去）",
            "_AUDIT_LEDGER.jsonl/action-queueを実体化（完了: 本pass）",
            "from_gpt RESULT群をnext_action_type付きでbackfill（完了: 25件）",
            "dry-run/apply/idempotencyログ添付（完了: _VERIFY_20260608）",
            "GPTQUEUELOOPIMPL_REQUEST.md で再投函（本pass）",
        ],
        owner_digest_5line=(
            "監査: queueaudit ループ実装の再監査\n"
            "結論: MODIFY_REQUIRED\n"
            "理由: キュー空確認はOKだがaction ledger未実体化・processed物理退避未完了\n"
            "次アクション: Claudeが台帳/action-queue/退避を実装し再投函（本passで実施）\n"
            "Owner確認: 不要"),
        claude_rethink_prompt=(
            "本passで実装: (1).processed.md を processed/へ物理退避しsuffix除去、"
            "(2)_AUDIT_LEDGER.jsonl を25件backfill、(3)_ACTION_QUEUE.md 生成、"
            "(4)dry-run/apply/idempotency検収ログ、(5)GPTQUEUELOOPIMPL_REQUEST 再投函。"
            "reflected は GPT 再監査が PASS したら true 化する。"),
    ),
]


def build_entries():
    entries = []
    for r in ROWS:
        e = LedgerEntry(
            request_id=r["request_id"],
            request_file_id=r.get("request_file_id", ""),
            result_file_id=r.get("result_file_id", ""),
            result_filename=f"{r['request_id']}_RESULT.md",
            request_filename=f"{r['request_id']}_REQUEST.md",
            result_label=r["result_label"],
            reflected=r.get("reflected", False),
            loop_state=r.get("loop_state", "returned"),
            need_more_type=r.get("need_more_type", ""),
            missing_materials=r.get("missing_materials", []),
            blocking_before_ratify=r.get("blocking_before_ratify", []),
            owner_digest_5line=r.get("owner_digest_5line", ""),
            claude_rethink_prompt=r.get("claude_rethink_prompt", ""),
            lane_status="processed_done" if r.get("request_file_id") else "result_only",
            updated_at="2026-06-08T00:00:00Z",
        )
        from alo_gpt_audit import gate_of_stem
        e.gate = gate_of_stem(r["request_id"])
        e.enrich_from_label()
        entries.append(e)
    return entries


def _res_stem(request_id: str) -> str:
    # RESULT ファイル名の stem は request_id と同じ（REQUEST_RESULT 重複名のみ例外）
    return request_id


def main():
    from dataclasses import asdict
    entries = build_entries()
    out = []
    for e in sorted(entries, key=lambda x: x.request_id):
        out.append(json.dumps(asdict(e), ensure_ascii=False, sort_keys=True))
    text = "\n".join(out) + "\n"
    target = Path(__file__).resolve().parent / "_AUDIT_LEDGER.jsonl"
    target.write_text(text, encoding="utf-8")
    sys.stderr.write(f"wrote {len(entries)} entries -> {target}\n")
    print(text)


if __name__ == "__main__":
    main()
