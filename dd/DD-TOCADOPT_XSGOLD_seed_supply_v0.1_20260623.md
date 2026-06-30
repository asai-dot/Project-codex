# DD-TOCADOPT/TOCATTACH ← cross-source gold seed 供給 v0.1（DD-LITID由来）

- 作成日: 2026-06-23
- 種別: **既存スレッドへの供給（合流）**。新アーキテクチャではない。
- 供給先: DD-TOCATTACH-001 v0.3（cross-source crosswalk 解禁条件）/ DD-TOCADOPT-001 v0.1（edition_identity gate）。
- 由来: DD-LITID cohort 突合（`artifacts/TOC_cross_source_gold_candidates_20260623.tsv`, 832ペア）。
- 前提: `dd/DD-LITID_TOC_RECONCILIATION_20260623.md`（M0撤回・既存設計帰属）。
- 監査拘束（不変）: candidate≠confirmed / 非循環 / read-only / production・embedding・DB write は HOLD。
- **監査結果**: `DDTOCADOPT_XSGOLD_PASS_WITH_NOTES`（result_file_id: 2303553397319, 2026-06-23）
  - must_fix: なし。
  - should_fix: θは reviewer≥2 Q1 adjudication 後に freeze。parent-qualified 照合の norm_title version / parser hash を必ず記録。
  - GO: self TOC read-only dry-run / θ較正サンプル設計 / 衝突厚め優先レビュー。
  - HOLD: 自動 crosswalk 本番解禁 / self TOC canonical 投入 / DB write / embedding。
- **確定数カウント（非循環監査 binding note）**:
  - `candidate_overlap_count` = 1,509（タイトル一致全件）
  - `high_priority_pair_count` = 832（self 側 ISBN+NDL 両保持）
  - `high_priority_bencom_distinct_count` = 810
  - `adjudicated_gold_count` = 0（独立裁定前）

---

## 0. なぜこの供給か（既存ゲートが「待っている」もの）

DD-TOCATTACH v0.3 監査は明言:
> "Keep automatic crosswalk limited to same-source swaps **until cross-source gold evidence exists**."
> "Treat title-only matches as review required." / different-source rebasing は review-first。

＝ **異源(cross-source)の自動 crosswalk は『cross-source gold』が出るまで解禁されない**。
本供給は、その **gold の候補（seed）と、それを gold へ昇格させる非循環の裁定方法**を提供する。
**設計（採用ルール・三層・granularity guard 等）は一切変更しない。** 入力（gold seed）だけを足す。

---

## 1. 供給する候補集合（832ペア）

| 属性 | 値 |
|---|---|
| ペア数 | 832（self_bib_id 832 distinct → bencom_bib_id 810 distinct） |
| 条件 | self(asai-bookshelf) と bencom のタイトル正規化**完全一致**、かつ **self側が ISBN+NDL 両保持** |
| provenance_origin | self=`self_scan` / bencom=`bencom_provider`（**異源**） |
| 衝突 | 18件の bencom が複数 self と一致（14件×2 + 4件×3 = 40行）＝ edition曖昧、要 disambiguation |
| 出力 | `artifacts/TOC_cross_source_gold_candidates_20260623.tsv`（read-only） |

**候補に過ぎない理由（gold ではない）**:
- タイトル正規化一致のみ＝ TOCATTACH の "title-only = review required" に該当。
- ISBN/NDL は **self側のみ**。bencom 側同定子は無い＝「この bencom 本は ISBN X の self 本と同一版」という**主張は未確認**。
- 18件の bencom（40行）で self→同一bencom 衝突＝別版が同一タイトルに化けている。

---

## 2. gold への昇格＝非循環の裁定方法（本供給の核）

候補を gold にするのは **2つのTOCそのものの一致度**。NDL/ISBN は候補生成側なので**裁定には使わない**（非循環）。

