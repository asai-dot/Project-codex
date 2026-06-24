# KAKEN 取得・統合 実行版プラン v1 (2026-06-22)

> 目的: 6/15〜6/17 に v0.1→v0.3.7 と 9 版に分裂した KAKEN 計画を **1 枚に畳み**、
> 観測された非効率（後追い計測・全件ブルートフォース・二重取得）を断ち、
> **seed 逆引き** と **担当分担** を正本化する。
> このファイルが以後の KAKEN レーンの現行プラン (current)。旧 v0.x は superseded 扱い。

- author: materials-organization-review session
- status: Owner レビュー反映済（A〜E 判断を本文に織込）。最終 ratify 待ち
- supersedes: KAKEN_author_object_acquisition_plan v0.1〜v0.3.7（status_to_codex 各版含む）
- 不変ルール: 取得は read-only / 本番 DB 書込・人物 canonical 化・gold マージは別ゲート

### Owner レビュー判断（2026-06-22）
| 判断 | 内容 | 結論 | 反映先 |
|---|---|---|---|
| A | seed 外の隠れ研究者の取りこぼし対策 | **別系統で対応**（分野スコープ列挙＋共同研究者グラフ） | §2.4 |
| B | 9 版を 1 枚に集約 | **OK（accepted）** | §0 / §6 |
| C | 偵察ファースト | **必須（ブロッキング gate-0）** | §1 |
| D | fetch 分担表 | **承認・責任明確化（単一責任者、TBD 廃止）** | §3 |
| E | HOLD の扱い | **無期限にせず測定可能な解除条件を付す** | §5 |
| F | KAKEN の位置づけと繋ぎこみ | **KAKEN は first-class（劣後撤回）。オーサー由来の一次情報。論文/文献と結線して初めて使える＝繋ぎこみが本命の成果物** | §0.5 / §2.4 Y-4 / §4.1 |

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

## 0.5 設計原則（不変）— KAKEN は first-class / 密結合構造

> Owner 決定（最優先）。以後この原則に反する書き換えは不可。

- **KAKEN を劣後させない。** 他サイトでは取りにくい **オーサー由来の一次情報**（著者本人が自己申告した研究テーマ・所属・共同研究者・科研費歴）であり、**著者自身が価値があると考えている情報**。だからこそ必ず拾い、**使い切る**。fallback でも enrichment 専用でもない。
- **両側を first-class で耕す。** 人物/著者・論文(article)・文献(書籍/書誌) を各々独立した正本として作り込む。「どちらかを主、他方を従」にしない。
- **リンク層で双方向に結ぶ。** 発見（recall）は各レイヤの **和集合**（論文に出ない研究者は KAKEN 側が、KAKEN に出ない論文は文献側が拾う）。正答（precision）は **突合**で出す。各レイヤは互いの突合キー（受け口）を出し合う。
- **欲しいのは密結合データ構造そのもの。** 著者 × 論文 × 文献 が証拠付きで密に繋がった構造を作るのが目的。雑に片側から流し込むのではない。
- **設計投資の主戦場はリンク層**（同名異人・異名同人＝旧姓/表記揺れ/ローマ字の解決）。取り込み自体は一回処理で安い。コストはここに寄せる。

---

## 1. 偵察ファースト（**必須・ブロッキング**）

> **Owner 決定: 必須。** §1 が完了するまで §2 以降の本 fetch・計画版追加を**開始しない**（gate-0）。
> 走り出してから規模が 43x ズレた再発を防ぐための強制ゲート。安価（数分の読取り）。

- [ ] ResourceSync `capabilitylist` / `resourcelist`（23 本）の **hash・件数** を記録
- [ ] スキーマ 2 系統を確定: 新採番 `<review_section>`（小区分） / 旧採番 `<field>` 階層
- [ ] 研究者番号の抽出経路を固定: `eradCode` 属性・`<researcherNumber type='erad'>`（`MEMBER-xxxx` は使わない）
- [ ] 採番比率の確認: 新 ~15% / 旧 ~85%（≈937k）

成果物: `kaken_resourcesync_inventory_v1.json`（hash・件数・スキーマ・採番比率・取得日・fetcher 版）

---

## 2. 取得戦略 — 全件クロール廃止、2 系統リコールで網羅

法ヒット率 1〜2% の母集団を全件クロールしない。代わりに **2 つの相補的なリコール経路**で
「既知の人」も「seed に居ない隠れ研究者」も拾う。

