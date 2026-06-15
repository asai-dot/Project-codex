# PoC仕様: 「同定→積層」を501冊コホートで回す（thin→thick 検証 / v0.1 紙上設計）

- 作成: 2026-06-14 / Claude（リモートセッション・浅井さん指示）
- 親: `docs/2026-06-14_library_3source_data_reuse_reanalysis.md` §5.5–5.6（同定が利活用の律速・基本戦略「巨人の肩に乗る」）
- 評価軸: `docs/2026-06-14_ai_research_evaluation_design.md`（本PoCはC1網羅・C3反対線・C7重み付けの“素材の厚み”を検証）
- **governance: 読み取り＋dry-runのみ。本番DB（biblio/authority）への書込なし。** 産物は `eval/poc_thick_501/` に隔離。production projection は owner ratify＋お目付け役レビュー後。

---

## 0. 目的と成功条件

**目的**: 「薄い別レコードを本の同定で束ね、各ソースの属性を積層して分厚い書誌を作る」を、3サイト共通の高重なりコホート（501冊）で**本番に触れず**検証し、全冊展開の Go/No-Go を出す。

**成功条件（このPoCが“通った”と言える基準）** ― **owner合意済み 2026-06-15**:
1. **同定（非対称基準）** ― precision と recall を非対称に扱う:
   - **誤マージ（別の本を同一視）= 絶対0**。監査で1件でも出たら **No-Go＋同定ロジック改修**（毒が積層で増幅するため）。
   - **auto_accept precision ≥ 99%**。
   - **recall ≥ 90% で可**（取りこぼし＝同一本を別扱いは毒でない。human_review で回収）。
2. **積層効果** ― thick 化後の1冊あたり属性数が、単一ソース最良値より有意に増える（定量、§4）。
3. **整合の可視化** ― クロスソースの一致率と**不一致カタログ**が出る（厚さの裏でどこが食い違うか）。
4. **Go/No-Go** ― 全冊（次は pairwise の B4+LLB 1,551 等）へ広げる判断と、widening の precision 閾値案が出る。

---

## 0.5. 既存設計との整合【重要・2026-06-15 追記】

本PoCは**新規の同定設計ではない**。プロジェクトには既に owner作の正本がある:
- **正本設計**: `DD-LITID-001 v0.2`（biblio_item 3層・fingerprint・resolution_log。GPT監査 PASS_WITH_NOTES）。
- **実行計画**: `20260611_book_identity_lane_plan_v0.1.md`（B0〜B6）。
- **501の所在**: 既に生成済みの `identity_candidates.jsonl`（4,296組）の **weak候補2,354組のうち「B4+LB+LLB 501」**＝**lane plan の B2（TOC fingerprint）対象**そのもの。

→ **本PoC = lane plan B2 を「3源501サブセット」に限定して回す instantiation ＋ 既存計画が明示していない「積層(thin→thick)の効果測定」レイヤの追加**。同定の規律は下記の正本に従う（本書独自のゲート定義は破棄し、正本を引く）:

- **証拠階層 E1–E5 と独立証拠2つ要件**（自動confirmは独立証拠2つ）:
  E1 isbn13(0.95) / E2 NDL識別子(0.9) / E3 fingerprint(title+pub+year+**pages**)(0.85) / E4 **toc_fingerprint**(高一致+0.2・独立証拠) / E5 title+pub+year(pages欠損,0.6・単独はreview止まり)。
- **501はE5(0.6)単独＝review止まり**。confirmには **E4(TOC fingerprint)を独立証拠として加算**して2証拠にするのが本筋（弁コム・legallibはTOC100%保有で判別力が高い）。
- **ゲート（lane plan §3 を継承）**: gate_no_auto_merge_without_dual_evidence / gate_edition_family_not_merged（版違いマージ0）/ gate_serial_not_book_merge / gate_resolution_log_append_only / gate_isbn13_checkdigit / **gate_provenance_group_no_double_count**。

### 落とし穴: provenance group（同一供給元TOCの二重計上）
弁コムとlegal-libraryは**同じ出版社供給のTOCを再配信している可能性**があり（B4↔LLB重複は約46%＝2,052組）、両者のTOC一致は**独立観測ではない**ことがある。
- 同定では「TOC全文ほぼ同一」を `provenance_group` 同一とみなし、E4を**多数決に二重計上しない**。
- **本PoCの「積層」にも同じ警告が効く**: §3 の `genre_consensus`・クロスソース一致信頼度は、弁コム×legallib を**別ソースとして二重に数えてはいけない**。一致を信頼度に使う前に provenance_group を判定し、同一群は1票に畳む。

