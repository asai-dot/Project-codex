> ⚠ **SUPERSEDED by `DD-TMPLSTRUCT-INTEGRATION-001_v0.2-draft.md`**（2026-06-15、監査 `DDTMPLINTEG_PASS_WITH_NOTES` 反映）。本v0.1は**監査提出版＝参照点として凍結**。現行はv0.2を見ること。

# DD-TMPLSTRUCT-INTEGRATION-001 v0.1: 書式構造2系統の統合（FORMOBJ-001 × MEANING-001）

> **id**: DD-TMPLSTRUCT-INTEGRATION-001 / **version**: v0.1-draft
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / date: 2026-06-12
> **gate**: 設計のみ（DDL・DB書込み・SF write・accepted化なし）
> **統合対象**:
> - **DD-FORMOBJ-001 v1.0-draft**（本リモートセッション。Pモデル＝P1転写/P2構造体/P3意味構造。解説接地の設計知識が中心）
> - **DD-TMPLSTRUCT-MEANING-001 v0.3.1-draft**（Mac側。Lモデル＝L1形式/L2型/L3意味overlay。GPT監査 `DESIGN_PASS_WITH_NOTES`、seed実装は `REVISION_REQUIRED`）
> **基本姿勢**: どちらも canonical を一方的に supersede しない。本DDは両者を**1つのスタックへ調停する提案**であり、それ自体を監査に回す（look-before-build / 並行canonical禁止の規律に従う）。

---

## 0. 結論（先に）

2系統は**重複ではなく相補**である。誤読を避けるため最初に確定させる：

- **MEANING-001 = 型付け・接地・束縛の背骨**（form → 統制語彙 → concept_uri / SF binding）。既存資産（alo-kg 10,772定義 / e-Gov / shared_term_registry / seed→accepted 機構）を持つ。
- **FORMOBJ-001 = 設計知識の背骨**（解説接地の *なぜ / 押し引き / 有利不利*）。MEANING が**空けている** legal_effect / 規範的意味を埋める。
- 両者の接合キーは **統制語彙の正準term**：FORMOBJ の `clause_function` は MEANING の `clause_type`（正準term）と**同一物**にする。**語彙を fork しない**（MEANING Q6 のブロッキング指示＝shared_term_registry を使う）。

→ 統合形は **L1–L4 の単一スタック**。FORMOBJ の P3 は MEANING の L3 を**置換しない**。L3 の**上に乗る新層 L4（design knowledge）**として位置づける。

## 1. 層モデルの対応（P-model ↔ L-model）

| 統合層 | 内容 | FORMOBJ(P) | MEANING(L) | 調停 |
|---|---|---|---|---|
| **L1 形式** | 観察事実。document_hash で不変 | P1 転写（form_object content blocks＝snapshot/canonical） | L1 form（restorable_profile_v0.2.1） | **L1 を正本**。FORMOBJ の snapshot/canonical 合成（S2/S3）は L1 を生成する**製造工程**として位置づけ。出力スキーマは restorable_profile に整合させる |
| **L2 型** | 統制語彙による型付け。seed→candidate→accepted | P2 の clause.function暫定タグ＋typed slots＋obligations | L2 schema（clause_type / semantic_type、anchor必須、status機構） | **L2 を正本**。FORMOBJ の「暫定function タグ」＝MEANING の `status: seed`。**両者の反ブラインド規律は同一物**（§4） |
| **L3 束縛overlay** | concept_uri / sf_binding / legal_effect / relations。版管理 | （FORMOBJ には無い） | L3 semantic overlay | **MEANING L3 をそのまま採用**。FORMOBJ は L3 を持たないので競合なし |
| **L4 設計知識** ★新 | 条項機能の *baseline＋押し引き＋favors*、**解説接地**（grounded_from必須） | **P3 = clause_design_knowledge** | （MEANING は legal_effect を「L3かDD-D1LIC」に委ね、ここは空） | **FORMOBJ の P3 を L4 として新設**。L2 の正準term をキーに L4 を引く |

