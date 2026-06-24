# 集めた材料の整理 — 全体像サマリ (2026-06-24)

> 「集めた材料の整理について現状を知りたい」への回答。ALOナレッジDB（法令・判例・文献・人物の統合知識基盤）の
> 収集材料と整理状況を、設計正本＋**本番DB read-only照合(2026-06-23)**の実測に基づきまとめる。
> 本ファイルは現状サマリ。設計判断の詳細は各DD（同 PR）参照。

---

## 0. ひとことで

**材料の収集はほぼ完了。整理（編む=接続）の器も既に本番稼働中。残るは「論文を載せて人と繋ぐ」最優先タスクと、本番投入のOwner/SE承認。**
思想は「ALOはデータを作るのではなく**編む**」（データ編成指針）。価値は単一ソースでなく**多ソースの接続（繋ぎこみ）**から出る。

## 1. 集めた材料の棚卸し

| 材料 | 収集元 | 規模 | 状態 |
|---|---|---|---|
| 学術論文 | CiNii Research(法律系~150誌) | **638,021件** JSON | 取得済(Box)。**DBには未投入**(下記ボトルネック) |
| 図書館書誌 | OPAC | 110,948 HTML | 取得済→`opac_parsed_v04`で構造化 |
| 蔵書(本棚) | ISBN/NDL/OpenBD | 6,383冊中4,890(77%) | `biblio.books` 3,802 / `biblio.bib_records` 10,326 投入済 |
| 目次(TOC) | OpenBD/OCR | 4,789件 | 索引化済 |
| 法令 | e-Gov API v2 | 308〜355法令 | 取得済 |
| 判例 | D1-Law/最高裁OPAC | 契約249,863件 | **`dynamic.cases`=0（DB未投入）** |
| 法律用語辞書 | EX-word解読 | 1.4MB抽出 | 取得済 |
| 語彙 | e-Gov条文/NDLSH | 25,359ラベル | term_dict v0.3 ACTIVE |
| 人名(著者・研究者・裁判官) | CiNii/researchmap/NDL/日弁連/KAKEN | **`authority.person` 128,081** | DB投入済・属性豊富 |
| リンク(引用等) | 上記から抽出 | — | edges/claim設計済 |

## 2. どう整理されているか（編成の規律）

- **層構造**: L0 Raw（生保持）→ L1 Canonical（薄い identity + 同一性ハブ）→ L2 Curated Overlay（要約・属性）→ L3 Derived（AI用・再生成可）。
- **不変原則**: Raw First / Canonical is Thin / Value from Layering / No Destructive Import / Curate-not-Clone（データ編成指針）。
- **Links Are the Core Asset**: ノード数でなく**エッジ密度**が価値。`alo_edges`(明示=Canonical/推定=Derived) + claim+evidence。
- **本番実装(asai-dot's Project, Supabase東京, PG17)**: `authority`(人物/論文/claim) / `biblio`(書籍) / `dynamic`(案件/判例) / `d1law_taikei` / 他。人物は claim+evidence 型で稼働。

## 3. 現在地（本番DB実測 2026-06-23）

| テーブル | 行数 | 含意 |
|---|---|---|
| authority.person | **128,081** | 弁護士92,969+研究者73,155+裁判官64,185。薄いidentity |
| authority.person_history/affiliation | 270k / 230k | 識別子(scholar_nrid 73,155=1:1:1)・所属を source並列で保持 |
| authority.publication | **7,348** | 弁コム+NDL判事突合中心。**CiNii63.8万は未投入** |
| publication_author_claim | 7,125 | 人↔論文(trust_tier付)は実装済 |
| biblio.books / authors | 3,802 / 2,200 | 書籍著者はauthority.personと別系統(要統合) |
| dynamic.cases | **0** | 判例未投入 |

## 4. ★最大のボトルネック（繋ぎこみが進まない理由）

**人は厚い（128k、研究者73kにクリーンなNRID）が、繋ぐ相手の「論文」が薄い（publication 7,348のみ）。**
→ KAKEN/研究者が宙に浮いて見える原因は「CiNii法律論文63.8万がDBに入っていない」こと。
→ **最優先＝CiNii論文をauthority.publicationへ投入し、NRID(13桁・完全一致)でpersonと繋ぐ**。判例投入(cases=0)はその次。
（設計: `DD_cinii_publication_ingestion_v1` ＋ dry-run雛型 `cinii_publication_dryrun_templates_v1`）

## 5. KAKENの現状（※当初サマリの訂正）

- **研究者名鑑(NRID)は取得済**（kaken_raw 208MB, 3月）。法学者抽出も済。CiNii NRID 73,155がDBに 1:1:1 でクリーンに載っている。
- **科研費プロジェクトXMLの全件取得は「やり残し」ではなく意図的にHOLD/縮小**。実測で111.6万URL・旧採番85%と判明し、7日全件クロールは割に合わないため新採番の法分野スライスに限定（`KAKEN_lean_plan_v1`）。
- **eradCode(KAKEN固有キー)は本番DB未投入**。`authority.person_identifier`ハブ新設時に受け皿を作り、NRID経由で接続。
- KAKENはオーサー由来の一次情報として first-class。属性は L2 に source 並列で保持し使い切る方針。

## 6. 未整理・残課題

1. **CiNii論文のDB投入**（最優先・繋ぎこみの相手）— dry-run→Owner ratify→本投入。
2. **判例(dynamic.cases=0)の投入** — 人↔判例(評釈)はその後。
3. **biblio.authors(2,200) ↔ authority.person(128k) の統合**（書籍著者と論文著者の二重系統）。
4. **`authority.person_identifier` ハブ新設**（識別子が person_history に散在、eradCode受け皿なし）。
5. KAKEN旧採番の逆引き取得（seed/分野スコープ）、ISBN未回収~1,500冊、ルートフォルダcleanup。

## 7. 性質と次の判断

- 本サマリと関連DDは **read-only調査＋設計のみ。本番DBへの書込なし。**
- 本番投入は **dry-run通過＋Owner ratify＋SE(花岡さん)レーン承認** が前提（各DDにHOLD明記）。
- 次の現実的な一手: Phase 0（CiNii法律ISSNフィルタ実走→対象件数・NRID歩留まり実測）= 実装フェーズ。

### 関連ドキュメント（同 PR #36）
- `KAKEN_lean_plan_v1` / `DD_author_model_resolution_v1` / `DD_cinii_publication_ingestion_v1` / `HANDOFF_author_linkage_implementation_SE` / `cinii_publication_dryrun_templates_v1`
