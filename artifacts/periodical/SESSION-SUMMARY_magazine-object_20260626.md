# 雑誌オブジェクト 作業まとめ（Cloud Web=head セッション）— 2026-06-26

## 1. 雑誌オブジェクトの到達点（層モデル DD-PERIODICAL-002）
| 層 | 状態 |
|---|---|
| L3 号同定/誌authority | ✅ 完成 99.7%（v14, 921/931誌）・精度検収PASS（誤マージ0） |
| L4 記事↔issue_id 接合 | ✅ 完成 99.28%（299,957/302,130）・受入PASS・別冊ジュリストisbn化適用 |
| L4 記事種別 粗分類(10種別) | 🟢 **全量29.7万件 実行中**（qwen3:30b・パイロット92.2%でPASS済） |
| L0-L2 生/OCR・L4初出・L5本文リンク | 設計済(DD-002)・owner GO+ライセンス確認済・順次着手 |

## 2. 主要な成果
- **銀行法務=銀行法務21 同定**: 実記事データで同一誌(ISSN 1341-1179)と確定（書誌推論でなくデータが決着）。
- **DD-PERIODICAL-002**: 雑誌オブジェクトを7層パイプライン(生→分割→OCR→号同定→メタ/初出→リンク→語彙)として全体設計。
- **進捗確認＋ヘッド決定**: L3凍結/別冊ジュリストisbn化(D2)/記事接合最優先(D3)/OCRはパイロットゲート(D4)。
- **L3精度検収**: v14で衝突24件すべて良性表記揺れ・新規誤マージ0 → 基盤production-ready認定。
- **L4記事接合検収**: article_collision=0・被覆99.28%・百選issue_id衝突0 → 接合完了認定。
- **ローカル分類パイロット**: 規格外0・分布健全・クロスチェック92.2% → 全量GO。

## 3. 構築した仕組み（恒久化）
- **AIチーム組織＋ルーティング規約**を CLAUDE.md / docs/alo/AGENT_ORG_AND_ROUTING.md に常設
  （ヘッド→ハンド3種[ワーカーちゃん/コーデックス/ローカルちゃん=QEN]→GPT Pro監査）。Box にも記録。
- **口語発注**: 「ワーカーちゃん起こして/回して」等→ ORCH-CURRENT を自動投下。
- **遠隔ワーカー体制**: wake_worker.sh / worker_watch.sh(launchd常駐) / trigger_worker.sh / install_worker_watch.sh。
  → Cloud Web も Mac Cloud Code も `.worker_trigger` push でワーカー遠隔起動（実証: 37秒で消費）。
- **受入検査harness**: audit_article_join.py / audit_article_type.py（headが版ごと独立監査）。

## 4. 事故と対処（教訓）
- **force-push事故**: Mac CCのforce-pushが口語発注機能のコミットを消失 → 復元＋「共有ブランチforce-push禁止」をCLAUDE.mdに明記。
- **storm事故**: remote-trigger×watcher競合で classify worktree が約26本乱立しGPUデッドロック。
  原因=Mac作業ツリーのgit競合でwatcherがトリガ消費できず60s毎再launch。
  対処=watcher/wake堅牢化(競合自動解除)・storm worktree一掃・全量は単一プロセス直接実行。
- **ドライバ修正(Worker)**: grep -P→awk(BSD移植性)・ollama CLI crash→HTTP API版・qwen2.5全件その他→qwen3:30b。

## 5. 現在進行中 / 次の一手
- **進行中**: 記事種別 全量29.7万件分類（qwen3:30b, 背景, resume対応）。完走→head再監査。
- **次段**: 判例評釈サブセット→ L5(評釈→判例リンク)。初出(pacsigny)・OCRパイロット(scan_data)も owner GO済で順次。
- **整理事項**: authority CSV が v14本線と v2_sru/v3_ratified系で並存(alo-ccマージ)→ 後日統合。
