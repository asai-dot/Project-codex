### DD-LINKBOOT-001 v0.1: 反復・文脈累積リンキング（Iterative context-accretion link promotion）

> **id**: `DD-LINKBOOT-001` / **version**: v0.1 / **status**: candidate / **gate**: DDLINKBOOT
> **recorded_at**: 2026-06-08 / **owner**: 浅井 / **author**: Project-codex Fork 4 (claude-code remote)
> **depends_on**: DD-TOCLEGALREF-001 **v0.2 (ratified)** / 35_link_layer v0.1 /
>  31_case_layer v1.4 / 30_law_layer / DD-LAWTIME-001 (candidate) / 32_literature_layer / control.*
>
> 自信のないリンクを無理に張らない。**固い(high)リンクを先に確定し、それを「その本／類似本が
> 何の法律を扱う本か」という文脈として立ち上げ、後続パスで quarantine 候補を文脈付きで再採点して
> 閾値を越えたものだけ昇格する**——という多パス昇格機構。DD-TOCLEGALREF v0.2 の medium 昇格条件
> （gold set で precision≥0.95）を満たす具体手段。**DB 書込みなし**（accept＋層実装後）。

---

## §0 原則
- **precision-first**：閾値未達の候補は出さない。quarantine 据え置きは「失敗」ではなく正常状態。
- **単調・無撤回志向**：一度確定した high アンカーは撤回しない。撤回が要るときは別パスで明示 invalidate（candidate のまま、silent retraction 禁止）。
- **claim_support 据え置き**：昇格しても `claim_support_eligible=false` は維持（v0.2 継承）。
- **文脈は“固いもの”由来のみ**：主題モデルは high アンカー由来で作り、生の部分文字列一致は使わない（§1 の失敗例）。

## §1 問題設定と実証所見（PRECISION_VALIDATION_6000）
6,000ノード実測で medium precision = **0.906 < 0.95**（high=1.000 / low=0.615）。
- **素朴な「書名に法令名が含まれれば昇格」は無効**：confirmed 0.885 ＜ unconfirmed 0.912。
  書名にも substring バグが再輸入される（『QA法人登記の実務_医療法人』の "医療法"）。
- だが **medium FP 10件中 7件は「本の主題が別」の本に集中**：『病院・診療所経営』の医療法**人**、
  『渉外不動産登記』のブラジル民法、『ドイツとEUにおける税務裁判』の独法人税法、『日仏…』の都市計画法**制**。
- → **主題事前確率（anchor 由来）＋境界/外国ガードで分離可能**、というのが本 DD の仮説。

## §2 機構（multi-pass）
1. **Pass-1 アンカー**：`high`（条番号つき, 実測 precision 1.000）のみ確定。各本の `anchor_laws(book)` を生成。撤回しない。
2. **主題モデル `subject_prior(book, law)`**：
   - 主：`anchor_laws(book)`（同一本の high リンク）。
   - 従：書名由来だが **境界判定後**（医療法**人** を法令名として数えない）。
   - 伝播：近傍本（共有 anchor / 著者 / 分類でクラスタ）へ重み付き伝播。クラスタ純度閾値で過伝播を抑制。
   - 生 substring は不使用。
3. **機械ガード `fp_guard(law, text)`**（強制 quarantine 維持）：
   - 境界：直後が `人|制|院` 等／longest-known-term で別語を形成（海商法・民商法・国際民事訴訟法・罪刑法定・モニター商法）→ 否定。
   - 外国文脈：近接に `ブラジル|中国|ドイツ|独|EU|アメリカ|日仏|欧州|韓国|フランス` → 否定。
4. **Pass-2 再採点**：quarantine の medium を `subject_prior × fp_guard` で再採点。posterior が閾値を越えた候補**のみ** `rollout_status=initial` へ昇格。残りは quarantine 据え置き。
5. **反復**：昇格で anchor が増え主題モデルが濃くなる → 次パスで未解決候補を再評価。**新規昇格ゼロで収束停止**。
6. **監査性**：各昇格に `promotion_evidence`（採用 anchor / 伝播元の近傍本 / 通過 guard / posterior）を必須付与。

## §3 評価・ゲート（accept 条件）
- gold set **≥300**（層化）で pass-2 昇格集合の sampled precision **≥0.95** を確認してから promotion 有効化。
- 提案 gate：
  - `gate_no_promotion_without_subject_evidence`（promotion_evidence 必須）
  - `gate_promoted_precision_meets_threshold`（gold で ≥0.95）
  - `gate_foreign_context_never_promoted`
  - `gate_compound_boundary_guarded`
  - `gate_monotonic_no_silent_retraction`
  - `gate_claim_support_stays_false_on_promotion`

## §4 スコープ／非対象
- v0.1 は **TOC statute medium のみ**。case candidate・cross-domain は将来版。
- temporal は DD-LAWTIME 遮断を継承（昇格しても `valid_from=NULL` / 版解決禁止）。
- **DB 書込みなし**。実装＆実測（B フェーズ）は owner 指示時。

## §5 risks
- 主題モデルの過剰一般化（会社法の本の中の刑法言及を会社法へ吸わない＝**law 単位 prior**で緩和）。
- 近傍伝播のドリフト（クラスタ純度閾値・伝播減衰で緩和）。
- 単調性と「誤昇格の是正」の両立（昇格も candidate 層に置き、是正は明示 invalidate パスで）。

## §6 changelog
- v0.1 (2026-06-08): 初版。DD-TOCLEGALREF v0.2 ratified を前提に、medium 昇格の多パス機構を設計。
  実証（PRECISION_VALIDATION_6000）で「主題ミスマッチ本に FP が集中／素朴な書名一致は無効」を確認し、
  anchor 由来の主題モデル＋境界・外国ガード＋閾値昇格＋反復、を機構化。
