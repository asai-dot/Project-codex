# 参照記録 — 法令の「意味の時間軸」をどうデータ化するか（先行事例調査・DD-LAWSUBTRANS-001 の土台）

- **記録**: 2026-06-08 / head=Project-codex (claude-code remote) / 起点=浅井さん「法令ロータイム(形式軸)は進んだが、改廃に伴う“意味”の変化は未検討。別DDに切る。世界中が同じ問いに直面しているはずなので、先に解法をリサーチせよ」
- **status**: 調査＋枠組み記録（DD-LAWSUBTRANS-001 v0.1 の根拠文書）
- **方法**: 5アングルの並行 web リサーチ（標準/各国point-in-time/AI&Law学界/法理論+citator/ソース階位+dispute）。各主張に出典URL。
- **上位文書**: `REFERENCE_temporal_law_identity_universal_20260605.md`（形式軸=FRBR+point-in-time の収束解）の**続編＝実質軸**。

---

## 0. 結論（一行）
**「形式的改正があった」と「実質的意味が変わった」を構造的に分離し、後者を出典付き・順位付きの主張(assertion)として持ち、決して真として自動確定しない** ——これが Akoma Ntoso・ELI・各国 point-in-time・citator・AI&Law 学界・KG 標準に共通して収束している解。

---

## 1. 形式 vs 実質の分離は「普遍的設計」

- **Akoma Ntoso / OASIS LegalDocML**（著者 Monica Palmirani, Fabio Vitali, CIRSFID Bologna）は、形式と実質を別メタデータ族で分離する:
  - 形式: `<textualMod>`（`@type`: substitution / insertion / repeal … renumber/split/join/relocation/replacement も同族）。`@incomplete`(自動適用に情報不足)/`@exclusion` フラグ。
  - 実質: **`meaningMod` / `scopeMod` / `efficacyMod` / `forceMod` / `legalSystemMod`**（非テキスト改正）。
  - active modifications（他文書に与える改正）vs passive modifications（自身が受ける改正）の分離。
  - 典拠: https://en.wikipedia.org/wiki/Akoma_Ntoso ／ OASIS spec `textualMod`: https://docs.oasis-open.org/legaldocml/akn-core/v1.0/csprd01/part2-specs/material/AkomaNtoso30-csd13_xsd_Element_textualMod.html ／ AKN4UN ch.: https://unsceb-hlcm.github.io/part1/index-167.html
- **Palmirani の三分類**（改正は ①テキスト ②規範の射程(scope) ③力/効力/適用可能性の時間 のいずれかに作用）が共通の祖。
  - "Legislative Change Management with Akoma-Ntoso" (Springer 2011): https://link.springer.com/chapter/10.1007/978-94-007-1887-6_7
  - "Model Regularity of Legal Language in Active Modifications": https://link.springer.com/chapter/10.1007/978-3-642-16524-5_5
- **ELI（EU 法令識別子）** は FRBR/FRBRoo ベースで版を `LegalExpression` として持ち、変更を明示分離: **direct change(textual or non-textual amendment) vs consequential/indirect change**。`eli:amends`(実質変更) / `eli:repeals` / `eli:corrects`(テキストのみ・法的変更なし) / `eli:consolidates`。v1.1→v1.5、**ELI-I (Impact Ontology) v1.0**(2024)。
  - https://op.europa.eu/en/web/eu-vocabularies/eli ／ https://data.europa.eu/eli/ontology ／ https://eur-lex.europa.eu/eli-register/news_item_9.html
- **FRBR / FRBRoo / LRMoo**: Work=抽象規範, **Expression=日付/言語付き版（point-in-time はここ）**, Manifestation=形式, Item=複製。AKN/FRBR の限界＝**文書レベルで条文(component)レベルでない**。2025-26 の event-centric/component-level 研究がギャップを埋める: arXiv 2506.07853, arXiv 2505.00039。
- **CEN MetaLex**（Boer, Hoekstra, Winkels）: FRBR 型・**event-centric**（どの改正イベントが版を作ったか）。ただし「改正情報の優美な表現は苦手」と自認＝AKN/ELI より実質側が弱い。 https://blog.law.cornell.edu/voxpop/tag/cen-metalex

## 2. 多時間軸：efficacy が validity を超えて生き残る＝旧法存続の形式的根拠