---

## 1. コホート定義（凍結）

- **母体**: `newsources_books_identity_dryrun` の overlap `B4+LB+LLB | title_publisher_year_exact = 501`（弁コム×LION BOLT×legal-library の3社共通）。
- **凍結**: 501冊を各ソースの primary key で manifest 化し sha256 固定（再現性）。
  - 弁コム `content_id` / LION BOLT `isbn`・`book_id` / legal-library `book_id`。
- **レイヤ追加**: 各冊に対し ISBN を解決（LION BOLT 実ISBN＋NDL書名突合/fingerprint で復元）し、**NDL書誌**と、可能なら **asai-bookshelf（所蔵）** も候補レイヤとして付す。
  - → 最大 5レイヤ（弁コム／LION BOLT／legallib／NDL／所蔵）が1冊に乗りうる。
- 産物: `eval/poc_thick_501/cohort_manifest.jsonl`（+ sha256）。

---

## 2. 同定（precision最優先・既存ゲート踏襲）

3社共通として拾われた501は**候補クラスタ**であって確定ではない。確定までを本PoCで検証する。

- **入力**: 1冊あたり各ソースのレコード＋候補ISBN。
- **手法**: 既存 fingerprint（title_norm＋publisher_norm＋pub_year[＋page_count]）を再利用。既存ゲートを必須適用:
  - `gate_no_auto_merge` / `gate_title_only_match_prohibited` / `gate_valid_isbn13_checkdigit`。
- **バケット**: `auto_accept` / `human_review` / `reject`。各クラスタに**マッチ根拠**を記録（一致したフィールド・confidence・basis）。
- **必ずログするエッジケース**（DDL-20260428-01「版を束ねない」厳守）:
  - 版違い（第1版/第2版）＝**別manifestation**として分離維持。
  - 分冊（上/下・I/II/III）／シリーズ巻号。
  - 同名異本・改題・合本。
- 産物: `identity_clusters.jsonl`（cluster_id・members[]・evidence・bucket・confidence）。

---

## 3. 積層（“厚く”する・dry-run projection）

確定クラスタごとに、**フィールド単位の provenance 付き**で thick 候補レコードを合成（**本番biblioには書かない**）。

| 群 | フィールド | 供給源（優先順） | 合成規則 |
|---|---|---|---|
| 識別 | cluster_id・ISBN(s)・各ソースid・ndl_bib_id | 全レイヤ | Work URIはmintしない（PoCはcluster_idで代用） |
| 分類 | `ndc10`・`ndlc` | NDL | そのまま。所蔵にも有れば一致確認 |
| 分類 | `genre_consensus`・`genre_by_source[]`・`genre_conflict` | LION BOLT genre[]／弁コム category・series／legallib 分野 | 正準軸へ寄せ多数決＋不一致フラグ |
| 構造 | `toc`（採用元）・`toc_nodes_by_source` | merge policy: manual>ndl>publisher>toc_pdf>legallib>openbd>bencom>... | 最優先ソースを採用、他は保持。採用元を記録 |
| 要約 | `abstract` | 弁コム | 有れば付す（無ければ空） |
| 品質 | `accuracy_rank`・`source_type`・`source_hash[]` | LION BOLT＋各ソース | 重み付け用に保持 |
| リンク | `cinii_url`・`calil_url`・`amazon_url`・`citation_links` | LION BOLT／弁コム | pointer保持（gatedは再配布しない） |

- **クロスソース一致 = 信頼度シグナル**: 同一フィールドを n ソースが裏取り → confidence に反映。
- 産物: `thick_records_dryrun.jsonl`（field毎に value＋source＋confidence）。

---

## 4. 指標（“効いた”の測り方）

1. **同定品質**: auto_accept率／human_review率／監査precision／推定mis-merge率（目標≈0）。
2. **厚み（before→after）**: 1冊の属性数 = before（単一ソース最良）vs after（積層）。コホート全体での各属性カバレッジ:
   - NDC/NDLC 取得率・genre 取得率・abstract 取得率・TOC 保有ソース数分布・外部リンク種別数。
