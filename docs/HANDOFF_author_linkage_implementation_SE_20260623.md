# HANDOFF: 著者リンク実装（CiNii→authority.publication）SE向け v1 (2026-06-23)

- 宛先: 花岡さん(SE) / 浅井(Owner)
- 出し手: materials-organization-review セッション
- 種別: 設計→実装 ハンドオフ（**本番書込は Owner ratify ＋ dry-run 通過まで HOLD**）
- 根拠 DD（同 PR 内）:
  1. `DD_author_model_resolution_v1`（著者モデル裁定＋実DB照合）
  2. `DD_cinii_publication_ingestion_v1`（CiNii取込設計＋キー実証）
  3. `KAKEN_lean_plan_v1`（KAKEN取得を実装準拠に改訂）

---

## 1. なぜやるか（実測ボトルネック）

本番DB `asai-dot's Project`(nixfjmwxmgugiiuqfuym) は人物が厚い一方、繋ぐ相手の論文が薄い:

- `authority.person` **128,081**（研究者 73,155 に NRID）/ person_affiliation 230k / person_history 270k
- `authority.publication` **7,348のみ**（弁コム+NDL判事突合中心、**CiNii法律論文 63.8万は未投入**）
- `dynamic.cases` **0**

→ KAKEN/研究者が宙に浮いて見える原因は「論文側が無い」こと。**CiNii法律論文を publication に載せ、NRIDで人と繋ぐ**のが最優先。

## 2. 確定事項（read-only実測で確証済み）

- 突合キー: `authority.person_history(history_type='scholar_nrid')` は **13桁数値・73,155件・1:1:1**（多重/汚染なし）。CiNii NRID と**文字列完全一致**で `person_id` 解決可能。
- CiNii側: CRID 100% / ISSN系 100% / NRID は creator.personIdentifier に格納。
- 既存実装は **claim+evidence 型**（publication → publication_author_evidence → publication_author_claim, trust_tier付き）。**この上に積む**（新方式を作らない）。

## 3. SE に依頼する成果物

| # | 成果物 | 内容 | 参照 |
|---|---|---|---|
| S1 | `authority.person_identifier` 新設(DDL) | id_system(nrid/kaken_id/researchmap/orcid/ndl_auth) / id_value / person_id / source / confidence / active partial-unique。person_history散在分を移行 | author_model §8.3 |
| S2 | staging スキーマ（dry-run用） | `staging_cinii.*` に publication/evidence/claim を本番非破壊で生成 | cinii_ingestion §8 |
| S3 | CiNii取込パイプライン | Adapter/Parser/Merger。CRID冪等 UPSERT。raw は L0 保持 | cinii_ingestion §1,3 |
| S4 | 法律ISSNフィルタ | `legal_journal_issn_filter.jsonl`(~150誌) で 63.8万を絞る | cinii_ingestion §5 |
| S5 | NRID突合→claim生成 | trust_tierはしご（NRID完全一致=high/accepted … 氏名only=candidate） | cinii_ingestion §4 |

## 4. 確定パラメータ（実装値）

- publication_id = `cinii:{CRID}`（UPSERTキー）
- person 突合 = `cinii.NRID == person_history.history_value(13桁) → person_id`
- trust_tier: nrid_exact→high/accepted / nrid_resolved(代表ID選別後)→medium/needs_review / name_journal→low/candidate / name_only→low/candidate(自動accept禁止)
- source_system = `cinii_research`、source_record=1 CRID=1行
- 流入creator側のNRID多重のみ代表ID選別＋resolution_log（DB側は汚染なし）

## 5. ゲート & HOLD（順序固定）

1. (read-only) 法律ISSN絞り込み → **対象CRID件数を実測**（未測定の唯一の数字）
2. **dry-run**（staging、本番書込なし）→ §6 ゲート実測
3. dry-run レポート（解決率・tier分布・著者欠落率）を **Owner レビュー**
4. **Owner ratify ＋ ロールバック手順** → 誌単位バッチで本投入

**HOLD（ratifyまで）**: authority.* 本番INSERT / person canonical昇格 / biblio.authors統合 / eradCode投入。

## 6. 受入ゲート（合格基準）

| ゲート | 基準 |
|---|---|
| publication CRID 一意 | UNIQUE(publication_id) |
| NRID claim の person解決率 | 可視化（目標値は dry-run 後に Owner と確定）|
| 著者なし論文率 | < 10% |
| name_only 自動accept | 0件 |
| 法律ISSN外混入 | 0件 |
| trust_tier 分布 | high/medium/low を記録 |

## 7. 未測定（dry-runで判明する）

- 法律ISSN絞り後の対象論文件数（63.8万の部分集合）
- NRIDハードjoin歩留まり（対象論文の著者のうち 73,155 に当たる率）
- KAKEN直結率（CiNiiに構造化project IDなし＝NRID経由のみ）

## 8. dry-run の雛型

SQL/擬似コードのひな型は `cinii_publication_dryrun_templates_v1` を参照（本番非破壊・staging限定）。
