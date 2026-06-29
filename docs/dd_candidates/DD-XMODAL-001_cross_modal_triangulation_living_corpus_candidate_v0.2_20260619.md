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