**重要な非対称**：旧 FORMOBJ の「P3」と MEANING の「L3」は**別物**だった。
- MEANING L3 = *外延的束縛*（このslot→このSFフィールド、この concept_uri、この法効果タグ、文書間relations）。
- FORMOBJ P3 = *内包的設計知識*（なぜこの条項か、どう締める/緩める、どちらに有利か）。
- ゆえに衝突せず**積層できる**。L3 が「何に繋がるか」、L4 が「なぜその形か・どう動かすか」。

## 2. 接合キー：clause_function ≡ L2 正準 clause_type

- FORMOBJ の `clause_function`（再委託・損害賠償・知財帰属・支払…）は、**MEANING の L2 統制語彙の正準term と同一名前空間**にする。
- 実体は MEANING §6 の **`shared_term_registry`** に置く（template専用語彙を fork しない）。FORMOBJ・MEANING・DD-D1LIC（判例）・lawsubtrans が同じ台帳を共有。
- L4 `clause_design_knowledge.clause_function` は **`shared_term_registry` の正準term への外部キー**。未登録の機能名で L4 を起こすことを禁止（§5 gate）。
- 逆向き：L2 の `clause_type` に L4 設計知識が存在すれば、`clause_type.design_knowledge_ref → L4` で双方向に引ける（FORMOBJ §2.1 の P3リンクを L2↔L4 リンクとして正式化）。

```
shared_term_registry（正準term台帳・PJ横断）
  term: "subcontracting"
    ├─ L2 (MEANING):  clause_type ラベル群 / anchor(alo-kg,egov) / status / sf_binding_map(L3)
    └─ L4 (FORMOBJ):  clause_design_knowledge（baseline/push-pull/favors/grounded_from）
```

## 3. 検証思想の合流（両監査の指摘は同根）

FORMOBJ と MEANING は**同じ「自動結論の禁止」規律**を別の層で言っている。統合して用語を揃える：

| 規律 | MEANING（L2/L3）での呼称 | FORMOBJ（L4）での呼称 | 統合後 |
|---|---|---|---|
| 出所のない断定をしない | anchor authority tiers / `no AUTO_ACCEPTED_SEMANTICS` | `gate_grounding_citation_required`（grounded_from必須） | **接地必須**を全層共通原則に。L2=anchor出所、L4=解説出所 |
| 暫定と正準を分離 | `seed → candidate → accepted` | `gate_no_blind_tagging`（暫定タグはP3リンクまで正準化しない） | **status機構を L4 にも適用**：design_knowledge も seed/candidate/accepted を持つ |
| 観測からの推測で確定しない | anchor を surface一致だけで authoritative にしない（seed監査 FF-1/FF-2） | `gate_favors_from_context_only`（favors/tightness は解説からのみ） | **観測は仮説生成まで**。確証は出所（anchor / 解説）で（§6 監査Q2 と整合） |

→ FORMOBJ の `grounded_from`（解説引用追跡）は、MEANING の `anchor authority`（定義条文 vs ローカル略称）の **L4版アナログ**。同じ「出所の格付け」を、L2は法令定義に、L4は解説テキストに対して行う。

## 4. HOLD と gate の継承（両監査の制約を合算）

統合スタックは**両系統の禁止事項を AND で継承**する。

**MEANING 監査由来の HOLD（継続）**：production DDL / Salesforce write・sf_binding実書込 / 事務所スキャンPDFの production rollout / L3 concept_uri の accepted化 / MCP outlet・自動法的意味確定 / bengo4・LionBolt の docx新規取得 / 事務所内文書（メール・議事録）の L2帰納素材化。

**FORMOBJ 由来の gate（継続）**：`gate_form_anchor_required` / `gate_sticky_form_uid` / `gate_no_blank_invention` / `gate_snapshot_per_source` / `gate_no_node_invention_in_merge` / `gate_no_auto_group` / `gate_page_calibration_recorded` ＋ v1.0追加4種。

