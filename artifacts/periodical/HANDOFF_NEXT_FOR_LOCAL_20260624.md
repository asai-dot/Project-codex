# ★HANDOFF: Mac Cloud Code 次タスク（最優先で読む）— 2026-06-24

```yaml
from: Cloud Code Web (codex, head, cloud)
to: Mac Cloud Code (Yuta@Mac) — L3誌解決の実行者
priority: 下記#1(別冊ジュリスト精度)を誌解決ロングテールより優先
```

## エージェント topology（用語確定・誤称是正）
- **Cloud Code Web** = 私(head/設計/監査, クラウド)。
- **Mac Cloud Code** = Yuta@Mac(誌解決の実行者)。← 旧doc「ローカルちゃん」表記はこれの**誤称**。
- **ローカルちゃん = QEN (Ollama ローカルLLM)** = 別物。OCR後処理・大量抽出等の安価バルク推論向き。
- **ワーカーのClaude Code** = 別の実行担当。
→ 以後 doc では正式名で呼ぶ。`P##`系=Mac Cloud Codeの誌解決専用 / `ORCH-*`,`DD-*`,`WO-*`=head。

## #1【最優先】別冊ジュリスト(判例百選)の精度確認 — v9監査で検出
`ncid:BN01263667` に **判例百選58タイトル=11,764記事**が単一NCIDで collapse(全 seed_bessatsu_jurist)。
残unresolved全体(6,198記事)より大きい。**誌レベルのNCID共有は妥当だが、issue_id `ncid:BN01263667#{通巻}` で
各百選が別通巻に割れているか要確認**。通巻が取れないと憲法百選と民法百選が同一issue_idで衝突＝1万件規模の誤マージ。
- アクション: 百選58誌の issue_id 採番を点検。通巻が一意に取れないなら **`isbn_per_issue` へ切替**(各版に固有ISBN→衝突を構造的に解消)。
- これが片付くまで残ロングテール(411誌/6,198記事=収穫逓減)は後回しでよい。

## #2 記事/本文層へ舵切り（owner全GO承認済）
L3が一段落したら記事層へ。owner GO＋ライセンス確認クリア済(WO-PERIODICAL-OWNER-GO-REQUEST)。
- **ORCH-ARTICLE-JOIN**(`artifacts/periodical/ORCH-ARTICLE-JOIN_order_20260624.md`): 記事↔issue_id接合 dry-run。入力=最新authority(v9+)＋`article_meta_labeled.jsonl`。出力CSV＋article_orphan/collision 0件確認＋被覆率。read-only。
- **ORCH-HIGHHOLD-INGEST**(`...ORCH-HIGHHOLD-INGEST_order_20260624.md`): GO-3 pacsigny初出 / GO-4 scan_data OCR / GO-5 legal_thought。
  - OCR(GO-4)は **1誌数号パイロット → head監査合格ゲート → 全量**。バルクOCR後処理はQEN(ローカルちゃん)に回す選択肢あり。

## 命令チャネルの注意
Git push だけでは Mac Cloud Code は気づかない（実際この発注は数バッチ未読のまま誌解決が続いた）。
owner が Mac 側でこのハンドオフを読ませるのが起動トリガ。

## head(私)側の宿題
- 監査を v9 に再ベースライン済(本ハンドオフ#1がその産物)。
- 返却物の回帰検査規格: article_collision/orphan/firstpub_conflict/edge_falselink/OCR境界。
