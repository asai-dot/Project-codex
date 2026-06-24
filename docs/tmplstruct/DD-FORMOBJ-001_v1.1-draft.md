# DD-FORMOBJ-001 v1.1: 書式オブジェクト — 設計文書（監査 DDFORMOBJ_PASS_WITH_NOTES 反映）

> **id**: DD-FORMOBJ-001 / **version**: v1.1-draft / **supersedes**: v1.0-draft（監査参照点として `DD-FORMOBJ-001_v1.0-draft.md` を凍結保持）
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / date: 2026-06-15
> **gate**: 設計のみ。DDL・DB書込み・SF write・MCP公開・accepted化なし。
> **改訂理由**: GPT監査 `DDFORMOBJ_PASS_WITH_NOTES`（2026-06-12）＋統合監査 `DDTMPLINTEG_PASS_WITH_NOTES`（2026-06-13）の修正notesを反映。owner ratify 済（2026-06-15）。
> **最重要の位置づけ変更**: 本DDは **standalone canonical ではない**。MEANING-001 の L1/L2/L3 を背骨とし、FORMOBJ は **L4 design knowledge layer** として統合される（DD-TMPLSTRUCT-INTEGRATION-001）。旧称「P3」は本版以降 **L4** と呼ぶ。

---

## 0. owner テーゼ（本DDの根本前提・不変）

1. **書式だけからの構造化は悪手**。答えのないブラインドテストになる（抽出者=判定者）。
2. 書式は「結論」である。**何を載せるべきか／載せると何が起きるか／なぜその構造か**は書式自体に書かれておらず、**解説書・法令・契約類型論・条項例の解説・書式の書き方**という「理由を語るテキスト」に書いてある。そこが answer key。
3. 契約条項の実務の知恵とは、**条項の原則的なあり方**と、それを**どう緩めるか・どう締めるか**（押し引き）である。
   - 緩んでいるのか締まっているのかは、**観測（書式の読み比べ）だけでは判定できない**。
   - 緩める/締めるが**どちらの当事者ロールに有利/不利か**は、**より大きなコンテキスト**（解説・法令・契約類型）から読んでこなければならない。
4. 大量に読み比べて差分を出すだけなら世のLLMが既にやっている。**法律家の書式議論はそれでは成立しない**。
5. ゆえに **複数の解説書への接地が必須**であり、**文献OCRの進捗が本プロジェクトの律速**である。

## 1. フェーズ／層モデル（統合スタックでの位置）

統合スタック（INTEGRATION-001）における本DDの担当は **L1製造工程・L2材料・L4本体**。L3（束縛overlay）は MEANING-001 の担当で本DDは触らない。

| 統合層 | 旧P呼称 | 本DDの担当 | 状態 (2026-06-15) |
|---|---|---|---|
| **L1 形式** | P1 転写 | form_object content blocks（snapshot/canonical合成＝L1の製造工程） | **できる**。自炊600dpi×vision OCRで実証。restorable_profile 整合 |
| **L2 型** | P2 構造体 | clause.function暫定タグ（=seed）＋意味型slots＋obligations（**材料**） | **動く**。ただしタグは `status: seed/provisional`。正準化は L4接地後（§4ゲート） |
| **L3 束縛** | — | （MEANING-001 担当。FORMOBJ は持たない） | 対象外 |
| **L4 設計知識** ★本体 | P3 意味構造 | **clause_design_knowledge**（baseline＋押し引き＋favors、解説接地） | **本来のゴール**。再委託1件で接地抽出を実証（`poc_grounded/`）。律速は文献OCR |

> L1/L2 は L4 の材料調達。L2 タグは L4 の設計知識から「答え合わせ」されて初めて検証可能になる（=ブラインド脱却）。

## 2. オブジェクトモデル（二層）

### 2.1 form_object（L1/L2層）— 個々の書式
S0-S3 設計を維持（住所先行・snapshot/canonical分離・発明禁止・sticky form_uid）:
```text
form_object
  form_uid / anchor(canonical_book_id + toc_node_id + page_span) / form_title / form_kind
  content(blocks: heading|party|recital|clause|item|signature|date|attachment|note, blanks, …)
  provenance(源別snapshot) / canonical_source / quality / confidence(分解)
  + L2拡張: clause.function_ref(→shared_term_registry.term_id) / status:seed / 意味型slots / obligations|rights
            slotには source_text_locator・extraction_version を必須（§4）
  + L4リンク: clause.design_knowledge_ref → clause_design_knowledge
```
L2のfunctionタグは**暫定（seed）**であり、独自語彙を作らず **shared_term_registry の term_id を参照**する（§2.3・gate_no_vocab_fork）。

