# DD-LITID 書籍同定 フォワード・ロードマップ v0.3

- 作成日: 2026-06-20（v0.2 を改訂）
- 改訂理由: 監査 `ROADMAP_MODIFY_REQUIRED`（v0.2 RESULT, must_fix 10件）＋ v0.1 RESULT(PASS_WITH_NOTES) の
  評価ガバナンス要件を畳み込み。**v0.2 で消してしまった「評価・証拠ガバナンスWS」を復元し、NDLオフライン参照と分離する。**
- 上位設計: DD-LITID-PLAN v0.1 / DD-LITID-001 v0.2 / DD-LITID-FP / INGEST_SPEC v0.2。
- ゲート原則（不変）: 可逆=安価先行、不可逆=高価は shadow 実証＋独立再監査後。
  **本書は計画＋reversible artifact 準備のみ。production 実装/DDL/DB書込/backfill/promote/serving/embedding/外部公開は HOLD。**

## 0. 確定した現実と「未検証仮説」の分離

**確定（観測根拠あり）**
| 事実 | 根拠 |
|---|---|
| bib_records 実在は self/own(6,524)・bencom(3,802) のみ。LION BOLT/legallib 未投入 | snapshot 20260619 |
| self/own は ISBN↔NDL 厳密1:1・衝突0、`edition`7.6%/`volume`0%（版正誤は内部判定不能） | Phase 0 |
| 421=ISBN有NDL無（全件ISBN妥当、うち53件が2024+新刊）/ 1,101=ISBN無NDL無（全件 manual・ISBN無） | A2 |
| edition 値424: 版73% / 刷12%（印刷回次混入）/ 日付14% | A3 |
| 弁コム既存 1,737（high962/medium775）。ISBN provenance 不一致6件 | snapshot/Phase0 |
| Box に NDL フルダンプ既在: `ndl_all_records_001-161.csv`≈16.7GB ＋ `ndl_law_isbn.txt`116MB ＋ NDC別 | Box 観測 20260620 |

**未検証仮説（UNVERIFIED HYPOTHESIS・正解ラベル化禁止）**
- 「DB の `ndl_bib_id` 76.7% はダンプ由来」＝状況証拠のみ。**lineage（import log / 一致hash）検証まで前提化しない**（→ WS-R R4）。
- ダンプ CSV/txt の列スキーマ（ISBN/edition 列）＝未確認（→ WS-R R1）。

監査拘束（不変）: candidate≠confirmed / coverage≠correctness（dump hit率は候補回収指標で正誤の代替にしない）/
cohort外挿禁止 / medium775=existing_unconfirmed / 全 production HOLD。

## 1. クリティカルパス（v0.2→v0.3 修正）

runner は**消えていない**。**network access runner → offline processing/build contract に形を変えた**だけ。
さらに「runner が開く＝版が正しい」ではない（循環評価の罠）。真の二本立て:

```
P1 cohort-A較正: (R2 offline索引 + Q1/Q2 gold・証拠契約) → A1 → D1較正 → E個別gate
P2 bencom remediation: 証拠lineage契約 → B1/B2 → D1較正 → E個別gate
P3 source landing: C1/C2 field-profile → provisional cohort確定 → cohort別較正
```
- P3（LION/legallib 着地待ち）を理由に P1/P2 を止めない。
- offline build の残 load-bearing 条件（＝新しい技術ゲート、§6）:
  source manifest/完全性/encoding/delimiter/schema/checksum、snapshot date、record lineage、重複方針、
  ISBN正規化、16.7GB ストリーム環境、再現可能な索引build、reject/error レポート、
  取扱権利/egress境界/保管先/cleanup。

## 2. ワークストリーム（WS名衝突を解消・評価レーン復元）

### WS-R Offline NDL Reference Build（旧 v0.2 WS-F を改名）
- R1 **manifest/schema/rights 検証**: 161 CSV＋`ndl_law_isbn.txt` の列（ISBN/bibid/title/publisher/pub_year/**edition**/NDC）、
  件数、encoding/delimiter、snapshot date、欠番/破損、checksum を read-only 検証。
- R2 **再生成可能な lookup artifact**（**derived・discardable。hub/canonical ではない**）。
  各 hit に `source_file, source_row_or_record_key, source_snapshot_id, raw_digest, parser_version, normalizer_version, index_build_id` を保持。
