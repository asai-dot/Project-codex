---
request_id: 20260623_commercialreclass_v0.2_DDPROCREG
topic: commercialreclass
gate: DDPROCREG
version: v0.2
supersedes: 20260621_commercialreclass_v0.1_DDPROCREG
source_hash: sha256:4603f3eca72f8be382e91d7c16d60013470e2ab85787ab56372ad5da1a3289bf   # procedure_registry.json(v0.2) + procedure_registry.py + test_procedure_registry.py + v0.1_RESULT
git_commit: 89e21ec6093faf8f807120f9360797094b6c4d3e
git_branch: claude/pipeline-collect-validation-EnNJM
git_pr: https://github.com/asai-dot/Project-codex/pull/15
result_expected_filename: 20260623_commercialreclass_v0.2_DDPROCREG_RESULT.md
status: dispatched
dispatched_at: 2026-06-23   # Box gpt_ometsuke/to_gpt/ へ投函 (owner 承認「しておいて」)
prior_result: docs/dd/20260621_commercialreclass_v0.1_DDPROCREG_RESULT.md (DDPROCREG_MODIFY_REQUIRED)
---

# 20260623 commercialreclass v0.2 — 商事再分類 **再投函**（DDPROCREG / MODIFY_REQUIRED 反映）

- gate: **DDPROCREG** / version: v0.2 / supersedes v0.1 / 種別: owner ratify packet（再監査依頼）
- RESULT 先頭行: `DDPROCREG_PASS` / `DDPROCREG_PASS_WITH_NOTES` / `DDPROCREG_MODIFY_REQUIRED` /
  `DDPROCREG_FAIL` / `DDPROCREG_NEED_MORE`
- 前回判定 `DDPROCREG_MODIFY_REQUIRED`（v0.1 RESULT）の **must_fix MF-1〜4 を schema/validator で反映**。
  本番 write・`owner_ratified` 追記は一切していない（全 entry candidate・owner_ratified 0件）。

## 0. 何を直したか（MF 対応サマリ）

| # | 前回指摘 | v0.2 での閉じ方（実装・テスト緑） |
|---|---|---|
| MF-1 | family↔6手続の親子が schema に無い | `procedure_registry.json` に **`family_membership` crosswalk** 新設（`{family_id, procedure_id, valid_from, valid_to, source_basis, status}`）。`validate_family_membership` が参照存在・kind 整合（family=procedure_family / member=procedure\|variant）・自己参照・重複を検査 |
| MF-2 | `commercial_nonlitigation` の同一ID silent narrowing | **意味を狭めない**。`rollup_notes` で `action: keep_unchanged` を宣言。`narrow/split/deprecate` を選ぶ場合は **supersession 記録を validator が必須化**（`_check_rollup_semantics`）。court 会社非訟用の新ID/split は owner 判断 + L2 migration として HOLD のまま |
| MF-3 | owner_ratified の根拠が `ratified_by/at` だけ | validator が **`ratification_basis_type`(enum: owner_legal_judgment / statutory_plus_practice / multi_source) + `ratification_basis_refs` か `statutory_or_official_refs` + `ratification_note`** を必須化 |
| MF-4 | ordinary_liquidation の昇格水準 | `ordinary_liquidation` を **candidate 止め**。`definition`/`start_trigger`/`terminal_state` の操作的定義を付与。特別清算（`insolvency_special_liquidation`）と別 procedure と明記 |

## 1. registry v0.2 の現状（`pipeline/procedure_registry.json`）

```text
version 0.2 / entries 8件 = candidate 8 / owner_ratified 0
family: corporate_reorganization(procedure_family) ← merger / company_split / share_exchange /
        share_transfer / entity_conversion / share_delivery（family_membership で6本）
ordinary_liquidation: candidate（特別清算と別・操作的定義つき）
commercial_nonlitigation: rollup_notes=keep_unchanged（狭めない）
validate_registry: 健全（不変条件 0 違反）
promotion_report: 単一source ゆえ 0/8 自動昇格なし（ゲート機能維持）
```

- Q-A: `entity_conversion` は会社法上の「組織変更」と一対一であることを definition/aliases に固定。
- Q-E: `share_delivery.flow_ref` で `commercial_share_delivery.json` を別ゲート紐付け（identity の独立証拠に数えない・`flow_status: draft`）。

## 2. 確認いただきたい点（v0.2）

1. **MF-1**: `family_membership` crosswalk（option B）で親子関係の規範表現として十分か。`parent_family_id`
   方式（option A）との併用は不要、で合っているか。
2. **MF-2**: 「`commercial_nonlitigation` は keep_unchanged で据え置き、court 会社非訟用の新ID/split は
   owner+L2 migration 待ち」という保守的選択で v0.2 として妥当か。
3. **MF-3**: owner_ratified の必須メタ（type/refs/note）の粒度はこれで監査可能性を満たすか。
4. **MF-4 / should_fix-1**: candidate entry に持たせた `definition/start_trigger/terminal_state` の
   水準（`legal_basis_refs` は ratify 時に固定する前提で現状空）で良いか。

## 3. HOLD（v0.2 でも踏まない）

- `owner_ratified` の本番追記（owner ratify の手を経るまで書かない）。
- `commercial_nonlitigation` の scope 縮小・`procedure_spine.json` の意味変更。
- DDL / DB write / canonical promotion / MCP publication。
- 法人類型の直積展開（sparse facet/variant のまま）。

## 4. 参照

- v0.2 実装: `pipeline/procedure_registry.json` / `scripts/procedure_registry.py`
  （`validate_family_membership` / `_check_rollup_semantics` / ratification_basis 検査）
- テスト: `tests/test_procedure_registry.py`（family membership・silent narrowing guard・ratification basis を固定、全緑）
- 前回 RESULT: `docs/dd/20260621_commercialreclass_v0.1_DDPROCREG_RESULT.md`