**統合で新設する gate**：
- `gate_no_vocab_fork` — clause_function / clause_type は `shared_term_registry` の正準term のみ。PJ独自語彙の併存を禁止（MEANING Q6 のブロッキング指示を統合スタック全体に拡張）。
- `gate_l4_keyed_by_l2` — L4 design_knowledge は L2 正準term をキーに持つ。未登録キーでの L4 生成を禁止。
- `gate_layer_immutability` — L4/L3 を改訂しても L1/L2 を再生成しない（MEANING の form/meaning 分離原則を L4 まで延長）。

## 5. パイプライン統合（FORMOBJ S1–S5 ＋ MEANING SEED工程）

```
[S1] アドレス確定        式→toc_node→page_span                         （FORMOBJ・実装済）
[S2] L1スナップショット   書式頁OCR→snapshot→canonical（restorable整合） （FORMOBJ・実装済）
[L2] 型付け(seed)         clause_type/semantic_type 付与＋anchor解決      （MEANING SEED・要改訂反映）
[S2.5/L4] 解説接地        解説節OCR→clause_design_knowledge（grounded_from必須）（FORMOBJ・PoC実証）
[S3] canonical合成        源優先＋粒度ガード＋発明禁止                     （FORMOBJ・実装済）
[S3.5] 知識合成           同一正準termの L4 を複数解説書から合成（source_diversity≥2）（FORMOBJ）
[V] 検証                  L2 anchor品質＋L4 引用追跡＋三点測量              （両系統の検証を合流）
[reg] レジストリ登録      shared_term_registry に term＋L2＋L4 を紐付け     （統合・新設）
[S5] 永続化              （Mac側承認フロー。accepted化は owner ratify のみ）
```

MEANING seed監査の `REVISION_REQUIRED`（anchor を surface一致だけで authoritative にしない、ja_labels の凝集性、inline_iu を正式gateから除外）は、**L2工程の受け入れ条件**として本統合に取り込む。

## 6. 監査（お目付け役GPT）に確認したい点

1. **層の積み方**：FORMOBJ P3 を MEANING L3 の上の独立層 **L4（design knowledge）** とする調停は妥当か。L3（束縛overlay）と L4（設計知識）を分けるべきか、L3 の中の一区画にすべきか。
2. **接合キー**：`clause_function ≡ L2正準clause_type`（shared_term_registry 経由・fork禁止）で、両系統の語彙は本当に1つに保てるか。L4 の機能粒度（再委託・支払…）と L2 の clause_type 粒度がずれる懸念はないか。
3. **status機構の L4 適用**：design_knowledge にも seed/candidate/accepted を課すべきか。解説接地は1冊では candidate 止まり（source_diversity≥2 で accepted）という運用は MEANING の昇格規律と整合するか。
4. **検証思想の統一**：FORMOBJ の `grounded_from`（解説引用）を MEANING の `anchor authority`（法令定義の格付け）と同じ枠組みで扱う統合は、過度な一般化ではないか。L2接地（恒等性）と L4接地（規範的設計）は本質的に別物として分離すべきか。
5. **ガバナンス**：本統合後、DD-FORMOBJ-001 と DD-TMPLSTRUCT-MEANING-001 を (a) 統合DDに吸収して両者を deprecated にする / (b) 各層DDとして残し本DDを上位の調停層にする、のどちらが保守しやすいか。

## 7. 移行（提案・owner判断待ち）

- DD-FORMOBJ-001 v1.0：用語を L4 に揃える改訂（P3→L4、clause_function→shared_term_registry キー）。中身（押し引き/接地）は不変。
- DD-TMPLSTRUCT-MEANING-001 v0.3.1：L4 への参照宣言を追記（legal_effect の空欄を「L4 design knowledge が埋める」と明記）。L1–L3 は不変。
- 新設：`shared_term_registry` のスキーマ（MEANING §6 を正本とし、L4 外部キーを追加）。
- いずれも **設計のみ**。実装・accepted化・DB化は各監査の go 後。