3. **整合**: 2社以上が genre を持つ冊での**一致率**／NDC の整合／TOC ノード一致率（既往 73–78% の再現確認）。
4. **不一致カタログ**: genre・pub_year・page_count・著者表記の食い違いを列挙（厚さの裏のリスク＝同定/品質の検査対象）。
- 産物: `metrics_report.md`。

---

## 5. フェーズ計画

| Phase | 内容 | ゲート | 産物 |
|---|---|---|---|
| **P0** | コホート凍結（501のkey固定）＋3ソース＋NDL を read-only 取得 | **不要**（読取のみ） | cohort_manifest.jsonl(+sha256) |

> **P0 アクセス現実（2026-06-15 実査）**: 501の個別キーは **Mac ローカル `build/newsources_books_identity/20260611/identity_candidates.jsonl`**（basis=`title_publisher_year`、members が B4&LB&LLB を跨ぐ行＝501）にあり、**Box/Supabase からは読めない**（biblio には bencom 3,802＋蔵書のみ、LION BOLT/legallib 未投入）。
> → **凍結の実行は Mac ワーカー側**。リモート(本セッション)からの P0 成果物は「**選択述語＋manifest スキーマの runbook**」に限定する:
> - 選択述語: `identity_candidates.jsonl` で `basis ∈ {title+publisher+year}` かつ cluster members の source 集合 ⊇ {bengo4, lionbolt, legallib} の 501 行。
> - manifest 列: `cluster_tmp_id, bengo4_content_id, lionbolt_isbn|book_id, legallib_book_id, ndl_oai_id(解決後), title_norm, publisher_norm, pub_year` ＋ 生成 sha256。
> - 産物の置き場は §7 に従い `build/`/Box（GitHub には置かない）。
| **P1** | 同定クラスタリング（既存ゲート適用）→ バケット＋根拠 | 不要（dry-run） | identity_clusters.jsonl |
| **P2** | 人手監査 **層化~150**（human_review 全件 ＋ auto_accept から無作為~100）→ precision推定。**誤マージが1件でも出たら 501 全件 census へ自動拡大**（owner合意 2026-06-15）。rule of three: 誤り0なら誤マージ率上限 ~2% | owner時間 | identity_audit.csv |
| **P3** | 積層 dry-run projection ＋ 指標算出 | 不要（書込なし） | thick_records_dryrun.jsonl / metrics_report.md |
| **P4** | 報告＋Go/No-Go＋widening閾値案 | owner＋お目付け役 | poc_report.md |

> P0–P1・P3 は読取/dry-runゆえ**ゲート不要で即着手可**。本番biblio/authorityへの projection は P4 後の別承認。

---

## 6. 受け入れ・撤退条件

- **Go（全冊展開へ）**: 誤マージ=0（絶対）＆ auto_accept precision≥99% ＆ recall≥90% ＆ 厚み増が定量確認 ＆ 不一致が管理可能。
- **No-Go/要改修**: 誤マージが1件でも出る（→census拡大の上、同定ロジック改修へ差し戻し）／fingerprint が版・分冊を誤束ね／厚み増が乏しい。
- 次コホート候補（Go後）: pairwise B4+LLB 1,551 / B4+LB 174 / LB+LLB 128、さらに LB+所蔵 ISBN一致 1,932。

---

## 7. 未決事項
- 正準ジャンル軸（`genre_l2`）の確定（別タスク。本PoCは暫定対応表で可）。
- 版・分冊の「同一Work／別manifestation」境界の運用（authority設計と接続）。
- 監査サンプル数と precision 閾値の owner 合意値。
- 産物の置き場【確定・2026-06-15】: プロジェクト規約「コード=GitHub / ドキュメント=Box / 構造化データ=Supabase」に従い、**構造化産物（manifest/clusters/thick jsonl）は GitHub に置かない**。`build/book_identity/`（Mac→Box）配下に蓄積し、本リポジトリには**本仕様(doc)のみ**を置く。lane plan の `build/book_identity/IDENTITY_PROGRESS.md` 台帳に進捗追記。

---

## 付録: 依拠データ
- overlap 501 / pairwise 1,551等: `_inventory/summary.json`(2277187057925)
- TOC横断一致 73–78%: `_inventory/e2_results.json`(2278293571061)
- merge policy 優先順: bib_toc→toc_nodes schema差分(2278358764765)
- ライブ biblio 実測（2ソース・NDL projection実証）: 親doc §5.6
