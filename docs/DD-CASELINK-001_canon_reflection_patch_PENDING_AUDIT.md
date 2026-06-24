# DD-CASELINK-001 → 正典反映パッチ（**適用待ち / DO NOT APPLY YET**）

> ⛔ **適用条件**: `DDCASE_PASS(_WITH_NOTES)` + 浅井先生 ratify + **Wave57 MAP_UPDATE owner GO** が揃うまで適用しない。
> 本ファイルは repo 内の*下書き diff* であり、Box の設計正典（`docs/alo/35_link_layer.md` 等）は**監査前に編集しない**（設計正典の単一書き手＝owner を保つ / 地図ガバナンス遵守）。
> 適用先正本はローカル `事務所内本棚DX化計画/docs/alo/`（Mac CC）→ Box ミラー同期。

DD-CASELINK-001 v0.2 §7 の「正典反映 queue」を、適用時にそのまま使える形に展開したもの。3点。

---

## パッチ1 — `35_link_layer §2.1/§2.2`: `alo_edges` に `stance` qualifier 列を追加
**目的**: commentary→case の `compares` に「同旨(supporting)／反対(contrasting)／中立(neutral)」を保存（edge_type は増やさない）。§11「OPPOSES」開項目の解決方針。

### §2.1 カラム仕様 に1行追加
| カラム | 型 | NULL | 備考 |
|--------|-----|------|------|
| `stance` | text | ○ | `compares`(commentary→case)の同旨/反対。CHECK: ck_ae_stance。NULL=非該当(大半のedge) |

### DDL（適用時）
```sql
ALTER TABLE alo_edges
  ADD COLUMN stance text NULL;

ALTER TABLE alo_edges
  ADD CONSTRAINT ck_ae_stance
  CHECK (stance IS NULL OR stance IN ('supporting','contrasting','neutral'));

-- stance は compares 以外では NULL を推奨(運用則。物理制約にはしない＝将来の他edge転用余地を残す)
COMMENT ON COLUMN alo_edges.stance IS
  'commentary→case の compares における同旨/反対(supporting/contrasting/neutral)。DD-CASELINK-001。NULL=非該当';
```
- `alo_edges_active` VIEW は `SELECT *` のため stance は自動的に透過（変更不要）。
- 既存 EXCLUSION / uq_dedup 制約は stance を含めない（同一(src,dst,edge_type)の時点重複判定に stance は影響させない）。

### §2.2 edge_type 一覧 — 脚注追記（edge_type は増やさない）
> `compares`(commentary→case) は `stance` 列で同旨/反対を保存（DD-CASELINK-001）。`evaluates`/`review_chain` は評価そのもののため stance=NULL。

---

## パッチ2 — `35_link_layer §6 エッジ生成パターン`: 本文採掘の生成元を1行追加
現状は「文献**標題**推定マッチ → evaluates (strength=implicit)」のみ。**本文採掘**経路が未記載。

### §6 表に追加
| ソース | edge_type | assertion_mode | 仕様書参照 |
|--------|-----------|----------------|------------|
| 雑誌/文献**本文**採掘（masthead/本文 span） | `evaluates`／`compares`(+stance) | masthead=vendor_explicit ／ 本文=vendor_implicit(strength=implicit) | DD-CASELINK-001（`case_link_extract`→`case_link_map`） |

- masthead 由来=自動エッジ可（vendor_explicit）／本文由来=review-first（vendor_implicit, strength=implicit）。
- `llm_inferred` は生成しない（PoC DB制約）。LLM は候補提示まで。

---

## パッチ3 — `33_magazine_layer §4`（OPAC判評）に境界注記
OPAC由来(書誌レベル)と本文採掘(記事内 span)の**二経路**がともに `evaluates` を生むことを明示。

### §4 に注記追加
> 評釈→判例の `evaluates` には二経路がある: (1) **OPAC判評**（書誌レベル・本 §4）、(2) **記事本文採掘**（記事内 span・DD-CASELINK-001）。両者は重複しうるため、`alo_edge_evidence`（role=source_field/quote）と source_system で由来を区別し、`DD-CASECORROB-001` L2 で独立源一致として confidence を加点する（merge はしない）。

---

## 適用後チェック（owner/Mac CC）
- `35_link_layer §8 品質ゲート` に stance の値域逸脱が無いこと（CHECK で物理担保）。
- repo 側 `case_vocab.LINK_STANCES` と DDL の CHECK が一致（`test_case_consistency` が既に repo 側を担保）。
- Wave57: MAP_UPDATE → MAP_VALIDATE 完了まで反映は未完扱い。
