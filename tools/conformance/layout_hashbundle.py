"""layout_hashbundle — DD-LAYOUT-001 v0.5 §2 の hash bundle 5種（用途別分割）。

依存ゼロ・read-only 純関数。content_hash を1本にせず**用途別に5分割**することで、
変化した次元のハッシュだけが無効化され、他は安定する（v0.2 blocking#1 / 「崩れても追従」）。

5種（LAYOUT v0.5 §2）:
  asset_content_hash  : asset 全体バイト（版同定）
  page_image_hash     : ページ画像ラスタ（軽量版再生成で変わる・テキストは不変）
  block_image_hash    : ブロック切出し画像
  text_range_hash     : ブロックのテキスト内容（再OCR で変わる・画像は不変）
  selector_bundle_hash: セレクタ束（bbox + text_pos + text_quote。アンカリングの同一性）

これにより:
  - 再OCR（同一画像, テキスト変化）  → text_range_hash のみ変化、image hashes 安定
  - 軽量版再生成（再ラスタ, テキスト不変）→ image hashes 変化、text_range_hash 安定
  - bbox 微調整（セレクタ変化）        → selector_bundle_hash のみ変化
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

try:
    from . import xdoc_canonical as _xc
except ImportError:  # pragma: no cover
    import xdoc_canonical as _xc


def _h(*parts) -> str:
    return _xc.sha256_hex(_xc.canonical_json(list(parts)))


@dataclass(frozen=True)
class BlockInputs:
    """ブロック1個分の生入力（各ハッシュの独立な原料）。"""
    asset_bytes_digest: str      # asset 全体の事前 digest（巨大バイト列の代理）
    page_raster_digest: str      # ページ画像ラスタの digest
    block_crop_digest: str       # ブロック切出し画像の digest
    text_content: str            # ブロックの文字列（OCR 出力）
    bbox: Tuple[float, float, float, float]   # 正規化 bbox
    text_pos: Tuple[int, int]    # (begin, end)
    text_quote: str              # exact（長さ制限済の引用）


@dataclass(frozen=True)
class HashBundle:
    asset_content_hash: str
    page_image_hash: str
    block_image_hash: str
    text_range_hash: str
    selector_bundle_hash: str

    def changed_vs(self, other: "HashBundle") -> set:
        """他 bundle と比べて変化したハッシュ名の集合。"""
        names = ("asset_content_hash", "page_image_hash", "block_image_hash",
                 "text_range_hash", "selector_bundle_hash")
        return {n for n in names if getattr(self, n) != getattr(other, n)}


def compute_bundle(inp: BlockInputs) -> HashBundle:
    return HashBundle(
        asset_content_hash=_h("asset", inp.asset_bytes_digest),
        page_image_hash=_h("page_img", inp.page_raster_digest),
        block_image_hash=_h("block_img", inp.block_crop_digest),
        text_range_hash=_h("text", inp.text_content),
        selector_bundle_hash=_h("selector", list(inp.bbox), list(inp.text_pos), inp.text_quote),
    )
