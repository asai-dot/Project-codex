# scripts.amendparse — 改め文パーサ（gold の公式真実源）

改正法の「**改め文**」は、どの条をどう変えたかを**官報の一次データとして断定**する
（「第七百三十三条を削る」＝repeal、「第七百七十二条を次のように改める」＝substitution、
「…の次に次の一条を加える」＝insertion）。本モジュールはその改め文を解析し、
lawdelta と**同じ delta_kind 値域**へ機械写像する。

## 役割
- **gold 生成器**: 改正法の改め文から `(article_path, delta_kind)` を自動生成。
  `scripts.eval` がそのまま使える形（key=article_path, label=delta_kind）。**人手目視ではない**。
- **第一級の改正抽出レーン**: 改め文が取れる改正は、text-diff (lawdelta) より**上位の真実源**
  （findings §8.5）。lawdelta は改め文が取れない/溶け込み済みしか無い場合の代替。

## 使い方
```sh
python -m scripts.amendparse --in amendment.txt --out out/gold_from_amendment \
  --source 504AC0000000102   # 改正法令番号
# -> out/gold_from_amendment.gold.jsonl     (article_path, delta_kind, operation, ...)
# -> out/gold_from_amendment_summary.json   (件数・unknown 件数)
```
入力 `amendment.txt` は改正法の改め文テキスト（改正法 標準 XML の Sentence 連結でも可）。
real な改め文は e-Gov 法令API v2（改正履歴）等から取得（本サンドボックスは allowlist 外 HTTP 403）。

## カバレッジ（v0.1）
- `repeal`: 「第X条[（及び第Y条）]を削る。」「第X条の枝番を削る。」
- `substitution`: 「第X条を次のように改める。」「第X条中「A」を「B」に改める。」
  「第X条中「…」を削る。」「第X条の見出しを「…」に改める。」「第X条に次の項/号を加える。」
  「第X条から第Y条までを次のように改める。」（範囲展開、枝番混在は安全側で展開せず）
- `insertion`: 「第X条の次に次の一条を加える。…第X条の二　…」（次文の追加条番号を先読み解決）
- `renumber`: 「第X条を第Y条とする。」（new_path に Y を記録）
- `relocate`: 「…に/へ移す。」
- `unknown`: 上記いずれにも該当しない条文参照を含む文（**沈黙させない**）

## 真実観
改め文が断定する操作は事実。一方で**条文 ID 解決**（漢数字→正準 article_path）は `scripts.articlepath` を
通すことで失敗をフラグ化（`unknown` / `unparseable`）。**推測しない・沈黙させない**は DD-LAWSUBTRANS の家風と一致。
