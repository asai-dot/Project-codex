# DD-LITID-001 追補提案: 属性観測層 + 決定的projection（biblio_item_attr_observations）v0.1-draft

- 作成: 2026-06-15 / Claude（リモートセッション・浅井さん指示）
- 親: `DD-LITID-001_biblio_identity_noisbn_draft_v0.2`（Box 2275006797196, GPT `DESIGN_PASS_WITH_NOTES`）
- 査読元: `docs/2026-06-15_dd-litid-001_review_stacking_perspective.md`（R1本丸＋R2〜R6/R10）
- **ゲート: 設計提案のみ。** DDL・既存移行・backfill・データ更新はしない。次工程は owner decision ＋ お目付け役監査。
- 解く穴: **R1**（scalar属性に観測層が無い＝積層不能）を本丸に、**R2**（分類の居場所喪失）・**R3**（衝突/時点）・**R4**（field_confidence）・**R5**（OCR品質伝播）・**R6**（provenance二重計上）・**R10**（厚さ指標）を同一機構で解消。

---

## 0. 段階分離の方針【owner確定・2026-06-15】── 重み付けは“後”

**重み付け(R4)の前に、由来が明確な綺麗な層別観測データを先に揃える。** データ作成と重み付け関数は**並行でやらない**。混ぜると汚れる。

- **Stage 1（先・本提案の本体）**: 各データの**出所が明確な綺麗な観測DB**を作る。雑誌も文献も同じ。揃えるべき層:
  1. **NDLベースのメタ**（中立な第三者書誌）
  2. **刊行物単位の個別メタ**（文献=書籍 / 雑誌、さらに**版(edition)単位**）
  3. **刊行物内部**（TOC / 記事 / 章）
  この3層が「観測（出所・provenance付き・append-only）」として綺麗に並ぶ状態が Stage 1 の完了条件。
- **Stage 2（後）**: 各属性に複数の原典候補があるとき**何を最良とするか**の評価＝**`field_confidence` 重み付け関数**。これは Stage 1 の綺麗なデータが揃ってから設計する。
- **層ごとに最良を判断する（単一ソース盲信の禁止）**: 「あるソースを一律に信じる」は本データ構造と整合しない。最良判断は **NDLメタ層 / 刊行物メタ層 / 内部(TOC・記事)層 の各層で別個に**行う。priority_profile は層別に持つ。

→ 以下 §3 は Stage 1（綺麗な観測＋出所）。§4 step3 の `field_confidence` は **Stage 2 へ繰り延べ**（本提案では“接続点の予約”のみ。既定重みは置かない）。

---

## 0.6 「厚さ」と「正しさ」を分ける ── AIが捏造できず・必要精度が出る逆算設計【owner方針・2026-06-15】

owner指摘: **コーパスが“厚い”こと自体は価値でない。雑魚観測が大量にあっても無意味で、綺麗な観測が1つあれば薄くてもそれが正しい。** ゆえに2つを分離する:

- **(A) 厚さ（地層）**: 各属性に積もった観測群。これは**材料**であって目的でない。多観測=正しい、ではない。
- **(B) 正しさ（採用値）**: その地層から我々が**採用する1つの正規値**。重み付け判断は(B)を取り出した後の話。

設計はこの2目的から**逆算**する:

1. **AIが捏造できない構造（anti-hallucination）**: 採用値は必ず**実観測(obs_id＋source＋raw_payload_ref)に接地**する。**観測の無い値は存在できない**。serving/RAG は採用値とその出所しか出せない＝でっち上げの余地が構造的に無い（評価設計の grounded-only を**データ層で強制**）。
2. **必要精度が出る構造（precision優先）**: 採用値は**決定的に1つ**選ぶ。ソースが割れたら勝手に多数決せず **disputed で止めて人手へ**（薄くても正しい1値 ＞ 厚いが曖昧）。**単独の権威観測（例: NDL 1件）だけで採用してよい**（裏取り数は必須でない）。
3. **厚さはKPIにしない**: 観測数・ソース数は“材料の在庫”として見えればよく品質の証明ではない。KPIは「採用値カバレッジ・disputed率・**採用値が100%観測に接地している率**」。

