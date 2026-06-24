# DD-LINKBOOT-001 v0.1.1 反映 ＋ B（検証prototype）実装計画

> 種別: **実装計画（repo）**。canonical DD は Box `alo/DD-LINKBOOT-001_iterative_context_accretion_linking_v0.1.md`。
> 競合SoTを作らない。本書は v0.1 への GPT 監査 `DDLINKBOOT_PASS_WITH_NOTES`（2026-06-08, Box
> `from_gpt/20260608_linkboot_v0.1_DDLINKBOOT_RESULT.md`）の **required_patches 7点**を v0.1.1 として反映し、
> **B＝検証prototype** の範囲・受入を固定する。
>
> **ゲート状態**: A=合格（設計候補 accept）/ owner ratify 方向。**B は実装ではなく prototype 検証**。
> **production promotion 禁止**＝gold set ≥300（層化）で promoted precision **≥0.95** 実測まで。
> **`claim_support_eligible=false` を全工程で維持**。**B は DB 書込みなし**（eval/staging のみ）。
>
> 上流依存: DD-TOCLEGALREF-001 **v0.2 (ratified)**（TOC→法令参照 candidate, tier=high/medium/low）/
> 本リンク層が消費する TOC は legallib **bib_toc 詳細TOC（Phase 0.1 で 661,141 nodes へ回復）**。
> temporal は DD-LAWTIME 遮断を継承（昇格しても `valid_from=NULL`・版解決禁止）。

---

## A. required_patches 7点の反映（v0.1.1・B着手前に拘束）

### P1. `anchor_source` を4状態に分離（F2）
アンカーを単一視しない。状態と遷移を固定：

| anchor_source | 由来 | subject_prior 重み |
|---|---|---|
| `seed_high` | Pass-1 の high（条番号つき・実測 precision 1.000, Wilson下限0.896） | **満額**（継続監視＝`gate_seed_high_precision_monitored`） |
| `promoted_candidate` | Pass-2 で posterior≥θ 昇格・未検証 | **減衰**（P2, λ<1） |
| `validated_promoted` | gold/レビューで確認後 | **満額** |
| `invalidated` | 誤昇格を明示無効化（P7） | **0**（かつ negative_anchor へ） |

遷移: high link→`seed_high` / Pass-2 posterior≥0.95→`promoted_candidate`(rollout_status=initial) /
gold確認→`validated_promoted` / 誤り検出→`invalidated`(明示・監査保持)。

### P2. 反復汚染防止＝`promoted_candidate` の減衰（F2/F3）
- subject_prior で `promoted_candidate` 由来 anchor に重み **λ（既定0.3, 調整可）** を掛ける。`seed_high`/`validated_promoted` のみ満額。
- さらに**周回減衰** `decay^pass_no` を掛け、1件の誤昇格がクラスタ全体を汚染しないようにする。
- 伝播は **`min_seed_anchors`（≥2 など）の seed_high を持つ本/クラスタからのみ**起動。`promoted_candidate` 単独では伝播 prior を立てない。

### P3. `subject_prior(book, law)` の算出式を明文化（F4）
```
subject_prior(book, law) = σ(
      w_a · anchor_term(book, law)          # seed_high/validated=1.0, promoted=λ の重み付き本数
    + w_t · title_boundary_term(book, law)  # 書名一致は「境界判定後」のみ1（生substring不使用）
    + w_c · cluster_prop_term(book, law)    # 近傍本伝播（decay^hops·purity, capped）
    − w_f · foreign_comparative_penalty     # 外国/比較法文脈ペナルティ
)
```
- `anchor_term` = Σ_{a ∈ anchor_laws(book)} weight(anchor_source(a))·1[law(a)=law]
- `title_boundary_term` = 1[law が書名に **longest-known-term 境界判定後** 出現]（医療法**人**→医療法 を数えない）。生 substring 不使用。
- `cluster_prop_term` = Σ_{n ∈ neighbors(book)} decay^hops · cluster_purity · seed_anchor_frac(n, law)。
  起動条件: `cluster_purity ≥ τ` かつ `hops ≤ max_hops` かつ n が `min_seed_anchors` 以上。foreign/comparative 本は伝播停止 or 別 profile 隔離。
- `foreign_comparative_penalty` = 1[候補近接 or 本レベルで外国/比較法文脈]。
- `posterior(candidate)` は σ 出力を **gold で校正**（F4: calibration curve / reliability table）。
  **昇格条件 = posterior ≥ 0.95 かつ fp_guard 通過 かつ foreign でない**。
- パラメータ `{w_a,w_t,w_c,w_f, λ, decay, τ, max_hops, min_seed_anchors}` は `model_version` に固定記録。

