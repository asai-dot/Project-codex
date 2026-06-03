# ALO 今後の進め方 — ロードマップ v2（2026-06-03 / owner条件付き採用を反映）

> v1→v2: owner レビュー（80点・条件付き採用）を反映。**Phase A の前に A0「接続契約」を必須化**し、
> 検索ベンチを前倒し、bib_terms を弱リンク化、554/5,638 を分離、B/C を reorder。A0 詳細は
> `docs/A0_biblio_alo_crosswalk_contract.md`、ベンチ雛形は `docs/search_bench/baseline_queries.template.md`。

## ★方針決定（確定・全体の前提）
**当面 `biblio/authority/control`（codex実体）を「作業用実体」として育てるが、恒久正本は将来の
`alo_*`（cases/statutes/alo_works/alo_terms/alo_hubs/alo_entity_links/alo_edges/fingerprints）側に置く。**
→ `biblio.*` は ALO本体への**供給源（feedstock）であって本体ではない**。第二本体化＝二重管理を防ぐため、
投入物はすべて crosswalk付き・出所付き・弱リンクは弱いままで入れる（A0）。

---

## 0. 現在地（2026-06-03 時点・実測）
**リポジトリ資産（git PR #2）**
- e-Gov法定定義錨: フル18,099 / high 5,874 / 機械ゲート後 canonical候補 high&unreviewed 5,638（`gate_egov_anchors.py`）
- 用語カード3,063（リッチ554）／読み訂正台帳44／条見出し4,367・見出し→条リンク1,731／JLT3,869・学陽2,684・有斐閣13,344
- ツール群（抽出・三点測量・読み裁定・ゲート・カード・蔵書変換・ローダ）

**実DB（Supabase `nixfjmwxmgugiiuqfuym`）**
| レイヤ | テーブル | 件数 | 状態 |
|---|---|---|---|
| 語彙 | `biblio.terms` | 554 | **canonical**（浅井承認済） |
| 書誌(蔵書) | `biblio.bib_records` source=asai-bookshelf | 6,524 | 投入済 |
| 書誌(bencom) | `biblio.bib_records` source=bencom-library | 3,802 | 既存(codex) |
| 目次 | `biblio.bib_toc` | 555,887 | 既存(codex) |
| 人物 | `authority.person` 等 | ~128k | 既存(codex, CiNii/弁護士/裁判官) |
| 橋 | `biblio.bib_terms` | 0 | **未** |
| 統治 | `control.source_snapshots/ingest_jobs/releases` | — | 承認付きリリース運用 |

---

## 1. ★最重要・戦略的論点：設計と実体のギャップ（owner/codex/花岡 判断）
ドキュメント上のALO設計（`20_architecture`）は**6レイヤ＋ `alo_edges`(Links Are the Core Asset)＋SKOS 3層
`alo_terms/alo_hubs/alo_entity_links`＋`fingerprints`＋`cases/statutes`** という壮大な構造。
**だが実Supabaseには `cases/statutes/alo_edges/alo_terms/alo_hubs/fingerprints` が無い**。実在は
codex が作った `biblio`(書誌+terms+bib_terms+toc)／`authority`(人物)／`control`(統治) のみ。

含意:
- 私が語彙錨を入れた `biblio.terms`、蔵書を入れた `bib_records` は**実体に合わせた現実解**。だが仕様の
  `alo:term:{scheme}:{key}` / `alo:hub:{slug}` / `alo_edges(edge_type=interprets/doctrine/subject_index…)`
  とは**URI体系・テーブルが食い違う**（例: 実 term_id=`egovcard:子会社` vs 仕様 `alo:term:…`）。
- **判例軸(cases)・法令軸(statutes)・エッジ(alo_edges)が live に存在しない**＝ALOの中核価値「判例→条文→
  文献→語彙のリンク密度」はまだDB上で実現していない。今日揃えたのは語彙と書誌の2軸の“ノード”まで。

