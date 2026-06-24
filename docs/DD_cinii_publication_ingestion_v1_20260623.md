# DD: CiNii法律論文 → authority.publication 取込設計 v1 (2026-06-23)

- status: 設計のみ（read-only 調査に基づく）。**本番書込は HOLD**、dry-run→Owner ratify ゲート後に実投入。
- 親: `DD_author_model_resolution_v1` §8.4-8.5（繋ぎこみ最優先＝論文母数の投入）/ `KAKEN_lean_plan_v1` §4.1
- 目的: 実測ボトルネックを解消する。**人は厚い(authority.person 128,081, 研究者73,155にNRID)が、繋ぐ相手の `authority.publication` が7,348件しか無く CiNii法律論文63.8万が未投入**。これを載せ、NRIDで `publication_author_claim` を張って人↔論文を密結合にする。

---

## 1. 方針（既存実装の上に積む。新方式を作らない）

実DBは既に **claim+evidence 型**（`publication` → `publication_author_evidence` → `publication_author_claim`）。
CiNii取込も**同じ三段**に流し込む。新テーブルは識別子ハブ `authority.person_identifier`（DD §8.3）のみ。

```
CiNii detail JSON-LD (638,021件, cinii_batch/detail)
   │  Adapter/Parser (read-only, raw保持)
   ▼
authority.source_record   (1 CRID = 1 source_record, source_system='cinii_research')
   ▼
authority.publication     (CRIDで冪等。法律系ISSNでスコープ)
   ▼
authority.publication_author_evidence  (creator[] 1人=1 evidence, raw+normalized+payload_json)
   ▼  NRID/氏名突合
authority.publication_author_claim     (person_id を解決, trust_tier付与)
```

## 2. ソース構造（CiNii JSON-LD 実フィールド・偵察実測）

| CiNii フィールド | 中身 | 用途 |
|---|---|---|
| `@id`(CRID) | 全件必須・論文主キー | publication 冪等キー / source_identifier |
| `productIdentifier[]` | NAID / NDL_BIB_ID / HDL | 補助ID |
| `dc:title[]` | ja / en / ja-Kana | title / title_normalized |
| `creator[].@id` | 研究者CRID | evidence |
| `creator[].personIdentifier[]` | **NRID** / KAKEN_RESEARCHERS / CINII_AUTHOR_ID / RESEARCHMAP / ORCID | **人物突合キー** |
| `creator[].foaf:name` | 氏名(ja/en) | author_raw |
| `jpcoar:affiliationName` | 所属(あれば) | affiliation_raw |
| `publication.publicationIdentifier[]` | **ISSN/PISSN/LISSN** / NCID | 法律誌スコープ / container |
| `prism:publicationName` | 誌名 | container_title |
| `prism:volume/number/startingPage/pageRange` | 巻号頁 | volume / issue |
| `prism:publicationDate` | 発行日 | publication_year |
| `project[].projectIdentifier` | KAKEN番号(一部) | KAKEN結線の補助 |

## 3. ターゲットマッピング（CiNii → authority.*）

### 3.1 `authority.publication`
| 列 | 値 |
|---|---|
| publication_id | `cinii:{CRID}`（text。冪等キー） |
| publication_type | `journal_article`（resourceTypeで細分可） |
| title / title_normalized | dc:title(ja) / NFC正規化 |
| container_title | prism:publicationName |
| volume / issue | prism:volume / number |
| publication_year | prism:publicationDate の年 |
| publisher | dc:publisher |
| source_system | `cinii_research` |

### 3.2 `authority.source_record`（1 CRID = 1行）
source_system=`cinii_research` / source_identifier=CRID / record_kind=`article` / source_url / retrieved_at。raw payload は L0(`ext_cinii_*_raw`)に保持（編成指針 Raw First）。

### 3.3 `authority.publication_author_evidence`（creator 1人 = 1行）
publication_id / source_record_id / evidence_type=`cinii_creator` / author_raw(foaf:name) / author_normalized / affiliation_raw / role_raw / time_raw(発行年) / `evidence_payload_json`=creator全体(personIdentifier含む) / evidence_strength。

### 3.4 `authority.publication_author_claim`（人物解決後）
publication_id / person_id / primary_evidence_id / claim_status / confidence / decision_method / trust_tier（§4のはしご）。

## 4. 人物突合（CiNii著者 → authority.person）と trust_tier

**既存の接続点を使う**: `authority.person_history`(history_type=`scholar_nrid`) に研究者番号が入っている。
CiNii creator の NRID → person_history.scholar_nrid の**完全一致**で `person_id` が取れる。

