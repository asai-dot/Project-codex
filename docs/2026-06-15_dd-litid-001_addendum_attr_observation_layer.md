# DD-LITID-001 追補提案: 属性観測層 + 決定的projection（biblio_item_attr_observations）v0.2-draft

- 作成: 2026-06-15 / Claude（リモートセッション・浅井さん指示）
- 親: `DD-LITID-001_biblio_identity_noisbn_draft_v0.2`（Box 2275006797196, GPT `DESIGN_PASS_WITH_NOTES`）
- 査読元: `docs/2026-06-15_dd-litid-001_review_stacking_perspective.md`（R1本丸＋R2〜R10）
- **ゲート: 設計提案のみ。** DDL・既存移行・backfill・canonical promotion・データ更新・本番書込は対象外。

## 監査反映（v0.1 → v0.2）

GPTお目付け役 `DESIGN_PASS_WITH_NOTES`（result: Box `2286160319588` / req `2286086385325`）の **must-fix 8件・追加ゲート5件・should-fix** を反映。final_gate=PASS_WITH_NOTES（DDL/backfillはHOLD継続）。

| must-fix | 反映箇所 |
|---|---|
| 1. SoT境界を明示（fingerprints=同一性 / attr_observations=属性主張 / attr_canonical=射影cache / biblio_item scalar=view・cacheのみ） | §0.7・§7 |
| 2. 採用状態の区別（single_authority/corroborated/disputed/unresolved/manual_override） | §3.2 `adopted_status` |
| 3. dispute triage（equivalent_after_normalization/definition_difference_allowed/edition_suspected/true_conflict/needs_owner_policy）を人手review前に | §3.5・§4 |
| 4. `provenance_family`＋独立性confidence（provenance_groupだけにしない） | §3.1・§4 |
| 5. work rollup は work昇格まで遅延（`rollup_status`） | §3.2・§3.3・§8 gate |
| 6. rights伝播＋serving-deny gate | §7・§8 `gate_rights_profile_serving_allowed` |
| 7. 既存 biblio_item scalar 読者の互換gate | §8 `gate_existing_consumer_compatibility` |
| 8. 正規化/派生値の derivation tracing（value_raw, norm_rule, obs_id, projection_version） | §3.2・§8 `gate_norm_derivation_traceable` |

should-fix（attr_policy・access/書誌の分離・NDCはpivotでなく1scheme/bridge・item単位rollback・dry-runメトリクス）も §3.3/§9/§10 に反映。

---

## 0. 段階分離の方針【owner確定】── 重み付けは“後”

**重み付け(R4)の前に、由来が明確な綺麗な層別観測データを先に揃える。** データ作成と重み付け関数は並行でやらない。

- **Stage 1（先・本提案の本体）**: 出所明確な綺麗な観測DB。層: ①NDLメタ ②刊行物単位メタ（書籍/雑誌・版単位） ③刊行物内部（TOC/記事/章）。観測（出所付き・append-only）として綺麗に並ぶのが完了条件。
- **Stage 2（後）**: 複数原典候補から何を最良とするかの **`field_confidence` 重み付け関数**。Stage1が揃ってから層別に設計。
- **層ごとに最良判断（単一ソース盲信の禁止）**。priority_profile は層別。

> **Stage順序の罠への手当て（監査§Stage順序）**: Stage1スキーマは Stage2 が必要とする生事実を**全て保持**する＝ `source_system, provenance_group, provenance_family, observed_at, fetched_at, parser_version, medium_origin, OCR facts, rights_profile, source_locator, raw_payload_ref, value_raw, value_norm`。これが揃えば破壊的再設計なしに Stage2 を足せる。

## 0.6 「厚さ」と「正しさ」を分ける ── AIが捏造できず・必要精度が出る逆算設計【owner方針】

- **(A) 厚さ（地層）**＝観測群＝材料。多観測=正しい、ではない。
- **(B) 正しさ（採用値）**＝地層から採る1つの正規値。重み付けは(B)の後。
- 逆算原則:
  1. **anti-hallucination**: 採用値は必ず実観測(obs_id＋source＋provenance)に接地。観測なき値は存在不可。**DB射影だけでなく serving/RAG 出力でも強制**（監査指摘）。serving は採用値＋出所を出すか「not available」と言う。捏造合成しない。
  2. **precision優先**: 採用値は決定的に1つ。割れたら**triage→（真の衝突なら）disputed で人手へ**（多数決しない）。単独権威観測でも採用可（ただし§3.2 の `adopted_status=single_authority` で区別・可逆）。
  3. **厚さはKPIにしない**。KPIは採用値カバレッジ・triage後disputed率・**採用値の観測接地100%**・rights_blocked率・ungrounded値数。

