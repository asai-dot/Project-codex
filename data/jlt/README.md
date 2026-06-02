# JLT v19.0 権威見出し語リスト（派生物）

法務省「法令用語日英標準対訳辞書」v19.0 から決定的に抽出した権威ある見出し語。
有斐閣⟷学陽 2辞書相互突合の**権威基準**。

## 出所（provenance）
- 正典: `jlt_dict_v19.0_utf8.csv`（Box: 05＿語彙レイヤー/jlt_v19_0, file 2259902010075）
  - canonical sha256 = `3a2b06121f675241fe0ad00f2e77524198871e7ed45a4f305de49b0454fb8b97`（byte-exact 確認済）
- 生成: `phases/build_jlt_authority.py`（決定的・LLM非依存）
- データ行 5,248 → 一意見出し語 **3,869**
- term-set sha256 = `51d767a0de4eeca9a921fe0751c185fac56682b4dc7fb92924a624dab6be746b`

## ファイル
- `jlt_terms_authority_v19.0.txt` : 一意見出し語（NFC・ソート）1行1語
- `jlt_term_reading_v19.0.jsonl`  : (用語, 読み) ペア

## 再現
```
python3 phases/build_jlt_authority.py <jlt_dict_v19.0_utf8.csv> out.txt
# -> term-set sha256 が 51d767a0… と一致すること
```
