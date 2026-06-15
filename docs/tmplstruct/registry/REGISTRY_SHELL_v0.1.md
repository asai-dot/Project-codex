# R0 registry shell — 運用仕様（shared_term_registry 具体化）

> **version**: v0.2 / **owner**: 浅井 / **author**: 番頭(リモートClaude) / date: 2026-06-15
> **gate**: 設計＋ローカル dry-run のみ。**DDL・DB書込みなし（HOLD）**。
> **改訂**: 監査 `DDREGSHELL_PASS_WITH_NOTES`（2026-06-15）反映。owner ratify 済。
> **狙い**: 統合スタックの接合キー `shared_term_registry`（INTEGRATION-001 §2 / FORMOBJ v1.1 R0）を、**検証可能な実体**に落とす。先験オントロジーではなく**発散防止の仮置き台帳**。PJ横断共有（tmplstruct/d1lic/alo_kb/biblio/lawsubtrans）。

---

## 0. 成果物（この一式が R0 の具体化）

| ファイル | 役割 |
|---|---|
| `shared_term_registry.schema.json` | 1レコードの契約（draft-07, v0.2） |
| `shared_term_registry.seed.jsonl` | 実データ seed（14語）。subcontracting=L4 candidate、他13=seed |
| `../../../tools/validate_shared_term_registry.py` | ゲート強制バリデータ（self-test **19/19**、seed **0違反**） |
| 本書 | 運用手順・ライフサイクル・役割分担 |

## 1. これは何で、何でないか
- **である**: L2(MEANING の clause_type) と L4(FORMOBJ の clause_design_knowledge) が**同じ term を指す**台帳。語彙 fork を防ぎ、status で発散を抑える。PJ横断で共有。
- **でない**: 完成した条項機能オントロジー。語彙全集を先に決めない（R4 で帰納正準化）。

## 2. レコードの要点（schema v0.2 準拠）
- `term_id`（snake_case・不変）= 接合キー。L2 も L4 もこれを参照（`gate_no_vocab_fork`）。
- **status 3系統**（監査Q1・改称）:
  - `term_identity_status`（term識別性＝registry entry の採否）
  - `linked_l2.l2_anchor_status`（型語彙としての確からしさ。anchor品質に依存）
  - `linked_l4.l4_design_status`（設計知識としての確からしさ。解説接地に依存）
- **PJ横断の仕切り**（監査Q5・必須追加）: `term_kind`（legal_concept/clause_type/remedy_type/…）／`source_lane`（tmplstruct/d1lic/alo_kb/…）／`usage_scope`（template_l2/template_l4/case_issue/…）。`domain`（法分野）だけでは template由来 vs 判例由来 vs 法令定義 の混在を防げないため。
- **粒度差**は `linked_l4.narrower_relations`（registry内下位term＋`narrower_kind`）で表現。例: `payment → late_payment_interest (remedy)`。
- **anchor は配列**（`linked_l2.anchors[]`）。各 anchor に `authority_class`＋`evidence_purpose`。
- **owner_override は構造体**（reason/decided_by/decided_at/scope/expiry）。理由文字列だけにしない。

## 3. ゲート（バリデータが強制 / 19テスト緑）
| gate | 内容 | 由来 |
|---|---|---|
| STRUCT | 必須項目/enum/term_id命名 | schema |
| G_UNIQUE | term_id 一意 | — |
| G_TERM_KIND_PRESENT / G_SOURCE_LANE_PRESENT / G_USAGE_SCOPE_PRESENT | PJ横断の仕切り3項 | 監査Q5 |
| G_SOURCE_BASIS_TYPED | source_basis_kind が enum | 監査§6 |
| G_ANCHOR_PURPOSE | 各 anchor に evidence_purpose | 監査Q4 |
| G_NO_FORK / G_NARROWER_CHILD_EXISTS | narrower child は registry 内 term | N1/Q2 |
| G_NARROWER_NOT_SELF / G_NARROWER_NO_CYCLE | 自己参照・閉路禁止 | 監査Q2 |
| G_L4_KEY | L4実体があるなら L2識別性必須 | gate_l4_keyed_by_l2 |
| G_SINGLE | 独立源≤1 で L4 accepted 不可（単一書籍は candidate 止まり） | FORMOBJ R4 |
| G_L4_ACC | L4 accepted = 独立源≥2＋独立性確認＋**矛盾なし＋scope明示**＋参照L2≥candidate＋label_cohesion | N3/N5＋監査Q3 |
| G_L2_ACC | L2 accepted = authoritative_anchor＋label_cohesion | SEED監査 FF-1/FF-2 |
| G_TERM_ACC | term accepted = owner_ratified | — |
| G_OWNER_OVERRIDE_STRUCTURED | override は構造体（reason/decided_by/decided_at/scope） | 監査Q3 |