### 2.2 clause_design_knowledge（L4層）— 条項機能の設計知識 ★本DDの中心
**単位 = 条項機能**（再委託・損害賠償・知財帰属・支払…）。書式でなく**解説/法令から**抽出する。
```jsonc
clause_design_knowledge {
  term_id,                    // ★shared_term_registry の L2 canonical term への参照（独自語彙禁止）
  design_scope,               // ★clause | clause_family | option_axis | party_role | procedure_form（粒度差吸収・統合N1/Q2）
  narrower_term_ref,          // ★必要時のみ。別語彙でなく registry 内の下位term（例 payment→late_payment_interest）
  applies_to_document_type,   // ★適用文書型
  applies_to_party_role,      // ★適用当事者ロール
  baseline,                   // 条項の原則的なあり方
  rationale_why,              // なぜその原則か（当事者構造・リスク配分）
  must_address: [],           // 載せるべき論点
  design_options: [{          // ★押し引きモデル（§3）
    axis_type,                // ★統制語彙（§3.1）。permission_condition|liability_scope|…
    choices: [{
      choice, effect,
      favors_role,            // ★当事者「ロール」で記録（principal/contractor/…）。当事者名でなく role（統合・FORMOBJ Q1）
      favors_basis,           // ★commentary_explicit|statute_structure|case_law|practice_manual|observed_hypothesis_only
      tightness,              // tighten | loosen | neutral（baselineに対して）
      // 観測のみ由来は accepted に入れず hypothesis 隔離（§3.2）
      hypothesis_favors_role, // ★観測由来の仮説（accepted favors とは別フィールド）
      hypothesis_tightness,   // ★観測由来の仮説
      legal_caveat
    }]
  }],
  legal_basis: [],            // 法令・改正・一問一答・判例
  grounded_from: [{           // ★引用必須（接地の証跡＝answer key）
    source, printed_pages, pdf_pages, toc_anchor, extracted_by,
    grounding_type,           // ★commentary_explanation|statute_text|official_guidance|case_law|practice_manual|observed_template_variation（統合R2）
    evidence_purpose          // ★identity_anchor|design_rationale|legal_basis|drafting_guidance|observed_variation（統合N2）
  }],
  source_diversity: {         // ★単なる冊数でなく独立性（統合R3/N3）
    n_books, n_independent,   // 同一出版社・同一著者系列・同一テンプレ再利用は独立票にしない
    independence_checked
  },
  status,                     // ★seed | candidate | accepted | deprecated（§4.2）
  form_instances: []          // この知識のインスタンスである書式（form_uid/条項例）へのリンク
}
```
**検証原則**: タグの正しさは「私がそう思う」でなく**引用追跡**で検証（grounded_from の解説テキストに根ざすか）。ブラインド脱却の仕組みそのもの。

### 2.3 接合キー（独自語彙を作らない）— 統合N1
- `clause_design_knowledge.term_id` と `clause.function_ref` は、ともに **shared_term_registry の L2 canonical term_id を参照**する。
- 旧 v1.0 の「clause_function ≡ clause_type（完全同義）」は**強すぎる**ため撤回。**「同一 term_id を参照する」**を必須条件にし、粒度差は `design_scope` / `narrower_term_ref` で吸収する（例: L2 `payment` に対し L4 で `late_payment_interest` を下位局面として扱う）。
- 別名前空間の語彙生成は禁止（`gate_no_vocab_fork`）。

## 3. 押し引きモデル（L4の核）

- 各条項機能に **baseline（原則形）** がある。実務の知恵は baseline からの **tighten/loosen** とその **favors_role（有利不利の方向）**。
- **観測（書式読み比べ）では tightness も favors も確定できない**。解説・法令という大きなコンテキストからのみ確定値を取る。

### 3.1 axis_type 統制語彙（FORMOBJ Q1）
`permission_condition` / `liability_scope` / `notice_or_consent` / `burden_of_proof` / `termination_trigger` / `monetary_risk` / `confidentiality_scope` / `procedural_step`（不足は registry に candidate 追加し帰納的に拡張）。