→ 帰結: §4 projection の主目的は「**地層から1採用値を出所付きで決定的に取り出す**」こと。重み付け(R4)は(B)抽出後のStage2。agreement_count は補助シグナルで**採用の必須条件ではない**。

---

## 1. 結論（一行）

DD-LITID-001 の **TOC に既にある「多観測→決定的projection」を、scalar/分類属性にも対称適用**する。
すなわち **`biblio_item_attr_observations`（append-only 観測）** ＋ **決定的 projection（正規値＝再計算可能）** を新設し、
`biblio_item` の scalar 列は**観測群からの projection（派生・キャッシュ）**に格下げする（二重正本にしない＝fingerprints正本化と同型）。

設計原則の踏襲: 「ISBNは証拠であって主キーでない」と同じ思想で、**「`biblio_item.genre` 等の単値は“正規値”であって正本でない。正本は観測群」**。

---

## 2. なぜ「観測層」か（TOCとの対称性）

| | TOC（既存 §5.5） | scalar/分類（本提案） |
|---|---|---|
| 多観測の生保全 | `toc_observations` | **`biblio_item_attr_observations`** |
| 正規値 | `alo_toc_nodes`（canonical_confidence/source_votes） | **`biblio_item_attr_canonical`**（field_confidence/agreement） |
| provenance二重計上回避 | `provenance_group` | **同左（属性層へ）** |
| 原本主義 | raw_toc_ref 保全 | raw_payload_ref 保全・append-only |

TOCにできてscalarにできない理由は無い。**同じ型をコピーするだけ**で R1 が解ける。

---

## 3. スキーマ案（DDLでなく構造案）

### 3.1 `biblio_item_attr_observations`（観測・append-only・正本）

```text
biblio_item_attr_observations
  obs_id            opaque PK (ULID/UUID)
  item_id           FK biblio_item  -- nullable: 同定前は source_item_id に付き、解決後に紐付く
  source_item_id    provisional id  (LB_xxx / B4_xxx / LLB_xxx / NDL oai_id / bookdx_id)
  attr_key          enum: title | subtitle | publisher | pub_date | pub_year | page_count
                        | edition_statement | volume_no | abstract
                        | classification | author | held_by_office | shelf_locator | fulltext_access
  attr_scheme       分類/語彙の出所。classification/author 等で必須、素のscalarは null
                        NDC | NDLC | NDLSH | BSH
                        | vendor_genre:lionbolt | vendor_category:bencom | vendor_field:legallib
  value_raw         原値（落とさない）
  value_norm        比較用正規化値（NFKC等。§6.1準拠。原値は保持）
  source_system     lionbolt | bencom | legallib | ndl | bookdx | openbd | manual
  provenance_group  同一供給元の再配信を畳むキー（R6）
  observed_at       そのソースが示す時点（無ければ取得時刻）
  parser_version
  medium_origin     digital | paper_scan   -- R5/owner採用: 全観測共通。デジタル由来か紙スキャン由来か（meta・TOC・本文すべてに付す）
  ocr_accuracy_rank nullable  A|B|C         -- OCR精度（ソース提供 or 自所評価）。Stage1は生値保持のみ
  source_type       nullable  scan|digital  -- ソースnative値（あれば。medium_originの根拠）
  vertical          nullable  bool          -- 縦書き
  -- ↑ R4方針: ここでは「出所の生事実」だけ保持。confidence_seed/field_confidence は Stage 2 で導出
  rights_profile    raw / normalized_meta / toc / body / fingerprint  -- §5.7継承
  raw_payload_ref   生応答への参照（本文は複製しない）
  is_active         supersession用。**削除しない**（データ落とすな）
  supersedes_obs_id nullable -- 同一 source_item の再取得で旧値を更新した時だけ繋ぐ
  created_at
```

- **append-only**: 訂正・再取得は**新行**を追加し `supersedes_obs_id` で旧行を指す。旧行は `is_active=false` で**保全**（履歴＝誤同定監査と as-of 再現の資産）。
- 同定前から観測は存在しうる（source_item_id に付く）。解決時に `item_id` を埋めるだけ＝観測自体は不変。

### 3.2 `biblio_item_attr_canonical`（正規値・決定的projection・派生）

