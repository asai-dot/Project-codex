# DD-TRILOGY-JOINT-RELEASE-MANIFEST v0.3 — leaf + 三部作 + 入口 LITID 凍結・依存 pin crosswalk（owner ratified）

> **id**: DD-TRILOGY-JOINT-RELEASE-MANIFEST / **version**: v0.3 / **supersedes**: v0.2
> **lifecycle**: **accepted（owner 浅井 ratify・atomic 維持）**。v0.2（leaf+三部作 atomic accept）に、入口 DD **DD-LITID-001 v0.5 の凍結**と RECONCILE §7 依存 pin の解決を追加。**設計のみ**（accepted≠deployed）。
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-27 JST
> **gate**: 実装ゲートは全 **HOLD**（DDL/DB/Box mutation/mint/OCR/embedding/production/promotion/claim-support/serving/backfill）。
> **改訂理由（v0.2→v0.3）**: DD-LITID-001 v0.5（統合版）が **DDLITID_PASS_WITH_NOTES**（RESULT 2312578962778・blocking なし）で owner ratify。RECONCILE v0.3 §7 が「content_hash は joint manifest で確定」とした依存 pin のうち **DD-LITID-001 を本 manifest で解決**（残 DD-LITLINK-001 は別凍結待ち）。三部作・leaf の §0 は不変（byte-immutable）。

---

## 0. bundle members（v0.2 から不変・byte-immutable）
| # | dependency_id | version | content_hash (sha256) | acceptance_ref |
|---|---|---|---|---|
| 1 | DD-INDEP-LINEAGE-001 | v0.1 | `a7856be147a3f45b19fafe04d8ad2044565f00d7572a93cd477e144101629b43` | RESULT 2306834650821（DDINDEP_PASS_WITH_NOTES） |
| 2 | DD-TRILOGY-RECONCILE-001 | v0.3 | `386266456b63d833c863cfb3b513fac2ba149e91d61465456d9e71afbe941edd` | RESULT 2309127656929（DDRECONCILE_PASS_WITH_NOTES） |
| 3 | DD-XMODAL-001 | v0.6 | `4aede823e57247416ca29d7b0f0563d022b0154481e25523f9f74d8d2f1392a6` | RESULT 2309127899046（DDXMODAL_PASS_WITH_NOTES） |
| 4 | DD-XDOC-001 | v0.9a（addendum） | `b95cb4c5a3f7f9575dd92045f8d093da9a4ba844ef54f0a78732eefc0d1c9a1e` | base RESULT 2303550755480・addendum 統治 |

## 1. ★入口 DD 凍結（v0.3 追加）
| # | dependency_id | version | content_hash (sha256・accepted-state) | acceptance_ref | accept |
|---|---|---|---|---|---|
| 5 | **DD-LITID-001** | **v0.5（consolidated）** | `4b8f4a5751daf9067dfb6f9e4c42c2a058b9fe8c9a40dfb50ae22d4ed4553356` | **RESULT 2312578962778（DDLITID_PASS_WITH_NOTES）/ source 2312342128307** | ✅ accepted（owner ratify）2026-06-27 |
- content_hash は **ratify 後の accepted-state バイト**（lifecycle=accepted ヘッダ込み）。監査は source 2312342128307（audited draft `2f6ed66e1b…`）で行い、accepted notes をヘッダに反映後の確定バイトを pin する（leaf v0.1 と同型の凍結方式）。
- DD-LITID-001 v0.5 は v0.2-draft / ATTR / FP / PLAN-4route を supersede & absorb（4断片→1）。独立性は §0 の leaf #1 を一方向 consume（DDLITID note2・循環なし）。

## 2. ★RECONCILE v0.3 §7 依存 pin crosswalk（解決状況）
RECONCILE v0.3 §7 は「id+version+content_hash+acceptance_ref を全て埋める。空欄は Phase1 gate fail。content_hash は joint manifest で確定」と規定。本 manifest が crosswalk:
| dependency（RECONCILE §7） | version | content_hash | acceptance_ref | 状態 |
|---|---|---|---|---|
| DD-INDEP-LINEAGE-001 | v0.1 | a7856be1… | RESULT 2306834650821 | ✅ 解決（§0 #1） |
| DD-XMODAL-001 | v0.6 | 4aede823… | RESULT 2309127899046 | ✅ 解決（§0 #3） |
| DD-XDOC-001 | v0.9(+a) | b95cb4c5… / base c61d119a… | RESULT 2303550755480 | ✅ 解決（§0 #4） |
| DD-LAYOUT-001 | v0.5 | 33079bf0… | accepted 2026-06-19 | ✅ 解決 |
| **DD-LITID-001** | **v0.5** | **4b8f4a57…** | **RESULT 2312578962778** | ✅ **解決（v0.3 で確定）** |
| **DD-LITLINK-001** | **TBD** | **TBD** | **TBD** | 🔴 **未解決（別凍結待ち）** |
- **Phase1 dependency gate**：DD-LITLINK-001 の TBD が残るため**まだ FAIL**（緑化は LITLINK 凍結後）。LITID 行はこれで埋まった。

## 3. 非循環 DAG（v0.2 §2 ＋ LITID 追加・確認）
```text
DD-INDEP-LINEAGE-001 v0.1   → (consumes) DD-LITID-001（asset 同定のみ）    # leaf は LITID identity を参照
DD-LITID-001 v0.5           → pin INDEP v0.1（独立性正本・一方向 consume）  # 入口も leaf を consume
DD-TRILOGY-RECONCILE-001 v0.3 → pin INDEP, LAYOUT, XMODAL, XDOC, LITID v0.5, LITLINK(TBD)
DD-XMODAL-001 v0.6 / DD-XDOC-001 v0.9a → pin INDEP v0.1
```
- **G_MANIFEST_ACYCLIC**：INDEP は in-edge のみ（LITID/三部作→INDEP）。INDEP↔LITID は「leaf が LITID の asset identity を参照／LITID が leaf の独立性を consume」だが、**参照する側面が異なり**（identity vs 独立カウント）相互の定義循環を作らない（leaf の独立カウント定義は LITID に依存しない・LITID の identity 定義は leaf に依存しない）。→ 閉路なし。

## 4. accept 記録・受入試験（health）
1. §0/§1 の各 content_hash が実ファイル sha256 と一致。
2. §2 で LITID pin が解決・LITLINK が未解決として明示（silent な空欄なし）。
3. §3 pin グラフに定義循環なし。
4. DD-LITID-001 v0.5 の accept は DDLITID_PASS_WITH_NOTES（RESULT 2312578962778）に接地。
5. 全 accept は設計のみ（実装ゲート HOLD）。

## 5. GO / HOLD / loop_state
- **GO（達成済み）**：入口 DD-LITID-001 v0.5 凍結・RECONCILE §7 の LITID pin 解決・独立性を leaf へ binding（入口と三部作の独立カウント一致）。
- **次の GO（owner 判断・別ゲート）**：**DD-LITLINK-001 の凍結**（§9 で別 DD 維持確定・GPT 支持）→ RECONCILE §7 の最後の TBD を埋めて **Phase1 dependency gate 緑化**。
- **HOLD**：実装一切。
- loop_state = **accepted（v0.3・入口 LITID 凍結・依存 pin は LITLINK 残1）**。実データ投入前ゲートは「LITLINK 凍結→Phase1 緑化→各実装 GO」を残すのみ。
