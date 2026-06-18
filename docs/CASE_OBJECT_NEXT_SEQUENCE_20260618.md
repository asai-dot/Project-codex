# 判例オブジェクト 次工程 統合シーケンス (CASE OBJECT NEXT SEQUENCE)

- date: 2026-06-18 JST
- author: Claude (Project-codex セッション)
- status: **read-only 計画統合 / HOLD維持**（DDL・DB write・canonical mint・alo_edges write・Box mutation を含まない）
- 前提資料: `CASE_META_MESH_STATUS_20260618.md`(本repo) / `DD-CASEID-001`(Box 2266457039407) / `31b_case_id_resolution_flow.md`(Box 2264249368602) / `SILVER_RESOLUTION_KICKOFF_PLAN_v0.1.1`(Box 2291346469605) / 同 GPT監査(Box 2291338874123)

> 目的: 散在する判例オブジェクト関連スレッドを **1本の順序付きロードマップ** に束ね、(a) どのレーンが何のgateで止まっているか、(b) 何を先にやると最大のレバレッジになるか、(c) 各stepのHOLD境界、を確定する。本書は**統合と順序付けのみ**で、新たな実装許可を与えるものではない。

---

## 0. 全体像 — 4レーンと現在地

判例オブジェクトは独立した4レーンが並走している。**設計はどれも進んでいるが、canonical確定が0**という同じ壁で揃って止まっている。

| レーン | 何をする | 現在地 | 止めているgate |
|---|---|---|---|
| **L-ID** 判例ID確定 | NII×D1×LIC×準司法を1 case_keyに名寄せ | DD-CASEID-001 candidate v0.1、机上検証done(NII∩D1一致12,661) | **owner_approval=pending / independent_audit=pending** |
| **L-SR** source-record精度 | LIC掲載位置B-tier→判例source-record候補 | SILVER v0.1.1、GPT監査`ADOPT_AS_PLAN` | Step3前must_fix消化済→**bounded候補生成までGO / DB/canonical HOLD** |
| **L-DL** D1判例取得 | 契約母数249,863の取得 | **取得≈192,885(77%)** ※下記訂正 | Phase0スイープ上限実測（残≈57k） |
| **L-RV** 人手レビュー | Tier B/C曖昧マッチの人手確定 | review枠は用意済、**decision=0 / accepted=0** | 人手判断が1件も流れていない |

### 重要訂正（全計画に未反映）: L-DL の取得率
DD-CASE reality check / WO-D1LAW-DL-001 の「取得67,966(27%)/残182k」は **2026-06-01のstale値**。6/5の大規模ingest(NEW +124,805)後の実態は：

> **取得 ≈192,885（≈77.2%）/ 残り ≈57,000（≈22.8%）**（二経路検証: ingest積上 68,080+124,805=192,885 / `acquired_hanrei_ids_20260605.txt` 1,928,850B÷10≈192,885）

→ Phase0/Phase1の工数見積りは**残量約1/3**を前提に引き直す。6/5 ingestが「浅井承認後のcanonical昇格」を経たかは要確認（RUNBOOK §2: canonical更新は承認後）。

---

## 1. 依存関係とクリティカルパス

```
                    [G1: DD-CASEID-001 ratify]  ←★最上流・オーナー判断
                              │ (canonical identity 体系を確定)
              ┌───────────────┼────────────────────────────┐
              ▼               ▼                            ▼
   [L-SR SILVER v0.1.1]  [L-RV 人手レビュー試走]      [L-DL 残57k取得計画]
   source-record候補生成   decision overlay 0→N         Phase0上限実測
              │               │                            │
              └──────┬────────┘                            │
                     ▼                                     │
        [G2: production-readiness gate]  ←別gate           │
        D1-LICをcase_observation candidateで受ける          │
                     │                                     │
                     ▼                                     ▼
        [canonical case 初回昇格(branch dry-run)]  ←★全green後のみ
```

- **クリティカルパスの起点は G1（DD-CASEID-001 ratify）**。canonical identity の体系（case_key/forum_code/identity_status）が確定しないと、L-SR/L-RV の成果を最終的に canonical case へ落とす受け皿が無い。
- ただし **L-SR と L-DL と L-RV は G1 と並走可能**（いずれも source-record / staging レベルで、canonical を作らないため）。G1を待たずに進められる。
- **G1自体は実装GOではない**（design accept のみ）。実際のDDL/backfillは G2 で別途判断。

---

## 2. 順序付きシーケンス（誰が・何を・どのgateまで）