- **経路 X（精度／既知）= seed 逆引き** … §2.1。重要な既知法学者を速く高品質に。
- **経路 Y（網羅／未知）= 分野スコープ列挙** … §2.4。**Owner 指摘の取りこぼし対策の本体。**
  人ではなく **分野コード**で絞るので、seed 非依存で漏れを潰しつつ母数は法学相当 ~1〜2%（≈1〜2 万件）に収まる。

### 2.1 seed（既知の法学者）の集約 — 経路 X
- PACSigny KAKEN 868 ブリッジ（`eradCode`）
- `books.json` 著者文字列 → 氏名候補
- researchmap 既収集（2,003 packs / 約 100 名、recovery 完了 92 名）
- NRID 名鑑（取得済 208MB, 3/3）/ CiNii NRID 抽出（済 3/31）

成果物: `kaken_seed_persons_v1.jsonl`（eradCode / 氏名・yomi / 所属 / 活動年）

### 2.2 取得レーン（優先度順）
1. **modern 法分野スライス（新採番）** — 継続中。境界明確・実測済み。`law_modern_2026` レーン。
2. **旧採番 = 分野スコープ列挙（§2.4）＋ seed 逆引き** — **全件 937k クロールはしない。**
   分野コードで法学相当 project を列挙して取得（網羅）＋ seed 該当を確実取得（精度）。
   - 着手前に**サンプルで `<field>` 法判定の precision/recall を計測** → 妥当なら本実行。
3. **PUBLICLY (14,137)** — まず小サンプルでスキーマ互換を確認。PROJECT 互換なら同抽出器を再利用、非互換なら別レーン。**全件 fetch は互換確認まで HOLD。**

### 2.4 seed 外（隠れ研究者）のカバレッジ — 経路 Y（別系統）

> Owner 指摘: seed 逆引きだけだと seed に居ない法学者を構造的に取りこぼす。
> これを seed に依存しない 3 段で補う。すべて read-only / candidate-only / DB 書込は HOLD のまま。

**Y-1. 分野スコープ列挙（主リコール）**
- 人ではなく **KAKEN 分野コードで法学 project を直接列挙**する。母数は全件ではなく法学相当 ~1〜2 万件。
- 対象区分（正式区分表で code 確定）:
  - 新採番（中区分「法学およびその関連分野」の小区分）: 基礎法学 / 公法学 / 国際法学 / 社会法学 / 刑事法学 / 民事法学 / 新領域法学
  - 旧採番（分科「法学」の細目）: 同名の細目群。新小区分 ↔ 旧細目の対応表を §1 偵察で作る。
- 列挙手段は KAKEN 検索 API / OAI（区分フィルタ可）を第一候補。不可なら ResourceSync 列挙 → `<review_section>`/`<field>` で法判定フィルタ（要 precision/recall 計測）。
- 列挙された project XML だけ fetch → `eradCode` 抽出。**ここで seed 外の研究者が初めて発見される。**

**Y-2. 共同研究者グラフ展開（芋づるリコール）**
- 取得済み法 project の **研究分担者（co-investigator）の `eradCode`** を収穫。
- seed にも Y-1 にも未出の人物が出たら discovery queue に積み、その人の他 project を **1-hop だけ**（上限付き）追加取得。
- 根拠: 法 project の共同研究者は法学隣接の確度が高い。少ない fetch で recall を底上げ。

**Y-3. デルタ同期（鮮度）**
- ResourceSync changelist で**新規追加 project だけ**を定期取得し、Y-1 の分野フィルタを再適用。
- 全件再クロール不要で最新を維持。`fetch_policy_manifest` の last_synced を更新。

**Y-4. 論文側との結線で残差を吸収（KAKEN を孤立させない）**
- 分野コードが法学でない学際 project（例: 法と経済・医事法の医学側）は Y-1 単体では漏れうる。
- これは KAKEN を諦める理由ではない。**学際の法学者は法律雑誌の著者として論文側に必ず現れる**ので、§4 のリンク層で **KAKEN(著者) × 法律論文(CiNii 法律系 176 誌)** を結べば、KAKEN 側で分野漏れした人も論文側から同一人物として回収される（発見＝和集合）。
- 補助の タイトル/キーワード fallback は **サンプルで効果計測**し費用対効果が出る時だけ。出なくても**論文側結線が本命**なので残差は実害が小さい。漏れ量は明示記録。

> **原則（§0.5）再掲**: KAKEN 単体では価値が出ない。**法律論文データと結線して初めて使える情報**になる。
> よって KAKEN レーンの完了条件は「取得」ではなく「論文・文献レイヤとリンク済み」であること。

