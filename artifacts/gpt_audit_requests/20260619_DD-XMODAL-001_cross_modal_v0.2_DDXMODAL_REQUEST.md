---
request_id: DD-XMODAL-001-v0.2-20260619
topic: cross-modal triangulation & 生きたコーパス（独立3軸＝視覚×テキスト×外部法律体系）candidate v0.2 の独立意味監査
gate: DDXMODAL
status: queued
result_expected_filename: 20260619_DD-XMODAL-001_cross_modal_v0.2_DDXMODAL_RESULT.md
target_mode: inline_embedded
source_hash: sha256:3318f3bb071199d57c6175e8f6be2e0a27138001052e374fdc360bf5068e13dc
review_scope:
  include:
    - ★v0.2 の核：第3独立軸を「外部の法律体系(D)」に置換した是正の妥当性。印刷TOC構造はテキスト派生で第3独立軸にならない、という独立性分析は正しいか
    - 「V+T だけの一致は self-consistency で検証でない(同根)」「D が絡む一致のみ検証」という G_XMODAL_EXTERNAL_AXIS の論理
    - 「既存(引用)／白地(novelty)」の分離。3点比較の機械を発明と誤主張していないか
    - 独立性の破れへの対処（相関補正・correlation_group で V,T を同根扱い・D を external）が十分か
    - 5ガードレール＋inventory-probe が暴走（自己循環・誤り増幅）を止めるか
    - DD-PROOF への visual_reocr / doctrinal_external 接続、三軸 research_unit / FORMOBJ witness_cluster / FRBR への接続
  exclude:
    - DD-LAYOUT-001 v0.2 の幾何面設計（別 REQUEST DDLAYOUT で審査）
    - 三軸 v0.3 research_unit の中身（既決）
regression_anchors:
  - DD-LAYOUT-001 v0.2（PR#32 / sha256:7c79e46f…）V/T アンカー供給
  - DD-PROOF-001 v0.1（Box 2245856531451）+ v0.2 patch（Box 2246032441589）多源校正・自己循環§7・外部クリーン源＝D軸の鏡
  - 三軸インデックス v0.3（Box 2287660763513）doctrine_source ≥2独立源 / research_unit ＝ D軸の正体
  - DD-FORMOBJ-002 v0.2（Box 2286527242803）witness_cluster / form_variant
  - 01_TOC DD v0.1（Box 2279844275881）claim_support_eligible=false
  - prior_art: Fellegi-Sunter JASA1969 / Snorkel arxiv:1605.07723,VLDB2017 / Co-training COLT1998 / co-reg ICML-W2005 / EAC TPAMI2005 / FRBRization OCLC / RoadRunner VLDB2001 / multi-view outlier IJCAI2015 / CLIP arxiv:2103.00020
self_doubt:
  - V-T の同根結合度（相関）の実測がまだ（O7）。割引が過大/過小になりうる
  - D軸照合器（text→体系ノード）の実装・confidence 未定（O2）
  - a_v/閾値は ground truth 校正前の仮置き
  - D軸も結局テキストを読んで照合するため「artifact から完全独立」ではない（外部知識注入による“材料的独立”の主張に留める）—この限定が適切か
questions_for_gpt:
  - 第3軸を外部法律体系に置く是正は妥当か。D軸の独立性主張（完全独立でなく材料的独立）の表現は適切か
  - G_XMODAL_EXTERNAL_AXIS（V+T のみの一致を検証に昇格させない）は過剰/妥当か
  - novelty の白地（独立AI観測×安定アンカー×外部体系照合×連続再評価）は実在するか（既出でないか）
  - 5ガードレール＋独立性ゲート＋inventory-probe で暴走を構造的に防げているか
decision_requested:
  - PASS可否 / candidate 前進可否 / 独立3軸是正の採否 / novelty 範囲の適否 / 追加 must_fix（過信・自己循環・独立性の穴）
expected_label: DDXMODAL_PASS_WITH_NOTES または DDXMODAL_MODIFY_REQUIRED
---

# DDXMODAL 監査依頼: DD-XMODAL-001 v0.2（独立3軸＝視覚×テキスト×外部法律体系）

- target_mode: inline_embedded（全文を下記に逐語）。authoritative bytes = GitHub `asai-dot/Project-codex` ブランチ `claude/daiichi-houki-fact-system-qcn7ph` `docs/dd_candidates/DD-XMODAL-001_cross_modal_triangulation_living_corpus_candidate_v0.2_20260619.md`（PR #32, sha256:3318f3bb…）。
- gate: 設計のみ candidate。DDL/DB/mint/Box mutation/学習/embedding/OCR は HOLD。
- v0.1→v0.2 の核：image/text/structure は導出チェーン（画像→OCR→印刷TOC）で印刷TOCはテキスト派生＝第3独立軸にならない。第3軸を**外部の法律体系**（法令/論点/事実認定体系・D1分類・要件事実＝三軸 research_unit）に置換。