### 3.2 favors は role・観測は仮説隔離（FORMOBJ Q1/Q2）
- **favors_role**：当事者名（甲乙・委託者受託者）でなく **role 語彙**で記録（`principal/contractor/consignor/consignee/buyer/seller/employer/employee/applicant/respondent`）。甲乙は文書ごとに反転するため。
- **観測は仮説生成までOK・確定は不可**：複数書式の統計的観測は `hypothesis_favors_role` / `hypothesis_tightness` に**隔離**し、`favors_role`/`tightness`（accepted）へ自動昇格させない。確定は解説・法令の記載（`favors_basis ≠ observed_hypothesis_only`）からのみ。
- 実証例（再委託, `poc_grounded/saiitaku.knowledge.json`）:
  - baseline: 原則禁止＋事前承諾で限定許容
  - 押し引き: 責任を「選定・監督のみ」に限定 → **loosen / favors_role=contractor** ／ 全責任 → **tighten / favors_role=principal**（favors_basis=statute_structure：旧民法105条1項削除）

## 4. ゲート（v1.0継承＋監査反映）

継承: `gate_form_anchor_required` / `gate_sticky_form_uid` / `gate_no_blank_invention` / `gate_snapshot_per_source` / `gate_no_node_invention_in_merge` / `gate_quality_overlay_not_silently_absorbed` / `gate_no_auto_group` / `gate_page_calibration_recorded` / `gate_grounding_citation_required` / `gate_no_blind_tagging` / `gate_favors_from_context_only` / `gate_source_diversity_tracked`

**監査反映で更新・新設**:
- `gate_no_vocab_fork` ★ — function_ref / term_id は shared_term_registry の term_id のみ（統合N1）。
- `gate_favors_role_not_party` ★ — favors は当事者名でなく role 語彙（FORMOBJ Q1）。
- `gate_observation_hypothesis_isolated` ★ — 観測由来は hypothesis_* に隔離、accepted へ自動昇格しない（FORMOBJ Q2・更新版 gate_favors_from_context_only）。
- `gate_grounded_from_typed` ★ — grounded_from に grounding_type＋evidence_purpose 必須（統合R2/N2）。
- `gate_l2l4_grounding_separation` ★ — L2 identity_anchor と L4 design_rationale を同一metricで扱わない（統合N2）。

### 4.1 L2（暫定タグ）の大量先行：条件付き可（FORMOBJ Q4）
**許容条件**：status=seed/provisional ／ source_text_locator あり ／ extraction_version 記録 ／ accepted legal meaning なし ／ sf_binding write なし ／ MCP publication なし ／ 後段 L4接地で検証・棄却可能。
**禁止**：ungrounded タグを canonical 扱い／大量生産で不確実性を隠蔽／同一surfaceラベルが未追跡の複数意味を生む／ブラインドラベルを法的助言・claim support に使用。

### 4.2 L4 status 昇格規律（FORMOBJ R4・統合Q3/N3）
| status | 条件 |
|---|---|
| **seed** | 1書式/1抽出の観察。助言・根拠に使わない |
| **candidate** | grounded_from あり（解説/実務書≥1）。owner レビュー未確定。**単一書籍はここ止まり** |
| **accepted** | grounded_from あり＋**source独立性確認**＋未解決矛盾なし＋**適用scope明示**＋owner/reviewer ratify |
| **deprecated** | 法改正・新解説・owner判断・より良い設計知識で更新 |
- **L2参照品質の制約（統合・MEANING SEED連動）**：L4 は seed/candidate の L2 term を参照してよいが、L4 が **accepted になるには参照先 L2 term が最低 candidate かつ label-cohesion / anchor-quality レビューを通過**していること（または owner override の明示）。

## 5. パイプライン（統合版・INTEGRATION-001 §5 と整合）

```
[S1] アドレス確定        式→toc_node→page_span                         （実装済: 会社議事録321式完全一致）
[S2] L1スナップショット   書式頁OCR→snapshot→canonical（restorable整合） （実装済: 3タイプ）
[L2] 型付け(seed)         function_ref/semantic_type 付与＋anchor解決＋source_text_locator （MEANING SEED連動・要改訂反映）
[S2.5/L4] 解説接地        解説節OCR→clause_design_knowledge（grounded_from typed 必須）（PoC実証）
[S3] canonical合成        源優先＋粒度ガード＋発明禁止                     （実装済: 9/9）
[S3.5] 知識合成           同一 term_id の L4 を複数解説書から合成（独立性確認・出典別併記）
[V]  検証                L2 anchor品質＋L4 引用追跡＋三点測量
[reg] レジストリ登録      shared_term_registry に term＋L2＋L4 を紐付け
[S5] 永続化              （Mac側承認フロー。accepted化は owner ratify のみ）
```

