# DD-TRILOGY-JOINT-RELEASE-MANIFEST v0.1 — leaf + 三部作 atomic acceptance bundle（相互 pin）candidate

> **id**: DD-TRILOGY-JOINT-RELEASE-MANIFEST / **version**: candidate v0.1
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-25 JST
> **gate**: 設計のみ candidate（acceptance bundle の定義）。DDL/DB/Box mutation/mint/OCR/embedding/production/promotion/claim-support は **HOLD**。
> **目的**: 独立性 lineage 正本（leaf）と三部作の改訂を **1つの atomic acceptance** に束ね、相互 pin（id+version+content_hash+acceptance_ref）を固定して循環参照なしに同時 ratify できる状態を作る。content_hash は本 manifest が単一の crosswalk（各 DD §7/pin の `<joint manifest で確定>` を本表で解決）。
> **依存方向（非循環）**: leaf（DD-INDEP-LINEAGE-001）が唯一の正本。RECONCILE/XMODAL/XDOC は leaf を一方向 consume。leaf は三部作に依存しない（DD-LITID asset 同定のみ参照）。

---

## 0. 同梱物（bundle members）と content_hash
> content_hash = ファイルバイトの sha256（NFC・UTF-8）。RECONCILE v0.3 §6 の field-level canonicalization は artifact 内部 ID 算定の規約であり、本 manifest の DD 文書同定は文書バイト hash を採用する。

| # | dependency_id | version | role | content_hash (sha256) | acceptance_ref |
|---|---|---|---|---|---|
| 1 | DD-INDEP-LINEAGE-001 | v0.1 | **leaf 正本（独立性 lineage）** | `a7856be147a3f45b19fafe04d8ad2044565f00d7572a93cd477e144101629b43` | accepted 2026-06-25 / RESULT 2306834650821（DDINDEP_PASS_WITH_NOTES） |
| 2 | DD-TRILOGY-RECONCILE-001 | v0.3 | 整合付録（R1 を leaf へ委譲） | `386266456b63d833c863cfb3b513fac2ba149e91d61465456d9e71afbe941edd` | candidate（DDRECONCILE 再監査待ち・本 bundle で同時） |
| 3 | DD-XMODAL-001 | v0.6 | confirmed（leaf 直 pin） | `4aede823e57247416ca29d7b0f0563d022b0154481e25523f9f74d8d2f1392a6` | candidate（DDXMODAL 再監査待ち・本 bundle で同時） |
| 4 | DD-XDOC-001 | v0.9a（addendum） | eligibility（leaf pin・base v0.9 不変） | `b95cb4c5a3f7f9575dd92045f8d093da9a4ba844ef54f0a78732eefc0d1c9a1e` | base v0.9 accepted 2026-06-24 / RESULT 2303550755480・addendum は再 ratify 不要 |

参照（pin 先・本 bundle では改訂しない既存 accepted）:
| dependency_id | version | content_hash (sha256) | acceptance_ref |
|---|---|---|---|
| DD-XDOC-001（base） | v0.9 | `c61d119a4e65fbc3cb360bab04a8482a4c0fb3ed4e9236728afc4326f4f05ea7` | accepted 2026-06-24 / RESULT 2303550755480 |
| DD-LAYOUT-001 | v0.5 | `33079bf02d4fa6a602512cd8da88f073681f7159607b2f03981d21c20ee80876` | accepted 2026-06-19 |

## 1. 相互 pin マトリクス（誰が誰を pin するか・一方向性の検証）
```text
DD-INDEP-LINEAGE-001 v0.1   → (consumes) DD-LITID-001（asset 同定のみ）        # leaf・三部作に非依存
DD-TRILOGY-RECONCILE-001 v0.3 → pin INDEP v0.1, LAYOUT v0.5, XMODAL v0.6, XDOC v0.9(+a), LITID, LITLINK
DD-XMODAL-001 v0.6          → pin INDEP v0.1（独立性正本）, RECONCILE v0.3（law/canonical 写像）, LAYOUT v0.5, XDOC v0.9, LITID
DD-XDOC-001 v0.9a           → pin INDEP v0.1（独立性正本）, RECONCILE v0.3
```
- **非循環条件（PASS 条件）**：INDEP への矢印は全て **INDEP へ向かう（in-edge のみ）**。INDEP からは三部作への out-edge が無い（LITID のみ）。→ leaf が source of truth、三部作が consumer の DAG が成立。
- **G_MANIFEST_ACYCLIC**：bundle 内 pin グラフに INDEP を含む閉路が無いこと。

## 2. atomic acceptance 規約
- bundle は **all-or-nothing**：#2/#3/#4 のいずれかが監査で MODIFY なら bundle 全体を再投函（部分 accept しない）。leaf #1 は既 accept で固定（変更時は新 version＝再 mint で bundle 版を上げる）。
- 各 consumer の `content_hash:<joint manifest で確定>` プレースホルダは**本 manifest §0 の値で解決**される。consumer 文書を再編集して hash が変われば、本 manifest を同時改訂（version up）する。
- **G_MANIFEST_PIN_RESOLVED**：bundle ratify 時点で全 consumer の content_hash が §0 と一致（未解決プレースホルダ残存は gate fail）。
- **G_MANIFEST_LEAF_IMMUTABLE_IN_BUNDLE**：bundle 内で leaf を編集しない（編集は新 leaf version＋新 bundle version）。

## 3. ratify 手順（owner・設計のみ）
1. RECONCILE v0.3 / XMODAL v0.6 を DDRECONCILE / DDXMODAL に投函（本 manifest を添付し相互 pin を提示）。
2. 両監査が PASS（または PASS_WITH_NOTES・blocking なし）なら、owner が本 manifest を ratify＝3点同時 accept。
3. XDOC は addendum 統治（base v0.9 不変・再 ratify 不要）として bundle に同梱。
4. accept 後も **実装ゲートは HOLD**（accepted ≠ deployed）。

## 4. 受入試験（manifest 自体の health check）
1. §0 の各 content_hash が実ファイルの sha256 と一致する。
2. §1 pin グラフに INDEP を含む閉路が無い（DAG・leaf は in-edge のみ）。
3. consumer 文書中の `content_hash` pin が §0 の値で解決可能（未解決プレースホルダなし＝ratify 時条件）。
4. bundle メンバの version が各 DD の最新 candidate（RECONCILE v0.3 / XMODAL v0.6 / XDOC v0.9a / INDEP v0.1）と一致。
5. leaf #1 の acceptance_ref が DDINDEP_PASS_WITH_NOTES（RESULT 2306834650821）を指す。

## 5. GO / HOLD / loop_state
- **GO**：RECONCILE v0.3・XMODAL v0.6 を再監査投函（本 manifest 添付）／両 PASS で owner が atomic ratify／XDOC addendum 同梱。
- **HOLD**：実装一切（DDL/DB/mint/Box mutation/OCR/embedding/production/promotion/claim-support）。
- loop_state = **bundle 起票（v0.1・相互 pin 固定・非循環 DAG 確認）→ DDRECONCILE/DDXMODAL 再監査 → atomic ratify**。
