"""run_2dict ワンショット テスト."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_2dict as r2  # noqa: E402


class TestCrossDictCount(unittest.TestCase):
    def test_cross_dict_hubs(self):
        mem = [
            {"hub_id": "h1", "scheme_id": "yuhikaku_legal_dict"},
            {"hub_id": "h1", "scheme_id": "hourei_yougo_jiten_11"},  # またぎ
            {"hub_id": "h2", "scheme_id": "yuhikaku_legal_dict"},    # 単一
        ]
        self.assertEqual(r2.cross_dict_hubs(mem), 1)


class TestEndToEnd(unittest.TestCase):
    def test_main_with_explicit_paths(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            # 有斐閣: terms(定義なし) + labels(定義)
            (d / "yt.jsonl").write_text(json.dumps(
                {"stg_term_key": "y1", "scheme_id": "yuhikaku_legal_dict", "authority_rank": 101,
                 "term_tier": 1, "normalized_pref": "占有", "reading": "せんゆう"}, ensure_ascii=False) + "\n",
                encoding="utf-8")
            (d / "yl.jsonl").write_text(json.dumps(
                {"stg_term_key": "y1", "label_type": "definition", "label_text": "物を事実上支配すること"},
                ensure_ascii=False) + "\n", encoding="utf-8")
            # 学陽: entries(インライン定義, カタカナ読み)
            (d / "he.jsonl").write_text(json.dumps(
                {"scheme_id": "hourei_yougo_jiten_11", "entry_id": "h1", "headword": "占有",
                 "reading": "センユウ", "definition": "物を事実上支配する状態をいう"}, ensure_ascii=False) + "\n",
                encoding="utf-8")
            rc = r2.main(["--yuhikaku-terms", str(d / "yt.jsonl"), "--yuhikaku-labels", str(d / "yl.jsonl"),
                          "--hourei-entries", str(d / "he.jsonl"), "--out", str(d / "out"),
                          "--thresholds", "0.3,0.6"])
            self.assertEqual(rc, 0)
            self.assertTrue((d / "out" / "hub_build_report.md").exists())

    def test_load_terms_joins_and_adapts(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "yt.jsonl").write_text(json.dumps(
                {"stg_term_key": "y1", "scheme_id": "yuhikaku_legal_dict", "authority_rank": 101,
                 "term_tier": 1, "normalized_pref": "債権", "reading": "さいけん"}, ensure_ascii=False) + "\n",
                encoding="utf-8")
            (d / "yl.jsonl").write_text(json.dumps(
                {"stg_term_key": "y1", "label_type": "definition", "label_text": "給付請求権"},
                ensure_ascii=False) + "\n", encoding="utf-8")
            (d / "he.jsonl").write_text(json.dumps(
                {"entry_id": "h1", "headword": "債権", "reading": "さいけん", "definition": "給付を請求する権利"},
                ensure_ascii=False) + "\n", encoding="utf-8")
            terms, n_y, n_h = r2.load_terms(d / "yt.jsonl", d / "yl.jsonl", d / "he.jsonl")
            self.assertEqual((n_y, n_h), (1, 1))
            yt = [t for t in terms if t.get("stg_term_key") == "y1"][0]
            self.assertEqual(yt["definition"], "給付請求権")  # labels から join 済


if __name__ == "__main__":
    unittest.main()
