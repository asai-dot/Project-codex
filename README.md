# Project-codex

事務所内本棚DX化計画の解析・推薦ツール群。

## 購入レコメンド（アイデアD / Fork 3）

未所蔵で詳細TOCを持つ書籍を現業テーマとの関連度でランキングして購入候補を提案し、
「2度買い防止」アラートも出すスタンドアロン・ツール。

- エンジン: [`term_dict/scripts/purchase_recommender.py`](term_dict/scripts/purchase_recommender.py)
- 仕様/使い方: [`term_dict/scripts/README_purchase_recommender.md`](term_dict/scripts/README_purchase_recommender.md)
- テスト（合成データ・実データ不要）: `python tests/test_purchase_recommender.py`

stdlib のみ。依存パッケージ無し。実データ（`books.json` / `bencom_clean.json` 等）は
Box 同期パスを `--base` または環境変数 `BOOKDX_BASE` で指定する。
