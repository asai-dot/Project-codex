# GPT監査TOP5の具体化 ― 既存データモデル v0.3 への適合と最小差分提案

- 作成日: 2026-06-06
- 位置づけ: GPT監査(CASELINK_PASS_WITH_NOTES)が挙げた「実装前に決めるべき設計判断TOP5」を、**本体の確定データモデル `case_data_model_v0.3`（MVP Core 11＋Support 1）に適合させた**もの。
- **重要**: TOP5の大半は **既存v0.3で既に充足**している。本書はゼロからのDDLではなく、**(1)どのテーブルで満たされるかの対応表 ＋ (2)足りない分の最小差分提案**。確定は本体owner（浅井先生／久保さん）。

> 過去に本リポジトリは本体を再発明する誤りを繰り返した（141件サンプル突合・a03誤推定）。本書はその轍を踏まないため、**既存v0.3を正本として参照し、差分のみ提案**する。

---

## 0. 結論（先に）

| GPT TOP5 | 既存v0.3で充足？ | 主担当テーブル/機構 | 残ギャップ（提案） |
|---|---|---|---|
| ①link decisionをappend-onlyに | ✅ ほぼ充足 | `audit_log`（append-only, UPDATE/DELETE禁止）＋`matter_relationship`（status=proposed/…＋判断履歴・撤回可）＋`reconciliation_issue` | 「rejected/superseded」状態と**再学習除外フラグ**を明示（§2-①） |
| ②sf_record_idのBox metadata付与の最小単位 | ✅ DB側は充足 | `external_link`（polymorphic: entity_kind/entity_id × external_system='box'） | DBでなく**Box側メタデータ運用**の話。案件フォルダ単位から開始（§2-②） |
| ③自動確定/レビュー/未分類の閾値 | △ 機構は充足、閾値は未定義 | `inference_log`(confidence)＋`matter_relationship.status='proposed'`＋`reconciliation_issue`＋`observed_matter_candidate` | **閾値ポリシーの設定値**を持つ（§2-③） |
| ④alias/旧姓/同姓異人のevidence schema | △ `party_alias`はPhase2予定だが詳細未定 | `party_alias`（Phase2）＋`inference_log`（根拠） | **party_aliasにalias_type/status/evidenceを定義**（§2-④, 本書の主提案） |
| ⑤誤紐付けの検出・取消・再学習除外 | ✅ ほぼ充足 | `audit_log`＋`reconciliation_issue`＋`matter_relationship`撤回＋`inference_log` | 「却下を教師から除外」を運用フローに明記（§2-①と同根） |

→ **新規テーブルはほぼ不要。** 主な追加は `party_alias` の列定義と、`inference_log`/`activity` への少量の列・enum値、閾値ポリシーの置き場。

---

## 1. 用語の整合（v0.3 P1棚卸しに合わせる・重要）

オブジェクト接頭辞の対応は **v0.3（2026-06-04 P1棚卸し）が最新の正本**。古い `SF紐付けルールv1.1`（2026-05-20）の推定とズレがあるので注意：

| 接頭辞 | SFオブジェクト | 役割 | 件数(P1) | 備考 |
|---|---|---|---:|---|
| `a0A` | **`leala__Business__c`** | **受任案件**(engagement) | 779 | ※`leala__Matter__c`は1件の遺物で設計対象外 |
| `a0D` | `leala__Consultation__c` | 相談 | 230 | |
| `a03` | **`leala__AdvisorConsultation__c`** | **顧問相談**（Pattern G＝顧問派生案件の格納先） | 26 | 旧推定「関連交渉」は誤り。単独の関連交渉オブジェクトは存在しない |
| `a04` | `leala__AdvisorContract__c` | 顧問契約 | 25 | engagement_contract(Phase2) |
| `001` | `Account` | 取引先(マスタ) | 29,245 | account マスタ(Phase2) |
| `a1s` | （研修・活動系） | 案件外 | — | 非案件 |

→ 本書の指摘を受け、`docs/01` のオブジェクト対応表もこの正本に合わせて訂正済み。