## 4. ライフサイクル（誰が何を書くか）
```
worker  : 観察(書式/解説)から term を term_identity_status=seed で起票。L2 anchor 候補と L4 grounded_from を付す。
番頭    : seed を集約・重複統合・narrower 整理。バリデータを通す。GPT 再監査へ。
GPT監査 : anchor品質(authoritative vs weak)・label凝集性・接地の独立性をレビュー。
owner   : candidate→accepted を ratify。accepted で初めて事務所標準/AI根拠に使える。
```
- L4 は seed/candidate の L2 term を参照してよいが、**accepted になるには参照先 L2 が candidate 以上＋品質レビュー通過**（or owner_override）。
- 観測由来は仮説まで（evidence_purpose=observed_variation）。accepted の根拠にしない。

## 5. 現 seed スナップショット（2026-06-15）
- 14 term。**L4 candidate=1（subcontracting）**、残 13＝seed。
- A枠 stabilizer で authoritative_anchor＋label_cohesion 済の L2昇格候補: `termination` / `jurisdiction` / `bylaw_share_sellback`。
- anchor 未解決: `ip_assignment` / `ip_noninfringement` / `term_duration` / `individual_contract_framework`。
- 監査seedコメント反映: subcontracting の egov anchor は `weak`（再委託は法令定義語でなく条項機能ゆえ L2 authoritative化を急がない）。`late_payment_interest` は narrower_kind=remedy。

検証:
```
python3 tools/validate_shared_term_registry.py
# → self-test 19/19、seed 14 terms 0 violations
```

## 6. L2/L4 からの接続
- FORMOBJ: `form_object.clause.function_ref → term_id`、`clause_design_knowledge.term_id → term_id`。
- MEANING: L2 タグ付け時に `clause_type` を term_id に解決（fork せず参照）。L3 overlay の `legal_effect` は候補に留め、規範判断は L4 が term_id 経由で供給。

## 7. HOLD（解除は owner ratify 後）
DDL（registry の物理テーブル化）/ DB canonical write / SF write / MCP publication / accepted 化。
- 物理化案: `toc_nodes` 隣接に `shared_term`（term台帳）＋ `l2_tag`／`l4_design_knowledge`（term_id FK）。v0.2 は JSONL で十分。

## 8. 次の一手（R0 完了後）
1. subcontracting の **2冊目独立接地**を取り、L4 candidate→accepted の昇格を1件通す（R3 の最小実証）。
2. A枠 stabilizer の L2 を candidate 昇格（termination/jurisdiction/bylaw_share_sellback）→ GPT 再監査。
3. 未 anchor 4語に alo-kg/e-Gov anchor を付与。
4. seed を 30〜50 へ拡張（暫定上限 100〜200）。

## 9. 改訂履歴
- **v0.2（2026-06-15）**: 監査 `DDREGSHELL_PASS_WITH_NOTES` 反映。status 3系統改称、term_kind/source_lane/usage_scope 追加(Q5必須)、narrower_relations 構造化＋cycle/self/child gate、anchor 配列化＋evidence_purpose、owner_override 構造化、L4 accepted に矛盾・scope条件、source_basis_kind。self-test 11→19。
- v0.1（2026-06-15）: 監査提出版（schema+seed+validator の初版）。