```text
biblio_item_attr_canonical
  item_id
  attr_key
  attr_scheme
  canonical_value        -- single基数なら1値 / multi基数なら値ごとに1行
  cardinality            single | multi
  field_confidence       -- R4。0..1
  agreement_count        -- provenance_group で畳んだ後の独立裏取り数（R6）
  contributor_groups[]   -- 寄与した provenance_group / source の一覧（説明可能性）
  conflict_status        single_source | corroborated | disputed
  projection_version     -- 決定的。同一観測群→同一出力（再計算可能）
  computed_at
  PRIMARY KEY (item_id, attr_key, attr_scheme, canonical_value)
```

`biblio_item` の `genre/page_count/...` 列は、この canonical の **薄いVIEWまたはキャッシュ**（正本ではない）。

### 3.3 `attr_registry`（属性ごとの規律＝R7/R8の受け皿）

```text
attr_registry
  attr_key
  attr_scheme
  cardinality       single | multi
  rollup_scope      item | work     -- R7: 分類/件名/著者は work、物理属性は item
  value_type        text | int | date | code
  norm_rule         正規化規則ID
  priority_profile  source優先順プロファイルID（既定: manual>ndl>publisher>toc_pdf>legallib>openbd>bencom>...）
  currency_sensitive bool            -- recency減衰を効かせるか（pub系/改正系）
```

- **multi＋work**: `classification`(NDC/NDLC/件名), `author`, ベンダーgenre群 → **版を越えて合議**（R7）。
- **single＋item**: `page_count`, `pub_year`, `edition_statement`, `volume_no` → 版固有。
- `accuracy_rank`/`source_type`/`vertical`/`medium_origin` は**正規属性にしない**。観測の出所メタとして保持し、Stage2 の field_confidence に使う（R5）。

---

### 3.4 時点モデル（R3）── 取得時点 / 主張時点 / 版

観測は時間を2つ持ち、版は別granularityで扱う:
- **取得時点(transaction time)**: `created_at`＋append-only＋`supersedes_obs_id`。「我々がいつその値を見たか」。過去の知識状態を **as-of 再現**できる（誤同定監査・ロールバックの資産）。
- **主張時点(assertion time)**: `observed_at`。「ソースが何時点の値として示したか」。
- **版(valid time)は属性で持たない**: 「現行版か」「改訂で内容が変わったか」は **item粒度（版を束ねない, DDL-20260428-01）**で扱う。属性の valid-time 区間管理はしない（書誌メタは版に固定される）。**事後的に版・号を判別できる構造**は、edition_statement / volume_no / issue_no を item固有属性に保持することで担保（R7と同方針）。法令currency等“世界の真の時制”は別レイヤ(authority/法令時間)で扱い本層に持ち込まない。
- 訂正・再取得: 同一 source_item の値が変わったら **新observation＋supersedes**（旧は is_active=false で保全）。projection は is_active のみ参照。

---

## 4. 決定的 projection アルゴリズム（観測 → canonical）

純関数。同一観測集合から**毎回同一出力**（再現性ゲート）。

```
入力: ある (item_id, attr_key, attr_scheme) の is_active 観測群 O
1. provenance畳み: O を provenance_group ごとに1票へ畳む（R6）。
     群内代表は confidence_seed 最大→observed_at 最新。
   → 独立観測集合 O'（agreement_count = |O'|）。
2. 値決定:
   - cardinality=single:
       priority_profile（manual>ndl>publisher>...）→ recency（currency_sensitive時）で1値選択。
       O' の value_norm が2値以上に割れる → conflict_status = disputed（人手review＋誤同定監査へ）。
       割れない → corroborated（|O'|>=2）/ single_source（|O'|=1）。
       ※ single_source でも採用可（薄くてもよい）。裏取り数は採用の必須条件でない（owner方針/R10）。
   - cardinality=multi（genre/classification/author）:
       値を捨てない。value_norm ごとに canonical 行を作り、各値に寄与群と field_confidence。
       「代表値(primary)」だけ別途マーク（UI用）。
3. field_confidence — **【Stage 2・本提案では繰り延べ】**（R4方針）:
     Stage 1 の projection 出力は「値＋出所(contributor_groups)＋agreement_count＋conflict_status」まで。
     重み付け関数 `field_confidence = f(層別source_priority, recency, medium_origin/OCR品質, provenance畳み後agreement)`
     の具体形・重みは、**綺麗な観測DB(Stage1)が層別に揃ってから**、層ごとに設計（評価設計C7でキャリブレーション）。
     canonical には field_confidence 列の“接続点”だけ予約し、Stage1 では未算定(null)。
4. 出力(Stage1): canonical 行（value, agreement_count, contributor_groups, conflict_status, projection_version。field_confidence=null）。
```

