"""Project-codex: LegalLibrary 雑誌目次 → 論文 entity 抽出 + e-gov 法令リンク.

Fork 4 (アイデア B・F) のコア実装。

- article_parser : 雑誌目次の「タイトル　著者」ノードを {title, authors, ...} に分解
- author_normalize: 著者名正規化（横断検索の鍵を作る）
- egov_index      : e-gov 法令定義 jsonl から法令名/条文の索引を構築
- legal_links     : TOC 見出し/タイトルから条文・判例参照を抽出し e-gov へリンク
- jp_numerals     : 漢数字・全角数字 → int 変換（条番号の正規化に使用）
"""

__all__ = [
    "article_parser",
    "author_normalize",
    "egov_index",
    "legal_links",
    "jp_numerals",
]

__version__ = "0.1.0"