## 特に見てほしい点
1. **独立性の是正**：V(視覚)＋T(テキスト)は同根（画像→OCR）。**第3軸を文書外の法律体系(D)に置くことで真の独立を回復**。この分析は正しいか。
2. **G_XMODAL_EXTERNAL_AXIS**：V+T のみの一致は self-consistency で検証でない、D が絡む合意のみ検証、という論理。
3. **既存／白地**：2-of-3 の機械は全引用、白地＝AI世界の連続応用のみ。

===== 監査対象本文（逐語・inline_embedded）=====

# DD-XMODAL-001 v0.2 — cross-modal triangulation & 生きたコーパス（独立3軸 = 視覚×テキスト×法律体系）candidate

> **id**: DD-XMODAL-001 / **version**: candidate v0.2 / **supersedes**: v0.1（独立性の根本修正：印刷TOC構造はテキスト派生で第3独立軸にならない → 第3軸を「外部の法律体系」に置換）
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-19 JST
> **gate**: **設計のみ candidate**。DDL/DB/Box mutation/mint/学習/embedding/OCR は HOLD。
> **depends_on**: DD-LAYOUT-001 v0.2（V/T のアンカー供給）, DD-PROOF-001 v0.2（誤謬訂正 sink・外部クリーン源＝D軸の鏡）, 三軸インデックス v0.3（doctrine_source / research_unit ＝ D軸の正体）, DD-FORMOBJ-002（form_variant/witness_cluster）, DD-LITLINK-001（文書→法令/判例/語彙 signal）。

---

## 0. 中核命題（v0.2 で独立性を是正）
同じアンカー上に複数観測を張り、合意・不一致から **(1)誤謬訂正** と **(2)未知構造発見** を連続的に取る。各観測を別AI能力が生成し、モデル進歩のたびに同アンカー上で再生成すると、合意が時間で変化し訂正と新構造が湧き続ける **“生きたコーパス”** になる。

**v0.1 の誤り（owner 指摘）**：image/text/structure を3独立観測とした。しかし **画像→(OCR)→テキスト→(読むだけ)→印刷TOC構造** は導出チェーンで、印刷TOCは**テキスト派生＝第3独立軸にならない**。

## 1. ★独立3軸（是正後）
| 軸 | 中身 | 生成過程 | 独立性 |
|---|---|---|---|
| **V 視覚系** | 位置＋画像（page_block bbox / layout / 画像認識 visual_reocr） | 画像（根）を視覚過程で読む | 画像が根 |
| **T テキスト系** | OCR本文 ＋ **印刷TOC由来構造**（その本の目次・見出し） | 画像を記号過程(OCR)で読む＋その読みに従属 | V と**同根**（OCR で結合） |
| **D 体系系** | **外部の法律体系へのマッピング**：法令体系／論点体系／事実認定体系／D1分類／要件事実＝三軸 `research_unit` のどのノードを instantiate するか | 文書外の doctrine 権威に照合（外部知識を注入） | **artifact から真に独立** |

- **V と T は同根**（画像→OCR）なので“別過程”の半独立にすぎない。**V＋T の一致は「綺麗だが誤った版」に両方騙されうる**＝自己無撞着であって検証でない。
- **D だけが文書に無い情報（statute/doctrine）を持ち込む** → **D が絡む一致こそ検証**。これは三軸 v0.3「canonical は≥2独立 doctrine 源の突合後」、DD-PROOF「外部クリーン源を鏡に誤字検出」と同一原理（**再発明でなく統合**）。

## 2. ★既存と白地の分離（巨人の肩。主張はここだけ）
2-of-3 / 多源合意の機械は全部既存：**Fellegi-Sunter**(possible-match) / **Snorkel label model** / **co-training・co-regularization** / **consensus clustering(EAC)** / **multi-view outlier detection** / **FRBRization** / **wrapper/template induction(RoadRunner)** / **CLIP**(限定)。出典は各々（JASA1969 / arxiv:1605.07723,VLDB2017 / COLT1998,ICML-W2005 / TPAMI2005 / IJCAI2015 / OCLC / VLDB2001 / arxiv:2103.00020）。
**白地（novelty 候補）**：安定アンカー上に **V/T/D の独立観測**（特に**外部接地の D 軸**）を張り、**モデル改善のたび再生成**して合意を**恒常的監督信号**として運用、訂正と未知構造を**自己改訂し続ける** ＝ DD-PROOF flywheel の「多モーダル＋外部体系照合＋連続再評価」一般化。主張は調査で白地と確認できた範囲に限定。