- **【Stage 2 参考】** confidence_seed/src_authority_norm の例（A=1.0/B=0.8/C=0.5、digital=1.0/scan=0.85、vertical×0.95、priority順位の0..1正規化）は**重み設計の素案**であり、Stage1では採用しない。
- projection は **bib_toc→toc_nodes の map正本主義と同型**（原観測保全＋決定的射影＝二度回して hash 一致）。Stage1 はこの「綺麗で出所明確・再計算可能」までを完成形とする。

---

## 5. これで解ける穴（対応表）

| 穴 | 解消 |
|---|---|
| R1 scalar観測層なし | `attr_observations`＋canonical projection で対称化 |
| R2 分類の居場所喪失 | `attr_key='classification'`＋`attr_scheme∈{NDC,NDLC,NDLSH,BSH,vendor:*}`（multi・work rollup） |
| R3 衝突/時点 | `conflict_status=disputed` ＋ append-only＋`observed_at`/`supersedes`（as-of再現） |
| R4 重み伝播 | **Stage 2**（綺麗な層別観測の後）。Stage1は値＋出所＋agreementまで（接続点のみ予約） |
| R5 OCR品質/由来 | `medium_origin`(digital/paper_scan) を**全観測共通**の生フィールドに（owner採用・meta/TOC/本文）。OCR精度も生保持。重みはStage2 |
| R6 二重計上 | `provenance_group` を attr_observations の第一級次元に。**層を問わず**group畳み後に agreement_count（owner: 汎用的・必須） |
| R7 rollup | `attr_registry.rollup_scope`(item\|work)。分類/件名/著者=work合議、物理/TOC/版表示=item。**版・号は事後判別可**に保持 |
| R8 分類語彙 | scheme併存（**NDCをピボット**）。vendor genre→NDCのcrosswalkはStage2語彙設計 |
| R9 自所保有/原典到達 | id_type に `bookdx_id`。projection に `held_by_office`/`shelf_locator`＋**`fulltext_access`(none\|shelf\|local_pdf=自炊PDF)**＝原典即時到達の厚み |
| R10 厚さ≠正しさ | **KPIは「厚さ」でなく「採用値の正しさ・追跡可能性」**（owner）。指標=採用値カバレッジ・disputed率・**全採用値が観測に接地100%(anti-hallucination)**・held_by_office/fulltext_access率 |

---

## 6. ワークドエグザンプル（3源＋NDLが1冊に解決）

`保険法 第4版`（LION BOLT/弁コム/legal-library/NDL が同一 item に解決）の `classification` 観測:

```
obs1 attr=classification scheme=vendor_genre:lionbolt value="保険法"   src=lionbolt  pg=lb     seed=0.8(B,scan)
obs2 attr=classification scheme=vendor_category:bencom value="商法・会社法" src=bencom  pg=pubX  seed=1.0
obs3 attr=classification scheme=vendor_field:legallib value="商事法/保険" src=legallib pg=pubX  seed=1.0
obs4 attr=classification scheme=NDC                    value="324.6"     src=ndl      pg=ndl   seed=1.0
obs5 attr=classification scheme=NDLC                   value="AZ-512"    src=ndl      pg=ndl   seed=1.0
```
→ projection（multi・work rollup）:
- `NDC=324.6`（採用値。出所=NDL単独でも採用可。field_confはStage2）、`NDLC=AZ-512`、`vendor_genre:lionbolt=保険法`…
- **provenance畳み**: obs2/obs3 は `pg=pubX`（弁コム/legallib が同一出版社メタ再配信）→ **1票に畳む**（R6。二重計上しない）。
- `held_by_office`: bookdx 観測があれば true＋shelf_locator（R9）。