---

## 2. 残ギャップの最小差分提案（本体ownerが採否判断）

> 以下はすべて **提案（candidate）**。v0.3の命名規約（snake_case、append-only、partial unique index、`dynamic_alo` schema）に合わせている。本体のP2 DDLドラフトに織り込むかは本体判断。

### ① 誤紐付けの巻戻し＝既存機構で充足（新規テーブル不要）
GPTの「`link_decision_log`(append-only)」は、v0.3では次の組み合わせで実現済み：

- **紐付けの確定/却下/撤回** = `matter_relationship.relationship_status`（`proposed` / `confirmed` / 撤回）＋時間軸・判断履歴。
- **全状態変化の不可逆ログ** = `audit_log`（append-only、UPDATE/DELETE禁止のtrigger、`change_kind`）。
- **要レビュー** = `reconciliation_issue`（open/in_review）。

提案（最小追加）:
```text
-- matter_relationship.relationship_status の enum に rejected / superseded を保証
--   confirmed → superseded（別判断で置換）, proposed → rejected（誤り却下）
-- audit_log.change_kind に 'link_rejected' / 'link_superseded' を保証
-- 再学習除外: inference_log に outcome enum(accepted/rejected/superseded) を持つ。
-- CASELINKDM§高2: 運用規約だけだと漏れるので DB列で強制する。
--   ALTER TABLE dynamic_alo.inference_log
--     ADD COLUMN IF NOT EXISTS training_eligible boolean NOT NULL DEFAULT false;
--   初期は全件 false（人手で昇格）→ rejected/superseded は永久に false（教師から除外）。
```

### ② Box `sf_record_id` 付与＝`external_link` ＋ Box側メタデータ運用
- DB側: Box案件フォルダ↔matterの対応は **`external_link`**（`entity_kind='matter'`, `external_system='box'`, `external_id=<box_folder_id>`）で表現。新規テーブル不要。
- Box側: **案件フォルダ単位**で metadata template（`sf_record_id` / `object_api_name` / `matter_id`）を付与。**フォルダ名の一括改名は先にやらない**（GPT§中4）。
- 最小単位の推奨: **受任案件(Business)・相談(Consultation)の案件フォルダから開始**。ファイル単位は後段。

### ③ 閾値ポリシー（auto / review / unmatched）の置き場
v0.3に閾値の設定テーブルは無い（confidence列はある）。最小提案：
```sql
-- 提案: 紐付け自動化の閾値ポリシー（少数行の設定テーブル or アプリ設定）
CREATE TABLE dynamic_alo.link_policy (
    policy_id        smallint PRIMARY KEY DEFAULT 1,   -- policy_id=1 = global default（CASELINKDM§中3）
    policy_name      text NOT NULL DEFAULT 'global_default',
    scope_type       text,   -- 将来分岐の逃げ道: NULL=global / 'attorney' / 'case_field'(離婚/相続/倒産) 等
    scope_value      text,   -- scope_type に対応する値（NULL=global）
    auto_min_conf    numeric(4,3) NOT NULL DEFAULT 0.950,  -- これ以上で自動confirmed
    review_min_conf  numeric(4,3) NOT NULL DEFAULT 0.600,  -- これ以上は「これですか?」候補
    -- review_min 未満は unmatched（observed_matter_candidate / reconciliation_issue へ）
    updated_at       timestamptz NOT NULL DEFAULT now(),
    CHECK (auto_min_conf >= review_min_conf)
);
-- 初期MVPは global default 一行で開始。離婚/相続/倒産で望ましい precision/recall が違うため、
-- scope_type/scope_value で後から分岐できる設計にしておく（CASELINKDM§中3）。
-- 運用: inference_log.confidence と突き合わせ。閾値は後から調整可能なパラメータ（GPT§3-3）。
-- 初期は「高precisionのみ自動」= auto_min_conf を高めに設定（GPT TOP5#3 推奨）。
```

