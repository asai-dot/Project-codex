# R0 registry shell v0.1 — 運用仕様（shared_term_registry 具体化）

> **version**: v0.1 / **owner**: 浅井 / **author**: 番頭(リモートClaude) / date: 2026-06-15
> **gate**: 設計＋ローカル dry-run のみ。**DDL・DB書込みなし（HOLD）**。監査 `DDFORMOBJ/DDTMPLINTEG PASS_WITH_NOTES` の許可範囲内。
> **狙い**: 統合スタックの接合キー `shared_term_registry`（INTEGRATION-001 §2 / FORMOBJ v1.1 R0）を、**検証可能な実体**に落とす。先験オントロジーではなく**発散防止の仮置き台帳**。

---

## 0. 成果物（この一式が R0 の具体化）

| ファイル | 役割 |
|---|---|
| `shared_term_registry.schema.json` | 1レコードの契約（JSON Schema draft-07）。必須項目・enum・term_id命名 |
| `shared_term_registry.seed.jsonl` | 実データ seed（14語）。subcontracting=L4 candidate、他13=seed |
| `../../../tools/validate_shared_term_registry.py` | ゲート強制バリデータ（self-test 11/11、seed 0違反） |
| 本書 | 運用手順・ライフサイクル・役割分担 |

## 1. これは何で、何でないか
- **である**: L2(MEANING の clause_type/semantic_type) と L4(FORMOBJ の clause_design_knowledge) が**同じ term を指す**ことを保証する単一台帳。語彙 fork を防ぎ、status で発散を抑える。
- **でない**: 完成した条項機能オントロジー。語彙全集を先に決めない（R4 で帰納的正準化）。

## 2. レコードの要点（schema 準拠）
- `term_id`（snake_case・不変）= 接合キー。L2 も L4 もこれを参照（独自語彙禁止 = `gate_no_vocab_fork`）。
- status を**3系統**で別々に持つ（監査Q3）:
  - `status`（term識別性＝registry admission）
  - `linked_l2.l2_status`（型としての確からしさ。anchor品質に依存）
  - `linked_l4.l4_status`（設計知識としての確からしさ。解説接地に依存）
- 粒度差は `linked_l4.narrower_terms`（registry 内の下位 term_id）で表現。例: `payment → late_payment_interest`。

## 3. ゲート（バリデータが強制）
| gate | 内容 | 由来 |
|---|---|---|
| STRUCT | 必須項目/enum/term_id命名 | schema |
| G_UNIQUE | term_id 一意 | — |
| G_NO_FORK | narrower_terms は registry 内の既存 term のみ | N1/gate_no_vocab_fork |
| G_L4_KEY | L4実体があるなら L2識別性必須 | gate_l4_keyed_by_l2 |
| G_SINGLE | 独立源≤1 で L4 accepted 不可（単一書籍は candidate 止まり） | FORMOBJ R4 |
| G_L4_ACC | L4 accepted = 独立源≥2＋独立性確認＋参照L2≥candidate＋label_cohesion | N3/N5 |
| G_L2_ACC | L2 accepted = authoritative_anchor＋label_cohesion | SEED監査 FF-1/FF-2 |
| G_TERM_ACC | term accepted = owner_ratified | — |
| owner_override | 明示理由があれば accepted系ゲートをバイパス（証跡として記録） | 監査(owner override許容) |

## 4. ライフサイクル（誰が何を書くか）
```
worker  : 観察(書式/解説)から term を status=seed で起票。L2 anchor 候補と L4 grounded_from を付す。
番頭    : seed を集約・重複統合・narrower 整理。バリデータを通す。GPT 再監査へ。
GPT監査 : anchor品質(authoritative vs weak)・label凝集性・接地の独立性をレビュー。
owner   : candidate→accepted を ratify。accepted で初めて事務所標準/AI根拠に使える。
```
- L4 は **seed/candidate の L2 term を参照してよい**が、**accepted になるには参照先 L2 が candidate 以上＋品質レビュー通過**（or owner_override）。
- 観測由来は仮説まで。accepted の根拠にしない（evidence_purpose=observed_variation）。

## 5. 現 seed スナップショット（2026-06-15）
- 14 term。**L4 candidate=1（subcontracting／解説1冊接地・独立源1で candidate 止まり）**、残 13＝seed。
- A枠(stabilizer) で authoritative_anchor＋label_cohesion 済の L2 候補: `termination` / `jurisdiction` / `bylaw_share_sellback`（L2 を candidate へ昇格可能な品質。ただし昇格判定は番頭→GPT→owner）。
- anchor 未解決: `ip_assignment` / `ip_noninfringement` / `term_duration` / `individual_contract_framework`（後で alo-kg/e-Gov anchor を付与）。

検証:
```
python3 tools/validate_shared_term_registry.py
# → self-test 11/11、seed 14 terms 0 violations
```

## 6. L2/L4 からの接続（統合スタックでの使われ方）
- FORMOBJ: `form_object.clause.function_ref → term_id`、`clause_design_knowledge.term_id → term_id`。
- MEANING: L2 タグ付け時に `clause_type` を term_id に解決（fork せず参照）。L3 overlay の `legal_effect` は候補に留め、規範判断は L4 が term_id 経由で供給。

## 7. HOLD（解除は owner ratify 後）
DDL（registry の物理テーブル化）/ DB canonical write / SF write / MCP publication / accepted 化。
- 物理化案: `toc_nodes` 隣接に `shared_term`（term台帳）＋ `l2_tag`／`l4_design_knowledge`（term_id FK）。v0.1 は JSONL で十分。

## 8. 次の一手（R0 完了後）
1. subcontracting の **2冊目独立接地**を取り、L4 candidate→accepted の昇格を1件通す（R3 の最小実証）。
2. A枠 stabilizer の L2 を candidate 昇格（termination/jurisdiction/bylaw_share_sellback）→ GPT 再監査。
3. 未 anchor 4語に alo-kg/e-Gov anchor を付与。
4. seed を 30〜50 へ拡張（L3 PoC の emergent + a枠）。**上限の暫定 100〜200**（語彙肥大を防ぐ）。
