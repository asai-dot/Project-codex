# HEAD 発注書プロトコル v1 — 2026-06-27

ヘッド(Cloud Web codex)が Worker Claude Code 等に振る発注書(ORCH-*.md)の標準骨格。
全 ORCH-*.md は本プロトコルに従う。

## 1. 発注書の必須セクション(順序固定)
1. **目的(Why)** — なぜこの仕事が必要か。雑誌オブジェクトのどの層を埋めるか。
2. **入力(Inputs)** — 入力ファイル/列/前提データ。実在を Worker が最初に確認すべき。
3. **処理(Approach)** — 主アルゴリズムと**実装方針の自由度**。Worker が判断する余地を残す。
4. **出力スキーマ(Outputs)** — ファイル名・列名固定。head の検収スクリプトが前提にする。
5. **受入基準(Acceptance)** — head が独立検査でPASS/FAIL判定する具体的閾値。
6. **不合格時の挙動(On-Fail)** — Worker が結果が基準未達と気づいた場合の振る舞い。
7. **Self-Audit(Worker側)** — Worker が push 前に自分で回す軽い検査と report 行。
8. **サブエージェント活用ガイド(Subagent Hints)** — どのタスクに Explore/Plan/general-purpose を使うと良いか。
9. **安全(Safety)** — read-only/触ってよいファイル/触ってはいけない領域。
10. **再発注の前提(Re-order Hooks)** — head が v0.2 として再発注する場合の引き継ぎ点。

## 2. ループ前提(超重要)
すべての発注は「**一発で正解**」を目指さない。**v0.1 → 検収 → v0.2 → 検収 → 認定** のループ前提:
- Worker は v0.1 で「自分の自信度」と「弱点」を正直に summary に書く。
- head は検収で**(数値結果) + (Worker自己評価との一致度)** を見る。自己評価が嘘なら品質危険信号。
- 不合格なら head が**改善方針付きで v0.2 発注**を起こす。決して「再度同じ発注書を投げ直す」ことはしない。

## 3. サブエージェント活用ガイド(全 ORCH 共通)
Worker Claude Code 側で Task ツール経由のサブエージェントを使ってよい。推奨パターン:
- **Explore**: 広いリポジトリ探索や入力データの実在確認に。read-only 高速。
- **Plan**: アルゴリズム設計を出す前に1回。コーナーケース列挙が得意。
- **general-purpose**: 重い処理や検索を本ループから分離するため。
- Worker は「使ったサブエージェント数・用途・所感」を出力 summary.json の `subagents_used[]` に記録する(head監査の材料)。

## 4. 出力品質の3段階
- **honest_report**: 数値報告そのもの。嘘の数字は最も悪い罪。
- **caveat**: 判明している弱点を箇条書きで併記。隠さない。
- **self_grade**: A(満点)/B(実用可)/C(改善要)/D(不可) を Worker 自身が付ける。head の判定とのズレが>1段階あれば品質黄信号。

## 5. 命名規則
- 発注書: `artifacts/periodical/ORCH-<TASK>_order_<date>.md`
- 出力: `artifacts/periodical/<task_slug>_v<N>.csv` + `<task_slug>_summary_v<N>.json`
- v0.1 が初版。head が再発注した v0.2 / v0.3... と続く。

## 6. 検収プロトコル(head側)
head は以下の順で見る:
1. summary.json の self_grade と数値が辻褄合うか
2. caveat の網羅性(明らかな弱点を見落としてないか)
3. 受入基準の閾値を独立スクリプトで再計算
4. 出力スキーマの正規性
5. subagents_used の妥当性
全PASS → 認定書 `ORCH-AUDIT-<TASK>_verdict_<date>.md` を head が書いて push。
1つでもFAIL → `ORCH-<TASK>_v0.2_order_<date>.md` を head が起こして再発注。

## 6.5 HEAD_OWNER_LOG 照合（航海日誌・DD-ORCH-CONTINUITY-001 v0.3 RATIFIED）

発注の意図継続のため、ORCH と worker RESULT に下記 field を必須化（正本語彙6つ・旧称 alias 禁止）:

- **ORCH 発注書**: `required_log_commit` / `required_digest_id` / `required_standing_ids`（active な `global_required` standing は全件含む）
- **worker RESULT**: `read_log_commit` / `read_digest_id` / `read_standing_ids`（「読みました」の自然言語は不可）

head は検収時に7 reject code で機械判定（該当で差戻し）:

| 条件 | code |
|---|---|
| `read_digest_id != required_digest_id` | `REJECT_STALE_DIGEST` |
| `read_digest_id` が null/未記載 | `REJECT_MISSING_DIGEST` |
| `git merge-base --is-ancestor <required_log_commit> <read_log_commit>` が false | `REJECT_STALE_LOG_COMMIT` |
| `required_standing_ids ⊄ read_standing_ids` | `REJECT_STANDING_UNREAD` |
| ORCH が active な `global_required` を網羅しない | `REJECT_REQUIRED_STANDING_OMITTED` |
| `active_standing_count > 20` | `REJECT_STANDING_OVERFLOW` |
| 会話履歴の長文 inline 検出（保守的 heuristic 可）| `REJECT_INLINE_HISTORY` |

正本ログ: `docs/alo/HEAD_OWNER_LOG.md`。詳細設計: `docs/alo/DD-ORCH-CONTINUITY-001_head_owner_log_v0.3_20260630.md`。

## 7. 止め時の設計(Termination criteria) — 必読

ループは「永遠に回す」のではなく、**3種のEXIT条件**で必ず止める。
ヘッドは各発注書の冒頭で、その発注が以下のどの EXIT に向かうのかを明示する。

### EXIT-A: 価値達成型(SUCCESS)
- 受入基準PASS。検収書(ORCH-AUDIT-<TASK>_verdict_*.md)を書いて push。
- そのタスクは認定→次のタスクへ。

### EXIT-B: 収穫逓減型(STAGNATION)
- v0.2/v0.3 と再発注しても受入基準を満たさず、かつ **数値が前版から ≤2pt しか改善しない** 場合。
- ヘッドは「現状の vN を最終版として暫定採用、満たせなかった基準は constraint として記録」と決定書を push。
- 認定書ではなく **POSTMORTEM** 文書を起こす(`artifacts/periodical/ORCH-POSTMORTEM-<TASK>_<date>.md`)。
- 例: 月刊債権管理が NDL 未収録で取得不能、L3 で 99.7% で凍結したパターン。

### EXIT-C: 雑誌オブジェクトの完了型(CLOSE)
雑誌オブジェクト全体としてのループ終了条件:
1. **L3** 99.5%以上 認定済 ✓(現状99.7%)
2. **L4 接合** 99% 認定済 ✓(現状99.28%、引き上げ中)
3. **L4 補助メタ(連載/特集/著者/事件名/種別)** 各 PASS 認定済
4. **L5 接合可能性** Grade A 確認済 ✓(現状A)
5. owner GO のある **生データ取込(pacsigny/scan_data)** の方針が確定(着手 or 凍結)
6. **issue完全インデックス** PASS 認定済
これらが揃ったら **雑誌オブジェクト第1期完了** として宣言、ヘッドの注力を**別オブジェクト(判例/法令/語彙)**へ移す。
全量分類完走・OCRパイロット等の長期grindは別系統で継続してよいが、ヘッドのアクティブ管理は別オブジェクトへ。

### EXIT-D: 緊急停止型(ABORT)
- 重大な誤マージが見つかる/owner GO の前提が崩れる/storm事故等で安全側に止める。
- ヘッドは即座にトリガを全て consumed/ に退避、原因分析、再発防止策付きで recovery 発注書を起こす。

## 8. 止め時の判断は必ず数値で
「あと少しで…」「もしかしたら…」は最も危険。各 EXIT は具体的閾値で判定する。
ヘッドは各検収時に「残り改善余地 vs 投入コスト」を1枚で書き、3版連続で改善余地が ≤2pt なら EXIT-B を宣言する。
