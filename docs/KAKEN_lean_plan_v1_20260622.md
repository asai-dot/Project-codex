# KAKEN 取得・統合 実行版プラン v1 (2026-06-22)

> 目的: 6/15〜6/17 に v0.1→v0.3.7 と 9 版に分裂した KAKEN 計画を **1 枚に畳み**、
> 観測された非効率（後追い計測・全件ブルートフォース・二重取得）を断ち、
> **seed 逆引き** と **担当分担** を正本化する。
> このファイルが以後の KAKEN レーンの現行プラン (current)。旧 v0.x は superseded 扱い。

- author: materials-organization-review session
- status: proposal (Owner ratify 待ち)
- supersedes: KAKEN_author_object_acquisition_plan v0.1〜v0.3.7（status_to_codex 各版含む）
- 不変ルール: 取得は read-only / 本番 DB 書込・人物 canonical 化・gold マージは別ゲート

---

## 0. なぜ畳むか（観測された非効率）

| # | 観測された無駄 | 証拠 | 対処 |
|---|---|---|---|
| 1 | 計測を後回しにし規模が 43x ズレ | 想定 26,000 → 実測 **1,116,502 URL**。`MEMBER id` を研究者番号と誤認（実は `eradCode`） | §1 で「偵察を先に」固定 |
| 2 | 計画書を 2〜3 日で 9 版作り直し | v0.1〜v0.3.7 が各々 REQUEST→監査→RESULT→status を生成 | 本ファイルに一本化。版は実質変化時のみ |
| 3 | 二重取得リスク放置 | 監査が繰返し「Codex と重複 fetch を確認/停止せよ」 | §3 fetch ownership matrix |
| 4 | デフォルトが全件ブルートフォース | 旧採番 94 万件・7 日クロール想定、法ヒット率 **1〜2%**（99% 廃棄前提） | §2 seed 逆引きへ一本化、全件クロール廃止 |

> 正当な慎重さ（DB 書込 / canonical / gold マージの HOLD）は維持する。問題は「慎重にする前段の段取り」だった。

---

## 1. 偵察ファースト（着手前の安価な確定作業）

全件取得や計画版を増やす前に、**数分で終わる読取り**で母数とスキーマを確定する。

- [ ] ResourceSync `capabilitylist` / `resourcelist`（23 本）の **hash・件数** を記録
- [ ] スキーマ 2 系統を確定: 新採番 `<review_section>`（小区分） / 旧採番 `<field>` 階層
- [ ] 研究者番号の抽出経路を固定: `eradCode` 属性・`<researcherNumber type='erad'>`（`MEMBER-xxxx` は使わない）
- [ ] 採番比率の確認: 新 ~15% / 旧 ~85%（≈937k）

成果物: `kaken_resourcesync_inventory_v1.json`（hash・件数・スキーマ・採番比率・取得日・fetcher 版）

---

## 2. 取得戦略 — 全件クロール廃止、seed 逆引きに一本化

法ヒット率 1〜2% の母集団を全件クロールしない。**既知の人を起点に逆引き**する。

### 2.1 seed（既知の法学者）の集約
- PACSigny KAKEN 868 ブリッジ（`eradCode`）
- `books.json` 著者文字列 → 氏名候補
- researchmap 既収集（2,003 packs / 約 100 名、recovery 完了 92 名）
- NRID 名鑑（取得済 208MB, 3/3）/ CiNii NRID 抽出（済 3/31）

成果物: `kaken_seed_persons_v1.jsonl`（eradCode / 氏名・yomi / 所属 / 活動年）

### 2.2 取得レーン（優先度順）
1. **modern 法分野スライス（新採番）** — 継続中。境界明確・実測済み。`law_modern_2026` レーン。
2. **旧採番 = seed 逆引きのみ** — seed に該当する旧 project だけ取得。**全件 937k クロールはしない。**
   - 着手前に**サンプルで `<field>` 法判定の precision/recall を計測** → 妥当なら逆引き本実行。
3. **PUBLICLY (14,137)** — まず小サンプルでスキーマ互換を確認。PROJECT 互換なら同抽出器を再利用、非互換なら別レーン。**全件 fetch は互換確認まで HOLD。**

### 2.3 レート規律（`fetch_policy_manifest` に明記）
- KAKEN: 同時実行 **4 上限**（concurrency 6 で 503 多発・効率崩壊を観測）。jitter・retry/backoff・stop 条件を明記。
- NRID/researchmap: 8-way は許容範囲だが失敗ログ + backoff 必須。
- 記録: host / concurrency / interval / UA / 503 観測数 / last reviewed。