- **Palmirani & Brighi, "Time Model for Managing the Dynamic of Normative System," EGOV 2006, LNCS 4084**: 多時間軸 = **publication / validity(in-force) / efficacy / applicability / transaction time**。**廃止された規範が一定期間 efficacious/applicable であり続ける**＝ultra-activity の形式基盤。DOI 10.1007/11823100_19 ／ https://link.springer.com/chapter/10.1007/11823100_19
- **Palmirani, Governatori, Contissa, "Modelling Temporal Legal Rules," ICAIL 2011**: validity/efficacy に **applicability time** を加える。
- **Governatori & Rotolo, "Changing Legal Systems: Legal Abrogations and Annulments in Defeasible Logic," Logic J. IGPL 18(1):157–194, 2010**: **annulment = ex tunc（遡及・無かったことに、過去効果も無効）** vs **abrogation = ex nunc（将来効・過去効果は存続）**。 https://academic.oup.com/jigpal/article-abstract/18/1/157/655276
- **Governatori et al., "Variants of Temporal Defeasible Logics for Modelling Norm Modifications," ICAIL 2007**: 改正による「ルール変更」と「結論の存続」を分離＝形式改正≠実質効果の形式語彙。 https://dl.acm.org/doi/abs/10.1145/1276318.1276347
- **Governatori et al., "Retroactive Legal Changes and Revision Theory in Defeasible Logic," DEON 2010, LNCS 6181**: 遡及改正のモデル。DOI 10.1007/978-3-642-14183-6_10
- **"An approach to temporalised legal revision through addition of literals," AI & Law, 2023**: 現状の到達点。DOI 10.1007/s10506-023-09363-w
- **Boella et al., "An Ontology of Changes in Normative Systems from an Agentive Viewpoint," AICOL/LNCS 2020**: 変更型(abrogation/derogation/annulment/substitution)のオントロジー。DOI 10.1007/978-3-030-51999-5_11

## 3. 解釈を「反証可能な第一級オブジェクト」として持つ

- **Walton, Sartor & Macagno, "An Argumentation Framework for Contested Cases of Statutory Interpretation," AI & Law 24(1), 2016** ／ **Sartor et al., "Argumentation Schemes for Statutory Interpretation," JURIX 2014**: 解釈規準(canon)を **defeasible 論証スキーム**（11スキーム＋critical questions）として明示・攻撃・復活可能に。 https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2850164
- **Sartor, "Interpretation, Argumentation, and the Determinacy of Law," Ratio Juris 36, 2023**: 解釈を「解釈基盤(canon+理由)」上の defeasible 推論として形式化。 https://onlinelibrary.wiley.com/doi/full/10.1111/raju.12389
- **Rotolo, Governatori & Sartor, "Deontic Defeasible Reasoning in Legal Interpretation," ICAIL 2015**: 解釈言明を meta-level rule として第一級化。
- **isomorphism 原則**: Bench-Capon & Coenen, "Isomorphism and Legal Knowledge Based Systems," AI & Law 1(1), 1992（DOI 10.1007/BF00118479）。知識ベースを法源に 1:1 対応させ改正追跡を扱いやすくする。
- **LKIF Core** (ESTRELLA): Hoekstra et al. 2007/2009、Norm を deontic+directive qualification として表現。 https://ceur-ws.org/Vol-321/paper3.pdf
- **OASIS LegalRuleML** (Palmirani, Governatori, Rotolo): 規範＋変更の事実上の後継。validity/efficacy/applicability＋defeasibility＋出典authorityメタを標準装備。DOI 10.1007/978-3-642-24908-2_30

## 4. 各国 point-in-time：effects と不確実性表示

- **英 legislation.gov.uk**: Original(As Enacted) vs Latest(Revised) vs Point-in-time。**Changes to Legislation バナー**＝「outstanding changes not yet applied」。**effect** = atomic change record（affecting/affected provision, type[words substituted/repealed/inserted/restricted], in-force date[prospective可], applied/unapplied, extent[E&W/S/NI]）。**Textual amendment(F-notes) vs Non-textual/Editorial effect(C-notes「Modifications etc. (not altering text)」)** ＝意味/範囲/適用を変えるがテキストは変えない。API: https://legislation.github.io/data-documentation/api/overview.html ／ Guide to Revised Legislation (Oct 2013)。
- **豪 Federal Register of Legislation**: as made / in force / point in time。単位は **compilation**（番号＋日付）。endnote で未施行・未組込改正を明示。Legislation Act 2003 s15X「editorial change」は法効果を変えられない。
- **NZ legislation.govt.nz**: **官公式＝Coat of Arms 表示の有無**で official/unofficial を二値表示。単位は consolidation（"Version as at …"）＋ provision 単位の history note。
- **米 US Code / OLRC / USLM**: section 単位の currency date ＋ **Pending Updates**。**positive law(legal evidence) vs non-positive(prima facie)**。Editorial Reclassification はテキスト不変。USLM(XML): https://github.com/usgpo/uslm
- **EU EUR-Lex / CELLAR**: consolidated text に「**This text is meant purely as a documentation tool and has no legal effect**」。consolidation(法的価値なし) vs codification(新規法的行為)。CELEX 接頭 "0" ＋日付＝consolidated。
- **共通パターン**: いずれも「**権威ある正本**」と「**便宜的作業版**」を分離しギャップを明示。effect record 共通フィールド = affecting / affected / type / in-force date(prospective可) / applied status / jurisdiction。