成果物: `kaken_law_project_enum_v1.jsonl`（経路 Y 由来 project + 判定根拠列: review_section code/label / old field label / keyword fallback の別）。

### 2.3 レート規律（`fetch_policy_manifest` に明記）
- KAKEN: 同時実行 **4 上限**（concurrency 6 で 503 多発・効率崩壊を観測）。jitter・retry/backoff・stop 条件を明記。
- NRID/researchmap: 8-way は許容範囲だが失敗ログ + backoff 必須。
- 記録: host / concurrency / interval / UA / 503 観測数 / last reviewed。

---

## 3. fetch ownership matrix（**Owner 承認済 / 責任明確化**）

**広域 fetch を続ける前に、この表で重複を消す。** 既に Codex が取得済みのセットは Claude 側は停止し、reconciliation に切替える。
**各レーンに単一の責任者（accountable owner）を置く** — TBD を残さない。責任者はそのレーンの fetch 実行・`fetch_policy_manifest` 維持・重複申告に責任を負う。レビュー者は相互（Claude↔Codex）。

| 対象セット | 責任者 | レビュー | 状態 | 備考 |
|---|---|---|---|---|
| modern PROJECT 法分野 XML | Claude | Codex | running | 重複なら停止→照合 |
| 旧採番 PROJECT — 分野スコープ列挙(経路Y) | Claude | Codex | not started | §2.4、サンプル検証後 |
| 旧採番 — ターゲティング戦略 / 区分対応表 | Codex | Claude | not started | §1 偵察と統合、新小区分↔旧細目 |
| PUBLICLY (14,137) | Claude | Codex | not started | スキーマ確認のみ先行 |
| researchmap / NRID overlap | Claude | Codex | running | raw cache 3,435 取得済 |
| 全体 inventory（ResourceSync） | Codex | Claude | not started | §1 gate-0 |
| 人物同定 / PACSigny マージ | Codex | Owner | HOLD | §5 解除条件まで HOLD |
| PLANNED/ORGANIZER/AREA/WRAPUP/INTERNATIONAL | — | — | out of scope | 当面除外 |

> 競合・越境時のエスカレーション先は **Owner**。担当変更は本表の更新（= 版更新）で行い、口頭の暗黙変更は不可。
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

### 4.1 リンク層（**本命の成果物 — 繋ぎこみ**）

> Owner 決定: **繋ぎこみが最重要。** KAKEN・論文・文献を取得して並べるだけでは価値ゼロ。
> 三者を結んだ密結合構造が成果物。各レーンの「完了」は取得ではなく **リンク済み** を指す。

**実DB照合(2026-06-23)で確定した実装に合わせる。** 繋ぎこみは新規テーブルでなく、既に稼働中の
`authority` スキーマ（claim+evidence 型）の上に積む。詳細は `DD_author_model_resolution_v1` §8。

実装済みの器（本番 `asai-dot's Project`）:
- `authority.person`(128,081, 薄い identity) / `person_affiliation`(230k) / `person_history`(270k, 識別子も) / `person_alias`(30k)
- `authority.publication`(**7,348**) / `publication_author_claim`(7,125, **人↔論文リンク** confidence+trust_tier) / `publication_author_evidence`(7,589)
- `biblio.authors`(2,200, ndl_auth_id/viaf 保持) / `book_publication_link` / `dynamic.cases`(**0**)

結ぶべきエッジ → 実テーブルの対応（論文が最多だが人↔人・人↔文献・人↔判例も一級）:

| エッジ | 実装先テーブル | 突合キー | 状態 |
|---|---|---|---|
| 人 ↔ 論文 | `publication_author_claim`(+`_evidence`) | NRID / 氏名+収録誌 → evidence→claim(trust_tier) | ✅器あり。但し論文母数が薄い(下記) |
| 人 ↔ 人 | (claim 経由の共著/ KAKEN分担者) | NRID / 共同研究者 | △ 設計のみ |
| 人 ↔ 文献(書籍) | `biblio.bib_authors` ↔ `authority.person` 統合 | ndl_auth_id / 氏名+yomi | ❌ biblio.authorsとperson別系統(要統合) |
| 人 ↔ 判例 | (評釈著者→判例) | dynamic.cases | ❌ cases=0(投入待ち) |