**判断1（最優先）**: 今後は (a) 実 `biblio/authority` モデルを正として育てる／(b) 仕様の
`alo_edges/alo_terms/alo_hubs/cases/statutes` フルモデルへ寄せる／(c) 併存＋将来移行、のどれか。
これは**スキーマ所有者（codex/花岡SE）と浅井の合意事項**。本ロードマップは「(a)実モデルを育てつつ、
仕様の語彙/リンクの考え方を `biblio.*` 上で再現し、将来 (c) で接続」を暫定前提に置く。

---

## 2. ロードマップ（段階・各段は measure→設計→投入→検証）

### A0 — 接続契約（Phase A の前に必須）→ `docs/A0_biblio_alo_crosswalk_contract.md`
crosswalk（暫定ID↔将来ALO URI）／bib_terms の弱リンク定義（強エッジと混ぜない）／554 canonical と 5,638
unreviewed の分離／実装ガードレールを確定。**これを明文化してから A1 に入る**。

### Phase A — 二軸を“繋ぐ”（A0 反映・read-only 先行）
```
A1  検索ベンチ50件をベースラインとして作成・現状測定（bib_terms 未投入の今しか測れない）
A2  554 terms × 蔵書 subject/genre/tags の一致率を read-only 測定
A3  5,638 high&unreviewed を「投入せず」候補辞書として read-only 一致率測定
A4  554版 vs 5,638版 の差分比較（どちらで橋を張るか決定）
A5  精度許容なら biblio.bib_term_links に suspect/provisional 投入（弱relation・根拠メタ付き）
A6  サンプル監査/人手レビュー後、一部だけ canonical 化（control.releases 承認）
```
- bib_terms は**弱い主題リンク**（book_subject_matches_term 等）。`interprets/doctrine` と混ぜない。
- 5,638 は canonical と**同列にしない**（status 必須・検索/リンク既定は canonical のみ）。
- 読み訂正44の canonical 反映（owner手順、verify2件=図画/競売）も A 期に。

### Phase B — 語彙enrichment＋**名寄せを前倒し**（C より前に重複解消）
```
B1  条見出し・見出し→条リンク(4,367/1,731)を「弱い statute_term_link」としてDB化（用語↔条文の疑似edge）
B2  asai-bookshelf × bencom-library の重複候補を抽出（TOCチャンク化の前に）
B3  重複に fingerprint/work_identifier 相当の crosswalk を作る（同一文献対応表）
```
- JLT英訳・CiNii・読みconsensus を term に付与（多言語ブリッジの種）。e-Gov錨は全158法令ローカルに18,099有り。

### Phase C — 書誌の深掘り（名寄せ後）
```
C1  bencom 簡易TOC → chunk（葉TOC=1チャンク・content_function 12分類）。bib_toc 555,887 が素材。
```
- 重複(NOBN_ vs alo:book:isbn)を B2/B3 で解消してから chunk 化＝同一文献の重複チャンクで検索ベンチが濁るのを防ぐ。
- NDL reconcile 継続（per-field provenance）。

### Phase D — 合流と“検索で効くか”の検証（価値の証明）
- terms↔statute(条見出しリンク)↔book(bib_terms)↔(将来 case) を `alo_edges` 思想で接続。
- **★検索ベンチ（GPTの宿題・最重要の受け入れ条件）**: 法律相談クエリ50〜100件で、投入前後の
  「見出し語ヒット率／条文到達率／関連蔵書到達率／誤ヒット率」を実測。**「検索精度が上がった」と言える数値**を作る。
  ここまでやって初めて、今日積んだデータが“実務で効く”と証明できる。

### Phase E — ALO本体（owner主導・大）
- 仕様の `cases/statutes/alo_edges/CaseBundle`：D1-Law判例249,863・文献449,677・現行法規355 の取込、
  MCP配信（mcp-lawctx）、3フェーズ運用（相談準備→面談→深掘り）。語彙・書誌軸はこの土台の supporting_analysis を供給。
- これは花岡SE/codex のDDLと連動する大工事。本セッションの2軸はその feedstock。

---

