---
request_id: 20260621_commercialreclass_v0.1_DDPROCREG
topic: commercialreclass
gate: DDPROCREG
version: v0.1
source_hash: sha256:207e1315985b6b0f4f36118512e1cf4ee57287302db8697877ec76876a2a814a   # procedure_registry.json + procedure_registry.py + procedure_inventory.json + procedure_spine.json + dd_procedure_design.md
git_commit: 53879625d3608bfde96131a684260feef58c6518
git_branch: claude/pipeline-collect-validation-EnNJM
git_pr: https://github.com/asai-dot/Project-codex/pull/15
result_expected_filename: 20260621_commercialreclass_v0.1_DDPROCREG_RESULT.md
status: dispatched
dispatched_at: 2026-06-21   # Box gpt_ometsuke/to_gpt/ へ投函済 (owner 承認「どうぞ」)
box_file_id: 2299571392411
box_path: 浅井/claude/handoffs/gpt_ometsuke/to_gpt/20260621_commercialreclass_v0.1_DDPROCREG_REQUEST.md
---

# 20260621 commercialreclass v0.1 — 商事再分類 **owner ratify packet**（DDPROCREG）

- gate: **DDPROCREG**（procedure 再分類 / L1 registry 昇格）/ topic: commercialreclass / version: v0.1
- RESULT 先頭行: `DDPROCREG_PASS` / `DDPROCREG_PASS_WITH_NOTES` / `DDPROCREG_MODIFY_REQUIRED` /
  `DDPROCREG_FAIL` / `DDPROCREG_NEED_MORE`
- 種別: **owner ratify packet**。これは「正本化の起案」であって、番頭は**自動正本化しない**。
  本 packet の承認（owner ratify ＋ GPT お目付け）を経て初めて registry に owner_ratified を書く。

## 0. これは何（一言）
前回 `20260619_spinebottomup DDPROGRESS_PASS_WITH_NOTES` の **must_fix5（商事6手続を
`commercial_nonlitigation` 直下に置かず再分類）** と Q1（三層化）の積み残しを、**具体的な registry 差分**
として起案する。spine 正本（L2 roll-up）は触らず、**L1 `procedure_registry.json` への追加案**を問う。

## 1. 背景（実データで確認済の事実）
`spine_reconcile.py`（commit 5387962）で確認:
- `commercial_nonlitigation`（spine 1類型）に **実データで6手続**（合併/会社分割/株式交換/株式移転/
  組織変更/株式交付）がぶら下がる ＝ 過少解像 **かつ category error**（これらは裁判所の会社非訟ではなく
  会社法上の組織再編・会社行為・登記手続）。
- `通常清算` が spine に無い（特別清算のみ）。
- `procedure_registry.py` のゲートでは、現 inventory は**単一source**ゆえ **0/8 が candidate 不適格**
  （must_fix7「1冊1章 auto-accept しない」が発火）。⇒ **本 packet は owner ratify による昇格**を問う
  （独立source追加を待たず、owner の判断で owner_ratified にするか）。

## 2. 提案（registry 差分・**未適用**）

### 2-1. `corporate_reorganization` family を新設し、6手続を再分類
`commercial_nonlitigation` 直下の「分割」ではなく、会社法手続の **family 新設**として:

```json
{"id": "corporate_reorganization", "kind": "procedure_family", "status": "owner_ratified",
 "name": "組織再編", "legacy_rollup_id": "commercial_nonlitigation",
 "ratified_by": "<owner>", "ratified_at": "<date>"}
```
配下 procedure（status は owner 判断。owner ratify なら owner_ratified、保留なら candidate）:

| id | name | 旧 spine_ref | source |
|---|---|---|---|
| merger | 合併 | commercial_nonlitigation | 商業登記全書/7 第2編 |
| company_split | 会社分割 | 〃 | 第3編 |
| share_exchange | 株式交換 | 〃 | 第4編 |
| share_transfer | 株式移転 | 〃 | 第4編 |
| entity_conversion | 組織変更 | 〃 | 第5編 |
| share_delivery | 株式交付 | 〃 | 第6編（flow 実在: commercial_share_delivery.json） |

### 2-2. `commercial_nonlitigation` は**裁判所の会社非訟**として維持
検査役選任・新株発行差止・減資の認可等の**非訟手続**は別物として残す（aliases: 会社非訟/株主総会検査役/
新株発行/減資）。⇒ 旧 umbrella は「会社非訟」に**意味を絞る**（supersession ではなく scope 縮小）。

### 2-3. `通常清算` を新規 procedure として収容
```json
{"id": "ordinary_liquidation", "kind": "procedure", "name": "通常清算",
 "legacy_rollup_id": null, "source": "株式会社・各種法人別 清算手続と書式 第2章"}
```
（`special_liquidation`＝特別清算は既存 spine `insolvency_special_liquidation` に対応。）

### 2-4. 法人類型は **sparse facet / variant**（直積表にしない）
清算の法人類型別（医療/社福/NPO/宗教/学校/持分会社/士業）は `procedure_variant` か
applicability crosswalk で持つ。本 packet では **facet の存在を確認するに留め**、実体化は別 packet。

## 3. owner / GPT に問いたいこと（判断ポイント）
1. **Q-A 命名/ID**: `corporate_reorganization` family と 6 procedure ID（英小文字 snake）でよいか。
2. **Q-B 昇格水準**: 単一source（商業登記全書/7 のみ）の現状で、owner ratify によって
   `owner_ratified` まで上げるか、それとも `candidate` 止まりにして独立source追加を待つか。
3. **Q-C 会社非訟の scope 縮小**: `commercial_nonlitigation` を「会社非訟」に絞る扱いは supersession
   不要（同一IDのまま意味確定）でよいか。`legacy_rollup_id` の張り先として残すか。
4. **Q-D variant vs facet 境界**: 通常清算 × 法人類型は `procedure_variant`（局面分岐）か、単なる
   entity facet（適用可否のみ）か。RESULT Q3 の操作的定義に照らした判断。
5. **Q-E 株式交付**: 既に flow 実体（commercial_share_delivery.json）がある。これを registry の
   `flow` 参照として紐付けてよいか。

## 4. HOLD（本 packet では踏まない）
- spine 正本（`procedure_spine.json`）の置換・大量改訂。
- registry への owner_ratified の**自動**書き込み（owner ratify の手を経るまで書かない）。
- 法人類型の全組合せ実体化（直積表）。
- DDL / DB write / MCP publication / requirement_floor の accepted化。

## 5. 反映の道筋（承認後）
RESULT が `PASS` / `PASS_WITH_NOTES` なら、その next_action に従って owner が
`procedure_registry.json` に ratify メタ付きで追記 → `procedure_registry.py` の
`validate_registry` で不変条件を検算 → 台帳 `_AUDIT_LEDGER` に記録。**監査結果≠即正本化**。
