# ワーカー発注: 会社法実務スケジュール → 手続フロー化 (STEP 1 = TOC 取得)

⑥手続の本丸（→ `docs/dd_procedure_design.md` §8）。段取り本の構造を抽出してフロー化する第一段。
**read-only / 生データ非改変。** 解釈・確定はしない（番頭/owner/GPT の領分）。

## ゴール
「会社法実務スケジュール」の **詳細TOC** を機械可読で取り出し、業務一覧をフロー雛形にする材料を返す。

## 手順
1. **書籍特定**: 蔵書（`app/data/toc/` / 横断検索索引 / `books.json`）を「会社法実務スケジュール」で
   タイトル検索し、**ISBN** を確定。複数版あれば最新版。見つからなければその旨を報告（別ルート検討）。
2. **資産確認（報告するだけ）**:
   - **詳細TOC があるか**（`app/data/toc/isbn_<ISBN>.json` 等）。ノード数・最大階層。
   - **自炊PDF があるか**（`PDF_BASE` 配下等）。ページ対応(offset)の有無。
3. **TOC エクスポート**: 詳細TOC を **jsonl** で書き出す。1 行 1 ノード、最低限のキー:
   ```json
   {"title": "<節見出し>", "level": <章=0,節=1,...>, "page": <印刷ページ or PDFページ>}
   ```
   （既存スキーマのキー名が `l`/`t`/`p`/`depth` 等でも可。正規化は番頭側で吸収する。）
   出力先: `handoff/procedure_flow/kaishaho_jitsumu_toc.jsonl`。
4. **報告**: ISBN・TOCノード数・階層の深さ・PDF有無・offset有無・export パスを 5 行で。

## 禁止
- 生 `books.json` / TOC の改変、本番DB書込、SF/Box 削除、解釈の確定（分岐・根拠条文の判断は番頭/owner）。

## 番頭の次STEP（受領後）
```bash
python scripts/procedure_flow_from_toc.py \
  --toc handoff/procedure_flow/kaishaho_jitsumu_toc.jsonl \
  --book "会社法実務スケジュール" --isbn <ISBN> --write
# → pipeline/procedure_flow/<業務>.json (status: toc_stub) が業務数ぶん生成
python scripts/procedure_flow.py pipeline/procedure_flow/<業務>.json --render  # 検証+フロー図
```
線形 stub ができたら、**分岐（公開/非公開・同時廃止/管財 等）・根拠条文・期限・必要書類**を
本文の日程表＋条文(e-Gov)から抽出して node に足し、owner/GPT が監査 → `status: audited`。
