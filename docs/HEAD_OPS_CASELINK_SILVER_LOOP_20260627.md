# HEAD OPS — CASELINK / シルバー精度向上ループ運用規約

- 作成: 2026-06-27 / head: Claude Code (remote)
- 適用: docs/worker_queue/inbox/W-2026062[67]-50[1-9] 系列(判例オブジェクトのシルバー精度向上)
- 目的: **発注→実行→検収→再発注**を head が止めずに回せる規律集。ワーカー(下請けを含む)が止まらず、私(head)が機械的に検収して次手を打てるようにする。
- 原則: ループは止まらない。ただし HOLD 境界(canonical/alo_edges/claim_support/DDL/PII)は機械的に守る。

## 1. ループ全体図
```
inbox/W-NNN → claim → 実行(必要ならサブエージェント並列) → RESULT(構造固定)
                                                    │
                       head 検収(本書 §3 のチェックリスト)
                                                    │
   ┌────────────PASS────────────┬───────PASS_WITH_NOTES──────┬──MODIFY──┬──BLOCKED──┐
   ▼                            ▼                            ▼          ▼          ▼
 hold/ から次タスクを       notes を反映タスクへ          設計問題=     入力欠落=  人手判断=
 queue(本書 §4)            (head が編集 → queue)         私が修正→     上流再発注 owner ESCALATE
                                                          v0.x で再投入
```

## 2. サブエージェント許可方針(ワーカー向け)
ワーカーは Claude Code 内 `Agent`(subagent_type=general-purpose 等)を以下の用途で**使ってよい**:
- **chunked work**: 大量入力(5,475 LIC / 12,661 gold / 1,648 worksheet)を 500-1000 件単位の chunk に分割して並列処理。各 subagent は同一 forbidden_actions を継承(本書 §6)。
- **independent search**: 入力スキーマの存在場所特定、複数候補の探索(reality_check / SILVER 関連ファイル探索)。
- **adversarial verify**: 自分の出力を別 subagent に refute させて自己検証(gold の false_merge 候補は特に)。

**サブエージェント禁止**: HOLD 境界の判断は元ワーカーが singleton で行う(分散しない)。canonical 昇格・alo_edges write・claim_support 関連の判断はサブエージェント経由でも実行しない。

## 3. head 検収チェックリスト(私の役割)
各 W-501〜505 の RESULT は以下を全て満たすこと。一つでも欠けたら label を下げる(PASS→NOTES→MODIFY→BLOCK)。

### 3.1 共通(全タスク)
- [ ] RESULT 先頭行に `WORKER_PASS|WORKER_PASS_WITH_NOTES|WORKER_BLOCKED|WORKER_FAIL` のいずれか
- [ ] forbidden_actions 違反なし(diff 上に canonical/alo_edges/claim_support 触跡なし)
- [ ] read-only 維持(raw source / Box / SF / DB に書込みなし)
- [ ] PII の漏れなし(正規化キーのみ・本文/個人特定情報なし)
- [ ] 部分実行は理由明記(BLOCKED ではない)

### 3.2 タスク別 self-check
| ID | 必須出力 | 検収値の目安 |
|---|---|---|
| W-501 (CASELINK L5 dry-run) | route_distribution / edge_type_counts / stance_counts / span miss <=20 | auto は masthead 由来のみ・本文由来は全 review・evaluates が論文記事で 0 |
| W-502 (Q1 worksheet) | layered worksheet(S-A全+B/E各10+C/D全+NEG8)・decision 全空欄 | manifest の by_stratum と合致・negative_control_n=8 |
| W-503 (Q2 worksheet) | judgment-level worksheet 40+8・collision_group 3 を含む | frame_version=caserev_q2_v0_20260627・collision 3群 reachable |
| W-504 (D1-LIC corroborate) | L1/L2/L3 件数・multi_source_agree/conflict_review 分布・assignment 不変 assert | conflict_review > 0(false split 検出)・assignment hash 不変 |
| W-505 (gold + baseline) | gold jsonl(12,661+ハード負例 ≥120)・baseline report | false_merge=0 を維持・per_tier_precision A≥0.99 確認 |

