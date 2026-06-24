# P23: ローカルちゃん発注 — GO-3 / GO-4 / GO-5（HIGH-HOLD 実取込）

```yaml
artifact: P23_highhold_ingest_order
generated_at: 2026-06-24 JST
authority: owner GO 2026-06-24 全GO承認 ＋ ライセンス確認クリア「自所物だから進めて」
          (WO-PERIODICAL-OWNER-GO-REQUEST 承認記録)。LICENSE_CONFIRM_PENDING 解除済。
gate: 派生物は append-only + provenance。原盤は非破壊(read-only)。canonical昇格・DB投入・edge accepted化・
      外部公開(external_share=false)は含まない(別GO)。ロールバック=派生物 quarantine→破棄。
ref: DD-PERIODICAL-002 (L0-L2/L4/L5), WO-PERIODICAL-OWNER-GO-REQUEST
prereq: GO-0(locator行抽出, P22)で各レーンの primary_location/read_first を確定してから着手。
```

## 前提（GO-0 出力を使う）
P22 GO-0 で得た `pacsigny`/`scan_data`/`legal_thought` の `primary_location`/`read_first` に従って読む。
locator が示す `read_first` lane-map を必ず先に参照（atlas Wave51 protocol）。

## GO-3: pacsigny 初出メタ抽出 → article_first_pub
- 入力: `pacsigny` レーン論考メタ（read-only, locator経由）。
- 処理: 論考の初出誌/巻号/年を抽出し、`article_first_pub`(article_id, first_pub_issue_id, reprints[], evidence='signy')を実体化。
  既存 article_join_dryrun(P22 GO-1) の article_id と突合して紐付け。
- 検査: `firstpub_conflict`(1論考に複数初出主張)=0 を確認。provenance(出所ID)必須。
- 出力: `artifacts/periodical/article_first_pub_dryrun_v0.1.csv`。

## GO-4: scan_data 取込＋OCR（L0→L1→L2）── **パイロット先行**
**フェーズA(パイロット, 必須先行):** 1誌・3〜5号のみ（例: 金融法務事情の連続号）。
- L1: 多記事PDF/画像を**記事単位に分割**（目次/ページ範囲ベース）。境界候補と確信度を出す。
- L2: 各記事を OCR。**縦書き・二段組・ルビ対応**。`ocr_conf`/lang/layout を保持。
- 検査(パイロット): 分割境界を**全件目視抜取**、OCR conf 分布、誤分割(記事跨ぎ/分断)件数。
- 出力: `artifacts/periodical/ocr_pilot_<journal>_v0.1/`（本文 + conf + 境界レポート）。
- **ゲート: パイロットのcodhead監査(精度OK)を経てからフェーズB全量**。conf低/誤分割多発なら設定見直し。

**フェーズB(全量):** パイロット合格後に scan_data 全対象へ拡大。`article_text`(article_id, body_text, ocr_engine, ocr_conf, layout)を append。

## GO-5: legal_thought 取込（L4/L5補助）
- 入力: `legal_thought` レーン（read-only, locator経由）。
- 処理: 論考メタ/本文を L4補助メタとして取込、article へ紐付け。
- 検査: `edge_falselink`(対象ID実在せず/低信頼)検査。 出力: dryrun CSV。

## 期待アウトプット（P24として返す）
1. article_first_pub_dryrun の件数・firstpub_conflict 0確認・サンプル20件。
2. OCRパイロットの境界/conf レポート（codhead監査用）→ 合格判定後に全量GO。
3. legal_thought 取込サマリ・edge_falselink 件数。

## 分担
producer=ローカルちゃん（生データ・OCR計算資源はMac）。
監査=codex(head): firstpub_conflict / 分割境界 / edge_falselink を独立再検査。**OCRパイロットの合格判定は監査必須ゲート**。
