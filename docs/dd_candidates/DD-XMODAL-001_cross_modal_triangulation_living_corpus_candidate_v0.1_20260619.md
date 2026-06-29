# DD-XMODAL-001 v0.1 — cross-modal triangulation & 生きたコーパス（3面合意の派生レイヤ）candidate

> **id**: DD-XMODAL-001 / **version**: candidate v0.1 / **supersedes**: なし（新規）
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-19 JST
> **gate**: **設計のみ（candidate）**。DDL・DB書込み・Box mutation・mint・学習/embedding/OCR 実行は **含まない／HOLD**。
> **depends_on**: DD-LAYOUT-001 v0.2（image/text/structure の3面とアンカー供給）, DD-PROOF-001 v0.2（多源校正パイプライン／誤謬訂正の sink）, DD-FORMOBJ-002（form_variant/witness_cluster）, 三軸インデックス v0.3（research_unit）。
> **canonical 配置**: 未決（CANONICAL_MAP 従属）。

---

## 0. 中核命題
**image（紙面/視覚）・text（OCR本文）・structure（章節）の3面を、同じアンカー（bbox/char_span/toc_node）上の半独立観測**として持つと、合意・不一致の組合せ信号から **(1)誤謬訂正** と **(2)未知構造の発見** が連続的に取れる。さらに**各面を別々のAI能力が生成し、モデル進歩のたびに同じアンカー上で再生成**すると、合意パターンが時間で変化し、訂正と新構造が継続的に湧き出す **“生きたコーパス”** になる。

## 1. ★既存と白地の分離（巨人の肩。novelty 主張はここだけ）
**「3点比較」「2-of-3 合意」の機械は全部既存。** 自前で建てない。
| 我々のニーズ | 乗る既存枠組み | 出典 |
|---|---|---|
| 2面一致/1面不一致の3決定（保留ゲート） | **Fellegi-Sunter**(match/**possible-match**/non-match, log(m/u)) | JASA 1969 |
| 3ノイズ源を相関込みで確率ラベル化 | **Snorkel / data programming label model** | arxiv 1605.07723 / VLDB 2017 |
| 合意で構造伝播（昇格せず不一致を罰す） | **co-training / co-regularization** | COLT 1998 / ICML-W 2005 |
| 一致＝コア/不一致＝境界・新規 | **consensus clustering(EAC, co-association)** | TPAMI 2005 |
| 1面だけ外れの検出 | **multi-view outlier detection(class outlier)** | IJCAI 2015 / TIP 2018 |
| 版違いを work へ束ねる | **FRBRization / work-set** | OCLC Research |
| 反復テンプレ/section 帰納 | **wrapper/template induction(RoadRunner)** | VLDB 2001 |
| 視覚-意味の緩い一致（限定使用） | **CLIP 対照学習** | arxiv 2103.00020 |

**白地（＝novelty 候補・AI世界での応用）**：
> 安定アンカー上に **独立したAI観測×3** を張り、**モデル改善のたびに同一アンカーで再生成**して 2-of-3 合意を**恒常的な監督信号**として運用し、訂正と未知構造を**自己改訂し続ける**＝ DD-PROOF-001 の flywheel を多モーダル×連続再評価へ一般化したもの。主張は調査で白地と確認できた範囲に限定する。

## 2. 派生レイヤ語彙（観測は不可変。本層は append-only の assertion）
```text
agreement_unit(id, doc_id, selector_ref, granularity)            # 3面共通の比較単位（selector は DD-LAYOUT の W3C/IIIF を参照）
view_assertion(unit_id, view∈{image,text,structure}, predicted_label, view_confidence, abstain:bool)
agreement_signal(unit_id, agreement_pattern∈{3of3,2of3,1of3,split}, label_model_prob, decision∈{confirmed,possible,rejected})
derived_candidate(unit_id, kind∈{correction,toc_node,form_variant,work_expression}, target_view, proposal, confidence, status∈{proposed,reviewed,accepted,rejected}, provenance)
view_accuracy(view, task, m_prob, u_prob, weight, correlation_group)   # Fellegi-Sunter/Snorkel パラメタ永続化
```