## 5. 法理論の支柱（実質軸の語彙の根）

- **Kelsen**: 妥当性(validity=所属/拘束力) ≠ 実効性(efficacy=現実の遵守)。妥当性は条件付き。 https://plato.stanford.edu/entries/lawphil-theory/
- **Bulygin & Alchourrón**: **membership ≠ applicability**。所属は適用可能性の必要十分条件でない＝「廃止(非所属)でも過去事実に適用可能」「所属でも当該事案に不適用」。 https://www.cambridge.org/core/journals/canadian-journal-of-law-and-jurisprudence/article/abs/applicability-of-legal-norms/DDDC8502834EB7C56A38C491AFA147AD
- **ultra-activity（ultractividad）**: 廃止/置換された法が、施行中に確定した行為・状況をなお規律（刑法の軽い旧刑罰、労働協約、契約は成立時法で解釈）。
- **intertemporal 既定則**: 廃止は廃止前の効果・取得された権利義務に影響しない（Interpretation-Act 型 savings の背景推定）。**savings clause は経過措置(transitional provision)の一種**で、新法が消すはずの権利/手続を**保持**。
- **ex tunc(遡及) vs ex nunc(将来効)**: 廃止の既定は ex nunc。遡及は通常明示が要る（刑法の有利遡及等）。
- **形式的廃止 ≠ 実質的不連続**: 再制定された条文が同一意味を担うことがある（lex posterior derogat legi priori が置換則）。

## 6. citator の treatment 分類（出典付き評価主張の現実モデル）

- **二層構造が普遍**: 粗い **signal/flag 層**（caution 段階＝ヘッジ）＋細かい **controlled phrase 層**（何がされたか）＋**必ず特定の判決に帰属＋抜粋**。「自分の声で『これは死んだ法だ』とは言わない。裁判所が何をしたかを報告する」。
- **Shepard's**（LexisNexis）: 赤(overruled/reversed)/橙Q(questioned)/黄△(limited/criticized)/緑+(followed)/青A(analysis)。History(同一訴訟: affirmed/reversed/superseded/vacated) と Treatment(他事件: criticized/distinguished/explained/limited/overruled/questioned/followed) を分離。 https://www.lexisnexis.com/pdf/LexisNexis_Shepards-Signal-Indicators-and-Analysis-Phrases.pdf
- **Westlaw KeyCite**: 赤旗/黄旗/赤縞(partially overruled)/青縞(appeal pending)。負処理 phrase: Overruled / Abrogated / Called into Doubt / Declined to Extend / Distinguished / Limited / **Superseded by Statute** / Vacated 等。 https://legal.thomsonreuters.com/blog/westlaw-tip-of-the-week-checking-cases-with-keycite/
- **Bloomberg BCite**: Positive / Distinguished / Caution / **Superseded by Statute** / Negative の5複合。 ／ **vLex (Vincent)**: Positive/Neutral/**Caution**/Negative/Unclassified。 ／ **Justis JustCite**: Precedent Map（applied/approved/followed/distinguished/overruled/considered/not followed）。
- **決定的**: **"Superseded by statute" は judicial overruling と別カテゴリに隔離**され、自動で赤旗にならない（未置換命題ではなお good law）。＝**形式的な立法変更が必ずしも実質的意味を殺さない**という現実世界の分類学的裏付け。 https://www.aallnet.org/wp-content/uploads/2018/12/LLJ_110n4_02_hellyer.pdf

## 7. ソース階位＋主張/反証のKG表現＋安全出力

