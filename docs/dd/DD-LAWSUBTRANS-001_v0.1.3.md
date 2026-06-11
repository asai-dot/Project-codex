### DD-LAWSUBTRANS-001 v0.1.2: 法令改廃に伴う「実質的変更・解釈変遷」レイヤ（形式軸の上に乗る assertion overlay）

> **id**: `DD-LAWSUBTRANS-001` / **version**: v0.1.3 / **status**: accepted (design; owner ratified 2026-06-10。production DDL/DB write/MCP claim_support は HOLD)
> **supersedes_review**: v0.1.1（gate DDLAWSUBTRANS → `DDLAWSUBTRANS_PASS_WITH_NOTES` ×2,
> 2026-06-10。GPT Pro お目付け役＋GPT-5.5 Pro 再レビュー。v0.1 指摘4点すべて CLOSED、
> 即時 blocker なし。本 v0.1.2 は production 前 Note A–D を §10 に明文化したのみ＝設計不変）
> / v0.1（2026-06-08 PASS_WITH_NOTES, owner ratify可(design)）
> **gate**: `DDLAWSUBTRANS` / **owner**: 浅井 / **author**: Project-codex (claude-code remote)
> **recorded_at**: 2026-06-10
> **要旨**: DD-LAWTIME が解いた「法令の**形式的**時間軸（公布・施行・改正・廃止・版解決）」の上に、
> 「その改廃によって**実質的意味**がどう変わったか／旧法理は生き残るか」を扱う層を新設する。
> 本層は **事実テーブルではなく、出典付き・順位付きの主張(assertion)テーブル**であり、
> 「改正あり ⇒ 実質変更あり」という短絡を**物理制約で禁止**し、MCP 出口で**断言しない**。

- **depends_on**: `DD-LAWTIME-001 v0.2.1 design`（監査済 PASS_WITH_NOTES）＋ **resolved lawtime view まで**。
  **lawtime v0.2.2 は MODIFY_REQUIRED のため、その production 実装を前提にしない**（GPT指摘 2026-06-08）。
  / `30_law_layer`（alo_statutes, law_succession_map, temporal_resolver） / `35_link_layer`(alo_edges) /
  `31_case_layer` / `32_literature_layer` / `ALOデータ編成指針 v1.0`（L0–L3, resolution_log, raw-first）
- **不変の核（5つ）**:
  1. **形式と実質を分離する**。形式的改廃（lawtime）は実質変更の主張を**自動生成しない**。
  2. 実質的変化・解釈変遷は **assertion（主張）** として持つ。**出典・帰属・確度・反証**を必須化する。
  3. **真として自動確定しない**。`claim_support_eligible` は実質主張では既定 `false`。
  4. **alive/dead の二値ではなく多軸**で持つ（formal × substantive × applicability × temporal_reach）。
  5. **append-only**。再評価は破壊せず追記し、旧主張は `deprecated` に降格して保持する。

---

## §0. なぜ別 DD なのか（look-before-build：世界の収束解）

DD-LAWTIME は「いつ公布/施行され、どの改正法令で、どの時点でどの条文が有効か」までを解いた。
しかし「**その改正で“意味”が変わったのか／旧法理はなお妥当するのか**」は、法令時間軸の問題ではなく
**法解釈の変遷をどうデータ化するか**の問題である。両者を同一テーブルに押し込むと、

```
法令データ上は改正あり  →（短絡）→  だから実質変更あり
```

という法律家として危険な推論を機械が固定化する。先行事例調査（REFERENCE_law_substantive_transition_prior_art.md）の
結論は明確で、**「形式的改正の有無」と「実質的意味の変化」を構造的に分離し、後者を出典付き・順位付きの
主張として持ち、真として自動確定しない**——これが国際的な収束解である。

### 0.1 形式 vs 実質の分離は世界標準（典拠）