→ projection の主目的＝「地層から1採用値を出所付きで決定的に取り出す」。重み付け(R4)は(B)抽出後のStage2。agreement_count は補助で採用の必須条件でない。

## 0.7 SoT境界【must-fix 1・load-bearing】

四層を**役割で**截然と分ける。これが崩れると第3正本になり設計は失敗する。

| 層 | 役割 | 正本性 |
|---|---|---|
| `fingerprints`（既存） | **同一性**の証拠・外部ID | identity SoT（変更しない） |
| `biblio_item_attr_observations`（新） | **属性の主張**（各ソースが言う値） | attribute-claim の保全（append-only） |
| `biblio_item_attr_canonical`（新） | 観測からの**決定的射影**（採用値） | projection cache（再計算可能・正本でない） |
| `biblio_item` scalar 列（既存） | serving 用 **view/cache のみ** | **独立書込み禁止**（`gate_no_scalar_second_sot`） |

属性観測は同一性を主張しない（fingerprints の領分を侵さない）。canonical は cache であって権威でない。

---

## 1. 結論（一行）

DD-LITID-001 の TOC `toc_observations`（多観測→決定的projection）を **scalar/分類属性にも対称適用**。`biblio_item_attr_observations`（append-only）＋ 決定的 projection で **1属性=1採用値(canonical)**。`biblio_item` scalar は cache/view に格下げ（§0.7）。

---

## 2. なぜ「観測層」か（TOCとの対称性）

| | TOC（既存 §5.5） | scalar/分類（本提案） |
|---|---|---|
| 多観測の生保全 | `toc_observations` | `biblio_item_attr_observations` |
| 正規値（射影） | `alo_toc_nodes` | `biblio_item_attr_canonical` |
| 二重計上回避 | `provenance_group` | `provenance_group`＋`provenance_family`（§3.1） |
| 原本主義 | raw_toc_ref | raw_payload_ref・append-only |

---

## 3. スキーマ案（DDLでなく構造案）

### 3.1 `biblio_item_attr_observations`（観測・append-only・属性主張の保全）

```text
biblio_item_attr_observations
  obs_id            opaque PK (ULID/UUID)
  item_id           FK biblio_item  -- nullable: 同定前は source_item_id に付き、解決後に紐付く
  source_item_id    provisional id  (LB_xxx / B4_xxx / LLB_xxx / NDL oai_id / bookdx_id)
  attr_key          enum: title|subtitle|publisher|pub_date|pub_year|page_count
                        |edition_statement|volume_no|abstract|classification|author
                        |held_by_office|shelf_locator|fulltext_access   -- access系は§3.3で書誌と分離
  attr_scheme       classification/author等で必須。NDC|NDLC|NDLSH|BSH
                        |vendor_genre:lionbolt|vendor_category:bencom|vendor_field:legallib
  value_raw         原値（落とさない）
  value_norm        比較用正規化値
  norm_rule         value_norm を生成した規則ID（derivation tracing / must-fix 8）
  source_system     lionbolt|bencom|legallib|ndl|bookdx|openbd|manual
  provenance_group  同一供給元の再配信を畳むキー（R6）
  provenance_family 供給系統（例: publisher_feed:有斐閣）＋ grouping_confidence（must-fix 4）
  source_locator    ソース内の所在（API endpoint/レコードキー等。監査トレース用）
  observed_at       ソースが示す時点（主張時点）
  fetched_at        我々が取得した時点（取得時点。observed_at と分離・must-fix）
  parser_version
  medium_origin     digital | paper_scan   -- 全観測共通の出所事実（meta/TOC/本文）
  ocr_accuracy_rank nullable A|B|C
  source_type       nullable scan|digital
  vertical          nullable bool
  rights_profile    raw|normalized_meta|toc|body|fingerprint  -- §5.7継承。projection→servingへ伝播必須
  raw_payload_ref   生応答への参照（本文は複製しない）
  is_active         supersession用。削除しない（データ落とすな）
  supersedes_obs_id nullable
  created_at
```

