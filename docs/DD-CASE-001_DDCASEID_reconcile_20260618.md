# DD-CASE-001 ↔ DD-CASEID-001 reconcile メモ (S2 / accept条件)

- date: 2026-06-18 JST
- author: Claude (Project-codex セッション)
- status: **read-only reconcile メモ / HOLD維持**。DD-CASEID-001 `_accepted_v1.0_with_notes` 昇格の**前提資料**（GPT監査 must_fix #4 / finding G）。
- 対象: `DD-CASEID-001`(Box 2266457039407, ID確定機能) ／ `DD-CASE-001`(individual_judgment_canonical_node draft, **下記 §4 の所在問題あり**) ／ 周辺の cases系DD群

> 監査 finding G: 「DD-CASEID は case identity resolution の**上流機能**、DD-CASE-001 は cases母型・準司法を含む**エンティティ設計**。両者を重ねると case_key・canonical_uri・case_type・forum_code の責務が曖昧になる。」本メモはその責務を確定する。

---

## 1. 最重要発見 — "cases" の語が2つの別オブジェクトで衝突している

`cases` という名称が、**まったく別の2オブジェクト**に使われている。reconcile の第一の仕事はこの分離を固定すること。

| オブジェクト | 主キー | URI namespace | 何か | DD |
|---|---|---|---|---|
| **受任案件（matter）** | `alo_matter_id` (ULID) | `alo:matter:{ULID}` | 事務所の顧客案件（SF LEALA由来。受任事件/顧問/相談/研修） | DD-DYNDB-CASES-001（`dynamic.cases`） |
| **判例（precedent）** | `case_key` (CK-{ULID}) | `alo:case:jp:...` | 公表された裁判例・準司法判断 | DD-CASEID-001 / DD-CASE-001 / 31_case_layer |

- DD-CASEID-001 自身が既に注記: 「DDL-20260322-09（案件横断ID＝matter主キー、**別オブジェクトで衝突なし**）」。本メモでこれを**明示的な不変則に格上げ**する。
- **不変則 N-1**: `case_key`（判例）と `alo_matter_id`（受任案件）は**相互に代入・FK・混在禁止**。テーブル `dynamic.cases`（matter）と `cases`（判例）は別schema・別ライフサイクル。
- jufu（受任手元判決）は、この2つを**橋渡しする唯一の点**だが、識別evidenceとしてのみ使い、matter本体とは別管理（監査note 3）。

---

## 2. 判例サイドの DD 責務分担（重ねない）

判例オブジェクト側には複数DDがあり、責務を縦に積む：

| 層 | DD | 責務（owns） | 他DDに委ねる（not owns） |
|---|---|---|---|
| **エンティティ母型** | DD-CASE-001（individual_judgment_canonical_node） | 「canonicalな判例ノードとは何か」＝node存在・**case_type**(judicial/adr/conciliation/adjudication)・準司法の収容 | 名寄せ手順・採番（→CASEID） |
| **ID確定（上流機能）** | **DD-CASEID-001** | **case_key採番**・**canonical_uri生成**(fn_v2)・名寄せTier・case_observation・resolution_log・**forum_code registry** | node意味論・case_type定義（→CASE-001） |
| **取水口＋機密** | DD-CASE-SOURCE / DDCASESOURCE v0.4 | source_registry・**content_grade**・**confidentiality_class**・jufu隔離（matter_confirmed/matter_scoped_only/backfill==open/embedding global禁止） | identity確定（→CASEID） |
| **要約** | DD-CASESUM-001 | case summary（下流annotation） | identity・source |

### 監査の4つの曖昧面 → 責務の確定

| 曖昧面 | 一次所有 | 整合相手 |
|---|---|---|
| **case_key** | DD-CASEID-001（mint・不変anchor） | — |
| **canonical_uri** | DD-CASEID-001（fn_generate_case_uri_v2） | — |
| **case_type** | **DD-CASE-001**（エンティティ母型が定義） | CASEID は forum_type↔case_type を**整合させるだけ**（court→judicial 等） |
| **forum_code** | DD-CASEID-001（alo_forum_registry） | CASE-001 の case_type / DDCASESOURCE の準司法機関と整合 |