## 3. 派生レイヤ語彙（観測は不可変・本層 append-only）
```text
agreement_unit(id, doc_id, selector_ref, granularity)
view_assertion(unit_id, axis∈{V_visual,T_textual,D_doctrinal}, predicted_label, view_confidence, abstain, correlation_group)
  # correlation_group: V_visual と T_textual は "artifact_intrinsic"（同根）／D_doctrinal は "external"
agreement_signal(unit_id, pattern∈{3of3,2of3,1of3,split}, label_model_prob, decision∈{confirmed,possible,rejected}, involves_external:bool)
derived_candidate(unit_id, kind∈{correction,toc_node,form_variant,work_expression,research_unit}, target_axis, proposal, confidence, status∈{proposed,reviewed,accepted,rejected}, provenance)
view_accuracy(axis, task, m_prob, u_prob, weight, correlation_group)
```
- `involves_external` を保持：**D が絡む合意か否か**で証拠強度を区別（D無しの V+T 一致は弱証拠）。

## 4. conflict 解決（どの軸を信じるか・相関明示）
`score(y)=Σ w_v·1[λ_v=y]`, `w_v=log(a_v/(1-a_v))`、a_v は**タスク別**。**相関構造を明示**：V_visual と T_textual は同一 correlation_group（同根）→ label model（Snorkel 依存項）で**実効票数を割り引く**。D_doctrinal は別群＝フル票。グローバル「常に text」禁止。

## 5. 熱を本物にする5ガードレール
1. 不変アンカー＋append-only＋engine_version（世代横断で再計算・累積）。
2. 自己循環の物理禁止（DD-PROOF §7）。派生ラベルを観測へ書き戻さない。
3. 正準化は人手ゲート（新hub/新構造 auto=0）。爆発は候補生成まで。
4. 双方向＝撤回可能（良モデルで面再生成→過去合意の降格）。
5. 選択的再評価（不一致/低信頼/新モデル影響大のみ再走）。

## 6. ★独立性ゲート（v0.2 の核）
- **G_XMODAL_EXTERNAL_AXIS**：検証を主張できるのは **D（外部体系）が絡む合意**のみ。**V+T だけの一致は self-consistency であって検証ではない**（同根のため）。
- **G_XMODAL_INDEP_REEXTRACT**：D軸は**文書のテキストから独立に**doctrine 権威へ照合（印刷TOCをそのまま体系扱いしない）。
- **G_XMODAL_NO_RAW_MAJORITY**：生多数決禁止・相関補正必須（V,T 同根）。
- 既存：G_XMODAL_DERIVED / NO_CLAIM_SUPPORT / NO_SELF_LOOP / HUMAN_GATED。

## 7. 2つの出力パス
- **correction_candidate** → DD-PROOF-001 へ。visual 再認識を新 `source_family=visual_reocr`、体系照合を `source_family=doctrinal_external` として多源校正に合流。
- **未知構造**：`toc_node_candidate`（V+D が境界合意・印刷TOC欠落）／`form_variant`（FORMOBJ witness_cluster）／`work_expression_link`（FRBR）／`research_unit` 候補（三軸）。全て候補・自動正準化しない。

## 8. inventory-probe 規律（三軸 v0.3 継承）
カーネル1本で「合意（特に D 絡み）が候補を生むか／precision／撤回率」を実測してから拡張。`knowledge_yield`（世代あたり 新候補・昇格率・撤回率・possible率・**external_involved率**）を測定。

## 9. open items
O1 a_v/閾値の ground truth 校正／O2 D軸照合器（text→体系ノード）の実装と confidence／O3 visual_reocr・doctrinal_external の DD-PROOF source_family 接続確定／O4 form_variant↔witness_cluster 語彙整合／O5 work_expression↔FRBR/LRM（DD-LITID 接続）／O6 knowledge_yield カーネル選定／O7 V-T 相関の実測（同根の結合度）。

## 10. HOLD / 11. 一行
HOLD：DDL/DB/mint/Box mutation/学習/embedding/OCR/production。本DDは観測を1件も書き換えない。
**一行**：3点比較は枯れた技術。発明候補は「**視覚×テキスト×外部法律体系**の独立3軸を安定アンカー上で連続再評価し、自己改訂し続ける検証ループ」。鍵は**第3軸を文書外の法律体系に置く**こと（V+T だけでは自己無撞着で検証にならない）。暴走は5ガードレール＋独立性ゲート＋inventory-probe で構造的に禁じる。