- append-only。訂正・再取得は新行＋supersedes、旧は is_active=false 保全。
- `provenance_family`＋grouping_confidence: 「同一供給系統か」を**判定の確からしさ付き**で持つ。不明な関係は独立計上しない（高リスク属性では保守的に）。

### 3.2 `biblio_item_attr_canonical`（採用値・決定的射影・cache）

```text
biblio_item_attr_canonical
  item_id
  attr_key
  attr_scheme
  canonical_value         -- single=1値 / multi=値ごと1行
  cardinality             single | multi
  adopted_status          single_authority | corroborated | disputed | unresolved | manual_override   -- must-fix 2
  rollup_status           item_only | work_candidate | work_accepted                                   -- must-fix 5
  agreement_count         -- provenance_family 畳み後の独立裏取り数（R6）
  contributor_obs[]       -- 採用に寄与した obs_id（接地・説明可能性）。must-fix 8
  contributor_groups[]    -- provenance_group/family の一覧
  norm_rule               -- 正規化規則（derivation tracing）
  rights_profile          -- 観測から継承（serving gate 用）
  field_confidence        -- 【Stage2】Stage1ではnull
  projection_version      -- 決定的（同一観測群→同一hash）
  computed_at
  PRIMARY KEY (item_id, attr_key, attr_scheme, canonical_value)
```

- **採用値は必ず `contributor_obs` で実観測に接地**（anti-hallucination）。
- `adopted_status`: 単独権威での採用も「正しい」と断定せず `single_authority` と明示＝可逆・監査可能。高リスク属性は §3.3 の `attr_policy` で corroboration/人手必須に。
- `biblio_item` の `genre/page_count/...` 列はこの cache の view（§0.7）。

### 3.3 `attr_registry`＋`attr_policy`（属性ごとの規律・should-fix）

```text
attr_registry
  attr_key / attr_scheme
  cardinality        single | multi
  rollup_scope       item | work        -- 分類/件名/著者=work、物理=item（R7）
  fact_class         bibliographic | access     -- access系(held_by_office/fulltext_access)を書誌真実から分離（should-fix）
  value_type         text|int|date|code
  norm_rule
  priority_profile   層別プロファイルID（manual>ndl>publisher>toc_pdf>legallib>openbd>bencom>...）
  currency_sensitive bool

attr_policy（属性別の採用規律・should-fix / open_question回答の器）
  attr_key / attr_scheme
  single_authority_ok    bool   -- 単独権威で採用してよいか
  corroboration_required bool
  human_review_required  bool
  work_rollup_allowed_from  item_only | work_candidate | work_accepted   -- must-fix 5
```

- **分類はNDCを“pivot”にしない**（監査 modify-within-pass）。NDC は**1 scheme＋UI/既定 bridge**。NDC/NDLC/件名/vendor genre は scheme 併存（multi）。
- **access系 ≠ 書誌真実**: `held_by_office`/`fulltext_access`/`shelf_locator` は `fact_class=access`。書誌正しさの合議には混ぜず、rights/serving と厳密分離。

### 3.4 時点モデル（R3）

- 取得時点 `fetched_at`＋append-only＋supersedes（as-of再現）。主張時点 `observed_at`。
- 版(valid time)は属性で持たず item粒度（版を束ねない）。版・号は edition_statement/volume_no/issue_no を item固有に保持し事後判別可。

### 3.5 dispute triage（must-fix 3）── 人手review前の自動分類

value_norm が割れても**即 disputed/人手にしない**。先に triage:

| triage | 意味 | 既定処理 |
|---|---|---|
| `equivalent_after_normalization` | 正規化で同一（全半角・記号・空白） | 自動採用（差を吸収） |
| `definition_difference_allowed` | ソース間の定義差（page_count定義・副題揺れ） | policy で許容・採用 |
| `edition_suspected` | 年/頁差＝版違いの疑い | 別 item 候補へ（束ねない） |
| `true_conflict` | 上記でない実質衝突 | `disputed` → 人手review |
| `needs_owner_policy` | 規律未定義 | owner policy 待ち |