- **権威の階位**: 一次(憲法>法律>判例) vs 二次(学説・論文＝説得的のみ)。立法沿革は「一次だが説得的どまり」。Scalia は立法意図を"worthless fiction"と批判。階位は単一序数でなく多因子で持つべき（"Dethroning the Hierarchy of Authority"）。 https://guides.law.sc.edu/LRAWFall/WeightofAuthority
- **日本特有**: 判例は立法担当者解説に通常言及しないが、立法意図を**立案担当者解説(一問一答)・逐条解説**に求めうる＝説得的だが拘束力なし。**判例と学説は別クラス**。 https://digitalcommons.law.uw.edu/cgi/viewcontent.cgi?article=1590&context=wilj ／ METI 逐条解説例: https://www.meti.go.jp/policy/economy/chizai/chiteki/pdf/Chikujo.pdf
- **KG 表現の定石**: nanopublication(Assertion/Provenance/PublicationInfo の3グラフ) https://www.nanopub.org/guidelines/ ／ **W3C PROV-O**(`prov:wasAttributedTo`/`prov:wasDerivedFrom`) https://www.w3.org/TR/prov-o/ ／ **Wikidata rank**(preferred/normal/deprecated＋機械可読理由 P2241/P7452、誤主張も削除せず保持) https://www.wikidata.org/wiki/Help:Ranking ／ **AIF**(conflict/preference) http://www.mit.edu/~irahwan/docs/KER2006.pdf ／ **Toulmin**(claim/data/warrant/qualifier/rebuttal)。
- **決定的原則**: 「条文が改正された」は versioning 事実(PROV/lawtime)。「意味が変わった」は別個に帰属・順位付けされた解釈主張。**後者を自動で truth に昇格させない**。
- **安全出力の実証根拠**: Stanford RegLab — 汎用 LLM の法令幻覚 69–88% (arXiv 2401.01301)、RAG 付き商用ツールでも 1/6〜1/3 が幻覚 (Legal RAG study)。モデルは誤った法的前提を訂正できず強化する(sycophancy)。→ **単一の答えを断言せず、出典付き候補を順位・conflict ごと提示し人間検証必須**。 https://hai.stanford.edu/news/ai-trial-legal-models-hallucinate-1-out-6-or-more-benchmarking-queries

---

## 8. DD-LAWSUBTRANS-001 への落とし込み（設計含意）

| 先行事例 | 採用要素 |
|---|---|
| AKN `textualMod` vs `meaningMod/scopeMod/efficacyMod` | `substantive_change_type` 値域・textual_delta(形式)と substantive_change(実質)の物理分離 |
| Palmirani 多時間軸 / Governatori abrogation(ex nunc) vs annulment(ex tunc) | `temporal_reach` ＋ efficacy/applicability を survival 三軸に反映 |
| Kelsen validity≠efficacy / Bulygin membership≠applicability | `formal_status`(lawtime) と `substantive_status`/`applicability_scope` の三軸分離 |
| 英 non-textual effect / citator "superseded by statute" 隔離 | 「テキスト不変でも意味変化」を表現／形式変更を実質的死と短絡しない gate |
| nanopub / PROV-O / Wikidata rank / AIF | assertion + evidence(T5) + review-event(T6) + rank/counter による dispute 表現 |
| ソース階位（立法担当者=説得的どまり） | `source_tier` ＋ `drafter_intent_not_sole_truth` gate |
| Stanford 幻覚研究 | MCP 出口の断言禁止・claim_support 既定 false・両論併記 |

## 9. 落とし穴（DD の gate に反映済）
1. 改正あり→実質変更あり の短絡。 2. 立法担当者意図の最終真実視。 3. alive/dead 二値。
4. 出力で解釈を事実として断言。 5. 再評価で履歴破壊。 6. 文書レベル止まり（条文レベルにできていない）。

## 10. 出典一覧（主要・再取得用）
- AKN: oasis-open.org/standard/akn-v1-0 ／ docs.oasis-open.org/legaldocml ／ unsceb-hlcm.github.io/part1/index-167.html
- ELI: op.europa.eu/en/web/eu-vocabularies/eli ／ data.europa.eu/eli/ontology
- 英: legislation.gov.uk ／ legislation.github.io/data-documentation ／ Guide to Revised Legislation 2013
- 米: uscode.house.gov ／ github.com/usgpo/uslm ／ EU: eur-lex.europa.eu（consolidation glossary）
- Palmirani & Brighi EGOV 2006: doi 10.1007/11823100_19 ／ Governatori & Rotolo IGPL 2010: academic.oup.com/jigpal/article-abstract/18/1/157/655276
- Walton/Sartor/Macagno AI&Law 2016: ssrn 2850164 ／ Bench-Capon & Coenen 1992: doi 10.1007/BF00118479
- PROV-O: w3.org/TR/prov-o ／ nanopub: nanopub.org/guidelines ／ Wikidata rank: wikidata.org/wiki/Help:Ranking
- Shepard's PDF: lexisnexis.com/pdf/LexisNexis_Shepards-Signal-Indicators-and-Analysis-Phrases.pdf ／ AALL Hellyer 比較: aallnet.org/wp-content/uploads/2018/12/LLJ_110n4_02_hellyer.pdf
- Stanford 法令幻覚: arXiv 2401.01301 ／ hai.stanford.edu（1-in-6 benchmarking）

> 注: 一部一次ソース（OASIS/Springer/Oxford/各国官公サイト）は自動取得が 403。値域の verbatim 確認が必要な箇所
> （AKN 非テキスト mod の `@type` 完全列、ELI 時間プロパティ名、Shepard's/KeyCite 完全 phrase 表）は、
> production 実装前に上記 PDF/OWL を直接照合すること（DD §7 production HOLD と整合）。
