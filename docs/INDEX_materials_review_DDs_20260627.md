# 索引: 材料整理レビュー 設計文書マップ (2026-06-27)

> materials-organization-review セッションで追加した設計/調査文書の導線。**どれが何を決めたか**と**次に誰が動くか**を1枚に。
> 共通前提: いずれも **read-only調査＋設計**。本番DB書込・大量走査・API実走は含まず、実装は **Owner ratify ＋ SE(花岡さん)レーン**。

---

## 0. 出発点と全体像

| 文書 | 何を決めた/示した |
|---|---|
| `MATERIALS_ORGANIZATION_OVERVIEW_20260624.md` | 集めた材料の棚卸し＋本番DB実測の現在地。**最大ボトルネック=CiNii論文(63.8万)未投入で人(128k)が宙に浮く**を特定。まず読む1枚 |

## 1. KAKEN / eradCode 線

| 文書 | 何を決めた | status |
|---|---|---|
| `KAKEN_lean_plan_v1_20260622.md` | KAKEN取得を1枚に集約。**全件クロール廃止→seed逆引き**、偵察必須(gate-0)、HOLD解除条件、実装(authority schema)準拠 | proposal |
| `DD_eradcode_acquisition_v1_20260624.md` | eradCode取得方針。**E-1=1000系3,654をNRID下8桁から取得ゼロで導出(規則確定)**／E-2=73k seed逆引き(実現性確定, 9000系歩留まり≤23.7%)／E-3=残差は追わない | 設計(E-1着手可) |

## 2. 著者(オーサー)モデル — 繋ぎこみの器

| 文書 | 何を決めた | status |
|---|---|---|
| `DD_author_model_resolution_v1_20260623.md` | 設計2版の食い違いを裁定。**薄いCanonical＋リッチ属性はL2 overlay**。実DB照合で実装が裏付け(authority.person 128k等)。識別子ハブ `person_identifier` 新設を提言。biblio↔authority連結率16.5%も記録 | 実DB照合済 |
| `HANDOFF_author_linkage_implementation_SE_20260623.md` | 上記のSE向け実装ハンドオフ。**person_identifier DDL＋E-1投入SQL**(§9)を同梱。最小の取得ゼロジョブ | handoff |

## 3. CiNii 論文 — 繋ぎこみ本体

| 文書 | 何を決めた | status |
|---|---|---|
| `DD_cinii_publication_ingestion_v1_20260623.md` | CiNii→`authority.publication`の三段(source_record/publication/author_evidence→claim)取込設計＋NRID突合・trust_tier。**親=既存 DD-CINII-001**(法律論考判定・著者bindは既存、本DDは"論文側"のみ) | 設計 |
| `DD_cinii_flatten_decomposition_v1_20260626.md` | CiNii生JSON-LDを**フラット2表へ解きほぐす**(Parser段)。多値NRIDを nrid_all+nrid_primary+nrid_count、eradCodeを erad_from_nrid 列で導出。スコープ二重性(誌レベル数十万 vs 内容レベル2-3万)を確定 | 設計 |
| `cinii_publication_dryrun_templates_v1.md` | 本番非破壊のstaging dry-run雛型(ISSNフィルタ擬似コード/staging DDL/CRID冪等UPSERT/NRID突合claim/受入ゲートSQL) | 雛型 |

## 4. 判例 / 評釈 — 人↔判例

| 文書 | 何を決めた | status |
|---|---|---|
| `DD_case_layer_prereq_v1_20260626.md` | **訂正: dynamic.casesはSF案件(1,017)で判例ではない／判例レイヤは未作成(DDL未適用)**。元データ(RTF52.5GB/249,863, 抽出27%済)・設計v1.4・gapを整理 | 前提整理 |
| `DD_hyoshaku_parse_v1_20260626.md` | genuinely未着手の**評釈パース**。【判例評釈】を分解し **person→publication(評釈)→case の3ホップ**を結線。判例DDL適用が前提 | 設計 |

---

## 5. 実装フェーズの「次の一手」(Owner/SEレーン)

優先順（安い・効く順）:
1. **E-1**: `authority.person_identifier` DDL ＋ 1000系3,654のeradCode投入（取得ゼロ）— HANDOFF §9。
2. **CiNii論文投入**: DD-CINII-001の3軸で法律論考(≈2-3万)を絞り、`cinii_pub_flat`→`authority.publication`＋claim — dryrun雛型。
3. **判例レイヤDDL** ＋ RTF(27%抽出済)からの投入 — DD_case_layer_prereq §6。
4. **評釈パース**(判例DDL後): person→publication→case の3ホップ開通。
5. **E-2**: KAKEN研究者API実走サンプル(層別500)で9000系歩留まり実測。

各ステップとも **dry-run → Owner ratify → 本投入** の規律。

## 6. 既存資産（重複回避のため参照）

- `DD-CINII-001`(Box, 2026-05-12): CiNii法律論考の判定3軸＋著者bind(上位設計)。
- `d1law_ingest.py` / `RUNBOOK_d1law_ingest.md`(Box): 判例RTF取込(運用中・27%抽出済)。
- `authority` schema(本番Supabase): person/publication/claim+evidence が稼働中。