## 6. 既存資産（全て実証/実装済み・不変）

| 資産 | 状態 |
|---|---|
| 所蔵突合: 出典本101冊中89冊所蔵（書式3,762件分） | DB確認済 |
| 自炊監査: 1,148冊・4点セット規約 | 実地確認済 |
| 環境内vision OCR経路（Box preview, ≤約365MB） | 実証済（3書式＋解説頁） |
| `biblio.toc_nodes`: 弁コム552,544行・sticky ID | ライブ（LIONBOLT=次PJ） |
| S1リゾルバ＋バルクハーネス（7/7・5/5） | 実装済。会社議事録321式anchor確定 |
| form_snapshot.v1（S2標準・3参照実装） | 確定 |
| S3 canonical merge（9/9） | 実装済 |
| L4 PoC: 横断クエリ（機能行列/同機能比較/義務集計/ギャップ検出） | 実証済（限界も記録） |
| 解説接地PoC: 再委託の design_knowledge | 実証済（`poc_grounded/`） |

## 7. ロードマップ（オントロジー後置＋registry shell 早期設置）

| 段 | 内容 | 依存 |
|---|---|---|
| R0 ★ | **shared_term_registry shell** を早期設置（発散防止の仮置き台帳）。term_id/pref_label/provisional_aliases/status/source_basis/linked_l2/linked_l4_count | 即着手可（設計のみ） |
| R1 | 文献OCRの量産態勢: 本丸再自炊＋自炊済み本の解説章ポイントOCR | スキャン発注済・経路実証済 |
| R2 | 業務委託契約で L4 を1類型ぶん完成（再委託に続き、損害賠償・知財・支払…を同書＋他解説書で接地） | R1の一部 |
| R3 | 複数解説書の知識合成（S3.5）を1機能で実証（**独立** source ≥ 2） | R1 |
| R4 | 条項機能オントロジー正準化（L4知識が貯まってから帰納的に。先験的に作らない） | R0-R3 |
| R5 | コーパス全体への展開・DB化（toc_nodes隣接） | R1-R4＋LIONBOLT(次PJ) |

> **オントロジーを先に設計しない**。ただし**発散防止の registry shell（R0）は先に置く**（監査 Q3）。完成オントロジーと仮置き台帳は別物。

## 8. owner決定事項（v1.1・監査反映済）

| ID | 問い | 決定 |
|---|---|---|
| D-F5 | 構造の源 | 解説・法令・契約類型から抽出（書式は一インスタンス）— 採用 |
| D-F6 | L4の中心モデル | baseline＋押し引き（tighten/loosen × favors_role）— 採用。axis_type統制・favorsはrole |
| D-F7 | 検証方式 | 引用追跡（grounded_from typed 必須）でブラインド脱却 — 採用 |
| D-F8 | 律速の認識 | 文献OCRが進まないと書式は前に進まない — 共有認識 |
| D-F9 | 層認識 | L1製造/L2材料/L4本体。L3はMEANING担当。**FORMOBJはL4として統合**（standalone canonical化しない）— 採用 |
| D-F10 ★ | 観測の扱い | 観測は仮説生成まで（hypothesis隔離）。確定は解説・法令から — 採用 |
| D-F11 ★ | 接合キー | 独自語彙を作らず shared_term_registry の term_id を参照（≡でなく参照）— 採用 |

## 9. 改訂履歴
- **v1.1-draft（2026-06-15・本版）**：監査 `DDFORMOBJ_PASS_WITH_NOTES`＋`DDTMPLINTEG_PASS_WITH_NOTES` 反映。P3→L4 改称、favors→role＋axis_type統制、観測の hypothesis 隔離、grounded_from の typed化（grounding_type/evidence_purpose）、source独立性、L4 status昇格規律、term_id参照（fork禁止）、registry shell 早期設置（R0）。owner ratify 済。
- v1.0-draft（2026-06-11）：監査提出版（凍結・参照点）。
