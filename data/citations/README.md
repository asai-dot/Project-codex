# 本文・引用クリーニング（学陽 法令用語辞典）

学陽の定義文に含まれる法令引用の抽出・リンク・収縮エラー訂正。生データ非改変・別レイヤ。
`phases/cross_reference_web.py` による（引用=リンク候補、誤り扱いしない／収縮疑いは令+4桁のみ）。

## ファイル
- `gakuyo_citation_links.jsonl` … 7,058 引用（entry_id, headword, law, article, matched）。
  e-Gov 法令ノードへのリンク候補。次段で法令名→e-Gov law_id 解決（Box の `egov_json` 既存コーパス
  folder 372278889032 を利用、ライブAPI不要）。
- `gakuyo_collapse_corrections.jsonl` … 収縮エラー3件の訂正案（観測→訂正、文脈付き）。
  根拠=REVIEW_QUEUE_REASSESSMENT_20260602＋文脈。**auto_applied=false**（人手確認後に適用）。

## 既知の限界
- 有斐閣は `第六条`（漢数字＋第〇条）式の引用→本 regex（学陽のアラビア数字直結式）では0件。
  有斐閣本文を対象にするには漢数字＋第〇条 パターンの追加が必要。
- 収縮疑いは令+4桁のみ（3桁は正規引用が大半で regex 判定不能＝e-Gov照合の領分）。