## 3. 運用モデル（誰が・どこで）— 今回の摩擦から得た教訓
| 種別 | 適所 | 理由・教訓 |
|---|---|---|
| ツール設計・改良・ゲート・カード・**設計** | **クラウド(私)** | 反復・レビューに強い |
| 大規模抽出/変換（e-Gov全法令・蔵書6,524） | **ローカル(owner)** | 素材(32MB books.json・158法令)が手元。`--dir`/transform を1コマンド |
| 大規模DB投入 | **owner（psql）** or **codex** | SQLエディタはサイズ上限（~340KB可・600KB不可）。14MBは psql -f |
| DB認証 | — | **Google SSO=DBパスワード非保持**。リセットは影響不明で回避。**一時ロール(LOGIN+BYPASSRLS)をMCPで作り→削除**が安全（今回実証） |
| 小規模DB操作・検証・承認反映 | **クラウド(私, MCP)** | execute_sql（特権・RLSバイパス）。ただし大容量の手打ちは不可 |
| スキーマ/統治台帳の所有 | **codex/花岡** | `control.*` 規律・DDL。私は作法に倣い触れる範囲を最小化 |

**「データ投入プレイブック」を整備する**（次の小タスク）: ①ローカルで transform → ②`psql -f`（接続は
Session pooler / 一時ロール）or ③小さければ pbcopy→SQL Editor。これで毎回の摩擦を無くす。

---

## 4. 品質・ガバナンス（貫く原則）
- **昇格の梯子**: candidate → machine-gated(`gate_egov_anchors.py`) → provisional(`control.releases` pending) →
  canonical(浅井承認 `approval_status=approved`)。全投入この順。
- 生データ非改変／派生物を正本扱いしない／suspect層・auto_apply=false／**measure-then-build**／権威は万能でない。
- 可逆性: 全投入は `source` タグで `DELETE` 可・冪等(ON CONFLICT)・control にロールバック手順記録。
- **受け入れの最終条件は「検索ベンチ」（Phase D）**。データ件数でなく“実務で効くか”で測る（GPTレビュー）。

---

## 5. リスク・未決（owner判断待ち）
1. **スキーマ・フォーク**（§1）: 実 `biblio.*` vs 仕様 `alo_*`。放置すると二重メンテ。早期に方針合意を。
2. **語彙の置き場**: 法定定義を `biblio.terms` に置いたのは現実解。本来は語彙レイヤ(alo_terms/hub)＋ statute リンク。
3. **著作権/再配布**: JLT・Togi Lab IME・有斐閣 は内部利用前提。DB化/配信時に許諾範囲の再確認。
4. **依頼者データ**: 本DBは将来 client データも載る想定（東京リージョン確定済）。語彙/書誌は非機微だが、
   将来の混在時のRLS/権限設計は codex/花岡 と。
5. **bencom と蔵書の重複**: 同一本が NOBN_ と alo:book:isbn の二重に。fingerprints 名寄せで解消（Phase C）。
6. **medium 12,225 の品質**: 境界精緻化v3後も読点両義性は irreducible。canonical には上げない。

---

## 6. 次セッションの具体的第一歩（非破壊・measure）
**「§8の橋は張れるか」をデータで判定する**:
1. 蔵書6,524の `raw->ndl_subjects` / `genre` / `tags` を集計し、`biblio.terms`(554) への正規化一致率を出す
   （MCPのSELECTで可・read-only）。
2. 一致が薄ければ → 用語を5,638へ拡充(A2)してから再測。濃ければ → `bib_terms` 投入を設計。
3. 同時に「検索ベンチ用クエリ50件」を浅井と作り始める（実務の相談類型から）。

この3つは破壊的でなく、次の意思決定（橋を張る/用語を広げる/価値検証）に直結する。

---

## 7. 一枚要約
- **今日**: 語彙(554 canonical)＋書誌(6,524)の“ノード”がDBに乗った。
- **次**: それを**繋ぐ**(bib_terms)＝ALOの本丸「リンクが資産」の最初の一歩。
- **本当のゴール**: 判例/法令/文献/語彙のリンクで CaseBundle を組み、**実務の検索が良くなる**こと（Phase D/E）。
- **最大の論点**: 実DB(biblio) と 仕様(alo_edges/SKOS) のギャップをどう埋めるか＝owner/codex/花岡の合意。