`pub_year` で `bencom=2019 / legallib=2020` と割れたら → `conflict_status=disputed` で review へ（＝厚くする前に誤同定/版差を疑うシグナル）。

---

## 7. 既存設計との整合

- **二重正本にしない**: 観測=正本、`biblio_item` scalar=派生。fingerprints を正本化し biblio_identifiers をVIEW化した GPT 監査方針と同型。
- **rights**: `rights_profile` を観測行に持たせ projection に継承（§5.7）。分類/書誌メタは normalized_meta 階層、本文は別。
- **provenance_group**: §5.5 の概念を属性層へ拡張（GPT P1 の「metadata側にも」を具体化）。
- **DD-LITID 3層**: 本提案は item 中心を壊さない。R7 の work rollup は work_id 確定後に candidate→promotion で合議（誤結合防止）。

---

## 8. 追加ゲート案

| ゲート | 合格条件 |
|---|---|
| `gate_attr_obs_append_only` | 観測の update/delete 0。訂正は supersedes 新行のみ |
| `gate_attr_projection_deterministic` | 同一観測群を2回 projection → hash一致 |
| `gate_provenance_group_no_double_count` | agreement_count は group 畳み後に算定 |
| `gate_attr_conflict_surfaced` | single基数の値割れは必ず disputed（静かな上書き0） |
| `gate_attr_rights_inherited` | 観測→projection→serving で rights_profile が閉じる |
| `gate_adopted_value_grounded` | 採用値(canonical)は必ず ≥1 obs_id に接地。観測なき値=0（anti-hallucination） |
| `gate_no_scalar_second_sot` | `biblio_item` scalar は canonical の派生（独立書込み0） |

---

## 9. asai 決定事項

1. **観測層を採るか**（採用＝scalar/分類も TOC と同じ多観測→projection に統一）。推奨: 採用。
2. **`biblio_item` scalar をVIEW化 or キャッシュ列化**。推奨: 当面キャッシュ列（再計算可能・projection_versionで追跡）、正本は観測。
3. **classification を multi・work rollup に**（NDC/NDLC/件名/ベンダーgenre併存）。推奨: そうする（R2/R7/R8）。
4. **重み付け(field_confidence)は Stage 2**（綺麗な層別観測の後）。Stage1では算定しない。推奨: 段階分離（owner方針）。
5. **自所保有・原典到達を厚い属性に**（R9）: id_type に `bookdx_id`、projection に `held_by_office`/`shelf_locator`／**`fulltext_access`(none|shelf|local_pdf=自炊PDF)**。推奨: 採用（原典に即時到達できる厚みは高評価）。
6. **`medium_origin`(digital/paper_scan) を全観測・全層に必須**（owner採用）。推奨: 採用。
7. **「厚さ」と「正しさ」を分離**（R10/owner）: 採用値=1属性1正規値（薄くてもよい・単独権威で採用可）、全採用値は観測に接地。厚さはKPIにしない。推奨: 採用。

---

## 10. 段階導入（DDL/backfillは別承認）

- **Stage 1 = 綺麗な層別観測DB＋採用値抽出（先）**:
  - S0 設計: 本提案を to_gpt 監査へ。attr_registry 初版（attr_key×scheme×cardinality×rollup_scope）＋medium_origin＋provenance_group を確定。
  - S1 dry-run: 501コホートで既存source＋NDLから**射影シミュレーション**。各属性の**採用値1つ＋出所＋disputed**を出す（**重みは出さない**）。
- **Stage 2 = 重み付け（後）**: 綺麗な採用値が層別に揃ってから、層ごとに field_confidence を設計・キャリブレーション（評価設計C7）。単一ソース盲信は採らない。
- スキーマ追加→backfill は owner ratify＋お目付け役後。観測は append-only ゆえ既存破壊なし。

---

## 付録: この提案が活きる出口
- 501 PoC（`docs/2026-06-14_poc_thick_501_spec.md`）の「積層dry-run」は本 projection のS1そのもの。
- AIレディー・リサーチ（`..._ai_ready_legal_research_methodology.md`）の「重み付き著作ノード」= canonical＋field_confidence。
- 評価設計 C7（重み付け）の被験対象 = field_confidence の質。