---

## 3. fetch ownership matrix（二重取得の停止）

**広域 fetch を続ける前に、まずこの表を埋めて重複を消す。** 既に Codex が取得済みのセットは Claude 側は停止し、reconciliation に切替える。

| 対象セット | 担当 | 状態 | 備考 |
|---|---|---|---|
| modern PROJECT 法分野 XML | Claude | running | 重複なら停止→照合 |
| 旧採番 PROJECT（seed 逆引き） | TBD | not started | §2.2-2、サンプル検証後 |
| PUBLICLY (14,137) | TBD | not started | スキーマ確認のみ先行 |
| PLANNED/ORGANIZER/AREA/WRAPUP/INTERNATIONAL | — | out of scope | 当面除外 |
| researchmap / NRID overlap | Claude | running | raw cache 3,435 取得済 |
| 全体 inventory / 旧採番ターゲティング戦略 | Codex | TBD | §1 偵察と統合 |

> F 系（海外フェロー）は `scope_tag=foreign_fellowship_orphan` / `integration_priority=low` で隔離。
> 「日本人 member なし 92%」の隣接キーワード行を統合メトリクスの分母に混ぜない（別集計）。

---

## 4. 統合方式 — A-2（中間 JSONL → 既存バルクローダ）

直 INSERT (A-1) は HOLD、FDW/staging (A-3) は deferred。**A-2 を採用**（再現可能・レビュー可能・DB 書込はゲートまで保留）。

中間 JSONL（すべて read-only handoff、`production_write_allowed=false` / `canonical_promotion_allowed=false`）:
1. `kaken_project_observations_v0_1.jsonl`
2. `kaken_person_observations_v0_1.jsonl`
3. `nrid_researchmap_permalink_observations_v0_1.jsonl`
4. `researchmap_identifier_observations_v0_1.jsonl`
5. `researchmap_publication_observations_v0_1.jsonl`
6. `person_bridge_candidate_overlay_v0_1.jsonl`
7. `adapter_manifest_v0_1.json`

共通項目: `source_system` / `source_record_key` / `source_snapshot_path` / `payload_hash` / `parser_version` / `captured_at` / `generated_at_jst` / `lane`。

人物キーは 2 系統を並走（自動 alias しない）:
- Phase α: `alo:person:scholar:researchmap:{permalink}`
- Phase β: `alo:person:scholar:kaken:{eradCode}`（並走候補）
- 衝突は判定キュー `conflict_type=person_key_promotion_candidate`（owner 決定値: alias / separate_people / needs_more_evidence）

---

## 5. 次ゲートと許可/HOLD

**次ゲート: `SCHOLAR_ENRICHMENT_V038_ADAPTER_DRYRUN_SCHEMA_GATE`**

許可（ゲート前にやってよい）:
- §1 偵察、§2.1 seed 集約、サンプル pack 点検
- JSONL アダプタスキーマ設計、**100 人規模 dry-run 候補生成**
- 重複/コンフリクトレポート、レーン分離メトリクス

HOLD（Owner 判断 / 別ゲート）:
- 旧採番 937k 全件 fetch / PUBLICLY 全件 / PDF 一括
- PACSigny 直 INSERT / person_links INSERT / external_author_evidence INSERT / object_registry INSERT
- 人物 canonical 化 / PERSONDATAPILOT(gold) マージ / サービング公開
- prestige_score を権威・人物同定の真実として使用（実験的ランキング止まり）

---

## 6. 監査ループ運用（document churn の抑制）

- フル監査（REQUEST→GPT→RESULT）は **実質的に方針が変わる版だけ**。
- 細かい addendum / checklist は status 更新のみで回し、版番号を増やさない。
- このファイルを current とし、旧 v0.x は `_old/` 退避で superseded 明示。

---

## 7. 直近 To-Do（順序固定）

1. §1 偵察 → `kaken_resourcesync_inventory_v1.json`
2. §3 ownership matrix を Codex と確定（重複停止）
3. §2.1 seed 集約 → `kaken_seed_persons_v1.jsonl`
4. 旧採番サンプルで `<field>` 法判定 precision/recall 計測
5. §4 アダプタスキーマ + 100 人 dry-run → V038 ゲートへ