- R3 coverage/freshness/error レポート（cohort-A ISBN の被覆、`ndl_law_isbn.txt` 寄与、reject/重複）。
- R4 **lineage 検証タスク**: 既存 `ndl_bib_id` がダンプ由来かを import log / hash 照合で確認（§0仮説の検証）。

### WS-Q Evaluation & Evidence Governance（v0.1必須・v0.2で欠落→復元）
- Q1 **非循環 gold / adjudication protocol**: NDL を候補生成と正解の両方に使わない。
  奥付画像/OCR・現物・出版社一次情報を独立 adjudication evidence に。
  adjudication record = `reviewer, basis, source_hash, decision_type, decision, confidence, decided_at`。
- Q2 **証拠 family lineage & collapse**: `origin_family, same_origin_collapse_key, capture_url, content_hash, parser_lineage`。
  同一供給元の転載は1 family に collapse。
- Q3 **層化サンプリング & confusion buckets**: false merge / false split / same work different edition / printing-only / metadata noise。
- Q4 **最小n / 信頼区間 / hard veto / abstention**: 0件観測でも上側信頼限界で判定（rule-of-three: 91件で95%上限≈3.3%）。
- Q5 **ゲート matrix**: `route_cohort × decision_type(work | edition_manifestation | printing | holding→edition) × evidence_profile`。

### WS-A 自所(cohort-A) 版同定
- A0 ✅ Phase 0 QA / A2 ✅ 穴分類 / A3 ✅ edition 棚卸し（raw非破壊）
- A1 **二層評価に分割**:
  - candidate retrieval quality（R2 が正しい候補を回収したか）
  - resolution quality（NDLと独立な奥付/現物/出版社で work/edition/printing を裁定したか）
- A2 後段: 421 を R2 照合（**2024+ 53件は鮮度抜けとして `no_hit_after_valid_isbn` から分離**）。
  no-hit/source-trust bucket（valid-isbn no-hit / low-confidence-isbn / source-untrusted）を維持。
- A3 後段: 正規化は **raw-preserving**。`edition_statement / printing_no / date_role` に分解するが**正規化だけで同一版と決めない**。
  **版 vs 刷の分離が must（刷12%混入＝誤割りの実害源）**。
- A4 provenance 6件の原本確認 → **Q1 gold seed の最優先**。

### WS-B 弁コム no-ISBN remediation（quarantine lane）
- medium 775 = `existing_unconfirmed` / `lane=bencom_retro_remediation` / training・serving・count・promote 不適格。
- 「TOC/fingerprint=第2独立証拠」は**signal と source independence を分離**（Q2 で family collapse 後に独立証拠が立つ場合のみ confirm 候補）。
- **B1 は ISBN索引(R2)では解けない**。no-ISBN 用 candidate generator（title/publisher/author/year/TOC の blocking）を別途明示。
- B2 high 962 も層化抜き取りで systematic FP を確認。

### WS-C 未投入取り込み（並走・provisional）
- C1 LION BOLT=cohort-A' / C2 legallib=cohort-B。field-profile 完了まで **provisional label**。
- source名でなく実メタ形状（resource type/ISBN/edition/TOC/rights/route-local-id）で cohort 確定。記事混在は record 単位で DD-PERIODICAL へ route。

### WS-D NDLマッチング基盤（二段分割）
- D0 evidence/lineage/status/abstention 契約（A1前から設計可）: candidate/confirmed/rejected/superseded、family collapse、abstain/manual-review、source snapshot、decision version。
- D1 blocking/weight/threshold 較正（A1/B1 実測後）。**R2索引は L1-derived であって hub ではない**（§3）。

### WS-E promote — **HOLD**（Q5 matrix の個別 gate）
- 単一スイッチにしない。cohort×decision_type×evidence_profile 別。confirmed は versioned evidence を持ち、再評価は supersede event（silent mutation 禁止）。

### WS-X Runner & Observability（小 enabling lane）
- offline build runner と、補完用ライブAPI runner を共通 interface 化。raw response/manifest の append-only、rate/retry/error taxonomy、no-write check、(a)Mac→(b)env 移行条件。

## 3. NDL データの層分離（F2索引を hub にしない）

```
L0  NDL dump snapshot + manifest + hashes          （原本・不変）
L1  derived offline blocking/index artifact         （discardable / rebuildable = R2）
L2  assertion: "NDL record says X" + source row pointer
Resolution: ALO identity/edition decision + evidence bundle + adjudication（Q1）
Canonical hub: Resolution gate 通過後のみ（WS-E）
```