| 標準/実務 | 形式(textual/formal) | 実質(substantive/semantic) |
|---|---|---|
| **Akoma Ntoso / OASIS LegalDocML** | `textualMod`(substitution/insertion/repeal/renumber/split/join) | **`meaningMod`/`scopeMod`/`efficacyMod`/`forceMod`/`legalSystemMod`** |
| **ELI**(EU, v1.5＋ELI-I) | textual amendment / `eli:corrects`(法的変更なし) | non-textual / consequential change / `eli:amends`(実質) |
| **英 legislation.gov.uk** | Textual amendment(F-notes) | **Non-textual/Editorial effect**＝「テキストを変えず意味・範囲・適用を変える」(C-notes) |
| **米 US Code/OLRC** | textual amendment | Editorial Reclassification(テキスト不変) / positive vs prima facie |
| **Citator**(Shepard's/KeyCite/BCite) | — | **"superseded by statute" を overruled と別カテゴリに隔離** |

- **Palmirani の三分類**（改正は ①テキスト ②規範の射程(scope) ③力・効力・適用可能性の時間 のいずれかに作用）が共通の祖。
- 英国は国家データとして「**テキスト不変だが意味・範囲・適用が変わった**」を別カテゴリ（non-textual effect）で実際に保持している。本 DD の問題意識は空想でなく実在の設計要件である。

### 0.2 DD-LAWTIME 側に追記すべき境界宣言（本 DD と同時に効力発生）

> **DD-LAWTIME v0.2.1 は、法令の形式的時間軸・版解決・改廃イベントの基盤に限る。
> 改廃に伴う実質的変更、解釈変遷、立法担当者意図、旧法理の存続評価は、本 DD（DD-LAWSUBTRANS-001）
> に切り出す。後続 AI は lawtime を見て「法令の有効性も実質解釈も全部解ける」と誤読してはならない。**

---

## §1. レイヤ位置づけ（ALO データ編成指針との整合）

| ALO 層 | 本 DD の対象 |
|---|---|
| L0 Raw | 立案担当者解説/逐条解説/判例/論文/官報 の raw（既存 ext_* / bib 系を流用、本DDでは新設しない） |
| L1 Canonical(薄い) | 同一性ハブは lawtime（`alo_law_work` / `alo_statutes`）に既存。本DDは新 canonical を作らない |
| **L2 Curated Overlay** | **本 DD の中核**。`source_basis_json`/`confidence`/`generated_by` 思想の assertion 群 |
| L3 Derived | MCP 出口の提示生成（§5）。raw/curated から再生成可能 |

ALO データ編成指針の `resolution_log`（decision_type/basis/decision_confidence/decided_by）思想を、
本 DD では **append-only の review-event（T6）** として具体化する。

---

## §2. 統制語彙（各値に先行事例の典拠を付す）

### 2.1 `substantive_change_type`（条文×改正ペアの実質変化型）
`no_substantive_change`（文言整理のみ。AKN textual-only / `eli:corrects`）/
`wording_clarification`（明確化。立案担当者が「実質変更なし」と説明する典型）/
`scope_expansion` / `scope_reduction`（AKN `scopeMod`）/
`requirement_added` / `requirement_removed` / `requirement_changed` /
`effect_changed`（法的効果）/ `subject_changed`（主体・義務者）/ `procedure_changed` /
`efficacy_change`（停止・効力変動。AKN `efficacyMod` / Palmirani suspension）/
`substantive_change_unspecified` / `disputed` / `unknown`

### 2.2 `interpretation_transition_type`（解釈の変遷型）
`interpretation_continues`（旧法理が新法下でも妥当）/ `interpretation_discontinued`（維持不能）/
`interpretation_modified` / `interpretation_newly_established` / `interpretation_disputed` / `unknown`

### 2.3 旧法存続 = 三軸＋効果方向（二値では足りない）
- `formal_status`（**lawtime から継承するミラー値**。本DDは真の源でない）:
  `in_force / repealed / expired / superseded / not_yet_in_force / annulled`
- `substantive_status`: `continues / partially_continues / discontinued / transformed / disputed / unknown`
- `applicability_scope`（**多値**）: `pending_cases / past_events / existing_contracts /
  transitional_period / specific_industry / specific_procedure / none / unknown`
- `temporal_reach`: `ex_nunc`（将来効・過去効果存続＝abrogation）/ `ex_tunc`（遡及＝annulment）/ `unknown`
  （典拠: Governatori & Rotolo, *Logic J. IGPL* 18(1), 2010; Kelsen validity≠efficacy; Bulygin membership≠applicability）

### 2.4 `asserted_by_source_type` と `source_tier`（立法担当者意図は重いが絶対でない）
| source_type | tier | binding_weight | 備考 |
|---|---|---|---|
| `official_legal_data` | 1 | binding(formal) | 官報/改正法令/附則。**形式事実＝lawtime 側**。本DDでは参照のみ・再主張しない |
| `legislative_drafter` | 2 | strong_persuasive | 立案担当者解説・一問一答 |
| `ministry_commentary` | 2 | strong_persuasive | 所管庁逐条解説・通達 |
| `legislative_record` | 2 | strong_persuasive | 国会審議録 |
| `court` | 3 | strong_persuasive | 判例（適用場面での解釈結果） |
| `scholar` | 4 | persuasive | 学説・論文 |
| `treatise` | 4 | persuasive | 体系書・学者逐条解説 |
| `practitioner` | 4 | persuasive | 実務書 |
| `alo_internal` | 5 | observational | ALO 実務運用・内部メモ |

**重要**: tier は「**形式事実と評価を混ぜない**」ための仕切りであり、tier 2(立案担当者)を**最終真実視しない**。
tier 2 の「実質変更なし」主張に対し tier 3(判例)/tier 4(学説)が反対しうる（§2.5 dispute）。

### 2.5 `assertion_status`（Wikidata rank＋ワークフロー）と三概念の責務分離
`observed`（機械検知＝textual_delta 有等）/ `candidate`（抽出・提案）/ `reviewed`（人手確認）/
`accepted`（ALO として採用。ただし出典付き）/ `disputed`（競合主張あり）/ `deprecated`（より良い主張に降格・**削除しない**）

**責務分離（v0.1.1, GPT指摘2反映）** — 三つは独立した概念であり、相互に自動導出しない:
| 概念 | 意味 | 決め方 |
|---|---|---|
| `source_tier` | **証拠の強さ**（その出典が法解釈上どれだけ重いか） | 出典種別から機械付与 |
| `assertion_status` | **ALO 内の処分**（観測→候補→確認→採用→係争→降格） | T6 review-event のみで遷移 |
| `claim_support_eligible` | **出口利用可否**（MCP claim_support に出せるか） | §4 gate 条件から導出 |

したがって **高 tier 資料（立案担当者解説等）であることだけを理由に accepted にしない**。
`accepted` への遷移は tier を問わず **review_basis を持つ T6 review-event を必須**とする
（gate `accepted_requires_review_event`）。

### 2.6 `treatment_relation`（citator union：判例/学説が条文・法理を扱う関係）
positive: `followed/applied/approved/relied_upon`｜neutral: `cited/considered/explained`｜
caution: `distinguished/limited/questioned/criticized/called_into_doubt/declined_to_extend/followed_with_reservations/not_applied`｜
negative: `overruled/abrogated/disapproved`｜**statutory: `superseded_by_statute`（隔離。形式変更≠実質的死）**

---

## §3. スキーマ設計（append-only / assertion + evidence + provenance）

> URI/キー規約は lawtime に準拠: `law_id`=e-Gov 15桁, `law_revision_id`=e-Gov revision_id,
> `article_path`=egov URI tail（例 `art:709`, `art:415:para:2:item:1`）。
> これは lawtime P1 note（`fn_resolve_law_reference_at` が受ける `article_path_json` locator）との接続点。

### T1. `alo_law_textual_delta`（**観測・形式の基盤**。Phase 2。実質主張ではない）
```sql
CREATE TABLE alo_law_textual_delta (
  delta_id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  law_work_id          text NOT NULL REFERENCES alo_law_work(law_work_id),
  law_id               text NOT NULL,
  article_path         text NOT NULL,                 -- egov URI tail
  from_law_revision_id text NOT NULL,                 -- alo_statutes.law_revision_id
  to_law_revision_id   text NOT NULL,
  delta_kind           text NOT NULL,                 -- AKN textualMod 準拠
  text_changed         boolean NOT NULL,              -- false = 番号変更/移動のみ
  similarity           numeric,                       -- 0..1 正規化編集類似度（NULL可）
  diff_pointer         text,                          -- 差分 payload への pointer
  detector_version     text NOT NULL,
  source_snapshot_id   text NOT NULL,                 -- どの e-Gov 取込版で検出したか
  known_from           timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_delta_kind CHECK (delta_kind IN
    ('substitution','insertion','repeal','renumber','relocate','split','join','no_change','unknown'))
);
CREATE INDEX alo_delta_work_art_idx ON alo_law_textual_delta(law_work_id, article_path);
```
> **textual_delta は「テキストが変わった/変わらない」という形式観測にすぎない。実質変化を主張しない。**
> ここが実質軸への入口だが、§4 gate により自動昇格を禁止する。
> **ingest policy（v0.1.1 明文化）**: いかなる取込パイプラインも、textual_delta（または lawtime の
> 改正イベント）の存在のみを根拠に T2/T3/T4 行を自動生成してはならない。実質 assertion の生成には
> 実在の解釈源（§2.4 source_type）に基づく evidence pointer が必要。

### T2. `alo_law_substantive_change_assertion`（**中核**）
```sql
CREATE TABLE alo_law_substantive_change_assertion (
  assertion_id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  law_work_id          text NOT NULL REFERENCES alo_law_work(law_work_id),
  article_path         text NOT NULL,
  from_law_revision_id text,                          -- 全体改正等で NULL 可
  to_law_revision_id   text,
  related_delta_id     bigint REFERENCES alo_law_textual_delta(delta_id),  -- 形式基盤（任意）
  change_type          text NOT NULL,                 -- §2.1
  temporal_reach       text NOT NULL DEFAULT 'unknown',
  asserted_by_source_type text NOT NULL,              -- §2.4
  source_tier          smallint NOT NULL,             -- 1..5（source_type から導出・冗長保持）
  evidence_pointer_id  bigint REFERENCES alo_law_interpretive_evidence(evidence_pointer_id),
  confidence           text NOT NULL DEFAULT 'low',   -- low/medium/high（関連強度。真理確度ではない）
  rank                 text NOT NULL DEFAULT 'normal',-- preferred/normal/deprecated（Wikidata式）
  rank_reason          text,                          -- rank<>normal で必須（P2241/P7452 相当）
  counter_assertion_id bigint REFERENCES alo_law_substantive_change_assertion(assertion_id),
  valid_for_case_type  text,                          -- 適用場面の限定（任意）
  applies_from         date,
  applies_until        date,
  -- T2 は物理 assertion_status 列を持たない（設計意図, Note D）: 初期 status は
  -- view 上 'candidate' とみなし、現在 status は T6 review-event を畳んだ §3.7 view で解決する。
  -- claim_support_eligible は原則 view 導出（Note C）。物理列として保持する場合は
  -- §4 gate `claim_support_consistent_with_view` で view 導出値との drift を検査する。
  claim_support_eligible boolean NOT NULL DEFAULT false,  -- 実質主張は既定 false（原則 view 導出）
  asserted_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_subchg_type CHECK (change_type IN
    ('no_substantive_change','wording_clarification','scope_expansion','scope_reduction',
     'requirement_added','requirement_removed','requirement_changed','effect_changed',
     'subject_changed','procedure_changed','efficacy_change','substantive_change_unspecified',
     'disputed','unknown')),
  CONSTRAINT ck_subchg_reach  CHECK (temporal_reach IN ('ex_nunc','ex_tunc','unknown')),
  CONSTRAINT ck_subchg_src    CHECK (asserted_by_source_type IN
    ('official_legal_data','legislative_drafter','ministry_commentary','legislative_record',
     'court','scholar','treatise','practitioner','alo_internal')),
  CONSTRAINT ck_subchg_tier   CHECK (source_tier BETWEEN 1 AND 5),
  CONSTRAINT ck_subchg_conf   CHECK (confidence IN ('low','medium','high')),
  CONSTRAINT ck_subchg_rank   CHECK (rank IN ('preferred','normal','deprecated')),
  CONSTRAINT ck_subchg_rankrsn CHECK (rank = 'normal' OR rank_reason IS NOT NULL),
  -- 安全弁: claim_support は accepted・証拠あり・反証なし のときだけ（§4 で view/gate にも二重化）
  CONSTRAINT ck_subchg_claim  CHECK (
    claim_support_eligible = false
    OR (evidence_pointer_id IS NOT NULL AND counter_assertion_id IS NULL))
);
CREATE INDEX alo_subchg_work_art_idx ON alo_law_substantive_change_assertion(law_work_id, article_path);
```

### T3. `alo_law_interpretation_transition`（解釈変遷を第一級に）
```sql
CREATE TABLE alo_law_interpretation_transition (
  transition_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  law_work_id          text NOT NULL REFERENCES alo_law_work(law_work_id),
  article_path         text,
  doctrine_label       text,                          -- 法理/解釈命題の短ラベル
  transition_type      text NOT NULL,                 -- §2.2
  before_revision_id   text,
  after_revision_id    text,
  interpretive_basis   text,                          -- 解釈規準/canon（Sartor 論証スキーム名を任意で）
  treatment_relation   text,                          -- §2.6（判例/学説由来のとき）
  asserted_by_source_type text NOT NULL,
  source_tier          smallint NOT NULL,
  evidence_pointer_id  bigint REFERENCES alo_law_interpretive_evidence(evidence_pointer_id),
  assertion_status     text NOT NULL DEFAULT 'candidate',
  confidence           text NOT NULL DEFAULT 'low',
  counter_transition_id bigint REFERENCES alo_law_interpretation_transition(transition_id),
  claim_support_eligible boolean NOT NULL DEFAULT false,
  asserted_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_inttr_type CHECK (transition_type IN
    ('interpretation_continues','interpretation_discontinued','interpretation_modified',
     'interpretation_newly_established','interpretation_disputed','unknown')),
  CONSTRAINT ck_inttr_treatment CHECK (treatment_relation IS NULL OR treatment_relation IN
    ('followed','applied','approved','relied_upon','cited','considered','explained',
     'distinguished','limited','questioned','criticized','called_into_doubt','declined_to_extend',
     'followed_with_reservations','not_applied','overruled','abrogated','disapproved','superseded_by_statute')),
  CONSTRAINT ck_inttr_src  CHECK (asserted_by_source_type IN
    ('official_legal_data','legislative_drafter','ministry_commentary','legislative_record',
     'court','scholar','treatise','practitioner','alo_internal')),
  CONSTRAINT ck_inttr_tier CHECK (source_tier BETWEEN 1 AND 5),
  CONSTRAINT ck_inttr_conf CHECK (confidence IN ('low','medium','high')),
  CONSTRAINT ck_inttr_claim CHECK (
    claim_support_eligible = false
    OR (evidence_pointer_id IS NOT NULL AND counter_transition_id IS NULL))
);
```

### T4. `alo_old_law_survival_assertion`（三軸）
```sql
CREATE TABLE alo_old_law_survival_assertion (
  survival_id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  law_work_id          text NOT NULL REFERENCES alo_law_work(law_work_id),
  article_path         text,
  superseding_revision_id text,                       -- 形式的に廃止/置換した版
  -- v0.1.1: formal_status は原則 lawtime resolved view から都度算出する。
  -- 永続ミラー列として持つ場合は drift/consistency gate（§4）が必須。
  formal_status        text NOT NULL,                 -- lawtime ミラー（gate 必須）
  substantive_status   text NOT NULL,
  applicability_scope  text[] NOT NULL DEFAULT '{}',  -- 多値
  temporal_reach       text NOT NULL DEFAULT 'unknown',
  basis_kind           text,                          -- savings_clause/transitional_provision/case_doctrine/practice
  asserted_by_source_type text NOT NULL,
  source_tier          smallint NOT NULL,
  evidence_pointer_id  bigint REFERENCES alo_law_interpretive_evidence(evidence_pointer_id),
  assertion_status     text NOT NULL DEFAULT 'candidate',
  confidence           text NOT NULL DEFAULT 'low',
  counter_survival_id  bigint REFERENCES alo_old_law_survival_assertion(survival_id),
  claim_support_eligible boolean NOT NULL DEFAULT false,
  asserted_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_surv_formal CHECK (formal_status IN
    ('in_force','repealed','expired','superseded','not_yet_in_force','annulled')),
  CONSTRAINT ck_surv_subst  CHECK (substantive_status IN
    ('continues','partially_continues','discontinued','transformed','disputed','unknown')),
  CONSTRAINT ck_surv_reach  CHECK (temporal_reach IN ('ex_nunc','ex_tunc','unknown')),
  CONSTRAINT ck_surv_scope  CHECK (applicability_scope <@ ARRAY[
    'pending_cases','past_events','existing_contracts','transitional_period',
    'specific_industry','specific_procedure','none','unknown']::text[]),
  CONSTRAINT ck_surv_src   CHECK (asserted_by_source_type IN
    ('official_legal_data','legislative_drafter','ministry_commentary','legislative_record',
     'court','scholar','treatise','practitioner','alo_internal')),
  CONSTRAINT ck_surv_tier  CHECK (source_tier BETWEEN 1 AND 5),
  CONSTRAINT ck_surv_conf  CHECK (confidence IN ('low','medium','high')),
  CONSTRAINT ck_surv_claim CHECK (
    claim_support_eligible = false
    OR (evidence_pointer_id IS NOT NULL AND counter_survival_id IS NULL))
);
```

### T5. `alo_law_interpretive_evidence`（証拠ポインタ。TOCLEGALREF 再現性パターン再利用）
```sql
CREATE TABLE alo_law_interpretive_evidence (
  evidence_pointer_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_type          text NOT NULL,                 -- §2.4 と同値域
  source_tier          smallint NOT NULL,             -- v0.1.1: 証拠側にも tier を冗長保持
  -- Note A: 列は nullable のまま（candidate evidence では未確定があり得る）。
  -- 完全性は DDL CHECK でなく gate `evidence_locator_complete` で、reviewed/accepted/
  -- claim_support 対象の evidence に限定して NOT NULL 検査する（一律 NOT NULL にしない）。
  source_uri           text,                          -- canonical or provisional pointer
  source_record_key    text,                          -- bib_id / 事件番号 / 解説ID 等
  locator              text,                          -- 頁/条/項（reviewed/accepted で gate 必須）
  source_span_hash     text,                          -- 引用スパンの sha1（再現性）
  quoted_text          text,                          -- 抜粋（citator 流儀: 出典が何と言ったかを示す）
  parser_version       text,
  retrieved_at         timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_ev_tier CHECK (source_tier BETWEEN 1 AND 5),
  CONSTRAINT ck_ev_src CHECK (source_type IN
    ('official_legal_data','legislative_drafter','ministry_commentary','legislative_record',
     'court','scholar','treatise','practitioner','alo_internal'))
);
```

### T6. `alo_law_assertion_review_event`（append-only ライフサイクル＝編成指針 resolution_log の具体化）
```sql
CREATE TABLE alo_law_assertion_review_event (
  review_id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  assertion_kind       text NOT NULL,                 -- substantive_change/interpretation_transition/old_law_survival
  assertion_id         bigint NOT NULL,
  new_status           text NOT NULL,                 -- §2.5
  new_rank             text,                          -- preferred/normal/deprecated
  review_basis         text NOT NULL,                 -- 判断根拠（accepted 化に必須。Wikidata P2241/P7452 相当）
  decided_by           text NOT NULL,                 -- extractor/curator/gpt_ometsuke/owner
  decided_at           timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_rev_kind   CHECK (assertion_kind IN
    ('substantive_change','interpretation_transition','old_law_survival')),
  CONSTRAINT ck_rev_status CHECK (new_status IN
    ('observed','candidate','reviewed','accepted','disputed','deprecated')),
  CONSTRAINT ck_rev_rank   CHECK (new_rank IS NULL OR new_rank IN ('preferred','normal','deprecated'))
);
```

### append-only 強制（T1, T2, T3, T4, T6 の content 列は不変）
```sql
CREATE FUNCTION trg_subtrans_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION '% is append-only (content immutable); record lifecycle via alo_law_assertion_review_event', TG_TABLE_NAME; END; $$;
-- 各テーブルに BEFORE UPDATE OR DELETE トリガを張る。
-- status/rank の変更は T6 への INSERT で表現し、現在値は §3.7 view で解決する。
```
> **設計判断（GPT お目付け役向け論点）**: lawtime の eval_event と同じ append-only 思想を踏襲しつつ、
> Wikidata 式の「誤主張も削除せず deprecated 保持」を両立させるため、主張の**内容は不変**、
> **ライフサイクル(status/rank)は append-only の review-event** で表す event-sourced 構成にした。
> 現在 status/rank は最新 review-event を畳んだ view（下記）で解決する。

### 3.7 現在状態 view（claim_support 判定の単一窓口）
```sql
CREATE VIEW v_subchg_current AS
SELECT a.*,
       COALESCE(r.new_status, 'candidate') AS current_status,
       COALESCE(r.new_rank,  a.rank)       AS current_rank
FROM alo_law_substantive_change_assertion a
LEFT JOIN LATERAL (
  SELECT new_status, new_rank FROM alo_law_assertion_review_event e
  WHERE e.assertion_kind='substantive_change' AND e.assertion_id=a.assertion_id
  ORDER BY e.decided_at DESC LIMIT 1
) r ON true;
-- interpretation_transition / old_law_survival も同型 view を持つ。
-- v0.1.3（監査note）: T3/T4 は物理 assertion_status 列も持つが、**current_status の正本は本 view
-- （= 物理 status を起点に最新 review-event を畳んだ値）**とする。物理 status と review-event が
-- 食い違う場合は review-event が優先。T2 は物理 status を持たず 'candidate' 起点で同一規則に従う。
```

---

## §4. 品質ゲート（§8 の落とし穴を物理/検査で封じる。lawtime D6 様式）

| gate | 検証 | 合格 |
|---|---|---|
| `amendment_not_auto_substantive` | textual_delta のみを根拠に substantive_change が candidate 超の status を持たない（asserted_by_source_type が delta 検出器でなく実在の解釈源） | 0件 |
| `substantive_requires_evidence` | current_status ∈ (reviewed,accepted) ⇒ evidence_pointer_id NOT NULL | 0件 |
| `disputed_blocks_claim` | counter_*_id NOT NULL ⇒ claim_support_eligible=false かつ current_status='disputed' | 0件 |
| `claim_support_requires_accepted` | claim_support_eligible=true ⇒ current_status='accepted' ∧ disputed=false ∧ **evidence_count>=1** ∧ **未解決 counter なし** ∧ **lawtime_resolved=true**（from/to/superseding revision が lawtime で解決）。**Note B**: 当面は単一 `evidence_pointer_id IS NOT NULL` を evidence_count=1 とみなす。multi-evidence を許す場合は join table（`alo_law_assertion_evidence`）を新設し本 gate を count 化する。 | 0件 |
| `claim_support_consistent_with_view` | **Note C**: `claim_support_eligible` を物理列として保持する場合、その値は §3.7 view が §4 条件から導出する値と一致する（保持しない＝view 導出のみなら本 gate は不要）。**T2/T3/T4 全系統に適用**（v0.1.3 監査note 反映） | 0件 |
| `accepted_requires_review_event` | current_status='accepted' ⇒ 当該 assertion に review_basis 非空の T6 review-event が存在（**tier の高さだけで accepted 化しない**） | 0件 |
| `evidence_locator_complete` | **reviewed/accepted/claim_support 対象**の根拠 evidence は source_uri・source_type・source_tier・locator・source_span_hash・retrieved_at・parser_version を備える（**Note A**: DDL の一律 NOT NULL ではなく、本 gate SQL で対象を限定して検査。candidate evidence には適用しない） | 0件 |
| `drafter_intent_not_sole_truth` | tier2(立案担当者) 単独の「no_substantive_change/continues」に tier3(court) の反対主張があれば accepted 不可（disputed 強制） | 0件 |
| `old_law_survival_three_axis` | survival 行は formal_status・substantive_status・非空 applicability_scope を必ず持つ | 強制 |
| `formal_status_consistent_with_lawtime` | survival.formal_status は lawtime resolved view の算出値と一致（**永続ミラーである以上 drift gate 必須**。原則は view からの都度算出） | 0件 |
| `no_substantive_without_resolved_lawtime` | from/to/superseding revision が lawtime（alo_statutes/succession）で解決可能 | 0件 |
| `assertion_append_only_enforced` | T1–T4,T6 content 列の UPDATE/DELETE が拒否される | 強制 |
| `rank_reason_present` | rank<>'normal' は rank_reason 必須（Wikidata P2241/P7452） | 強制 |

---

## §5. MCP 出口契約（断言しない・出典付き候補・conflict 提示）

実証根拠: Stanford RegLab — 汎用 LLM の法令幻覚 69–88%、RAG 付き商用ツールでも 1/6〜1/3 が幻覚。
→ **単一の答えを断言せず、出典付き候補を順位・反証ごと提示し、人間検証を必須**にする。

```
NG: 「旧法理は現在も有効です。」
OK: 「形式的には〇年改正で当該条文が変更されています（lawtime: superseded）。
     ただし立案担当者解説 A は『実質変更なし』と説明（tier2, evidence ptr）。
     一方、文献 B はこの改正を要件変更と評価（tier4, evidence ptr）。
     裁判例 C は旧法下の判断枠組みを改正後にも参照（tier3, treatment=followed）。
     したがって実質的存続は reviewed candidate として扱うべきで、断定はできません。」
```

出力規則:
1. **形式事実（lawtime）は機械提示してよい**（「当時有効」「〇年改正で superseded」まで）。
2. **実質（本DD）は `claim_support_eligible=true`（accepted・証拠・反証なし）でも“候補”として提示**し、
   tier・evidence・counter を併記する。`disputed` は必ず両論併記。
3. 出力に出すのは `v_*_current` 経由。`deprecated` rank は既定で非表示（監査時のみ）。
4. **`unknown` を出口根拠に使わない**（v0.1.1, GPT指摘3）: substantive_status / temporal_reach /
   applicability_scope 等が `unknown` の行は、候補提示の**根拠**として用いず、提示する場合も
   「未確認」である旨を明示する。

---

## §6. 実装フェーズ（焦らず段階的に）

| Phase | 内容 | 成果物 |
|---|---|---|
| **1（済）** | 形式的時間軸 | DD-LAWTIME v0.2.1 |
| **2** | 条文テキスト差分（条・項・号の文言差分） | T1 `alo_law_textual_delta`（具体DDL・本DD） |
| **3** | 立法資料・逐条解説・所管庁資料の接続 | drafter_intent assertion（T2 を tier2 源で投入） |
| **4** | 判例・文献による実質変更/解釈評価 | T2/T3/T4 を tier3-4 源で投入、counter/dispute 形成 |
| **5** | MCP 出口での安全利用 | §5 出力契約・`v_*_current`・断言禁止 |

> Phase 2 は lawtime が「未着手」として持っていた P2（条文レベル差分）/`alo_amendment_effects` 構想を本DDが正式に引き取るもの。
> Phase 3-4 のスキーマ(T2/T3/T4)は本DDで candidate 設計まで提示し、production DDL は §7 の通り別ゲート。

---

## §7. accept 条件（lawtime と同方針：design accept と production を分離）

- **design accept**: GPT お目付け役 `DDLAWSUBTRANS_PASS / PASS_WITH_NOTES` 以上 ＋ owner ratify。
- **production DDL は HOLD**: §4 全 gate が branch dry-run で実行可能・全 PASS になるまで物理化しない。
- **依存**: DD-LAWTIME v0.2.1 の owner ratify 完了（formal_status ミラー・lawtime 整合 gate の前提）。
- **境界宣言（§0.2）を lawtime ratify メモにも同時反映**すること。

## §8. 監査観点（GPT お目付け役向け）
1. 形式的改廃と実質的変更を**分離**できているか（gate `amendment_not_auto_substantive`）。
2. 立法担当者意図を**重く扱うが絶対視していない**か（tier ＋ counter ＋ `drafter_intent_not_sole_truth`）。
3. 旧法の**形式的失効と実質的存続を分けて**いるか（T4 三軸 ＋ `formal_status_consistent_with_lawtime`）。
4. 判例・文献・行政解釈・逐条解説を **assertion** として持てるか（T2/T3/T5 ＋ tier）。
5. MCP 出口で**断言せず**根拠付き候補として提示できるか（§5）。
6. `claim_support` に使う条件を**安全側**に倒しているか（既定 false ＋ `claim_support_requires_accepted`）。
7. append-only と Wikidata 式 deprecated 保持の**両立**設計（T6 event-sourced）は妥当か。

## §10. production 前条件（v0.1.1 監査 Note A–D。設計不変・実装時に閉じる）

v0.1.1 は GPT Pro お目付け役＋GPT-5.5 Pro 再レビューで `DDLAWSUBTRANS_PASS_WITH_NOTES`（×2,
2026-06-10）。v0.1 指摘4点は **CLOSED**、即時 blocker なし。以下は **production DDL 化の前**に
閉じる条件であり、design は変えない。

| Note | 内容 | 閉じ方（production 時） |
|---|---|---|
| **A** evidence locator gate の SQL 化 | T5 の locator 系列は nullable のまま。一律 NOT NULL にしない | gate `evidence_locator_complete` を、reviewed/accepted/claim_support 対象 evidence に限定した SQL で実装 |
| **B** `evidence_count>=1` の算出 | 当面は単一 `evidence_pointer_id IS NOT NULL`=count1 | multi-evidence を許す時のみ join table `alo_law_assertion_evidence` を新設し gate を count 化 |
| **C** `claim_support_eligible` の drift | 物理列は view 値と乖離しうる | 原則 §3.7 view 導出。物理列を残すなら gate `claim_support_consistent_with_view` を追加 |
| **D** T2 の status 解決 | T2 は物理 `assertion_status` 列を持たず、現在値は T6 review-event を畳んだ view 解決 | 設計意図として明文化済（T2 コメント／本表）。初期 status は view 上 `candidate` |

その他 production 前必須（§7 と重複）: §4 gates の実 SQL 化、lawtime resolved view の実体接続、
DD-LAWTIME v0.2.x の production 確定（v0.2.2 は MODIFY_REQUIRED のため依存は v0.2.1 design に限定）。

### §10.1 production フェーズ宿題（v0.1.2 監査 P0/P1。設計不変・実装で閉じる）
1. §4 gates を実 SQL / 独立 validator として実行可能化。
2. `claim_support_consistent_with_view` を **T2/T3/T4 全系統**に適用。
3. T3/T4 の物理 `assertion_status` と T6 review-event の優先関係を **current view で正本固定**（§3.7 反映済）。
4. `evidence_locator_complete` は reviewed/accepted/claim_support 対象限定で実行。
5. MCP 出口の「`unknown` を根拠にしない」を snapshot test 化。
6. producer が `accepted` / `claim_support_eligible=true` を出さないことを CI gate に残す。

## §9. changelog
- v0.1.3 (2026-06-11): v0.1.2 確認監査 `DDLAWSUBTRANS_PASS_WITH_NOTES`（design 不変・producer 全段
  整合・即時 blocker なし）の note 2点を明文化。①`claim_support_consistent_with_view` を T2/T3/T4
  全系統適用と明記。②T3/T4 の物理 status と T6 review-event の優先関係を §3.7 view で正本固定。
  §10.1 に production P0/P1 を追記。**設計不変**。
- v0.1.2 (2026-06-10): v0.1.1 監査（PASS_WITH_NOTES ×2）の production 前 Note A–D を §10 に明文化
  し、T2 コメント・gate 表に反映（evidence_locator_complete を対象限定 SQL gate に、
  新 gate `claim_support_consistent_with_view`、evidence_count 算出注記、T2 status は view 解決の旨）。
  **設計は不変**（即時 blocker なしのため）。
- v0.1.1 (2026-06-10): GPT お目付け役 `DDLAWSUBTRANS_PASS_WITH_NOTES`（2026-06-08）の指摘4点を反映。
  ①lawtime 依存を「v0.2.1 design＋resolved lawtime view まで」に再定義（v0.2.2 MODIFY_REQUIRED を
  前提にしない）、formal_status ミラーの drift gate 必須化。②source_tier（証拠の強さ）/
  assertion_status（ALO内処分）/claim_support_eligible（出口利用可否）の責務分離を明文化、
  高 tier 単独での accepted 化禁止（gate `accepted_requires_review_event`、T6 `review_basis` 必須）。
  ③evidence locator 充実（source_tier 列追加、gate `evidence_locator_complete`）。
  ④claim_support gate 強化（accepted ∧ disputed=false ∧ evidence_count>=1 ∧ 未解決 counter なし
  ∧ lawtime_resolved=true）、`unknown` の出口根拠使用禁止、ingest 自動生成禁止の明文化。
- v0.1 (2026-06-08): 初版。先行事例調査（REFERENCE_law_substantive_transition_prior_art.md）に基づき、
  形式/実質分離原則・統制語彙・T1–T6 スキーマ・10 gate・MCP 出口契約・Phase 2-5 ロードマップを提示。
  DB 書込みゼロ（design accept ＋ 層実装後）。