→ **不変則 N-2**: case_type の**定義**は DD-CASE-001、forum_code の**registry**は DD-CASEID-001。CASEID は case_type を新規定義しない（参照・整合のみ）。

---

## 3. 機密（jufu）責務の一本化

監査 finding F / note 3 / DDCASESOURCE v0.4 が同じ機密machineryを別々に持つと二重管理になる。

- **不変則 N-3**: 機密・配布可否は **DD-CASE-SOURCE/DDCASESOURCE が一次所有**（`confidentiality_class` / `source_visibility` / `claim_support_eligible` / `mcp_exportable`）。
- DD-CASEID-001 の `content_grade` は **identity確定のための観測属性**に限定し、**配布判断はしない**（配布は DDCASESOURCE の confidentiality に委譲）。
- jufu: CASEID は identity evidence に使う／DDCASESOURCE が出口（claim_support/MCP/export）を**全面禁止**。役割が分離していれば二重管理にならない。

---

## 4. ⚠ accept前に解くべき所在問題（重要）

reconcile を**最終確定するには DD-CASE-001 の正本が必要**だが、現状：

- DD-CASE-001（`DD-CASE-001_individual_judgment_canonical_node_draft_v0.1.md`）は、2026-06-06 の準司法監査(DDCASESOURCE v0.4)時点で **Box `docs/alo` に不在＝BLOCKED**と番頭が確認（DD_REGISTRY 0件・Box検索ヒット無・実フォルダ位置が空）。準司法DDはそのため監査不能で `status: blocked`。
- つまり **DD-CASE-001 は現時点で安定したBox正本として確認できない**（ローカル下書きのまま未アップロード or 改名の疑い）。

### 含意
- 本メモは責務分担の**枠組み（不変則 N-1〜N-3 と §2 の所有表）を確定**する。これは DD-CASE-001 の本文が無くても、DD-CASEID-001・DD-DYNDB-CASES-001・DDCASESOURCE v0.4・監査findingから導ける。
- ただし **case_type の正準enum・individual_judgment_canonical_nodeの確定schema** は DD-CASE-001 正本に依存する。
- → **accept条件の充足度**:
  - ✅ 枠組みreconcile（N-1〜N-3 / 所有表）= 本メモで充足。
  - ⏳ 詳細field-levelreconcile = **DD-CASE-001 正本の所在確定が前提**。

### 推奨
1. DD-CASEID-001 は本メモ（枠組み）を前提資料に `_accepted_v1.0_with_notes` へ **ratify可**（監査も blocking無）。
2. ただし accept-note に「**case_type定義は DD-CASE-001 に従属。DD-CASE-001 正本の Box 所在を確定し、field-levelreconcileを CASEID-002 以前に完了**」を追記。
3. DD-CASE-001 / 準司法DDの**正本を Box `docs/alo` にアップロード**（番頭タスク）→ 準司法監査(DDCASESOURCE)の blocked 解除も同時に進む。

---

## 5. 確定する不変則（まとめ）

```
N-1: case_key(判例) と alo_matter_id(受任案件) は別オブジェクト。相互代入・FK・混在禁止。
N-2: case_type の定義=DD-CASE-001 / forum_code registry=DD-CASEID-001。CASEIDはcase_typeを新規定義しない。
N-3: 機密・配布可否=DDCASESOURCE が一次所有。CASEIDのcontent_gradeはidentity観測のみ、配布判断しない。
N-4: DD-CASEID-001 は「ID確定の上流機能」、DD-CASE-001 は「判例ノードのエンティティ母型」。重ねない。
```

→ この4則を DD-CASEID-001 `_accepted_v1.0_with_notes` の前提資料として添付（監査 must_fix #4 充足）。