**実DB確認済(2026-06-23)**:
- scholar_nrid は **13桁数値**（例 `1000000000034`、KAKEN由来の "1000+" 形）。history_value=history_normalized で前置なし → 突合は文字列完全一致でよい。
- **73,155行 = 73,155 distinct person = 73,155 distinct NRID の 1:1:1**（source=`cinii_identifier_traces`）。
  → **DB側にNRID多重(汚染)は無い**（既に解決済み）。汚染対策は *流入する CiNii creator 側*（1著者に複数NRID列挙）だけでよい（§6-2）。
- 将来は `authority.person_identifier` ハブに集約。

trust_tier のはしご（実装の high/medium/low に合わせる）:

| 条件 | decision_method | trust_tier | claim_status |
|---|---|---|---|
| NRID 完全一致（1著者=1 person に解決） | `nrid_exact` | high | accepted |
| NRID一致だが多重(汚染) → 代表ID選別後 | `nrid_resolved` | medium | needs_review |
| NRIDなし・氏名+収録誌(ISSN)一致 | `name_journal` | low | candidate |
| 氏名のみ（同名多発） | `name_only` | low | candidate（自動acceptしない）|

## 5. スコープと規模

- 対象: **法律系 ISSN（176誌のISSNセット）でフィルタ**した CiNii detail。全63.8万から法律誌分に限定。
- ISSN は同一性キーではなく誌レベル（fingerprints対象外/リンクレイヤ§4）。**publicationのcontainer記述＋スコープ用**に使う。
- 規模影響: publication 7,348 → 数十万規模に増。**段階投入**（誌単位バッチ）。

## 6. 冪等・dedup・落とし穴対策（偵察で実測した汚染を器側で防ぐ）

1. **CRID冪等**: publication_id=`cinii:{CRID}` で UPSERT。再実行で二重作成なし。
2. **NRID汚染**（1著者に10〜35 NRID）: evidenceには raw 全保持、claim 昇格時に**代表ID選別**（creator.@id 研究者CRID優先）＋ `resolution_log`。high tier は単一解決時のみ。
3. **著者ID欠落**（古い法律記事は creator無/氏名のみ）: evidence は作るが claim は low/candidate 止まり。canonical昇格しない。
4. **重複論文**（NAIDとCRIDの別レコード）: productIdentifier の NAID も source_record に記録し名寄せ。

## 7. 品質ゲート

| ゲート | 基準 |
|---|---|
| publication CRID 一意 | UNIQUE(publication_id) 物理保証 |
| evidence→claim 解決率 | NRID由来 claim の person_id 解決率を可視化 |
| 著者なし論文率 | < 10%（evidenceゼロのpublication） |
| trust_tier 分布 | high/medium/low を記録（暴走検知） |
| 同名only自動accept | 0件（name_only は candidate 固定） |
| ISSN→誌スコープ | 法律系ISSN外の混入 0 |

## 8. 実行手順（HOLD 規律）

1. **(read-only)** 法律系ISSNセット確定 → 対象CRID件数を計測。
2. **dry-run**: staging で publication/evidence/claim を生成、§7ゲートを実測（**本番書込なし**）。
3. dry-run レポート（解決率・tier分布・著者欠落率）を Owner レビュー。
4. **Owner ratify ＋ ロールバック手順** で本投入（誌単位バッチ、冪等）。
5. `authority.person_identifier` ハブ新設は並行（DD §8.5-2）。

**HOLD（ratifyまで）**: authority.* への本番INSERT / person canonical 昇格 / biblio.authors統合。

## 9. 確認結果と残課題（2026-06-23 実測）

確認済（設計確定）:
- ✅ **突合キー**: scholar_nrid=13桁数値・1:1:1・前置なし → CiNii NRID と文字列完全一致で `person_id` 解決。**73,155 研究者がhard-join可能**。
- ✅ **CiNii側のキー存在率**（task04 実測）: CRID 100% / ISSN(系) 100%(PISSN98/ISSN86/LISSN85/NCID99) / NRID は creator.personIdentifier に格納 → publication冪等・人物突合・誌スコープ いずれも成立。
- ✅ **法律誌ISSNマスタは存在**: `kaken_law_scholars/legal_journal_issn_filter.jsonl`(法律系 ~150誌) ＋ OPAC雑誌レジストリ 1,347誌。.jsonl は Box のテキスト抽出不可だが取込パイプラインが直接読む。

残課題:
- ⚠️ **dry-run対象件数の実測**: CiNii detail ~638,021件を法律ISSNで絞った件数は未計測（サンプルは紀要論文偏り）。フィルタ実走で確定（§8-1）。
- ⚠️ **KAKEN直結の歩留まり**: KAKEN参照は本文37%にあるが**構造化 project ID フィールドは無い**。eradCode直結は不可、NRID経由で接続。
- ⚠️ **eradCode は authority に未投入**（DD_author_model §8.3）→ person_identifier ハブ新設時に受け皿を用意。
