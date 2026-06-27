"""floor_bundle_check の単体テスト (stdlib のみ).

run_bundle() の実行結果を検証:
  - 床充足: 定款27 / 議事録199① がすべて充足
  - 値照合: 商号・本店が一致、資本金は要人確認
  - 商号不一致ケースで ❌ を出す

実行: ``python tests/test_floor_bundle.py``
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from floor_bundle_check import run_bundle, _extract_value, _values_match  # noqa: E402

_PASS = 0
_FAIL = 0

BUNDLE_PATH = ROOT / "pipeline" / "floor" / "bundles" / "募集株式発行.json"


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


# ── 値抽出 ────────────────────────────────────────────────────────────────

def test_extract_shogo_teikan():
    """定款形式の商号抽出。"""
    text = "当会社は、ABC株式会社と称する。"
    v = _extract_value("商号", text)
    check(v is not None, "商号が抽出できる")
    check(v and "ABC株式会社" in v[0], f"ABC株式会社を含む ({v})")


def test_extract_shogo_toki():
    """登記形式の商号抽出。"""
    text = "商号\n   XYZ株式会社\n"
    v = _extract_value("商号", text)
    check(v is not None and "XYZ株式会社" in v[0], f"登記形式の商号 ({v})")


def test_extract_honten_teikan():
    """定款の本店抽出(に置く形式)。"""
    text = "当会社は、本店を東京都渋谷区に置く。"
    v = _extract_value("本店", text)
    check(v is not None, "本店が抽出できる")
    check(v and "東京都渋谷区" in v[0], f"東京都渋谷区を含む ({v})")


def test_extract_shihonkin_total():
    """登記の資本金総額抽出。"""
    text = "資本金の額　　　　　　金15,000,000円"
    v = _extract_value("資本金", text)
    check(v is not None and "15,000,000" in v[0], f"資本金総額 ({v})")
    check(v and v[1] == "total", "note=total")


def test_extract_shihonkin_delta():
    """議事録の資本金増加額抽出 — note が delta になる。"""
    text = "増加する資本金の額　金5,000,000円"
    v = _extract_value("資本金", text)
    check(v is not None and "5,000,000" in v[0], f"資本金増加額 ({v})")
    check(v and v[1] == "delta", "note=delta で区別できる")


# ── 値比較 ────────────────────────────────────────────────────────────────

def test_values_match_exact():
    check(_values_match("ABC株式会社", "ABC株式会社"), "完全一致")


def test_values_match_prefix():
    """定款の本店(区まで) ↔ 登記の本店(番地まで)のプレフィックス一致。"""
    check(_values_match("東京都渋谷区", "東京都渋谷区東一丁目1番1号"), "プレフィックス一致")


def test_values_mismatch():
    check(not _values_match("ABC株式会社", "XYZ株式会社"), "不一致を正しく検出")


# ── run_bundle 統合テスト ──────────────────────────────────────────────────

def test_bundle_floor_all_ok():
    """床充足チェック: 定款・議事録がすべて充足(登記はスキップ)。"""
    result = run_bundle(BUNDLE_PATH)
    for r in result["floor_results"]:
        if r.get("skipped"):
            continue
        check(r["ok"], f"{r['label']} の床充足")
        check(not r["missing"], f"{r['label']} に欠落なし")


def test_bundle_anchor_shogo_present():
    """商号錨が両書面(定款・登記)に出現。"""
    result = run_bundle(BUNDLE_PATH)
    shogo = next((ar for ar in result["anchor_results"] if ar["concept"] == "商号"), None)
    check(shogo is not None, "商号錨が検出される")
    if shogo:
        check(all(shogo["presence"].values()),
              f"商号が全書面に出現 ({shogo['presence']})")


def test_bundle_shogo_value_match():
    """商号値照合が ✅ 一致。"""
    result = run_bundle(BUNDLE_PATH)
    shogo = next((ar for ar in result["anchor_results"] if ar["concept"] == "商号"), None)
    check(shogo is not None, "商号錨あり")
    if shogo and shogo["value_pairs"]:
        vp = shogo["value_pairs"][0]
        check(vp["match"] and not vp["needs_human"],
              f"商号一致: {vp['val_a']!r} ↔ {vp['val_b']!r}")


def test_bundle_honten_value_match():
    """本店値照合が ✅ 一致(プレフィックス)。"""
    result = run_bundle(BUNDLE_PATH)
    honten = next((ar for ar in result["anchor_results"] if ar["concept"] == "本店"), None)
    check(honten is not None, "本店錨あり")
    if honten and honten["value_pairs"]:
        vp = honten["value_pairs"][0]
        check(vp["match"], f"本店一致: {vp['val_a']!r} ↔ {vp['val_b']!r}")


def test_bundle_shihonkin_needs_human():
    """資本金は増加額 vs 総額なので 🔍 要人確認になる。"""
    result = run_bundle(BUNDLE_PATH)
    sk = next((ar for ar in result["anchor_results"] if ar["concept"] == "資本金"), None)
    check(sk is not None, "資本金錨あり")
    if sk and sk["value_pairs"]:
        vp = sk["value_pairs"][0]
        check(vp["needs_human"], "資本金は needs_human=True")


def test_bundle_shogo_mismatch_detected():
    """商号が食い違う書面セットで 不一致 を検出する。"""
    base = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    teikan_text = "当会社は、ABC株式会社と称する。\n商号　ABC株式会社\n本店の所在地\n東京都渋谷区"
    toki_text = "商号\n   XYZ株式会社\n本店\n   東京都渋谷区東一丁目1番1号\n資本金の額 金15,000,000円"
    giji_text = "増加する資本金の額 金5,000,000円 募集株式の種類及び数 普通株式200株"

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "teikan.txt").write_text(teikan_text, encoding="utf-8")
        (td / "toki.txt").write_text(toki_text, encoding="utf-8")
        (td / "giji.txt").write_text(giji_text, encoding="utf-8")

        bundle_def = {
            "手続": "テスト(商号不一致)",
            "documents": [
                {"label": "定款", "article": "27", "paragraph": None,
                 "file": str(td / "teikan.txt"),
                 "canonical_file": str(ROOT / "pipeline/floor/kaishaho_27.canonical.json")},
                {"label": "株主総会議事録", "article": "199", "paragraph": "1",
                 "file": str(td / "giji.txt"),
                 "canonical_file": str(ROOT / "pipeline/floor/kaishaho_199_1.canonical.json")},
                {"label": "変更登記申請", "article": "911", "paragraph": "3",
                 "file": str(td / "toki.txt"),
                 "skip_floor_check": True, "skip_floor_note": "テスト用"},
            ],
        }
        bundle_path = td / "bundle.json"
        bundle_path.write_text(json.dumps(bundle_def, ensure_ascii=False), encoding="utf-8")

        result = run_bundle(bundle_path)
        shogo = next((ar for ar in result["anchor_results"] if ar["concept"] == "商号"), None)
        check(shogo is not None, "商号錨が検出される")
        if shogo and shogo["value_pairs"]:
            vp = shogo["value_pairs"][0]
            check(not vp["match"],
                  f"商号不一致を検出: {vp['val_a']!r} ↔ {vp['val_b']!r}")


# ── main ─────────────────────────────────────────────────────────────────

def main() -> int:
    tests = [
        test_extract_shogo_teikan, test_extract_shogo_toki,
        test_extract_honten_teikan,
        test_extract_shihonkin_total, test_extract_shihonkin_delta,
        test_values_match_exact, test_values_match_prefix, test_values_mismatch,
        test_bundle_floor_all_ok,
        test_bundle_anchor_shogo_present, test_bundle_shogo_value_match,
        test_bundle_honten_value_match, test_bundle_shihonkin_needs_human,
        test_bundle_shogo_mismatch_detected,
    ]
    for t in tests:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