### 3.3 検収後の私の動作
1. RESULT を読む → §3.1/§3.2 で評価 → label 確定。
2. `_AUDIT_LEDGER`(後日台帳統合)へ結果を1行 append: `{w_id, label, key_metrics, follow_up_task_id}`。
3. **PASS** → §4 の対応する hold/タスクを `claim` 可能な状態へ昇格(本書 §4.1)。
4. **PASS_WITH_NOTES** → notes を反映する v0.x 作業票を私が生成(本書 §4.2)。
5. **MODIFY_REQUIRED** → 設計問題なら scripts/ を直し、入力スキーマ問題なら作業票を v0.2 で再投入。
6. **BLOCKED** → 上流不在(入力データ未生成)なら上流発注へ、人手判断不能なら owner ESCALATE。

## 4. 後続タスクの hold(条件付き起動)
**hold/ に先置き**するパターンを使い、ループを切らない。head が PASS 判定→ hold→inbox へ move でループ再開。

### 4.1 hold で待たせる次タスク(初期セット)
| 後続 ID | トリガ | 内容 |
|---|---|---|
| W-506 | W-503 PASS | Q2 worksheet の reviewer 記入を tally → judgment-level の Tier B 自動化条件抽出 |
| W-507 | W-504 PASS | conflict_review 候補 top100 を reviewer worksheet 化(Q1配管再利用・人手裁定で false split を回収) |
| W-508 | W-505 PASS | baseline で false_merge>0 になった case_key を抽出 → G6(cross-source conflict)強化提案を head に上げる |
| W-509 | W-501 PASS | CASELINK L5 結果の span 取りこぼし型を case_citation_span.py の正規表現拡張案へ(head 実装、worker 検証) |

### 4.2 PASS_WITH_NOTES の反映フォーマット
notes 反映タスクは `W-{元ID}_v0.2_notes_reflect.md`(`status: queued, priority: P1, depends_on: 元task`)で head が生成。notes 各項を `exit_criteria` 行に1対1で対応させる。

## 5. ループ復旧(止まったとき)
- 24h 以上 RESULT 無し → head が `recover` 実行 → doing/ の進捗メモを読む → 続行/blocked/取消 を判断。
- doing/ で進捗メモなし & lock 残存 → flock 解除 + 再起動指示。
- 連続 BLOCKED 3回 → owner ESCALATE("構造的に詰まっている"判断)。

## 6. forbidden_actions(全タスク共通・サブエージェント継承)
```
production_db_write / salesforce_write / box_write_move_rename_delete /
raw_source_mutation / alo_edges_write / canonical_promotion /
claim_support_eligibility / reviewed_true_backfill /
ai_estimate_as_human_decision / pii_in_general_artifact /
human_gate_bypass / fill_unknown_with_generalities /
stall_whole_run_waiting_for_input
```
サブエージェントは元タスクの allowed_paths を超えて読まない/書かない。判定(accept/reject/canonical確定)は singleton で。

## 7. ログ&計測(ループ健全性)
- 各 RESULT に **必須メトリクス節**(MERTRICS_JSON ブロック):
  ```json
  {"records_in": <N>, "records_processed": <N>, "elapsed_sec": <N>,
   "key_metrics": { ... task固有 ... },
   "subagent_calls": <N>, "halts": <N>, "blocked_reason": <str|null>}
  ```
- head は週次で `_AUDIT_LEDGER` から throughput / PASS率 / BLOCKED率 / 再発注率 を算出。
- PASS率 < 0.6 が続けば指示書(本書)の defect として head が修正。

## 8. owner の手番(最小)
- PR ready/merge(自走runner を起動可能にする)
- ESCALATE のときだけ意思決定
- 監査 RESULT が returned したときの ratify

それ以外は head と worker でループを回す。

## 9. ループ終止条件(STOP gate) — 暴走防止
ループは無限に回さない。下記いずれかを満たした時点で**そのレーンを止めて G2 production gate へ手渡す**。head が判定し、owner に1行報告(ratify要否は文脈次第)。

