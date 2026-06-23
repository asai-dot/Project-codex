"""scripts.amendparse — 改め文パーサ（PLAN: gold の公式真実源 / 接続軸の改正レーン）.

改正法の「改め文」は、どの条をどう変えたかを**官報の一次データとして断定**する
（「第七百三十三条を削る」＝repeal、「第七百七十二条を次のように改める」＝substitution、
「…の次に次の一条を加える」＝insertion）。本モジュールは改め文テキストを操作単位に分解し、
lawdelta と**同じ delta_kind 値域**へ写像する。＝

  - gold 生成器: 改正法の改め文から `(article_path, delta_kind)` を機械生成（人手目視でない）。
    lawdelta の text-diff 予測を `scripts.eval` で採点する正解になる。
  - 第一級の改正抽出レーン: 改め文が取れる改正は、text-diff より上位の真実源（findings §8.5）。

漢数字→正準 article_path は `scripts.articlepath` を再利用。stdlib のみ、DB なし。

カバレッジ(v0.1): 削る/次のように改める/中「」を「」に改める/見出し改め/項・号の追加・削除/
の次に…加える(insertion)/第Y条とする(renumber)/移す(relocate)。判定不能は **unknown**（沈黙させない）。
"""
from .parse import parse_amendments, Amendment

__all__ = ["parse_amendments", "Amendment"]
