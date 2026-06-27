# ハンドオフ・ランブック — Law-time プログラム（lawtime ＋ lawsubtrans）

- 作成: 2026-06-16 / owner: 浅井 / 目的: 設計＋コード＋監査が揃った本プログラムを、別スレッド／
  法令レイヤ DB とデータが存在する実行環境で継続するための起点。PR #19 はマージ済み（main 反映）。

## 0. なぜ新スレ／別環境が要るか
- 本セッションは Box/GitHub/Supabase MCP の断続切断で操作消失が頻発（throughput 律速）。長大化済み。
- alo-connect(public) は空。土台 alo_law_work/alo_statutes/alo_edges も既存行も無い → 空 DB apply は偽陽性。
  e-Gov API は 403。判例/逐条解説/ワーカー資産は別ホスト。
→ 実行（dry-run/apply/ingest/較正/MCP）は materialize 済み環境で。設計＋コードは完了・main にマージ済み。

## 1. 現在地（確定。新スレはここから）
- DD-LAWSUBTRANS-001 v0.1.3 設計: accepted (design, owner ratified)。監査 v0.1〜v0.1.3 全 PASS_WITH_NOTES。
- DD-LAWTIME-001 v0.2.3 patch: PASS_WITH_NOTES（P0-1〜4 CLOSED）。本番 apply は branch dry-run＋ratify 待ち。
- 実装監査: 投函済 to_gpt/20260616_lawsubtrans_v0.1.3_impl_DDLAWSUBTRANS_REQUEST.md (id 2289956639792)。
- コード: PR #19 マージ済（main）。69 unit tests green / DB書込みゼロ / candidates-only。
- 成果物: docs/dd/DD-LAWSUBTRANS-001_v0.1.3.md, docs/dd/DD-LAWTIME-001_v0.2.3_production_patch.md,
  docs/reference/REFERENCE_law_substantive_transition_prior_art.md, docs/PLAN_DD-LAWSUBTRANS-001_production_v0.1.md,
  docs/MILESTONE_DD-LAWSUBTRANS-001_20260611.md, migrations/lawsubtrans/{001..005,verify_dry_run}.sql,
  scripts/{lawdelta,drafterintent,casetreatment,assembler,mcprender}/。

## 2. 新スレで最初にやること
1. 実装監査 RESULT 取り込み: from_gpt/20260616_lawsubtrans_v0.1.3_impl_DDLAWSUBTRANS_RESULT.md。
   PASS系→notes 反映、MODIFY_REQUIRED→P0 を STEP B 前に修正。
2. lawtime v0.2.3 owner ratify（メモ: lawtime_resolved=true は claim_support 充分条件でない）。
3. 法令レイヤを materialize 済みの Supabase project/branch の所在を特定（本スレ未特定・最優先の前提確認）。

## 3. 実行順（Track 2 / 実行環境）
- STEP A lawtime apply: branch → v0.2.2+v0.2.3 patch（NOT VALID→backfill('unchecked')→
  gate_backfill_unknown_unchecked 空→VALIDATE）→ lawtime gate 群 0件 → R-1 view → 監査 → ratify → apply。
- STEP B lawsubtrans P1 dry-run: 001→002→003→004→(lawtime後)005 → fixture 投入＋わざと違反1件 →
  verify_dry_run.sql で全16 gate 0件 → 監査(DDLAWSUBTRANS) → ratify → apply。
- STEP C P2 ingest: producer JSONL→DB 冪等 UPSERT（dedup_key）。accepted/claim_support=true を書けない
  ことを DB 制約＋CI で二重保証。dispute/review-event→T6 append。冪等試験→監査。
- STEP D P3 較正: lawdelta=既知改正ペア（alo-kg/raw/egov_revisions/ 3,506 rev）で閾値確定。
  casetreatment/drafterintent=実判決・実逐条解説で pattern_id 単位 precision。
- STEP E P4 curation（binding キュー＋review-event 起票、dispute target のみ人手）。
- STEP F P5 MCP（mcprender 接続、formal_note は R-1 view 自動取得、snapshot test）。

## 4. production 精緻化（監査 note 由来・STEP B/C で閉じる）
gate9/13 結合キー近似→edge 単位／evidence_count=1 暫定→multi-evidence join table／
gate13 を T3/T4 へ拡張／formal_status は R-1 view 算出（物理ミラーなら drift gate）。

## 5. 不変の安全弁（全 STEP）
candidates-only / claim_support 既定 false / 両論併記 / append-only /
accepted は人手 review-event 専権 / 形式(lawtime)と実質(lawsubtrans)の分離 /
「改正あり⇒実質変更あり」を物理制約で禁止。