### 9.1 成功終止 (SUCCESS_STOP — 「シルバー磨きの目的達成」)
全て満たしたらシルバー精度向上ループは**成功終止**:
- [ ] **baseline 確立** (W-505 PASS): NII∩D1 12,661 + ハード負例 ≥120 で `false_merge_rate=0` 維持 / `Tier A precision ≥0.99` (95%CI 下限) 実測。
- [ ] **L2 confidence 実数化** (W-504 PASS): D1-LIC 5,475 で `multi_source_agree` 件数 / `conflict_review` 候補が出ている。assignment 不変も確認。
- [ ] **judgment-level gold 第一陣** (W-503+W-506 PASS): Q2 worksheet 40件以上が reviewer 判定済。Tier B 自動化の minimum gold 確保。
- [ ] **conflict→裁定済** (W-507 PASS): conflict_review top100 のうち ≥80% が accept/reject の terminal 状態。残りは defer/needs_more に分類済。
- [ ] **CASELINK L5 精度** (W-501+W-509 PASS): evaluates precision (実 corpus 計測) ≥0.95、span 取りこぼし型 ≤20 件が span 正規表現に反映済。
- → **STOP** + `HANDOFF_TO_G2.md` を head が作成(canonical mint・DDL設計・alo_edges accepted への引継ぎ)。

### 9.2 収穫逓減終止 (DIMINISHING_RETURNS_STOP — 「磨いても出ない」)
2連続バッチで以下のどれかなら当該レーン停止(別タスクへ振替):
- 同一指標の改善が **<0.5%** 連続2回(例: Tier A precision が 0.991→0.992→0.992)。
- 新規 conflict_review 検出数が前バッチの **<10%**(同じ false split パターンが繰り返し検出されるだけ)。
- 新規 span miss 型が **0**(取りこぼしが既知パターンに収束した)。
- → **STOP** + 残作業を「人手裁定 backlog」として頻度報告のみに格下げ(自動レーンを閉じる)。

### 9.3 HOLD境界到達 (HOLD_BOUNDARY_STOP — 「ここから先は別ゲート」)
次の改善案が以下のいずれかを要求し始めたら、当該タスクを止めて G2/owner GO 経路へ:
- production DDL(stance列追加 / cases拡張 / alo_forum_registry 投入 など)
- canonical case mint / alo_edges accepted promotion
- claim_support eligibility / reviewed=true backfill
- jufu の global egress / serving / embedding 配信
- 商用本文の外部送信(GPT監査含む)を新規に必要とする
- → **STOP** + `G2_HANDOFF_<topic>.md` 起票(改善案・必要 DDL・想定リスク・rollback)。production 反映は別 GO。

### 9.4 構造的詰まり終止 (BLOCKED_STOP — 「上流が壊れている」)
- 同一 blocked_reason が **3回**繰り返したら自動再発注を停止。
- doing/ で 48h 進捗ゼロが **2 task** 連続。
- subagent 起動が halts > processed の比で逆転(暴走)。
- → **STOP** + owner ESCALATE(構造改修判断: 上流 SILVER / corpus 取得 / 規約改訂)。

### 9.5 緊急終止 (EMERGENCY_STOP — 「事故」)
即時停止:
- forbidden_actions 違反検出(canonical/alo_edges/claim_support 書込 / PII 露出 / raw 改変)。
- RESULT が捏造された数値を含む疑い(検収で再現できない)。
- 監査 RESULT が `REJECT` を返した。
- → **STOP** + 該当 doing/ を blocked/ に強制移動 + 原因究明レポート + owner ESCALATE。

### 9.6 健全性メトリクス(終止判定の入力)
head は毎ループ末に `artifacts/caselink/_loop_health.json` を更新:
```json
{"cycle": <N>, "tasks_done": <N>, "pass_rate": <0-1>, "blocked_rate": <0-1>,
 "tier_a_precision": <0-1>, "false_merge_rate": <0-1>,
 "conflict_review_open": <N>, "span_miss_new_types": <N>,
 "diminishing_returns_signal": <bool>, "hold_boundary_hit": [<str>]}
```
これが §9.1〜9.4 の判定根拠になる。STOP 判断は head が単独で実行(owner には事後報告)。EMERGENCY_STOP のみ即時 owner 通知。

### 9.7 ループ再開条件(止めた後)
止めたレーンは原則再開しない。再開するには:
- SUCCESS_STOP 後の G2 で新 baseline が確定し、追加磨きが要件化された場合のみ。
- HOLD_BOUNDARY_STOP 後の owner GO で HOLD が解除された場合のみ。
- DIMINISHING_RETURNS 後は「人手裁定 backlog」モードで運用(自動レーンは閉じたまま)。

**ループの目的はシルバーを磨くことであって、磨き続けること自体ではない。** 上記いずれかで止まったら、次の階(G2)に渡す。
