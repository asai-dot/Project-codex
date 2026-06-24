---
request_id: 20260624_commercialreclass_v0.3_DDPROCREG
topic: commercialreclass
gate: DDPROCREG
version: v0.3
supersedes: 20260623_commercialreclass_v0.2_DDPROCREG
source_hash: sha256:faa734d07c89a00ae1c9a5ed384bd5a8e4d5d5082870cc7350e9f7631908d67b   # procedure_registry.json(v0.3) + procedure_registry.py + test_procedure_registry.py + v0.2_RESULT
packet_commit: PENDING_PUSH
implementation_commit: 558ff2e922f60f6f3808950c4a0b798142d6b15f
git_branch: claude/pipeline-collect-validation-EnNJM
git_pr: https://github.com/asai-dot/Project-codex/pull/15
result_expected_filename: 20260624_commercialreclass_v0.3_DDPROCREG_RESULT.md
status: dispatched
dispatched_at: 2026-06-24   # Box gpt_ometsuke/to_gpt/ へ投函 (owner 承認・監査ループ継続)
prior_result: docs/dd/20260623_commercialreclass_v0.2_DDPROCREG_RESULT.md (DDPROCREG_MODIFY_REQUIRED)
---

# 20260624 commercialreclass v0.3 — 商事再分類 **再投函**（DDPROCREG / v0.2 RESULT 反映）

- gate: **DDPROCREG** / version: v0.3 / supersedes v0.2 / 種別: owner ratify packet（再監査依頼）
- 前回 v0.2 判定 `DDPROCREG_MODIFY_REQUIRED`（MF-1/MF-2/MF-4 は CLOSED、blocker は **MF-3** と
  **canonical 境界**）。§5「再監査の最小受入条件」を**全て機械化**した。本番 write・`owner_ratified` 追記なし。

## 0. §5 最小受入条件への対応（全クローズ）

| §5 条件 | v0.3 での実装（validator 強制・テスト固定） |
|---|---|
| 1. owner-ratified validator が全必須根拠を non-empty 要求 | `validate_registry` の owner_ratified 検査を強化。`ratified_by / ratified_at / ratification_basis_type(enum) / ratification_basis_refs[] / statutory_or_official_refs[] / source_family_refs[] / legal_basis_refs[] / ratification_note` を**全て non-empty で必須**（`RATIFY_REQUIRED_SCALARS` / `RATIFY_REQUIRED_LISTS`） |
| 2. owner note だけの fixture を fail、完全根拠だけ pass | positive を完全根拠集合に置換。各根拠フィールドを1つずつ空にする **per-field negative fixture** を追加（`test_validate_invariants`） |
| 3. procedure ratify 時 `legal_basis_refs` 必須 | 上記 `RATIFY_REQUIRED_LISTS` に `legal_basis_refs` を含め、owner_ratified で non-empty 強制 |
| 4. candidate dry-run と canonical L1 の境界を機械可読化 | registry に `registry_mode: design_fixture` / `materialization_status: noncanonical`。validator が enum 強制、`is_production_loadable()` は **canonical のみ受理**（`test_canonical_boundary`） |
| 5. test log を source commit と紐付け同梱 | 本 REQUEST §3 に test log + commit SHA を同梱 |

## 1. その他 RESULT 所見への対応

- **MF-1 補強（§1 NOTES）**: membership に `valid_from` 必須 / `valid_to > valid_from`(or null) /
  `source_basis` 非空を validator 化（`test_membership_validity_checks`）。
- **flow_ref provenance（§2.2）**: `share_delivery.flow_ref` に `artifact_version: v0.1` /
  `artifact_hash: sha256:093af2011f966adf…` / `source_lineage`（bencom 綺麗TOC 由来）を付与。
  flow acceptance は L1 ratification と別ゲートのまま。
- **MF-4 構造化 applicability（§1.MF-4）**: `ordinary_liquidation` に `applicable_entity_types: ["株式会社"]`。
- **provenance pointer（§2.3）**: front-matter を `packet_commit` と `implementation_commit` に分離。

## 2. registry v0.3 の現状（`pipeline/procedure_registry.json`）

```text
version 0.3 / registry_mode=design_fixture / materialization_status=noncanonical
entries 8 = candidate 8 / owner_ratified 0
family corporate_reorganization ← merger/company_split/share_exchange/share_transfer/
                                   entity_conversion/share_delivery（family_membership 6本・validity 検査つき）
ordinary_liquidation: candidate（applicable_entity_types=[株式会社]）
commercial_nonlitigation: rollup_notes=keep_unchanged
validate_registry: 健全（0 違反）/ is_production_loadable=false（noncanonical）
promotion_report: 0/8 自動昇格なし（単一source ゲート維持）
```

## 3. test evidence（§5.5）

```text
implementation_commit: 558ff2e922f60f6f3808950c4a0b798142d6b15f
branch: claude/pipeline-collect-validation-EnNJM
command: for t in tests/test_*.py; do python3 "$t"; done   (stdlib のみ・ローカル実行)
exit: 全 0

test_egov_fetch.py            25 passed
test_floor_reconcile.py        8 passed
test_handoff_tools.py         26 passed
test_legallib_join.py         80 passed
test_pipeline.py              70 passed
test_procedure.py             17 passed
test_procedure_flow.py         7 passed
test_procedure_flow_from_toc.py 9 passed
test_procedure_registry.py    47 passed   ← MF-3 全フィールド必須/per-field negative/canonical 境界/membership validity
test_requirement_floor.py     10 passed
test_spine_reconcile.py       15 passed
TOTAL: 314 checks passed, 0 failed
```

## 4. HOLD（v0.3 でも踏まない）

- `owner_ratified` の本番追記 / 単一source候補の canonical L1 materialization。
- `commercial_nonlitigation` の scope 縮小・`procedure_spine.json` の意味変更。
- DDL / DB write / canonical promotion / MCP publication / claim-support。
- 法人類型の直積展開（sparse facet/variant のまま）。

## 5. 参照
- 実装: `pipeline/procedure_registry.json`(v0.3) / `scripts/procedure_registry.py`
  （owner_ratified 全根拠必須 / `is_production_loadable` / `validate_family_membership` validity）
- テスト: `tests/test_procedure_registry.py`（47 checks）
- 前回 RESULT: `docs/dd/20260623_commercialreclass_v0.2_DDPROCREG_RESULT.md`
