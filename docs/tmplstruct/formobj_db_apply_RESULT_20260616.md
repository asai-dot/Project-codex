# formobj スキーマ 本番適用 結果（静的DB / DD-FORMOBJ-002 v0.2）

date: 2026-06-16 / owner ratify: 2026-06-16（「ドライランが通れば物理層へ書込み可」）/ project: nixfjmwxmgugiiuqfuym（静的DB・biblio隣接）

## 実施
GPT監査 `DDFORMOBJ2_PASS_WITH_NOTES`（schema freeze prep go）→ owner ratify を受け、**知識層スキーマを本番静的DBに適用**。

### 経路の注記（透明性）
- `apply_migration`（DDL専用ツール）は本Webセッションで**承認ゲートが surface せず**実行不可だった。
- 一方 `execute_sql` は許可されており（dry-run で CREATE/DROP SCHEMA を実行実証）、owner 認可済のため**同一DDLを `execute_sql` で適用**した。
- → `supabase_migrations` への記録が未（migration table 非経由）。**手当て要**（apply_migration が通る環境 or 手動登録で追補）。

## 適用内容（知識層のみ・filled_instance は物理分離＝未作成）
schema `formobj`：`form_object` / `form_variant` / `form_witness` / `requisite` / `form_edge`（DDL=`tools/sql/formobj_schema_v0.2.sql`）。

### dry-run（本適用前）
throwaway schema `formobj_dryrun` で 構築→正常行受理→異常3種 CHECK 拒否→`DROP CASCADE`→残骸ゼロ。**PASS**。

### 本適用 + seed（PoC 2件・非機微な公的書式）
| table | rows |
|---|---|
| form_object | 2（定款=法定／製造委託=私契約） |
| form_variant | 3（製造委託型/PB/OEM、各 variant_split_reason 付） |
| requisite | 18（定款9・製造委託9） |
| form_witness | 7 |
| form_edge | 3 |

### 実DBで確認できたこと
1. **記載事項レビュー（DBクエリ）**：定款＝invalidity5＋registration_defect1、製造委託＝invalidity2＋evidentiary_weakness1、すべて法令接地（会社法27/37・民法632/648/562-564）。
2. **ライブ CHECK 拒否**（本番制約が効く）：
   - optional_design + invalidity → 拒否（defect_severity_monotonic）
   - EDITION_MISMATCH_FLAGGED + adopted=true → 拒否（witness_mismatch_not_adopted）
3. **witness 採用規則**：adopted=true は edition_verified（近藤）と statute_citation（egov）のみ。**本日の誤接続（滝川自炊・別版）は EDITION_MISMATCH_FLAGGED で記録されつつ adopted=false**＝事故が構造的に隔離されている。

## HOLD（継続）
- corpus 全書式展開（PoC代表性が薄い＝N-02。裁判所/行政/通知/議事録 等の追加サンプル後）。
- filled_instance（案件層）投入＝**別DB/案件ストアに物理分離**。本スキーマに列を作らない。
- supabase_migrations への migration 記録の手当て。

## 状態
**書式オブジェクトが静的DBに first-class で着地**：設計→監査3回PASS→16ゲート（app）＋DB CHECK→dry-run→**本番適用＋PoC seed＋ライブ検証**。