## 3. 2つの出力パス
- **(1) correction_candidate** → DD-PROOF-001 へ。3面の visual 再認識を新 `source_family=visual_reocr` として既存の多源校正に合流（テキスト源のみだった DD-PROOF にモダリティを1本追加）。
- **(2) 未知構造**：`toc_node_candidate`（GEO+TXT が境界合意・TOC欠落）／`form_variant`（反復テンプレ＝FORMOBJ `witness_cluster`）／`work_expression_link`（同内容・別版＝FRBR）／三軸 `research_unit` 候補。**全て候補。自動正準化しない**（新hub/新構造 auto=0 ゲート）。

## 4. conflict 解決（どの面を信じるか）
`score(y)=Σ_v w_v·1[λ_v=y]`, `w_v=log(a_v/(1-a_v))`。**a_v はタスク別**（heading=image 強／条番号=text 強／所属=structure 強）。グローバル「常に text」を禁止。相関補正は Snorkel 依存項。

## 5. ★熱を本物にする5ガードレール（暴走防止）
1. **不変アンカー＋append-only＋engine_version**：各モデルパスは新観測層。世代横断で合意再計算でき累積。
2. **自己循環の物理禁止**（DD-PROOF §7 継承）：観測が自分/自源を検証に使えない。派生ラベルを観測へ書き戻さない。
3. **正準化は人手ゲート**（新hub/新構造 auto=0）。爆発は候補生成とランキングまで。
4. **双方向＝撤回可能**：良モデルで面再生成→過去合意の無効化→候補を降格できる。
5. **選択的再評価**：不一致/低信頼/新モデルが大きく変えた箇所のみ再走（コスト爆発の triage）。

## 6. ★独立性の破れに注意（調査の重い指摘）
3面は条件付き独立でない（同スキャン/OCR由来、structure が text 派生になりがち）。**素朴な多数決は相関2票で正しい少数派1票を潰す**。対策：(a) 生多数決禁止・相関補正済み label model 必須、(b) structure は TOCページから **text と独立に再抽出**、(c) possible 帯は自動適用せず人手、(d) abstain 尊重。

## 7. inventory-probe 規律（三軸 v0.3 継承）＝爆発を主張する前に測る
カーネル1本で「合意レイヤが実際に候補を生むか／precision／撤回率」を**実測**してから拡張。測定列 `knowledge_yield`（世代あたり 新候補数・昇格率・撤回率・possible率）。「answer 生成」でなく「未構築の可視化」を最初の目的に。

## 8. ゲート
G_XMODAL_DERIVED（派生・観測不可変）／G_XMODAL_NO_CLAIM_SUPPORT（合意/候補は claim_support_eligible=false）／G_XMODAL_NO_RAW_MAJORITY（相関補正必須）／G_XMODAL_NO_SELF_LOOP（自己循環禁止）／G_XMODAL_HUMAN_GATED（正準化は人手）／G_XMODAL_INDEP_REEXTRACT（structure は text と独立再抽出）。

## 9. open items
O1 a_v / 閾値の初期値はground truthで校正／O2 selective re-eval のトリガ定義／O3 visual_reocr の DD-PROOF source_family 接続点の確定／O4 form_variant↔FORMOBJ witness_cluster の語彙整合／O5 work_expression↔FRBR/LRM 実装（DD-LITID 接続）／O6 knowledge_yield 測定のカーネル選定。

## 10. HOLD
DDL/DB/mint/Box mutation/学習データ生成/embedding/OCR 実行/production mapping。本 DD は1件も観測を書き換えない。

## 11. 一行
3点比較は枯れた技術。**それを「独立AI観測×安定アンカー×連続再評価」で自己改訂し続ける文書理解ループに仕立てた点**だけが白地。爆発を設計で歓迎し、暴走を構造（5ガードレール＋独立性補正＋inventory-probe）で禁じる。