→ 人手に回るのは `true_conflict` のみ。disputed 爆発を防ぐ。

---

## 4. 決定的 projection アルゴリズム（観測 → canonical）

純関数・再現性ゲート。

```
入力: (item_id, attr_key, attr_scheme) の is_active 観測群 O
1. provenance畳み: provenance_family（＋grouping_confidence）で独立票へ畳む（R6/must-fix4）。
     関係不明は高リスク属性で独立計上しない。→ O'（agreement_count=|O'|）。
2. triage（§3.5）: value_norm差を equivalent/definition_diff/edition_suspected/true_conflict/needs_policy に分類。
3. 採用:
   - single: priority_profile→recency で1値。
       triage=true_conflict → adopted_status=disputed（人手）。needs_policy → unresolved。
       割れない/吸収可 → corroborated(|O'|>=2) / single_authority(|O'|=1, policy.single_authority_ok時)。
       ※ single_authority も「正しい」と断定せず status で明示・可逆（監査）。
   - multi（classification/author）: 値を捨てず value_norm ごと canonical 行。各値に contributor_obs。
       rollup_status は work昇格状態に従う（item_only 既定。work_accepted まで版横断合議しない／must-fix5）。
4. 接地: 各 canonical 行に contributor_obs(obs_id) と rights_profile と norm_rule を必須付与（anti-hallucination/derivation）。
5. 出力(Stage1): value, adopted_status, rollup_status, agreement_count, contributor_obs, contributor_groups,
     rights_profile, norm_rule, projection_version。field_confidence=null（Stage2）。
```

- projection は bib_toc→toc_nodes の map正本主義と同型（原観測保全＋決定的射影＝二度回して hash 一致）。

---

## 5. これで解ける穴（対応表）

| 穴 | 解消 |
|---|---|
| R1 scalar観測層なし | attr_observations＋canonical projection |
| R2 分類の居場所喪失 | classification を attr_scheme(NDC/NDLC/件名/vendor:*) で併存・multi |
| R3 衝突/時点 | adopted_status＋triage＋append-only/observed_at/fetched_at |
| R4 重み伝播 | Stage2（Stage1は値＋出所＋agreement＋status＋接地まで） |
| R5 OCR品質/由来 | medium_origin 全観測共通＋OCR生保持。重みStage2 |
| R6 二重計上 | provenance_group＋**provenance_family/独立性confidence**で畳む |
| R7 rollup | rollup_scope＋**rollup_status（work昇格まで item_only）** |
| R8 分類語彙 | scheme併存。**NDCはpivotでなく1scheme＋UI bridge** |
| R9 自所保有/原典到達 | bookdx_id＋held_by_office/shelf_locator/fulltext_access（**fact_class=access で書誌と分離**） |
| R10 厚さ≠正しさ | KPIは採用値の正しさ・接地100%・triage後disputed率・rights_blocked率 |

---

## 6. ワークドエグザンプル（3源＋NDLが1冊に解決）

`保険法 第4版` の `classification` 観測（vendor_genre:lionbolt=保険法 / vendor_category:bencom=商法・会社法 / vendor_field:legallib=商事法 / NDC=324.6 / NDLC=AZ-512）。
→ projection（multi）: 各 scheme を採用値として保持（NDCは単独権威で `adopted_status=single_authority`、`rollup_status=item_only`）。弁コム/legallib が `provenance_family=publisher_feed:有斐閣` と判定されれば**1票に畳む**（独立計上しない）。
→ `pub_year` で 2019/2020 が割れたら triage: 版違いの疑い→`edition_suspected`（別item候補）。正規化同一なら吸収。真の衝突のみ `disputed`→人手。

---

## 7. 既存設計との整合 + rights serving

- **SoT境界（§0.7・must-fix1）**: fingerprints=同一性 / attr_observations=属性主張 / attr_canonical=cache / biblio_item scalar=view。
- **rights伝播（must-fix6）**: rights_profile を 観測→canonical→**serving** へ伝播。**serving-deny gate**で、対象コンテキストに許可されない rights_profile の値は出力しない（normalized_meta でも購読由来の制約が残りうる）。
- **DD-LITID 3層**: item中心を壊さない。work rollup は work昇格後（candidate→promotion）。
- **consumer互換（must-fix7）**: 既存 `app/booklib.py`・serving が biblio_item scalar を canonical として読む前提を壊さない（cache化＋互換テスト）。