### ④ alias / 旧姓 / 同姓異人 の evidence schema（本書の主提案）
v0.3の `party_alias`（Phase2予定）を、GPT§高1（旧姓は候補特徴量・evidence保持）に応える形で定義：
```sql
-- 提案: party_alias（Phase2の詳細化）
CREATE TYPE dynamic_alo.alias_type AS ENUM (
    'maiden_name',        -- 旧姓（離婚で旧姓に復し旧姓で立件 等）
    'married_name',       -- 婚氏
    'former_company_name',-- 旧社名（例: 旧サーモネット）
    'group_name',         -- グループ/別名（例: HIRAKU）
    'trade_name',         -- 通称・屋号
    'kana', 'romaji',     -- 読み・英字表記
    'typo_variant',       -- 表記ゆれ（中黒・全半角等の機械正規化候補）
    'other'
);
CREATE TYPE dynamic_alo.alias_status AS ENUM ('candidate', 'confirmed', 'rejected');

CREATE TABLE dynamic_alo.party_alias (
    party_alias_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    party_id          uuid NOT NULL REFERENCES dynamic_alo.party(party_id),
    alias_value       text NOT NULL,                 -- 原表記（保持）
    alias_value_norm  text,                          -- 正規化（※候補生成用、確定キーにしない: GPT§中6。unique index は貼らない）
    alias_type        dynamic_alo.alias_type NOT NULL,
    status            dynamic_alo.alias_status NOT NULL DEFAULT 'candidate',  -- 自動確定しない: GPT§高1
    confidence        numeric(4,3),
    evidence          jsonb,   -- 根拠を必ず残す（下記スキーマ）
    evidence_strength text,    -- weak / moderate / strong（CASELINKDM§追加推奨）
    review_basis      jsonb,   -- confirmed の判断根拠（誰が何で確定したか）
    created_by        text, created_at  timestamptz NOT NULL DEFAULT now(),
    confirmed_by      text, confirmed_at timestamptz,
    -- CASELINKDM§高1: confirmed には人手根拠を強制（同姓異人の誤併合防止）
    CONSTRAINT ck_alias_confirmed_has_reviewer
      CHECK (status <> 'confirmed' OR confirmed_by IS NOT NULL)
);
-- alias_value_norm は検索候補用 index のみ（unique にしない: CASELINKDM§中5）
CREATE INDEX IF NOT EXISTS ix_party_alias_norm ON dynamic_alo.party_alias(alias_value_norm);
COMMENT ON TABLE dynamic_alo.party_alias IS
  '別名・旧姓・旧社名等。status=candidate を自動でconfirmedにしない（人レビュー or 背骨ID一致で確定）。
   alias_value_norm は候補検索用で確定キーにしない（別法人誤併合の防止 GPT§中6）。';
```
**evidence jsonb の推奨スキーマ**（旧姓・消去法など根拠を機械可読で保持）:
```jsonc
// 旧姓の例（木戸/浅山 相当の匿名化）
{ "basis": "divorce_filed_under_maiden_name",
  "counterparty_name": "<相手方>", "case_field": "離婚",
  "cooccurrence_window_days": 7, "source": ["sf_consultation", "box_folder"] }
```
**同姓異人の扱い（誤併合防止）**: 同姓でも別人は **別 party のまま保持**し、party_alias で併合しない。併合は evidence（住所/生年/事件番号/メール等の一致）が揃った時のみ `confirmed`。

### ⑤ 担当 prior（assignee_prior）と 利益相反の消去法
- 担当そのもの: `matter` の担当弁護士（lead attorney）として保持（確定値）。
- **推定シグナル（消去法・宛先実績等）は `inference_log` に記録**し、**単独で matter の担当を上書きしない**（GPT§高2）。
```jsonc
// inference_log.evidence 例（利益相反確認の消去法）
{ "signal": "conflict_check_elimination",
  "checked_attorneys": ["A","B"], "roster": ["A","B","C"],
  "inferred_assignee_candidate": "C", "corroboration": "box_folder_owner=C",
  "note": "assignee_prior only; not auto-confirm" }
```

