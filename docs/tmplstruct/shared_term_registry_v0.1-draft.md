# shared_term_registry v0.1 — 条項機能 正準term台帳（L2↔L4 接合・registry shell）

> **version**: v0.1-draft / **owner**: 浅井 / **author**: 番頭(リモートClaude) / date: 2026-06-15
> **gate**: 設計のみ。DDL・DB書込みなし。
> **由来**: 監査 `DDFORMOBJ_PASS_WITH_NOTES` Q3（発散防止の registry shell を早期設置）＋`DDTMPLINTEG_PASS_WITH_NOTES` N1（接合キーは独自語彙でなく shared term_id）。
> **位置づけ**: 統合スタック（INTEGRATION-001）の **接合キー**。MEANING-001 §6 の `shared_term_registry` を正本とし、本DDで **L4 外部キー**を追加する。先験的オントロジーではなく**発散防止の仮置き台帳**。

---

## 0. 目的（何のための台帳か）

- L2（MEANING：clause_type/semantic_type 統制語彙）と L4（FORMOBJ：clause_design_knowledge）が **同じ term を指す**ことを保証する単一の正準台帳。
- 各 PJ が template専用語彙を **fork しない**ための共有レジストリ（MEANING Q6 ブロッキング指示）。共有相手: DD-D1LIC（判例）/ ALO-KB / biblio / lawsubtrans。
- **発散防止**：オントロジー完成を待たず、term を `seed` で受け、独立性・接地が揃ったものだけ `accepted` に昇格させる。

## 1. レコード schema（registry shell）

```jsonc
shared_term {
  term_id,                    // 正準ID（snake_case, 安定・不変）。例: subcontracting
  pref_label,                 // 代表ラベル（日本語）。例: 再委託
  provisional_aliases: [],    // 暫定別名（観察surface）。synonym のみ（related/example は別）
  status,                     // seed | candidate | accepted | deprecated（§3）
  source_basis,               // この term をなぜ起こしたか（observed_in_office_templates 等）

  // ---- L2 連携（MEANING） ----
  linked_l2: {
    clause_type,              // L2 clause_type ラベル
    semantic_type,            // 任意
    anchor: {                 // L2 anchor authority（恒等性の接地）
      anchored, anchor_source,// alo-kg | egov | jlt | abbreviation_dict | null
      anchor_match_kind,      // exact | exact_term | exact_article_title | substring_*
      authority_class,        // authoritative_anchor | weak_observation_anchor | non_anchor（SEED監査FF-1）
      label_cohesion_reviewed // bool（SEED監査FF-2）
    },
    l2_status                 // L2 側の seed/candidate/accepted
  },

  // ---- L4 連携（FORMOBJ） ----  ★本DDで追加
  linked_l4: {
    design_knowledge_ref,     // clause_design_knowledge への参照（複数可）
    design_knowledge_count,   // この term に紐づく L4 知識の数（発散監視）
    narrower_terms: [],       // registry 内の下位term_id（別語彙でなく）。例 payment→[late_payment_interest, withholding]
    l4_status                 // L4 側の seed/candidate/accepted（§3）
  },

  domain,                     // civil_obligation | civil_contract | corporate | labor | procedural | cross_practice | general | boilerplate
  version,                    // term scheme version
  notes
}
```

## 2. 接合不変条件（gate）

- `gate_no_vocab_fork` — L2 `clause.function_ref` も L4 `clause_design_knowledge.term_id` も、必ず **shared_term_registry.term_id を参照**。別名前空間禁止。
- `gate_l4_keyed_by_l2` — L4 レコードは linked_l2 を持つ term にのみ紐づく（未登録キー禁止）。
- 粒度差は `linked_l4.narrower_terms`（registry内下位term）で表現。L4 が独自に語彙を増やさない。

## 3. status 昇格規律（L2・L4 を分けて持つ）

| status | L2（identity） | L4（design knowledge） |
|---|---|---|
| **seed** | 観察＋curated clustering で起こす | 1書式/1抽出の観察。助言に使わない |
| **candidate** | 100件規模で再現観察 | grounded_from あり（解説≥1）。**単一書籍はここ止まり** |
| **accepted** | 3,806件＋cross-source整合＋**authoritative_anchor**＋label-cohesion通過＋owner ratify | grounded_from＋**source独立性**＋矛盾なし＋scope明示＋owner/reviewer ratify |
| **deprecated** | 統廃合・意味変更 | 法改正・新解説・より良い知識で更新 |

**連動制約（INTEGRATION N5）**：L4 を `accepted` にするには、参照先 L2 term が **最低 candidate かつ label-cohesion / anchor-quality 通過**（または owner override 明示）。

## 4. 接地の証跡（evidence framework・共通／purpose分離）

L2 と L4 は共通の evidence object を使うが `evidence_purpose` で目的を分ける（INTEGRATION N2）:
```text
evidence_purpose: identity_anchor | design_rationale | legal_basis | drafting_guidance | observed_variation
```
- L2 anchor は `identity_anchor`、L4 grounded_from は `design_rationale` / `legal_basis` / `drafting_guidance`。
- `observed_variation`（書式観測）は**仮説生成のみ**。accepted の根拠にしない。

## 5. 初期 seed の起こし方（B discover / A normalize）

- **B（事務所書式・解説から帰納）= discovery**：実際に出る term を `seed` 投入。
- **A（alo-kg / e-Gov / 民商法章節）= stabilizer**：normalization anchor。全部入りにしない。
- canonical term は **B が A にマップされるか明示レビューを通った時のみ**成立（worker は全 term を `seed` 出力、昇格は番頭→GPT→owner）。

## 6. 実装メモ（将来・HOLD）

- 物理化は toc_nodes 隣接テーブル（term は registry、L2タグ/L4知識は別テーブルで term_id FK）。**DDL は HOLD**（accepted 規律と owner ratify 後）。
- v0.1 は JSON/JSONL の設計スタブで十分。コーパス規模で DB 化。

## 7. 改訂履歴
- v0.1-draft（2026-06-15）：監査反映で新設。MEANING §6 を正本に L4 FK（linked_l4）を追加、status を L2/L4 分離、evidence_purpose 共通framework、registry shell として早期設置（FORMOBJ R0）。