### P4. `promotion_evidence` schema を固定（F1/F5・監査性）
昇格1件＝1行、必須列：
```
candidate_id, book_id, law_id, pass_no, posterior,
anchor_source_used[],            # 採用 anchor の状態（seed_high/promoted_candidate/validated_promoted）
seed_anchors[],                  # 採用した seed_high anchor の id/law
propagated_from[],               # 伝播元 neighbor book_id + hops
guards_passed[], guards_blocked[],
subject_prior_components{anchor,title,cluster,foreign_penalty},
model_version, goldset_version, scorer_commit, created_at,
rollout_status='initial', claim_support_eligible=false
```

### P5. gold set ≥300 を層化（F5）
candidate 単位の無作為だけでは同一本/クラスタ相関で precision 過大評価。**層化必須**：
- 軸: `book-level / law-level / cluster-level`
- FP-risk type: `foreign_context / compound_boundary(医療法人型) / comparative_law / generic_medium`
- 各層に最小件数を割当、**per-stratum precision ＋ overall** を報告（Wilson下限つき）。
- 合格条件: overall ≥0.95 **かつ** 各層 ≥0.95、**foreign_context 層は FP=0**。
- F4 校正: holdout で reliability table を出し、posterior≥0.95 帯の実測 precision が ≥0.95 か確認。

### P6. rollout / claim_support フラグ（必須・無条件）
- 昇格行はすべて `rollout_status='initial'` ＋ `claim_support_eligible=false`。
- production 有効化は **gold ゲート通過後に owner が明示**するまで不可。
- **B は DB 書込みなし**（eval 出力 or staging のみ）。本番 link テーブルへの INSERT 禁止。

### P7. `no_silent_retraction` ＋ `explicit_invalidate` 手順（F2/単調性）
- 誤昇格は**静かに消さない**。`anchor_source='invalidated'` ＋ `invalidation_evidence{reason, who, when, superseded_posterior, pass_no}` を残し、当該 law を `negative_anchor_laws(book)` に追加。
- 後段の読み手規約: `invalidated` は subject_prior と serving から**除外**するが、行は**監査保持**。
- 単調・無撤回志向は「確定 seed の不撤回」であり、是正は別パスの明示 invalidate で行う（candidate 層に留まる）。

---

## B. ゲート（GPT proposed_gates を採用）
`gate_seed_high_precision_monitored` / `gate_no_promotion_without_subject_evidence` /
`gate_promoted_precision_meets_threshold_gold300_stratified` / `gate_foreign_context_never_promoted` /
`gate_compound_boundary_guarded` / `gate_promoted_anchor_damped_until_validated` /
`gate_monotonic_no_silent_retraction` / `gate_explicit_invalidate_preserves_audit` /
`gate_claim_support_stays_false_on_promotion` / `gate_posterior_calibrated_on_holdout`

---

## C. B＝検証prototype の範囲・受入

### in scope
1. **pass-2 スコアラ prototype**（オフライン・DB書込みなし）: 入力＝DD-TOCLEGALREF v0.2 の candidate
   （high/medium/low）＋ 各本の TOC（legallib bib_toc）。§A の subject_prior×fp_guard で medium を再採点。
2. **層化 gold set ≥300 構築**（P5）。
3. **実測**: medium→promoted precision を gold で per-stratum＋overall、calibration curve、収束（新規昇格0で停止）。
4. **成果物**: 実測レポート ＋ `promotion_evidence` サンプル ＋ reliability table ＋ scorer prototype コード。

### acceptance（B 完了条件）
- promoted precision **≥0.95**（overall＋各層、foreign 層 FP=0）を**実測**。未達なら未達理由＋上位FPパターンを添えて据え置き（=正常）。
- promotion_evidence が P4 schema を満たす。
- **DB書込み0 / production無効 / claim_support_eligible=false** の維持を証跡で示す。

### out of scope（v0.1 継承）
- case candidate・cross-domain・temporal（DD-LAWTIME 遮断）・claim_support 利用・本番 link テーブル投入。

---

## D. 進め方
1. 本 v0.1.1（§A 7点）を owner ratify（GPT は反映前提で PASS_WITH_NOTES）。
2. worker へ B WO 投函（scorer prototype＋gold≥300＋実測, DB書込みなし）。
3. 実測レポート回収 → precision≥0.95 なら owner 判断で production 有効化検討（別ゲート）。未達なら据え置き＋FP分析で次反復。

> 注: 本リンク層は legallib 詳細TOC（661K nodes）を主入力にする。TOC 取込（legallib v0.5.2, INGEST）が
> 進むほど anchor 母数と主題モデルが濃くなる。両者は同じ「Links Are the Core Asset」原則の表裏。