### ⑥ 非案件の行き先（non_matter_type）
v0.3はmatter中心。非案件（matterに属さない activity）の行き先語彙を `activity` に持たせる最小案：
```sql
-- 提案: activity.matter_id IS NULL のときの非案件分類
CREATE TYPE dynamic_alo.non_matter_type AS ENUM (
  'sales','admin','conflict_check','vendor','hiring',
  'bar_association','system_notice','activity_training','advisory','unknown');
ALTER TABLE dynamic_alo.activity ADD COLUMN IF NOT EXISTS non_matter_type dynamic_alo.non_matter_type;
-- matter_id があるときは NULL。非案件確定時に分類を付け、未分類は 'unknown'。
-- CASELINKDM§中4: activityには「現在値」のみ。分類の根拠・変更履歴は inference_log / audit_log に残す
--   （非案件分類も推定で後から変わり得るため）。
```

---

## 3. 久保さんへの引き継ぎ（P2 DDLドラフトに織り込む候補）

| # | 差分 | 規模 | 依存 |
|---|---|---|---|
| ④ | `party_alias`（alias_type/status/evidence）の詳細化 | 中 | Phase2 マスタ強化 |
| ③ | `link_policy` 閾値テーブル | 小 | inference_log 運用前 |
| ⑥ | `activity.non_matter_type` 列＋enum | 小 | トリアージ運用前 |
| ① | `matter_relationship`/`audit_log`/`inference_log` の enum値（rejected/superseded/outcome）保証 | 小 | 既存定義の確認 |
| ②⑤ | external_link（Box）運用・inference_logのevidence規約 | 小（運用） | — |

→ いずれも **v0.3の非破壊拡張**。本体の P2「Supabase DDLドラフト → 既存14テーブル整合 → migration」に合流させるのが筋。

---

## 4. GPT再監査（CASELINKDM）反映ログ

- 監査: Box `from_gpt/20260607_caselink_CASELINKDM_RESULT.md` ／ 判定 **`CASELINKDM_PASS_WITH_NOTES`**（v0.3への非破壊差分として採用可・回帰なし）。
- 反映済み:
  - **§高1** party_alias の `confirmed` に人手根拠を強制（`CHECK (status<>'confirmed' OR confirmed_by IS NOT NULL)`）＋`evidence_strength`/`review_basis` 追加（同姓異人の誤併合防止）。
  - **§高2** 再学習除外を運用規約でなく**DB列**で強制（`inference_log.training_eligible boolean DEFAULT false`、初期全件false→人手昇格、rejected/superseded は永久false）。
  - **§中3** `link_policy` に `policy_name`/`scope_type`/`scope_value` を追加（初期はglobal default一行、離婚/相続/倒産での閾値分岐の逃げ道）。
  - **§中4** `non_matter_type` は activity に現在値、**分類根拠・変更履歴は inference_log/audit_log**。
  - **§中5** `alias_value_norm` は**unique にしない**（検索用 index のみ）。
- **migration の注意（CASELINKDM 非破壊性チェック）**: PostgreSQL の enum値追加は冪等化しづらい。`relationship_status`/`change_kind` への `rejected`/`superseded` 追加は **存在確認（`ADD VALUE IF NOT EXISTS`）または別 enum table 方式**で行う。

### 本体 P2 DDL への取り込み順（GPT推奨）
1. 既存enum保証: `relationship_status` / `audit_log.change_kind` / inference outcome。
2. `inference_log` 拡張: evidence規約・training_eligible・assignee_prior 扱い。
3. `party_alias` 新設: candidate既定・confirmed条件・検索index。
4. `link_policy` 新設: global default 一行。
5. `activity.non_matter_type` 追加。
6. gate追加: 「confirmed aliasに根拠あり／rejected・superseded は training除外／auto-confirm閾値違反0」を nightly check に。

> 本書は提案。確定は本体owner。実装は本体の `案件紐付け作業_20260520/` レーンで行うのが正本。
