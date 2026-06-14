# PoC仕様: 「同定→積層」を501冊コホートで回す（thin→thick 検証 / v0.1 紙上設計）

- 作成: 2026-06-14 / Claude（リモートセッション・浅井さん指示）
- 親: `docs/2026-06-14_library_3source_data_reuse_reanalysis.md` §5.5–5.6（同定が利活用の律速・基本戦略「巨人の肩に乗る」）
- 評価軸: `docs/2026-06-14_ai_research_evaluation_design.md`（本PoCはC1網羅・C3反対線・C7重み付けの“素材の厚み”を検証）
- **governance: 読み取り＋dry-runのみ。本番DB（biblio/authority）への書込なし。** 産物は `eval/poc_thick_501/` に隔離。production projection は owner ratify＋お目付け役レビュー後。

---

## 0. 目的と成功条件

**目的**: 「薄い別レコードを本の同定で束ね、各ソースの属性を積層して分厚い書誌を作る」を、3サイト共通の高重なりコホート（501冊）で**本番に触れず**検証し、全冊展開の Go/No-Go を出す。

**成功条件（このPoCが“通った”と言える基準）**:
1. **同定 precision** ― 監査サンプルで誤マージ ≈ 0、auto_accept クラスタの正解率 ≥ 98%（数値は P2 で確定・要 owner 合意）。
2. **積層効果** ― thick 化後の1冊あたり属性数が、単一ソース最良値より有意に増える（定量、§4）。
3. **整合の可視化** ― クロスソースの一致率と**不一致カタログ**が出る（厚さの裏でどこが食い違うか）。
4. **Go/No-Go** ― 全冊（次は pairwise の B4+LLB 1,551 等）へ広げる判断と、widening の precision 閾値案が出る。

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
| **P1** | 同定クラスタリング（既存ゲート適用）→ バケット＋根拠 | 不要（dry-run） | identity_clusters.jsonl |
| **P2** | 人手監査（全 human_review ＋ auto_accept から無作為50）→ precision推定 | owner時間 | identity_audit.csv |
| **P3** | 積層 dry-run projection ＋ 指標算出 | 不要（書込なし） | thick_records_dryrun.jsonl / metrics_report.md |
| **P4** | 報告＋Go/No-Go＋widening閾値案 | owner＋お目付け役 | poc_report.md |

> P0–P1・P3 は読取/dry-runゆえ**ゲート不要で即着手可**。本番biblio/authorityへの projection は P4 後の別承認。

---

## 6. 受け入れ・撤退条件

- **Go（全冊展開へ）**: precision≥閾値 ＆ mis-merge≈0 ＆ 厚み増が定量確認 ＆ 不一致が管理可能。
- **No-Go/要改修**: mis-merge が出る／fingerprint が版・分冊を誤束ね／厚み増が乏しい → 同定ロジック改修へ差し戻し。
- 次コホート候補（Go後）: pairwise B4+LLB 1,551 / B4+LB 174 / LB+LLB 128、さらに LB+所蔵 ISBN一致 1,932。

---

## 7. 未決事項
- 正準ジャンル軸（`genre_l2`）の確定（別タスク。本PoCは暫定対応表で可）。
- 版・分冊の「同一Work／別manifestation」境界の運用（authority設計と接続）。
- 監査サンプル数と precision 閾値の owner 合意値。
- 産物の置き場（`eval/poc_thick_501/` を Box正本にするか repo に置くか）。

---

## 付録: 依拠データ
- overlap 501 / pairwise 1,551等: `_inventory/summary.json`(2277187057925)
- TOC横断一致 73–78%: `_inventory/e2_results.json`(2278293571061)
- merge policy 優先順: bib_toc→toc_nodes schema差分(2278358764765)
- ライブ biblio 実測（2ソース・NDL projection実証）: 親doc §5.6