```text
入力: 各ペア (self_bib_id, bencom_bib_id)
  self TOC   = Box app/data/toc/isbn_<isbn>.json（≈777k corpus・未投入）
  bencom TOC = biblio.toc_nodes(book_id=bencom_bib_id)（DB既存552k）

照合（TOCATTACH準拠・parent-qualified, title-only禁止）:
  - norm_title(version記録) + parent scope + page近接 でノード対応
  - toc_agreement = 対応ノード率／ページ整合／章順一致 の合成

昇格規則:
  toc_agreement >= θ_high      → cross_source_gold（同一版を独立TOC2源が支持）
  toc_agreement <= θ_low       → different_edition（negative control＝別版検出。Q3 bucketへ）
  θ_low < agreement < θ_high   → abstain → human_review（18衝突bencom=40行 を優先）
  （θは本供給では未確定。較正は §4）
```

- **独立性（D0/Q1）**: self_scan と bencom_provider は別 provenance_origin。TOC一致は ISBN非依存の独立証拠。
  ∴ 「候補生成(NDL/title)」と「裁定(TOC一致)」が分離＝**非循環成立**。
- **negative control が出るのも価値**: different_edition は same_work_diff_edition 検出器（DD-TOCADOPT edition_identity の回帰素材）。

---

## 3. 既存ゲートへの接続（どこに刺さるか）

| 既存ゲート | 本供給の寄与 |
|---|---|
| TOCATTACH「cross-source gold が出るまで自動crosswalk禁止」 | **gold seed を供給**＝解禁の前提を満たしにいく |
| TOCADOPT `gate_edition_identity_phase0_regression`（別版26除外/偽陽性226通過） | cross_source_gold=positive、different_edition=negative の**ラベル付き回帰セット**を追加 |
| TOCADOPT `votes_by_provenance_origin` | self_scan を**独立 origin**として票に追加（重複再配信でない異源） |
| DD-LITID edition確定（NDL非依存の2本目証拠が必要） | TOC一致が **bencom→self の ISBN/NDL 貸与**を確証（810件規模） |

---

## 4. 較正計画（θ決定・本供給では未実行）

- 標本: 832から層化抽出（18衝突bencom=40行を厚く＋ random）。reviewer≥2、不一致は adjudication（Q1）。
- 指標: toc_agreement 分布、positive/negative 分離度、誤 gold 率の95%上側上限。
- θ_high は **誤 gold（false cross-source merge）上側 < 2%**（DD-LITID Q hard veto と整合）。
- 出力: θ_high/θ_low freeze 案 → TOCADOPT/TOCATTACH owner 裁定へ。

## 5. decision_requested（既存スレッド owner へ）
1. 832 を cross-source gold **候補**として TOCADOPT/TOCATTACH の gold lane に受け入れてよいか。
2. 裁定子を「self×bencom TOC一致（NDL非依存）」とする非循環方針でよいか。
3. self TOC(Box app/data/toc) を読む dry-run（read-only・DB write無）を許可するか。
4. θ較正の標本設計（18衝突bencom=40行厚め）でよいか。

## 6. HOLD（不変）
- 自動 cross-source crosswalk / rebasing の本番解禁（θ freeze＋owner裁定後の別gate）。
- self TOC の canonical(toc_nodes) 投入（N-2・別gate）。
- DB write / embedding / projection / API露出。
- 832 を確定リンク扱いすること（candidate のまま）。

## 付記: source / hash
- 候補TSV: `artifacts/TOC_cross_source_gold_candidates_20260623.tsv`（832行＋header）。
  - カラム（監査 binding note 対応 v2）: `self_bib_id / self_isbn / self_ndl / bencom_bib_id / bencom_self_count / edition_risk_flag / match_basis / snapshot_date / self_title`
  - `bencom_self_count`: そのbencom_bib_idに対応するself行数（1=clean, 2-3=collision）。
  - `edition_risk_flag`: bencom_self_count > 1 のとき 1（40行）、それ以外 0（792行）。
  - `match_basis`: "title_normalized_exact"（全行共通）。
  - `snapshot_date`: "2026-06-22"（全行共通）。
- 抽出SQL: self=asai-bookshelf(isbn≠∅ & ndl≠∅) × bencom title正規化一致。snapshot 2026-06-22。
- 全数値は集計/候補。原本・索引の外部搬出なし（external_egress=prohibited）。
