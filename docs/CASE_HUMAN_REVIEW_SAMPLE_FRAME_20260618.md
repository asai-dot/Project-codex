# 人手レビュー 層化サンプル設計 — decision overlay を 0→N にする初回バッチ (L-RV / S5)

- date: 2026-06-18 JST
- author: Claude (Project-codex セッション)
- status: **read-only サンプル設計 / HOLD維持**。本書はレビュー**枠の設計**であり、accept/reject の判断（人手の法的判断）も canonical 反映も含まない。商用本文は同梱しない（件数・strata・キーのみ）。
- 位置づけ: `CASE_OBJECT_NEXT_SEQUENCE_20260618.md` の **S5**。SILVER v0.1.1 §7 のQA原則（frame freeze / negative control / 層化 / 再現性）を、**既に行が存在し decision=0 のレビューキュー**に接続する。
- 目的: 真の律速＝「decision overlay 0 / accepted edge 0」を、**最小バッチ（~80件）の実レビュー**で 0→N に動かし、(a)false-positive率の実測、(b)Tier B自動化の gold 蓄積、(c)SILVER QAの校正、を同時に得る。

> 全件（1,648＋281＋1,006）をやる必要はない。**层化した数十件**を実際に流せば、詰まりの実体が初めて数値になる。

---

## 1. 対象キュー（実在・decision=0 の3レーン）

| キュー | 総数 | 内訳（実数） | claim scope | decision語彙 |
|---|---|---|---|---|
| **Q1 法令参照**(D1KOS↔OPAC/CiNii) | strong **281** | P1 77 / P2 135 / P3 69 | `opac_cinii_statute_ref_supports_d1kos_context_only`（同一性主張ではない＝低リスク） | pending_review / accept_d1kos_statute_ref_context / reject_not_same_statute_context / needs_more_evidence / defer |
| **Q2 判例引用**(OPAC/CiNii case citation) | seed 5,010 / worksheet **1,648**(9 batch) | P1 3,569 / P2 1,427 / P3 8 / HOLD 6 | 判例引用 source-record（judgment-level・高価値） | accept/reject/needs_more/defer（同型） |
| **Q3 D1-LIC 未解決** | **1,006** | page-absent 725 / alt-citation 227 / not-in-corpus 54 | LIC source-record掲載位置 | accept/reject/needs_more/defer |

---

## 2. パイロット選定 — どれを最初に流すか

**推奨: Q1(法令参照) P1 77件を第一バッチにする。** 理由：

1. **最小で完結**（281のうちP1 77、しかも top-root-aligned で最高信頼）。100%レビューが現実的。
2. **claim scope が最も低リスク**（「D1KOS文脈への支持証拠」であって法令同一性主張ではない）→ 誤acceptの被害が限定的。レビュー判断の練習に最適。
3. **risk flag が既に付与済**（cross_root / multi_law_token / suffix / provisional_kos）→ 層化の軸がそのまま使える。
4. decision overlay 契約・edge preview 契約が既に作られており、**0→N を動かす配管が出来ている**（accepted decisionが入れば edge preview が動く）。

→ Q1で「decision overlay 0→N」と「レビュー手順の確立」を達成してから、Q2(judgment-level・高価値) のbatch-1へ展開する。

---

## 3. 第一バッチ 層化サンプル枠（Q1 法令参照, frozen）

`qa_sample_frame_version = caserev_q1_v0_20260618` / `sample_seed = 20260618` / **rule tuning前に凍結**。

| stratum | 母数 | 抽出 | 狙い（何を検出するか） |
|---|---|---|---|
| S-A P1 top-root-aligned | 77 | **77（100%）** | 最高信頼の精度上限。ここが汚いと全体が崩れる |
| S-B cross_root（article_side一致のみ） | 181(P2/P3) | 10 | 分類文脈の過剰接続（taxonomy_root≠law）の誤りやすさ |
| S-C multiple_law_tokens | 5 | 5（全件） | 複数法令名混在（例「(民訴)刑訴47条」）のパース誤り |
| S-D parsed_law_suffix_of_longer | 1 | 1（全件） | suffix寄せ（金商法→商法）誤り |
| S-E provisional_kos_node | 244 | 10 | 暫定KOSノード接続の妥当性 |
| **S-NEG negative control** | （人工） | 8 | **絶対マッチ不可の組**を混ぜ、normalizer過剰検出を検出 |
| **合計** | — | **約111件**（実質コア77＋拡張） | — |

- negative control（S-NEG）は、誌名/号/法令を意図的にズラした「正解=reject」を8件混入。これに accept が出たら normalizer か基準にバグ。
- 各行に `expected_manual_check`（何を見れば判定できるか）を1行付す。raw本文は出さず、正規化キー＋構造ラベルのみ。

---

## 4. レビュー手順（reviewer向け・1件あたり）

```
1. 正規化キー（法令名 / 条 / D1KOSノード / article_side_root）を見る
2. 「この記事が参照する法令表現は、このD1KOS分類文脈の支持証拠か？」を判定
   - YES → accept_d1kos_statute_ref_context
   - NO  → reject_not_same_statute_context（理由コード必須）
   - 判断材料不足 → needs_more_evidence
   - 後回し → defer
3. P2/P3・cross_root・複数法令名・suffix・lower-rank の accept には review_note 必須
   （validator hardening: non-pending decision に decision_actor 必須）
4. 結果は decision overlay input（merged_review_queue）へ。canonical反映しない
```

---

## 5. 完了基準と、そこから取れる数値

第一バッチ done の条件：
- S-A 77件 + 拡張 + negative control = 全行に non-pending decision。
- negative control 8件が全て reject（=過剰検出なし）を確認。

得られる数値（初めて非ゼロになる）：
- **decision overlay rows > 0**（現在0）
- **accepted edge preview rows > 0**（現在0、accept分から生成）
- **stratum別 false-positive率**（特に cross_root / provisional_kos の機械accept可否を判定）
- → これが SILVER の Tier B「初回人手→gold蓄積後に限定自動」の **gold 第一陣**になる。

---

## 6. 第二バッチ以降（展開）

| 順 | 対象 | 抽出方針 |
|---|---|---|
| 2 | Q2 判例引用 P1 worksheet batch-1 | 9バッチの1本（≈183行）から層化40件。judgment-levelで高価値。collision group 3を必ず含める |
| 3 | Q3 D1-LIC alt-citation 227 | 同一事件番号・別引用の名寄せ。15件層化。page-absent 725は号/頁index構築後 |
| — | Q3 not-in-corpus 54 | corpus外＝取得対象。L-DL（取得）側へ回す |

各バッチで `qa_sample_frame_version` を発番し凍結。rule改訂は同一frameで前後比較。

---

## 7. HOLD（本サンプルでも維持）

- accept されても **canonical case / 法令正本 / canonical bib への反映なし**（claim scopeは support context のみ）。
- `alo_edges` 本反映・`reviewed=true` backfill・claim_support・MCP serve なし。
- candidate shell への INSERT は accept基準とvalidatorが固まってから別工程（D1KOS報告 §Next と整合）。
- 商用本文の外部送信なし。

---

## 8. 次手

- 本枠（caserev_q1_v0）で **Q1 P1 77＋negative control 8** の reviewer packet を生成（件数・キー・expected_checkのみ）。
- reviewer（浅井／花岡＋担当）が第一バッチを判定 → decision overlay 0→N。
- 結果の stratum別 false-positive を SILVER QA と DD-CASEID Tier B 基準にフィードバック。
