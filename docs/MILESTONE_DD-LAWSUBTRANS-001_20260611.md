# マイルストーン記録 — 法令オブジェクトへの「意味の時間軸」追加（DD-LAWSUBTRANS-001）

- **記録日**: 2026-06-11 / **owner**: 浅井 / **head**: Project-codex (claude-code remote)
- **位置づけ**: ALO 法令オブジェクトの**アップデート**。法令レイヤがこれまで持っていた
  「形式的時間軸」に加え、「**実質的意味・解釈の時間軸**」を第二の軸として追加した。
- **status**: 設計フェーズ完了（design accepted）。production 実装は別ゲートで HOLD。

---

## 1. 何を達成したか（一行）

**「法令時間軸は解けても、法令“意味”の時間軸はまだ解けていない」** という浅井さんの問題提起に対し、
形式的改廃（DD-LAWTIME）と実質的変更を**構造的に分離**し、後者を **出典付き・順位付きの
主張(assertion)** として持ち **真として自動確定しない** レイヤを、設計受理＋動く実装＋安全な出口まで
一気通貫で構築した。

## 2. 法令オブジェクトの二軸（before → after）

| 軸 | 担当 DD | 問い |
|---|---|---|
| **形式的時間軸**（従来） | DD-LAWTIME-001 | いつ公布/施行/改正/廃止されたか。どの時点でどの条文版が有効か |
| **実質的時間軸**（本追加） | **DD-LAWSUBTRANS-001** | その改廃で**意味・要件・効果・射程**が実際に変わったか。旧法理は生き残るか。誰がそう評価したか |

核となる不変則: **形式的改廃 ≠ 実質的変更**。「改正あり ⇒ 実質変更あり」の短絡を物理制約で禁止。

## 3. 監査・承認の記録

| 版 | gate 結果 | 備考 |
|---|---|---|
| v0.1 (06-08) | `DDLAWSUBTRANS_PASS_WITH_NOTES` | 初版・先行事例調査に基づく |
| v0.1.1 (06-10) | `PASS_WITH_NOTES` ×2 | GPT Pro お目付け役 ＋ GPT-5.5 Pro 再レビュー。指摘4点 CLOSED |
| v0.1.2 (06-11) | `PASS_WITH_NOTES` | producer 全5段「design 整合」確認 |
| v0.1.3 (06-11) | `PASS_WITH_NOTES` | note 2点明文化・設計不変 |

- **owner ratify 済（design accept）** 2026-06-10 — `approval_queue/APPROVAL_CARD__20260610_lawsubtrans_v0.1.2_DDLAWSUBTRANS.md`
- **境界宣言**: DD-LAWTIME は形式軸限定、実質軸は本 DD の管轄（後続 AI の誤読防止）

## 4. 成果物

### 設計（accepted, design）
- `docs/dd/DD-LAWSUBTRANS-001_v0.1.3.md` — 統制語彙 / T1–T6 スキーマ / 品質 gate / MCP 出口契約 /
  Phase 2-5 ロードマップ / §10 production 前条件
- `docs/reference/REFERENCE_law_substantive_transition_prior_art.md` — 世界の先行事例調査（全 URL 付き）

### 実装（candidates-only / DB 書込みゼロ / 69 unit tests green）
| Phase | 部品 | 役割 |
|---|---|---|
| 2 | `scripts/lawdelta/` | 条文テキスト差分（Akoma Ntoso `textualMod` 準拠）。形式観測のみ |
| 3 | `scripts/drafterintent/` | 立案担当者解説 → tier-2 実質変更候補 |
| 4 | `scripts/casetreatment/` | 判例引用 treatment 候補（citator 流儀） |
| 中核 | `scripts/assembler/` | **dispute 形成**。継続 vs 変化の衝突検出、勝者を選ばない |
| 5 | `scripts/mcprender/` | **両論併記・断言禁止**の安全出力 |

- PR: asai-dot/Project-codex **#19**

