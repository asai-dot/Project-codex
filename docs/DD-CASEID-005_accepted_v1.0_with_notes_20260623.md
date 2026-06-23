# DD-CASEID-005 — jufu 取込境界（identity 利用と出口遮断） **accepted v1.0_with_notes**

- accept(ratify)日時: **2026-06-23 JST（浅井さん「両方アクセプト」）**
- lifecycle: draft v0.1 → **`accepted_v1.0_with_notes`**（design accept・production HOLD）
- 監査: **`DDCASEID_PASS_WITH_NOTES`**（2026-06-23, GPT Pro, result 2303545117228）
- 設計本体: `DD-CASEID-005_jufu_intake_boundary_draft_v0.1_20260623.md`(Box 2303458384177)
- 実装: `scripts/jufu_intake.py` / `scripts/test_jufu_intake.py`
- parent: `DD-CASEID-001`(accepted, N-1) / `DD-CASE-001`(accepted, AC-3) ／ related: DDCASESOURCE / CASEBIND G2 / CASECITE V7/V8
- 位置づけ: DD-CASEID-001 §5 follow-up の最後の下位DD＝**CASEID ファミリー完結**

> **accepted 正本**。設計本体は v0.1。accept-notes を本文則化。design accept であり production acceptance ではない。「jufu は識別には効くが出口には出ない」（監査 final）。

## 0. 確定（accept 済の中核）
受任手元判決(jufu)は **identity evidence 専用**。global 出口5点は全拒否、matter 内は認可者に閲覧系のみ。`case_key`(判例) ≠ `alo_matter_id`(受任案件)（N-1）。

## 1.5 Accept-notes（拘束）
- **AC-1（identity/出口分離）**: jufu は A1 同一性 evidence に使える。**global の出口5点（global_content_index/embedding/mcp_serve/export/claim_support）は全拒否**。
- **AC-2（matter 内境界）**: matter 内は**認可者に display/mcp_serve のみ**。export/claim_support は matter 内でも拒否。
- **AC-3（RP-04 徹底）**: jufu embedding は **matter 認可でも global 禁止**。matter-local vector を将来許す場合は `namespace=matter_private` / `retrieval_scope=authorized_matter_only` / no_global_index・no_global_training を明示（監査 should_fix#1）。
- **AC-4（分類必須・監査 should_fix#2）**: jufu identity evidence に `source_class=private_jufu` / `egress_class=matter_confidential` を必須付与。
- **AC-5（fail-closed・監査 should_fix#3）**: CASECITE V7/V8 接続で `authorized_matter_ids` 空/未指定は **fail-closed**（実装済挙動）。authorized viewer でも **global bundle へ混入させない**（V7×V8 併用）。
- **AC-6（N-1）**: `case_key` と `alo_matter_id` の相互代入・FK・混在禁止（判例と受任案件オブジェクトの汚染防止）。
- **AC-7（HOLD）**: DDL / DB write / jufu本文の外部利用 / global cite / claim_support / public CaseBundle / canonical promotion は HOLD。

## 2. verification（充足）
- self = `test_jufu_intake.py` green（exit 0、identity許可・global出口全拒否・embedding matter認可でも拒否・matter内は認可閲覧のみ・分類）。
- audit = PASS_WITH_NOTES（2026-06-23）。owner = ratified（2026-06-23）。

## 3. 残務
- Mac CC: access policy 統合（read-only/dry-run）、source_class/egress_class 付与（AC-4）、matter-local vector の namespace 分離（AC-3, 将来）。台帳登録。
