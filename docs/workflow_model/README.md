# 業務フロー機械可読化 (workflow_model)

浅井法律事務所の実業務を、AI・ワークフローエンジン・Salesforce・ALO Connect が処理できる形へ
構造化するための原本と発注。前提方針 = **Box＝文書正本 / Salesforce＝業務制御塔 /
自然発生データ優先 / Raw・Canonical・Derived分離**。

```
v0.1/                      … 浅井さん受領の原本一式（上書き禁止）
  ├ 設計・ヒアリングパック.docx / 実査台帳.xlsx
  ├ alo_workflow_event_schema_v0.1.json / ..._example_anonymized_v0.1.json
REQUEST_v0.2.md            … v0.2 作成指示の原本（無改変）。台帳と食い違えばこれが正
v0.2/                      … ワーカーが書き出す v0.2 成果物の置き場（初期は空）
```

## 発注（ワーカーへの作業票）

v0.2 指示は巨大・長距離なので、`REQUEST_v0.2.md` を **実査・成果物単位の作業票** に分解し、
`../worker_queue/inbox/W-20260624-*.md` に投入済み。ワーカーは作業票を1件ずつ
（`alo-worker next` → `claim` → 実装 → `complete`/`block`）処理する。マネージャー（発注側）は
実査をせず、発注と監査だけを行う。

| task | pri | 内容 | 要接続 |
|---|---|---|---|
| W-20260624-101 | P0 | Phase0 v0.1構造インベントリ → CURRENT_STATE骨子 | rep oのみ |
| W-20260624-102 | P0 | Phase1 245問の5区分分類＋P0 58問ステータス | repo/Box |
| W-20260624-110 | P0 | Phase2 Salesforce/LEALA read-only 実査 | **SF/LEALA** |
| W-20260624-111 | P0 | Phase2 Box 文書ライフサイクル実査 | **Box** |
| W-20260624-112 | P1 | Phase2 Gmail等 3本の匿名トレース | **Gmail等** |
| W-20260624-120 | P0 | event schema v0.2＋検証CLI/テスト（CI） | repoのみ |
| W-20260624-130 | P1 | Phase3 実査台帳 v0.2 へ反映（9シート） | repo（110/111/112依存）|
| W-20260624-140 | P0 | 浅井グリルパック（P0から20問以内） | repo（102/110/111依存）|
| W-20260624-150 | P1 | CATALOG v0.2.yaml 統合（16セクション） | repo（130依存）|
| W-20260624-160 | P1 | GAP & PoC計画＋CHANGELOG | repo（130/120依存）|

各票の `forbidden_actions` に §2絶対原則・§7禁止事項（本番書換/移動改名削除/AI推定の確定記録/
PII転載/人間ゲート迂回/一般論埋め/全体停止）を、`exit_criteria` に §8完了条件を機械可読で焼き込み済み。
外部接続が要る票（110/111/112）は、接続不可なら推測で埋めず `WORKER_BLOCKED` 化する規約。
