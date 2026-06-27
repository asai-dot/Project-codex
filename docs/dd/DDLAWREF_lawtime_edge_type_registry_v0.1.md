# Edge_type Registry — DDLAWREF × lawtime 統合管理表 v0.1

> 管理: **DDLAWREF**（vocabulary owner）× **DD-LAWTIME-001**（temporal evaluation scope）
> 根拠: DDLAWREF v0.1 RESULT §3.3（Box from_gpt file_id `2305640889317`、2026-06-26）
>   "edge_type registry を作り、各 edge_type について definition / allowed src_type /
>    allowed dst_type / temporal evaluation required / claim_support default /
>    evaluation layer handoff rule を定義する"
> 日付: 2026-06-27（初版）
> 状態: **DRAFT** — DDLAWREF 側の formal confirm 待ち

---

## 凡例

- **temporal_eval_required**: `YES` = `lawtime.citation_temporal` 行が必要（lawtime gate 対象）。
  `NO` = lawtime 不関与。`TBD` = Q3/DDLAWREF clarification 待ち。
- **claim_support_default**: `false` = 明示 eval なしでは claim_support_eligible = false。
- **eval_handoff**: 評価層への送付先。`LAWTIME` = temporal eval / `LAWSUBTRANS` = 実質評価。

---

## Edge_type 定義表

| edge_type | 定義 | src_type | dst_type | temporal_eval_required | claim_support_default | eval_handoff |
|---|---|---|---|---|---|---|
| `cites_statute` | 条文が他の法令・条文を参照する（general statute citation） | article / provision | law / article | **YES** | false | LAWTIME |
| `delegates_to` | 法令条文が政令・省令等に委任する（委任チェーン） | article | law (subordinate) | **YES** | false | LAWTIME |
| `references` | 条文間相互参照（同一法内・別法間）| article | article | **YES** | false | LAWTIME |
| `implements` | 実施規定・施行令が根拠法令と接続する | law (subordinate) | law (parent) | **YES** | false | LAWTIME |
| `reads_as` | 読替え・準用・みなし（特定文言を他に読み替えて適用）| article | article | **TBD** | false | TBD — Q3 pending |
| `authority_basis` | 行政文書が根拠条文を参照する（根拠付け） | admin_doc | article | NO | false | LAWSUBTRANS |
| `cites_administrative_guidance` | 条文が告示・通達・ガイドライン等を参照する | article | admin_doc | NO | false | LAWSUBTRANS |

---

## lawtime 管理範囲（`citation_edge_type_v20260624`）

lawtime が `citation_temporal` の側テーブル行を要求するのは `temporal_eval_required = YES` の4種：

```sql
-- migrations/lawtime/placement_v0.2.4/200_gates.sql
CREATE OR REPLACE VIEW lawtime.citation_edge_type_v20260624 AS
  SELECT edge_type FROM (VALUES
    ('cites_statute'),
    ('delegates_to'),
    ('references'),
    ('implements')
  ) AS t(edge_type);
```

`reads_as` は temporal_eval_required が TBD のため現在除外。Q3 RESULT で確定後に追加可。

---

## 除外理由メモ

| edge_type | 除外理由 |
|---|---|
| `reads_as` | 読替えの「読替え版の法令が施行中か」は temporal 問いになりうる。ただし dst が article 内テキスト変換で law revision とは対応しない可能性あり。Q3（dst_uri URI 規約）確定後に判断。 |
| `authority_basis` | 根拠条文を参照するのは行政文書（admin_doc）側。行政文書の temporal validity は lawtime の scope 外（law_revision を持たない）。 |
| `cites_administrative_guidance` | 被参照が告示・通達（admin_doc）であり law revision 体系に乗らない。temporal resolver の対象外。 |

---

## source provenance 必須項目（DDLAWREF v0.1 RESULT §3.2）

各 edge に必須:

| 項目 | 型 | 備考 |
|---|---|---|
| `source_system` | text | 抽出元システム識別子 |
| `source_version` | text | パーサバージョン |
| `source_document_uri` | text | 抽出元文書 URI |
| `source_text_span` | text | テキスト位置（nullable） |
| `parser_version` | text | |
| `extraction_method` | text | `manual` / `auto` / `hybrid` |
| `confidence` | text / numeric | |
| `review_status` | text | `reviewed` / `unreviewed` / `confirmed` |
| `fetched_at` / `snapshot_id` | timestamp / text | |

`unknown` を claim_support に使わない（DDLAWREF RESULT §3.2 最終行）。

---

## 未解決・追跡事項

| # | 事項 | 担当 | ブロッカー |
|---|---|---|---|
| R-1 | `reads_as` の temporal_eval_required 判断 | DDLAWREF + LAWTIME | Q3 RESULT（file_id `2309304297318`） |
| R-2 | `dst_uri` URI 規約（statute-citation edge の dst が `alo:law:jp:…` work URI 体系か） | DDLAWREF | 同上 |
| R-3 | 本 registry の DDLAWREF 側 formal confirm | DDLAWREF | — |
| R-4 | admin_doc node の authority / binding_status 分離（§3.4）| DDLAWREF | — |