| # | step | レーン | 主担当 | 成果物 | exit / gate境界 |
|---|---|---|---|---|---|
| **S1** | DD-CASEID-001 ratification packet 作成 | L-ID | Claude(本repo) | `DD-CASEID-001_ratification_readiness`(本PR同梱) | オーナーが accept/差戻し判断できる1枚に集約。**accept=design確定のみ、実装GOではない** |
| **S2** | DD-CASEID-001 ↔ DD-CASE-001(cases母型) reconcile | L-ID | Mac CC / Codex | 重複排除メモ | 母型と確定フローの担当範囲を確定 |
| **S3** | SILVER Step1-2.5（inventory/normalizer/authority snapshot/QA凍結） | L-SR | Codex | v0.1.1 §5 packet群 | no DB write。authority_snapshot + QA frame freeze 完了 |
| **S4** | SILVER Step3（bounded候補生成） | L-SR | Codex | `resolution_candidate_set` ほか | status=`machine_suggested_*`。no `reviewed=true` |
| **S5** | 人手レビュー試走（層化40-80件） | L-RV | 浅井/花岡 + reviewer | decision overlay 0→N | accepted を初めて非ゼロにする。Tier B/C のgold蓄積開始 |
| **S6** | L-DL Phase0上限実測（残57k前提） | L-DL | Antigravity(実機) | 21大項目ヒット数表＋エクスポート上限 | 残量再見積り。取得と確定は並走 |
| **S7** | G2 production-readiness gate 設計 | 横断 | Claude/Codex | 最小・可逆な初回昇格チェックリスト | D1-LICをcase_observation candidateで受ける設計のみ |
| **S8** | canonical 初回昇格（branch dry-run） | 横断 | — | branch-only load plan | **S1-S7全green + 独立監査 + オーナー承認後のみ** |

★ 本セッションで着手するのは **S1（本PRで作成）**。S2-S8 は順次。

---

## 3. なぜこの順序か（レバレッジ根拠）

1. **S1（G1 ratify）を最上流に置く理由**: 噛み合わせ設計（L-ID）は机上検証まで終わっているのに candidate のまま凍結されている。ここが解けないと、L-SR/L-RV がいくら候補を作っても canonical case へ着地する受け皿が確定しない。**最小の労力（オーナーの1判断）で最大の下流を解放する**。
2. **S5（人手レビュー試走）を早期に置く理由**: 真のスループット律速は「decision=0」。全1,648件をやる必要はなく、層化40-80件を実際に流せば、(a) decision overlayが0→Nに動き、(b) Tier B自動化のgoldが貯まり始め、(c) SILVER QAのfalse-positive率が実測値になる。**詰まりの実体を最小サンプルで割る**。
3. **L-SR を SILVER v0.1.1 に委譲する理由**: 既にGPT監査通過済の精緻な設計があり、再発明はムダ。本ロードマップは L-SR を**参照するだけ**で重複させない。
4. **L-DL を並走の独立トラックにする理由**: 残57kの取得は identity 確定と独立。先に訂正値で工数を引き直せば、過大見積り（182k前提）の解消だけで計画が現実化する。

---

## 4. HOLD境界（全step共通・厳守）

本シーケンスのどのstepも、以下を**してはならない**（既存全レポートの規律を継承）:

- production / staging DB write、DDL / migration
- canonical case 行の作成、`alo_edges` promotion
- `reviewed=true` backfill、claim_support eligibility
- MCP publication、vector / embedding serve
- 商用ソース本文の外部（GPT等）送信、source / Box mutation

許されるのは: **local read-only inventory / 設計packet作成 / bounded候補生成（authority snapshot + QA frame freeze後）/ 層化QAサンプル設計**まで。
**ratify(S1) や design accept は「設計確定」であって「実装GO」ではない。** 実装は G2 で別途審査。

---

## 5. 本セッションの増分（順次）

- [x] **CASE_META_MESH_STATUS**（噛み合わせ現況 + D1取得訂正） — PR #26
- [x] **CASE_OBJECT_NEXT_SEQUENCE**（本書・統合ロードマップ）
- [ ] **DD-CASEID-001 ratification readiness packet**（S1・次にコミット）
- [ ] G2 production-readiness gate チェックリスト案（S7・後続）

> 各成果物は repo内read-only設計文書として積む。Box DD / GPT監査ループ（to_gpt→from_gpt）への投入＝正式ratify経路への載せ替えは、オーナー判断で行う（本セッションからは一方的にBoxへ書かない）。
