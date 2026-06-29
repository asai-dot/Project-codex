"""DD-LAYOUT-001 v0.5 §2 hash bundle 5種（用途別分割）の適合性テスト。"""
import os
import sys
import unittest
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from layout_hashbundle import BlockInputs, compute_bundle  # noqa: E402


def _base():
    return BlockInputs(
        asset_bytes_digest="A0", page_raster_digest="P0", block_crop_digest="B0",
        text_content="賃貸借契約の解除", bbox=(0.1, 0.2, 0.5, 0.3),
        text_pos=(100, 116), text_quote="賃貸借契約の解除",
    )


class TestHashBundleSplit(unittest.TestCase):
    def test_reocr_only_text_hash_changes(self):
        """再OCR（同一画像・テキスト変化）→ text_range_hash のみ変化、image hashes 安定。"""
        b0 = compute_bundle(_base())
        # OCR が「賃貸借契約の解除」→「賃貸借契約の解除（誤字訂正）」に変化
        b1 = compute_bundle(replace(_base(), text_content="賃貸借契約の解除（訂正）",
                                    text_quote="賃貸借契約の解除（訂正）"))
        changed = b1.changed_vs(b0)
        self.assertIn("text_range_hash", changed)
        self.assertNotIn("page_image_hash", changed)
        self.assertNotIn("block_image_hash", changed)
        self.assertNotIn("asset_content_hash", changed)

    def test_relight_only_image_hash_changes(self):
        """軽量版再生成（再ラスタ・テキスト不変）→ image hashes 変化、text_range_hash 安定。"""
        b0 = compute_bundle(_base())
        b1 = compute_bundle(replace(_base(), page_raster_digest="P1", block_crop_digest="B1"))
        changed = b1.changed_vs(b0)
        self.assertEqual(changed, {"page_image_hash", "block_image_hash"})
        self.assertNotIn("text_range_hash", changed)

    def test_bbox_tweak_only_selector_hash_changes(self):
        """bbox 微調整 → selector_bundle_hash のみ変化。"""
        b0 = compute_bundle(_base())
        b1 = compute_bundle(replace(_base(), bbox=(0.1, 0.2, 0.5, 0.31)))
        self.assertEqual(b1.changed_vs(b0), {"selector_bundle_hash"})

    def test_asset_change_only_asset_hash(self):
        b0 = compute_bundle(_base())
        b1 = compute_bundle(replace(_base(), asset_bytes_digest="A1"))
        self.assertEqual(b1.changed_vs(b0), {"asset_content_hash"})

    def test_identical_inputs_same_bundle(self):
        self.assertEqual(compute_bundle(_base()), compute_bundle(_base()))

    def test_all_five_distinct(self):
        b = compute_bundle(_base())
        vals = {b.asset_content_hash, b.page_image_hash, b.block_image_hash,
                b.text_range_hash, b.selector_bundle_hash}
        self.assertEqual(len(vals), 5)  # 用途別 prefix で衝突しない


if __name__ == "__main__":
    unittest.main()