## 4. 直近スプリント（GO範囲＝read-only / reversible のみ）

**GO（即時）**
1. R1: ダンプの inventory/manifest/hash/schema/encoding/件数/snapshot/ISBN・edition列/欠番・破損の read-only 検証。
2. R3先取り: `ndl_law_isbn.txt` の内部 read-only 被覆測定（cohort-A ISBN）。
3. Mac ローカルでの小規模 streaming smoke test。
4. A2属性集計（済）/ A3 raw棚卸し（済）/ A4原本確認 / B サンプル・lineage 設計 / 26件(ISBN無NDL有)由来監査。
5. Q1/Q2/D0 の契約・gold schema・confusion bucket 設計。

**CONDITIONAL GO（reversible artifact-only build）— R2 全量索引は次を全て満たす時のみ**
1. owner が内部利用・派生索引の保管範囲を確認。
2. Mac/local trusted を第一選択、外部 data env へ搬出しない。
3. source manifest/hash/parser version/build manifest を保持。
4. canonical/DB本体に write せず、再生成可能な isolated artifact に限定。
5. reject/error/duplicate レポートを同時生成。
6. source file を変更しない。

**HOLD**
- R2 を hub/canonical truth 扱い / 既存 `ndl_bib_id` の verified 一括昇格 / A1 結果だけで閾値 freeze /
  WS-D production matcher / DB write / backfill / promote / serving / embedding / 外部公開 / 取扱条件確認前の外部搬出。

## 5. 閾値設計（gate contract）

各 metric に: `route_cohort, decision_type, evidence_profile, bucket, denominator, minimum_n,
point_estimate, confidence_interval_or_upper_bound, hard_veto|soft_target, abstention_rate,
manual_review_queue_rate_and_capacity, pass|hold rule`。
- **false-confirmation は hard veto**（平均 precision に埋めない・上側信頼限界で判定）。
- coverage / dump hit率は候補回収指標。identity/edition correctness の代替にしない。
- 監視追加: source-untrusted率 / family collapse後の独立証拠数 / work-merge・edition-merge・split 別集計 / abstention backlog / snapshot変更後の再評価率。

## 6. runner 決定（v0.2 §6 修正）

- network API 律速は解消。**新ゲートは offline reference build contract**（§1 条件群）。
- 第1選択 **(a) Mac/local** ストリーム処理。(c) cache先行は smoke test 限定（coverage bias → precision/閾値/promote に使わない）。(b) ネット env は量・再現要件が出たら昇格。ライブAPIは欠落/鮮度補完に限定。

## 7. スコープ・権利

- 記事/論文層は DD-PERIODICAL へ typed interface（book/article/issue, work relation, source pointer）で接続。著者同定は DD-LITAUTHOR へ委譲（author string/authority id は evidence として保持）。
- **権利（v0.2 §7 修正）**: 「権利問題が消える」は**撤回**。API rate は消えるが、取得済みダンプの**利用条件・内部派生物の保管・外部 egress 可否は残る → owner gate**。本線は read-only 参照と内部 isolated artifact に限定、外部公開しない。

## 8. v0.2 監査 must_fix 10件 ⇄ 反映

| # | must_fix | 反映 |
|---|---|---|
|1|runner解消→offline build contract|§1, §6|
|2|権利問題撤回・owner gate|§7|
|3|NDL参照(WS-R)と評価ガバナンス(WS-Q)を分離|§2|
|4|F2=derived artifact, hub分離+lineage|§2 R2, §3|
|5|76.7%を仮説降格+lineage検証|§0, WS-R R4|
|6|非循環gold/adjudication+confusion buckets|WS-Q Q1/Q3|
|7|A1 sample strata+minimum n+CI|WS-Q Q4, WS-A A1|
|8|WS-B signal/independence分離+no-ISBN generator|WS-B|
|9|gate を cohort×decision_type×evidence_profile|WS-Q Q5, WS-E|
|10|artifact-only build GO と production HOLD 分離|§4|

## 9. 未確定・リスク
- ダンプ列スキーマ未確認（R1 最優先）/ 鮮度（2024+ 新刊抜け、A2で53件実証）/ 16.7GB 処理環境 /
  LION BOLT・legallib 実メタ未確認 / 独立性判定が origin 単独で足りるか（content_hash 併用）。