- 識別子の正しい置き場所は **新設 `authority.person_identifier`**（現状 person_history に散在）。fp_type相当 = `nrid/kaken_id(eradCode)/researchmap_id/orcid/ndl_auth_id`。**KAKEN を繋ぐ実装上の一手はこれ**（DD §8.3/§8.5）。
- マッチは **hard ID(NRID等) → 氏名+収録誌(ISSN)候補** の順。曖昧は claim_status と trust_tier で段階管理（既存実装と同型）。
- **同名異人/異名同人の解決がコストの中心**。設計投資をここに寄せる（§0.5）。

> ★**繋ぎこみの最大ボトルネック（実測）**: 人は厚い(128k, 研究者73k に NRID)が、繋ぐ相手の
> `authority.publication` が **7,348件のみ**（弁コム+NDL判事突合中心、**CiNii法律論文63.8万は未投入**）。
> dynamic.cases=0。→ **KAKEN を更に集めるより、CiNii論文を publication に載せて claim で人と繋ぐのが最優先**（§B / 別紙 CiNii取込設計）。

---

## 5. 次ゲートと許可/HOLD

**次ゲート: `SCHOLAR_ENRICHMENT_V038_ADAPTER_DRYRUN_SCHEMA_GATE`**

許可（ゲート前にやってよい）:
- §1 偵察、§2.1 seed 集約、サンプル pack 点検
- JSONL アダプタスキーマ設計、**100 人規模 dry-run 候補生成**
- 重複/コンフリクトレポート、レーン分離メトリクス

### HOLD と解除条件（**Owner 方針: 無期限 HOLD にしない。測定可能な解除ゲートを置く**）

各 HOLD は「いつ・何を満たせば解けるか」を明文化する。条件を満たしたら Owner ratify 1 回で解除（再設計不要）。

| HOLD 項目 | 解除ゲート（これを満たせば解く） | 解除後の最初の一歩 |
|---|---|---|
| DB 書込（PACSigny/person_links/external_author_evidence/object_registry INSERT） | V038 dryrun gate 通過 ＋ 重複/コンフリクト率が閾値内 ＋ ロールバック手順あり ＋ Owner ratify | staging テーブルへ限定 load → 差分検証 |
| 人物 canonical 化 | gold サンプルで同定 precision ≥ 合意閾値 ＋ person observation schema 確定 ＋ 衝突キュー裁定済 | candidate → canonical 昇格バッチ（可逆） |
| PERSONDATAPILOT(gold) マージ | exact-overlap / false-positive 率を別レーンで実測 ＋ import preview OK | レーン限定マージ（`researchmap_new_2026`）|
| 旧採番 拡大取得 | §2.4 サンプルで `<field>` 法判定 precision/recall が閾値超 ＋ ownership 確定 | 経路 Y 本実行（分野スコープ列挙）|
| PUBLICLY 全件 | 小サンプルでスキーマ互換確認 | 互換なら同抽出器再利用 / 非互換なら別レーン |
| PDF 一括 | 高価値 project の優先表 ＋ ストレージ/OCR 計画 ＋ 著作権/規約整理 | ターゲット限定 fetch |
| prestige_score を権威利用 | gold サンプルで専門家期待と一致検証 | 検証通過まで実験的ランキング止まり |

> 閾値（precision/false-positive 等）の具体値は §1 偵察と 100 人 dry-run の実測後に Owner と確定する。
> 各ゲートは `gate_registry` に登録し、満たした証拠（measured 値・artifact パス）を残してから解除する。

---

## 6. 監査ループ運用（document churn の抑制）

- フル監査（REQUEST→GPT→RESULT）は **実質的に方針が変わる版だけ**。
- 細かい addendum / checklist は status 更新のみで回し、版番号を増やさない。
- このファイルを current とし、旧 v0.x は `_old/` 退避で superseded 明示。

---

## 7. 直近 To-Do（順序固定）

1. **gate-0 必須**: §1 偵察 → `kaken_resourcesync_inventory_v1.json`（新小区分↔旧細目 対応表含む）
2. §3 ownership matrix を Codex と確定（重複停止・責任者確認）
3. §2.1 seed 集約 → `kaken_seed_persons_v1.jsonl`（経路 X）
4. §2.4 分野スコープ列挙 → `kaken_law_project_enum_v1.jsonl`（経路 Y）＋ 旧採番サンプルで法判定 precision/recall 計測
5. §4 アダプタスキーマ + 100 人 dry-run → V038 ゲートへ
6. §5 解除ゲートの閾値を実測値で確定 → Owner ratify で順次 HOLD 解除
