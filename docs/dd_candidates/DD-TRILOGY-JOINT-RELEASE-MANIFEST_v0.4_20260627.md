# DD-TRILOGY-JOINT-RELEASE-MANIFEST v0.4 — leaf + 三部作 + 入口 DD（LITID+LITLINK）完備・Phase1 dependency gate 緑化

> **id**: DD-TRILOGY-JOINT-RELEASE-MANIFEST / **version**: v0.4 / **supersedes**: v0.3
> **lifecycle**: **accepted（owner 浅井 ratify・atomic 維持）**。v0.3（leaf+三部作+LITID 凍結）に **DD-LITLINK-001 v0.1 の凍結**を追加し、RECONCILE v0.3 §7 の依存 pin を**全解決**。**設計のみ**（accepted≠deployed）。
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-27 JST
> **gate**: 実装ゲートは全 **HOLD**（DDL/DB/Box mutation/mint/OCR/embedding/production/promotion/claim-support/serving/backfill/edge promotion/alo_edges export）。
> **改訂理由（v0.3→v0.4）**: DD-LITLINK-001 v0.1 が **DDLITLINK_PASS_WITH_NOTES**（RESULT 2315090716649・blocking なし）で owner ratify。RECONCILE §7 の最後の TBD（DD-LITLINK-001）を本 manifest で解決 → **Phase1 dependency gate 緑化条件を充足**。入口 DD（identity=LITID / link=LITLINK）完備。

---

## 0. bundle members（v0.3 から不変・byte-immutable）
| # | dependency_id | version | content_hash (sha256) | acceptance_ref |
|---|---|---|---|---|
| 1 | DD-INDEP-LINEAGE-001 | v0.1 | `a7856be147a3f45b19fafe04d8ad2044565f00d7572a93cd477e144101629b43` | RESULT 2306834650821（DDINDEP_PASS_WITH_NOTES） |
| 2 | DD-TRILOGY-RECONCILE-001 | v0.3 | `386266456b63d833c863cfb3b513fac2ba149e91d61465456d9e71afbe941edd` | RESULT 2309127656929（DDRECONCILE_PASS_WITH_NOTES） |
| 3 | DD-XMODAL-001 | v0.6 | `4aede823e57247416ca29d7b0f0563d022b0154481e25523f9f74d8d2f1392a6` | RESULT 2309127899046（DDXMODAL_PASS_WITH_NOTES） |
| 4 | DD-XDOC-001 | v0.9a（addendum） | `b95cb4c5a3f7f9575dd92045f8d093da9a4ba844ef54f0a78732eefc0d1c9a1e` | base RESULT 2303550755480・addendum 統治 |
| 5 | DD-LITID-001 | v0.5（consolidated） | `4b8f4a5751daf9067dfb6f9e4c42c2a058b9fe8c9a40dfb50ae22d4ed4553356` | RESULT 2312578962778（DDLITID_PASS_WITH_NOTES） |

## 1. ★入口 link DD 凍結（v0.4 追加）
| # | dependency_id | version | content_hash (sha256・accepted-state) | acceptance_ref | accept |
|---|---|---|---|---|---|
| 6 | **DD-LITLINK-001** | **v0.1（freeze）** | `fb64b58e441cb9ebd9916ef41d288a104b2714bbf0f36f3d2a49a4feba04d812` | **RESULT 2315090716649（DDLITLINK_PASS_WITH_NOTES）/ source 2312912301080** | ✅ accepted（owner ratify）2026-06-27 |
- content_hash は ratify 後の accepted-state バイト（lifecycle=accepted ヘッダ込み）。監査は source 2312912301080（audited `4bf9cf767f…`）で実施・notes 反映後を pin（leaf/LITID と同型）。
- DD-LITLINK-001 v0.1 は identity を LITID v0.5（#5）へ委譲、独立カウントを INDEP leaf（#1）へ binding（DDLITLINK note・循環なし）。

## 2. ★RECONCILE v0.3 §7 依存 pin crosswalk（**全解決・Phase1 gate 緑化**）
| dependency（RECONCILE §7） | version | content_hash | acceptance_ref | 状態 |
|---|---|---|---|---|
| DD-INDEP-LINEAGE-001 | v0.1 | a7856be1… | RESULT 2306834650821 | ✅ |
| DD-XMODAL-001 | v0.6 | 4aede823… | RESULT 2309127899046 | ✅ |
| DD-XDOC-001 | v0.9(+a) | b95cb4c5… / base c61d119a… | RESULT 2303550755480 | ✅ |
| DD-LAYOUT-001 | v0.5 | 33079bf0… | accepted 2026-06-19 | ✅ |
| DD-LITID-001 | v0.5 | 4b8f4a57… | RESULT 2312578962778 | ✅ |
| **DD-LITLINK-001** | **v0.1** | **fb64b58e…** | **RESULT 2315090716649** | ✅ **解決（v0.4 で確定）** |
- **Phase1 dependency gate**：RECONCILE §7 の全 dependency が id+version+content_hash+acceptance_ref で埋まった（空欄ゼロ）→ **G_RECONCILE_DEP_PIN_EXACT を充足・緑化条件達成**。

## 3. 非循環 DAG（入口 DD 完備・確認）
```text
DD-INDEP-LINEAGE-001 v0.1   → (consumes) DD-LITID-001（asset 同定のみ）
DD-LITID-001 v0.5           → pin INDEP v0.1（独立性正本）
DD-LITLINK-001 v0.1         → pin INDEP v0.1（独立性正本）, LITID v0.5（identity 委譲）
DD-TRILOGY-RECONCILE-001 v0.3 → pin INDEP, LAYOUT, XMODAL, XDOC, LITID v0.5, LITLINK v0.1
DD-XMODAL-001 v0.6 / DD-XDOC-001 v0.9a → pin INDEP v0.1
```
- **G_MANIFEST_ACYCLIC**：INDEP は in-edge のみ。LITLINK→LITID は identity 委譲（一方向）。INDEP↔LITID は参照側面が異なり定義循環を作らない。→ 閉路なし。

## 4. 受入試験（health・全 PASS）
1. §0/§1 の各 content_hash が実ファイル sha256 と一致。
2. §2 で RECONCILE §7 の全 pin が解決（TBD ゼロ）。
3. §3 pin グラフに定義循環なし。
4. 入口 DD: identity=LITID v0.5 / link=LITLINK v0.1 が共に accepted・leaf を consume。
5. 全 accept は設計のみ（実装ゲート HOLD）。

## 5. GO / HOLD / loop_state
- **GO（達成済み）**：入口 DD（LITID identity + LITLINK link）完備・RECONCILE §7 全 pin 解決・**Phase1 dependency gate 緑化条件達成**・独立性は入口〜三部作で leaf に一本化（反こたつ記事が入口から confirmed まで一貫）。
- **次の GO（owner 判断・実装ゲート）**：Phase1 着手（背骨確定→4ルート raw 投入 append-only→正規化/fingerprint→NDL 突合 shadow…）。**ただし各実装ステップは個別ゲートで GO**（DDL/DB/mint/OCR/embedding/promotion/serving/edge export は依然 HOLD）。
- **HOLD**：実装一切。
- loop_state = **accepted（v0.4・入口 DD 完備・Phase1 dependency gate 緑化）**。実データ投入前の**設計ゲートは全閉鎖**。残るは実装ゲートでの個別 GO のみ（accepted≠deployed）。
