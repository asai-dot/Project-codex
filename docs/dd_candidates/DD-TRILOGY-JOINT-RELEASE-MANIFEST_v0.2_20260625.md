# DD-TRILOGY-JOINT-RELEASE-MANIFEST v0.2 — leaf + 三部作 atomic acceptance（owner ratified）

> **id**: DD-TRILOGY-JOINT-RELEASE-MANIFEST / **version**: v0.2 / **supersedes**: v0.1（candidate）
> **lifecycle**: **accepted（owner 浅井 ratify 2026-06-25・atomic）**。両監査 PASS_WITH_NOTES（blocking なし）成立につき #1〜#4 を atomic accept。**設計のみ**（accepted≠deployed）。
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-25 JST
> **gate**: 実装ゲートは全 **HOLD**（DDL/DB/Box mutation/mint/OCR/embedding/production/promotion/claim-support）。
> **監査根拠**:
> - DDRECONCILE v0.3 → **DDRECONCILE_PASS_WITH_NOTES**（RESULT Box 2309127656929・source_file_id 2306876505486）
> - DDXMODAL v0.6 → **DDXMODAL_PASS_WITH_NOTES**（RESULT Box 2309127899046・source_file_id 2306877366042）
> - leaf DD-INDEP-LINEAGE-001 v0.1 → **DDINDEP_PASS_WITH_NOTES**（RESULT Box 2306834650821・既 accepted）
> **不変条件**: 各監査済み候補ファイルは**バイト不変**（pin の content_hash は監査されたバイトを指す）。再編集は新 version＋新 manifest version を要する（G_MANIFEST_LEAF_IMMUTABLE_IN_BUNDLE）。

---

## 0. 同梱物（bundle members）と content_hash（= 監査済みバイト・確定）
> content_hash = ファイルバイトの sha256（NFC・UTF-8）。RECONCILE v0.3 §6 の field-level canonicalization は artifact 内部 ID 算定の規約であり、本 manifest の DD 文書同定は文書バイト hash を採用する。**本表が pin crosswalk の正本**。

| # | dependency_id | version | content_hash (sha256) | acceptance_ref | accept |
|---|---|---|---|---|---|
| 1 | DD-INDEP-LINEAGE-001 | v0.1 | `a7856be147a3f45b19fafe04d8ad2044565f00d7572a93cd477e144101629b43` | RESULT 2306834650821（DDINDEP_PASS_WITH_NOTES） | ✅ accepted 2026-06-25 |
| 2 | DD-TRILOGY-RECONCILE-001 | v0.3 | `386266456b63d833c863cfb3b513fac2ba149e91d61465456d9e71afbe941edd` | RESULT 2309127656929（DDRECONCILE_PASS_WITH_NOTES） | ✅ accepted 2026-06-25 |
| 3 | DD-XMODAL-001 | v0.6 | `4aede823e57247416ca29d7b0f0563d022b0154481e25523f9f74d8d2f1392a6` | RESULT 2309127899046（DDXMODAL_PASS_WITH_NOTES） | ✅ accepted 2026-06-25 |
| 4 | DD-XDOC-001 | v0.9a（addendum） | `b95cb4c5a3f7f9575dd92045f8d093da9a4ba844ef54f0a78732eefc0d1c9a1e` | base v0.9 RESULT 2303550755480・addendum 統治（再 ratify 不要） | ✅ accepted（addendum）2026-06-25 |

参照（pin 先・本 bundle では改訂しない既存 accepted）:
| dependency_id | version | content_hash (sha256) | acceptance_ref |
|---|---|---|---|
| DD-XDOC-001（base） | v0.9 | `c61d119a4e65fbc3cb360bab04a8482a4c0fb3ed4e9236728afc4326f4f05ea7` | accepted 2026-06-24 / RESULT 2303550755480 |
| DD-LAYOUT-001 | v0.5 | `33079bf02d4fa6a602512cd8da88f073681f7159607b2f03981d21c20ee80876` | accepted 2026-06-19 |

