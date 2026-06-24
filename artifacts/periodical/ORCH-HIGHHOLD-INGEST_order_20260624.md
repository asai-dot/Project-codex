# ORCH-HIGHHOLD-INGEST — Worker Claude Code 発注: 初出(L4) / OCR(L0-L2) / legal_thought

```yaml
order: ORCH-HIGHHOLD-INGEST
from: Cloud Code Web (codex, head)
to: Worker Claude Code
authority: owner GO 2026-06-24 全GO承認 ＋ ライセンス確認「自所物だから進めて」(LICENSE_CONFIRM解除済)。
gate: 派生物は append-only + provenance。原盤は非破壊(read-only)。canonical昇格/DB投入/edge accepted化/
      外部公開(external_share=false)は含まない(別GO)。ロールバック=派生物 quarantine→破棄。
ref: DD-PERIODICAL-002, WO-PERIODICAL-OWNER-GO-REQUEST, ORCH-AUDIT-L4(接合完了)
input: 記事接合は完了済 → artifacts/periodical/article_join_dryrun_v0.1.csv (article_id 確定済) と突合する。
       authority 最新 v14。pacsigny/scan_data/legal_thought の実パスは docs/alo の locator で確認。
```

## 実行順（厳守）: フェーズ1(初出) → 私の監査 → フェーズ2(OCRパイロット) → 私の監査 → 全量
重い OCR を先走らせない。初出を先に出して push し、一旦止めて head 監査を待つ。

## フェーズ1【今回これをやる】GO-3: pacsigny 初出メタ抽出 → article_first_pub
- 入力: `pacsigny` レーン論考メタ(read-only, locator経由) ＋ `article_join_dryrun_v0.1.csv`。
- 処理: 論考の初出誌/巻号/年を抽出し `article_first_pub`(article_id, first_pub_issue_id, reprints[], evidence='signy')を実体化。
  article_join の article_id と突合して紐付け。
- 検査: `firstpub_conflict`(1論考に複数初出主張)=0、provenance(出所ID)必須。
- 出力: `artifacts/periodical/article_first_pub_dryrun_v0.1.csv` ＋ サマリ json(total/conflict/紐付率)。push して**一旦停止**。

## フェーズ2【head監査合格後】GO-4: scan_data OCR パイロット
- 1誌・3〜5号のみ(例: 金融法務事情の連続号)。L1記事分割(境界+確信度) → L2 OCR(縦書き/二段組/ルビ, ocr_conf保持)。
- 出力: `artifacts/periodical/ocr_pilot_<journal>_v0.1/`(本文+conf+境界レポート)。push して停止。
- head が分割境界/conf を監査合格 → フェーズ3(全量, `article_text` append)。

## フェーズ補: GO-5 legal_thought 取込(L4/L5補助) — 初出・OCR が片付いてから。

## 返却(衝突回避の日付付き名で push。P##系は使わない)
1. article_first_pub_dryrun_v0.1.csv ＋ サマリ。
2. (合格後) OCRパイロットの境界/conf レポート。

## 分担
producer=Worker Claude Code(生データ/OCR計算資源はMac)。
監査=codex(head): firstpub_conflict / 分割境界 / edge_falselink を独立再検査。**OCRパイロット合格は監査必須ゲート**。
