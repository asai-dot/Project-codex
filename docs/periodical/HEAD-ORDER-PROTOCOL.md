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
