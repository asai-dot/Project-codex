# C: JSONL バイト検査 — 源側 期待値リファレンス＆フィンガープリント（2026-06-16）

> 番頭が手を動かした分。`.jsonl` 実体はこの環境(Box get_file_content)からテキスト取得不可のため、
> **源 `nodes.csv`(55,074) から決定論的変換仕様（`term_uri = alo:term:d1law-taikei:{digshmcd}-{seqno}`,
> skos_broader=L4-11内の親リンク, L1-3=statutes）どおりに期待値を独立再構成**し、バイト検査の不変条件を
> 源側で検証＋ worker VERIFY が一致すべき参照 sha256 を発行した。
> 成果: `C_expected_reference_20260616.json`

## 源側で検証できた不変条件（全 PASS）

| 検査 | 結果 |
|---|---|
| terms(L4-11) = 49,733 | OK |
| term_uri 重複 | 0 |
| statutes(L1-3) = 5,341 | OK |
| terms ∩ statutes 排他 | 0（重複なし） |
| skos_broader edges = 38,910 | OK |
| └ dst 未存在(orphan) | 0 |
| └ dst が statute 側（横断禁止違反） | 0 |
| └ 自己参照 | 0 |
| parentless terms(L3)=10,823・親が statute(L2) | OK / 違反0（reason=parent_is_statute_layer 相当） |
| labels 1/term = 49,733 | OK |

A1（木構造の循環0・level整合）と合わせ、**skos_broader が非巡回・同scheme・dst実在**であることは源側で確定。

## 参照フィンガープリント（sha256, sorted + NFC）

worker の WO-D1TAXO-002 VERIFY は、実 JSONL から同じ手順（term_uri / edge / statute_uri を sorted・NFC で
連結し sha256）でこの値を再現すべき。一致すれば「worker の JSONL = 源から期待される変換」とバイト等価
（直列化形式の差を除く）と確定する。

```
fp_terms (term_uri)     : 23bade6c355b04390eaaf7553dfac3ec5df3eb25fde7e89667f162512404f4cc
fp_edges (skos_broader) : d3e22bc6c28e783d678b6ec801dbc0a539c2f03cd27746e30348ebfdcabbe1ab
fp_statutes             : eb389a4935916b5961447924fcaa0b608d7ba7297ff8f9ccdd687392aa31b73e
```

(連結仕様: term/statute は `term_uri\n` を昇順連結。edge は `src\tskos_broader\tdst\n` を昇順連結。いずれも NFC。)

## これが証明すること / しないこと

- **証明する**: 源→期待変換の写像が健全（件数・term_uri一意・dst実在・同scheme・排他・parentless理由・labels 1:1）。
  つまり「設計どおりに変換すれば壊れない」こと、および worker 出力が満たすべき**期待値そのもの**。
- **証明しない**: worker の実 JSONL バイトがこの期待値に一致しているか（直列化バグ・取りこぼし・余剰行の有無）。
  → これは worker が実ファイルで上記 fp を再現すれば1コマンドで確定する。`.jsonl` がこの環境から取得できない
  ため、番頭はバイト等価の最終確認のみ worker（or ファイルにアクセスできる主体）に残す。

## C ゲートの現状

- 源側バイト検査: **DONE（全 PASS）**。
- バイト等価の最終確認: worker VERIFY が fp_terms/fp_edges/fp_statutes を再現するだけ（未返却）。
  ＝ C は「源側green ＋ 単一フィンガープリント照合待ち」まで縮小。
