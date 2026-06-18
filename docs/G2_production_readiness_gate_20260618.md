# G2 production-readiness gate — canonical 初回昇格の最小・可逆チェックリスト

- date: 2026-06-18 JST
- author: Claude (Project-codex セッション)
- status: **read-only ゲート設計 / HOLD維持**。本書は「実装GO」ではなく、G2を通すための**入場条件・検証・可逆性**を定義する設計文書。
- 位置づけ: `CASE_OBJECT_NEXT_SEQUENCE_20260618.md` の **S7**。クリティカルパス上、G1(DD-CASEID-001 ratify)とS3–S5(SILVER/人手レビュー)の成果を **canonical へ一歩だけ**進めるための別gate。
- 上位規律: SILVER v0.1.1 / DD-CASEID-001 / 各reality check の HOLD を継承。

> なぜ別gateか: 「設計accept(G1)」と「本番反映(実装)」を混同しないため。G1が通っても、実テーブル作成・データ投入は **G2を別途通過した時のみ**。G2自体も「全部反映」ではなく「**最小・可逆な第一歩**」に限定する。

---

## 1. G2 が扱う「第一歩」の定義（スコープを最小に固定）

G2の初回対象は **canonical case の mint ではない**。受け皿である **`case_observation` 着地層（源別の生同一性レコード, DD-CASEID §4.2）への candidate 投入**までに限定する。

```
[許可する第一歩]
  D1-LIC source-record crosswalk v0 (5,475 links) を
  case_observation に resolver_status=unresolved の candidate として load
  （source_system=lic / d1law, source_case_id付, content_grade付, fingerprint候補）

[この段階で作らない]
  - canonical case 行（cases の identity_status=confirmed）
  - alo_edges（審級・origin_decision等のlink）
  - reviewed=true / claim_support / MCP serve
```

根拠: SILVER v0.1.1 が「D1-LIC は source-record であって canonical case ではない」と明示。case_observation は**canonicalではない着地層**なので、ここへの candidate 投入は両設計と整合する。canonical 化（名寄せ確定）は case_observation 上で Tier規則に従い**後続**で行う。

---

## 2. G2 入場条件（すべて満たすまで実テーブル投入しない）

| # | 入場条件 | 充足元 | 現状 |
|---|---|---|---|
| E1 | DD-CASEID-001 が `_accepted_v1.0` | G1 / S1.5 GPT意味監査 → ratify | ⏳ 監査投函済(DDCASEID)・結果待ち |
| E2 | DD-CASE-001(cases母型)との reconcile 済 | S2 | ⏳ 未着手（accept条件） |
| E3 | SILVER candidate が QA frame freeze 後に生成され、negative-control含む層化QAを通過 | S3–S4 | ⏳ SILVER lane |
| E4 | 投入先が **branch / staging**（本番DBではない）で、dry-run→検証→の順 | 本書 §4 | 設計のみ |
| E5 | 可逆性が担保（rollback手順・バックアップ・版数履歴） | 本書 §5 | 設計のみ |
| E6 | 投入データに raw 商用本文を含まない（IDs/正規化キー/fingerprintのみ） | SILVER §9 | 設計のみ |

→ **E1・E2 が L-ID側のブロッカー**（=監査とreconcile待ち）。E3 が L-SR側。E4–E6 は本書で固める。

---

## 3. 検証ゲート（投入時に0でなければ止める）

DD-CASEID-001 §8 の品質ゲート9種を G2 の合格条件として流用する：

| ゲート | 条件 | 合格 |
|---|---|---|
| gate_case_has_observation | 全casesに≥1 case_observation | 0 orphan |
| gate_observation_source_id_dup | (source_system, source_case_id) 重複なし | 0 |
| gate_fp_collision | fingerprints(saikosai_id/d1law_id/lexis_id) 衝突なし | 0 |
| gate_resolution_logged | auto/human bind に resolution_log エントリ存在 | 0欠落 |
| gate_provisional_has_review | provisional case に review_queue タスク存在 | 0欠落 |
| gate_no_canonical_leak | **case_observation投入で canonical case 行が0増** | 0増 |
| gate_no_edge_leak | **alo_edges が0増** | 0増 |
| gate_no_reviewed_true | reviewed=true が0 | 0 |

最後の3つ（no_canonical_leak / no_edge_leak / no_reviewed_true）は G2 第一歩の**境界を機械的に保証する**ための追加ガード。

---

## 4. 投入順序（dry-run → branch → 検証 → 停止）

```
S7a  schema draft: case_observation / alo_forum_registry を branch にのみ作成（本番DDLなし）
S7b  dry-run load: D1-LIC v0 5,475 を candidate 形式に変換（書き込みなし・件数/衝突のみ）
S7c  目視: §3ゲート全0を確認
S7d  branch load: branch DBへ candidate 投入（resolver_status=unresolved）
S7e  post-load検証: §3ゲート再実行 + orphan/重複0
S7f  STOP: ここで一旦停止。canonical名寄せ確定(Tier適用)は別判断
```

各段で **承認不要なのは dry-run と branch検証まで**。branch load(S7d)以降は owner 確認を挟む。

---

## 5. 可逆性（rollback 手順）

| 対象 | 可逆化措置 |
|---|---|
| branch schema | branch廃棄で消える（本番に触れない）。reset_branch で復元 |
| candidate data | load前スナップショット保持。delete-by-dataset_version で一括撤去可 |
| 既存 staging | D1-LIC v0 は **non-destructive**（CROSSWALK_PERSISTENCE: do not overwrite）。読むだけ |
| 監査証跡 | resolution_log / dataset_version で全投入を追跡。撤去も記録 |

→ **本番に不可逆な変更を一切残さない**設計。第一歩が誤っても branch廃棄で原状復帰。

---

## 6. G2 でオーナーが判断する点（将来）

E1–E6 が揃った時点で、オーナーは以下を判断：

```
[ ] G2-a: branch/staging への case_observation candidate 投入を許可するか（本番DDLはまだ）
[ ] G2-b: content_grade=full の D1-LIC本文系を candidate に含めるか / メタのみに留めるか
[ ] G2-c: canonical名寄せ確定(Tier A自動bind)を、どの規模で初回試行するか（例: NII∩D1一致12,661のうち高信頼サブセット数百件）
```

→ G2-c が「accepted case が初めて非ゼロになる」瞬間。ここも**少量から**。

---

## 7. HOLD（G2通過後も維持）

- 本番 DB への DDL / write（branch/stagingのみ許可）
- canonical case の大量 mint（G2-cは少量試行のみ）
- `alo_edges` の大量promotion、`reviewed=true` backfill、claim_support、MCP/vector serve
- 商用ソース本文の外部送信、source mutation

---

## 8. 依存と次手

- **依存**: E1(DDCASEID監査→accept) / E2(reconcile) / E3(SILVER QA通過)。本書は E4–E6 を確定。
- **次手**: 監査RESULT が `from_gpt` に返ったら、(a)close→action-queue→reflect で監査を1周閉じ、(b)PASS系なら S2 reconcile→accept、(c)その後 E3達成を待って G2a dry-run に進む。
- canonical mint は **G2-c の少量試行まで一切しない**。