## 1. ★pin crosswalk（プレースホルダ解決・確定値）
各 consumer 文書中の `content_hash:<joint manifest で確定>` / `（manifest で確定）` を、本表の §0 値で解決する（文書バイトは編集しない・解決値は本 manifest が保持）。
```text
RECONCILE v0.3 §7 dependency_pin:
  DD-INDEP-LINEAGE-001 v0.1  content_hash = a7856be147a3f45b19fafe04d8ad2044565f00d7572a93cd477e144101629b43
  DD-XMODAL-001 v0.6         content_hash = 4aede823e57247416ca29d7b0f0563d022b0154481e25523f9f74d8d2f1392a6
XMODAL v0.6 §1 leaf pin:
  DD-INDEP-LINEAGE-001 v0.1  content_hash = a7856be147a3f45b19fafe04d8ad2044565f00d7572a93cd477e144101629b43
XDOC v0.9a §2 indep_source_pin:
  DD-INDEP-LINEAGE-001 v0.1  content_hash = a7856be147a3f45b19fafe04d8ad2044565f00d7572a93cd477e144101629b43
```
- **G_MANIFEST_PIN_RESOLVED**：全 consumer の content_hash プレースホルダが §0 で解決済み（未解決なし）→ **PASS**。

## 2. 相互 pin マトリクス（非循環 DAG・確認済み）
```text
DD-INDEP-LINEAGE-001 v0.1     → (consumes) DD-LITID-001（asset 同定のみ）   # leaf・三部作に非依存（out-edge は LITID のみ）
DD-TRILOGY-RECONCILE-001 v0.3 → pin INDEP v0.1, LAYOUT v0.5, XMODAL v0.6, XDOC v0.9(+a), LITID, LITLINK
DD-XMODAL-001 v0.6            → pin INDEP v0.1, RECONCILE v0.3, LAYOUT v0.5, XDOC v0.9, LITID
DD-XDOC-001 v0.9a            → pin INDEP v0.1, RECONCILE v0.3
```
- **G_MANIFEST_ACYCLIC**：INDEP は in-edge のみ（三部作→INDEP）。INDEP を含む閉路なし → **PASS**（DDRECONCILE/DDXMODAL 両監査が DAG 化を確認）。

## 3. atomic acceptance（実施記録）
- bundle は all-or-nothing。#2/#3 が両 PASS_WITH_NOTES（blocking なし）・#1 既 accept・#4 addendum 統治 → **4点 atomic accept 成立**。
- 監査 notes（非blocking）はすべて既存設計に反映済み（新規修正ゼロ）:
  - RECONCILE: R1 は leaf へ正しく委譲・RECONCILE は pin/consume のみ／set·multiset·sequence registry は十分。
  - XMODAL: confirmed は leaf content_independent のみ／observation pipeline は票に数えない／leaf pin は id+version+hash+acceptance／unknown lineage を既定独立にしない。
- accept 後も **実装ゲートは HOLD**（accepted ≠ deployed）。

## 4. 受入試験（manifest health・全 PASS）
1. §0 の各 content_hash が実ファイルの sha256 と一致（監査済みバイト）。
2. §2 pin グラフに INDEP を含む閉路なし（DAG）。
3. §1 で全 consumer の content_hash プレースホルダが解決済み。
4. bundle メンバ version が最新（RECONCILE v0.3 / XMODAL v0.6 / XDOC v0.9a / INDEP v0.1）。
5. leaf #1 の acceptance_ref が DDINDEP_PASS_WITH_NOTES（RESULT 2306834650821）。

## 5. GO / HOLD / loop_state
- **GO（達成済み）**：leaf+三部作 atomic ratify・pin crosswalk 確定・非循環 DAG 確認。循環依存（XMODAL↔RECONCILE）解消。
- **次の設計 GO（owner 判断・別ゲート）**：DD-LITID-001 / DD-LITLINK-001 の version+content_hash+acceptance_ref を埋めて Phase1 dependency gate を緑化（RECONCILE §7 の TBD 解消）。
- **HOLD**：実装一切（DDL/DB/mint/Box mutation/OCR/embedding/production/promotion/claim-support）／既存 ID 一括再生成。
- loop_state = **accepted（v0.2・atomic ratify 2026-06-25・両 PASS_WITH_NOTES blocking なし）**。三部作整合ループは設計レベルで**閉鎖**。実装は各実装ゲートで個別 GO を要する。
