# WO-D1TAXO-002 fp照合リファレンス（C byte等価を1コマンド化）— 2026-06-16

- 関連: `WO_d1taxo_jsonl_integrity_verify_20260615_2030.md`（+ ADDENDUM_20260616）
- 根拠: 番頭が源 `nodes.csv`(55,074) から決定論変換を独立再構成し、源側不変条件を全PASS確認済み
  （`C_byte_check_source_side_20260616.md` / `C_expected_reference_20260616.json`, PR #22）。
- 監査整合: DD-D1TAXO-RDB-006（PASS_WITH_NOTES）= 「deterministic Python が counts/hash/validation の権威・
  artifact で受理」に準拠。本照合は artifact(JSONL)→ sha256 の決定論検査。
- 種別: read-only。apply は HOLD 継続。

## ワーカーへ: 実 JSONL で次の3 sha256 を再現し一致させるだけで C(byte等価) クローズ

連結仕様（NFC・昇順・末尾改行）:
- term/statute: `term_uri + "\n"` を昇順連結 → sha256
- edge: `src_term_uri + "\t" + "skos_broader" + "\t" + dst_term_uri + "\n"` を昇順連結 → sha256

期待値（源側＝あるべき値）:
```
fp_terms     = 23bade6c355b04390eaaf7553dfac3ec5df3eb25fde7e89667f162512404f4cc   # v3 alo_terms.jsonl の term_uri 49,733件
fp_edges     = d3e22bc6c28e783d678b6ec801dbc0a539c2f03cd27746e30348ebfdcabbe1ab   # v3 alo_term_relations.jsonl 38,910件
fp_statutes  = eb389a4935916b5961447924fcaa0b608d7ba7297ff8f9ccdd687392aa31b73e   # v3 statutes_candidates.jsonl 5,341件
```

参照実装（そのまま流用可）:
```python
import json, hashlib, unicodedata
def fp_lines(lines):
    h=hashlib.sha256()
    for s in sorted(lines): h.update((unicodedata.normalize("NFC",s)+"\n").encode())
    return h.hexdigest()
terms=[json.loads(l)["term_uri"] for l in open("..._v3_alo_terms.jsonl")]
stat =[json.loads(l)["term_uri"] for l in open("..._v3_statutes_candidates.jsonl")]
rel  =[f'{json.loads(l)["src_term_uri"]}\tskos_broader\t{json.loads(l)["dst_term_uri"]}' for l in open("..._v3_alo_term_relations.jsonl")]
print(fp_lines(terms)==... , fp_lines(rel)==..., fp_lines(stat)==...)
```

## 判定
- 3つ全一致 → worker JSONL = 源期待値とバイト等価（直列化差を除く）→ **C クローズ**。
- 不一致 → 差分の term_uri/edge を最大50件添付して `from_worker/VERIFY_d1taxo_v3_jsonl_integrity_*` へ。
- あわせて ADDENDUM 8〜14（version閉鎖・raw/clean区別・enumerator・id混在等）も実施。