---

## 8. ゲート（提案＋監査追加）

| ゲート | 合格条件 | 監査判定 |
|---|---|---|
| `gate_no_scalar_second_sot` | biblio_item scalar は cache/view・独立書込み0 | **MUST（load-bearing）** |
| `gate_adopted_value_grounded` | 採用値は ≥1 obs_id 接地。**DB射影＋serving/RAG出力の両方**で強制 | ACCEPT |
| `gate_attr_obs_append_only` | update/delete 0・訂正は supersedes 新行 | ACCEPT |
| `gate_attr_projection_deterministic` | 同一観測群→同一hash | ACCEPT |
| `gate_provenance_group_no_double_count` | provenance_family＋独立性confidenceで畳む | ACCEPT_W_NOTE |
| `gate_attr_conflict_surfaced` | 先に triage→true_conflictのみ disputed | ACCEPT_W_NOTE |
| `gate_rights_profile_serving_allowed` | rights不許可コンテキストへ出力deny | 追加必須 |
| `gate_work_rollup_requires_work_promotion` | work_accepted まで版横断合議しない | 追加必須 |
| `gate_norm_derivation_traceable` | 正規化/派生値は value_raw＋norm_rule＋obs_id＋projection_version を保持 | 追加必須 |
| `gate_existing_consumer_compatibility` | 既存scalar読者の互換テストpass | 追加必須 |
| `gate_single_authority_policy_per_attr` | 単独権威採用は attr_policy 許可属性のみ | 追加必須 |

---

## 9. asai 決定事項（監査所見反映）

1. **観測層採用**: yes（SoT境界＋scalar独立書込み禁止前提）。
2. **scalar派生化**: yes（cache/view。破壊的移行はしない・互換テスト後）。
3. **分類 multi**: yes。**work rollup は work昇格(accepted/stable-candidate)後**のみ（早すぎ禁止）。**NDCはpivotでなく1scheme＋UI bridge**。
4. **重みStage2**: yes（Stage1は生事実を全保持）。
5. **自所保有/原典到達**: yes（ただし **fact_class=access** で書誌真実から分離・rights gate）。
6. **medium_origin必須**: yes（観測の出所事実）。
7. **厚さ/正しさ分離**: yes（接地済み採用値メトリクス。厚さはKPIにしない）。

open questions（監査）: ①どの attr_key が単独権威採用可か ②provenance_family の独立性ルール ③work_id がいつ rollup 可能な安定度か ④どの rights_profile をどのAI/tool文脈に出すか ⑤NDCの役割（UI pivot/既定bridge/単なる1scheme）。→ §3.3 `attr_policy` と owner決定で順次確定。

---

## 10. 段階導入（DDL/backfillは別承認）

- **Stage 1 = 綺麗な層別観測DB＋採用値抽出（先）**:
  - S0 設計: 本v0.2を owner ratify。**最小 attr_registry（501 PoC 必要属性のみ）**＋attr_policy初版＋provenance_family を確定（過剰一般化しない）。
  - S1 **report-only dry-run**（501コホート・**DDL/backfill/ scalar上書き なし**）: 各属性の採用値＋出所＋adopted_status＋triage結果を出す（重みなし）。
- **dry-run メトリクス（should-fix）**: adopted_value_coverage / single_authority_rate / triage後disputed_rate / rights_blocked_rate / ungrounded_value_count。
- **Stage 2 = 重み付け（後）**: 綺麗な採用値が揃ってから層別 field_confidence（評価設計C7）。
- DDL/backfill 計画は **owner ratify＋dry-run結果の後**に別途起案（監査 next-steps #5）。

---

## 付録: この提案が活きる出口
- 501 PoC（`docs/2026-06-14_poc_thick_501_spec.md`）の「積層dry-run」＝本 projection の S1（report-only）。
- AIレディー・リサーチの「重み付き著作ノード」= canonical採用値（出所付き）＋(Stage2)field_confidence。
- 評価設計 C4(接地)・C7(重み付け) の被験対象。
- 監査結果 result: Box `2286160319588`（DESIGN_PASS_WITH_NOTES）。