## 5. 設計を支える世界標準（調査の結論）

- 形式 vs 実質の分離は国際標準で確立（Akoma Ntoso `textualMod` vs `meaningMod/scopeMod/efficacyMod`、
  英 legislation.gov.uk の textual vs non-textual effect、citator の "superseded by statute" 隔離）
- 多時間軸（Palmirani: validity / efficacy / applicability）、abrogation(ex nunc) vs annulment(ex tunc)
- 妥当性≠実効性（Kelsen）、所属≠適用可能性（Bulygin）＝旧法存続の概念装置
- 主張＋出典＋順位＋反証（PROV-O / nanopublication / Wikidata rank）
- 断言しない安全出力（Stanford RegLab: 法令幻覚 69–88%）

## 6. 実装イメージ（達成済みの動作）

```
art:415  形式（DD-LAWTIME）: 2020-04-01 改正で条文変更（lawtime: superseded）
         立案担当者解説(T2): 実質変更なし（継続）
         裁判例(T3):        旧解釈は不継続（変化）
         学説(T4):          解釈の修正（限定）
   → dispute・両論併記・全員 disputed・claim_support 不可・勝者なし
```

## 7. 残タスク（production 実装フェーズ・HOLD）

設計とは別ゲート。重いが道筋は明確。

1. §4 gates の実 SQL / 独立 validator 化
2. lawtime resolved view への接続（DD-LAWTIME v0.2.x production 確定が前提。v0.2.2 は現在 MODIFY_REQUIRED）
3. T1–T6 の実 DDL 投入（branch dry-run → 全 gate PASS → 本番）
4. `claim_support_eligible` の view 導出 / drift gate（T2/T3/T4）
5. evidence locator gate・unknown 非根拠・accepted/claim_support 非産出 を CI gate / snapshot test 化
6. ゴールド評価セット（lawdelta 閾値・treatment/drafter cue の precision 測定）
7. casetreatment → assembler の binding 運用（判例 treatment を条文・法理へ束ねる）

## 8. 一言

法令オブジェクトは、これで「**いつの版か**（形式）」だけでなく「**その版で意味がどう変わり、誰がどう
評価し、旧法理は生きているか**（実質）」を、**断定せず・出典付きで・両論を保持して**扱える土台を得た。
production は重いが、設計は世界標準に接地し、安全弁（candidates-only / claim_support 既定 false /
両論併記 / append-only）は全段に組み込み済みである。

## 9. なぜこれは事務所の発明であり、公的機関には作れないのか（戦略的位置づけ）

本レイヤの核心的価値は「形式（公的データ）」ではなく「**実質＝解釈の構造化**」にあり、これは
**公的機関には原理的に作れない**。本調査が裏付けている。

- **公的データは「形式」までを権威として提供し、「意味の変化」の評価は明示的に放棄している**。
  EUR-Lex の consolidated text は「This text has no legal effect」と明記。英 legislation.gov.uk は
  textual / non-textual effect を分類しても**評価は下さない**。citator は「裁判所が何をしたかを
  報告するだけで、自分の声で『これは死んだ法だ』とは言わない」。
- **公的機関は構造的に「解釈の主体」になれない**（中立性・権限分立ゆえ）。「旧法理はなお妥当する」
  「この改正は実質的射程変更を伴う」という**評価**を出した瞬間、それは中立的事実でなく一つの法的
  見解になるからである。
- **解釈＝評価は、評価者が責任を負って行う法律実務家の本質的職能**。誰が（立案担当者／判例／学説）、
  どの根拠で、どう評価したか——その編集・評価・文脈化こそ ALO データ編成指針の「作るのでなく**編む**」
  であり、事務所固有の判断資産。汎用 LLM も安全に代替できない（法令幻覚 69–88%）。
- 結論: 本発明の要は **「形式は公的データから引用し、実質は事務所の判断資産として、出典付き・
  両論併記・反証可能・断定しない構造で持つ」という切り分けそのもの**にある。
