"""publisher_norm テスト — DD-EDIDENT-001-IMPL R1 (出版社 alias 正規化)。

法人格トークン (株式会社/(株)/㈱ 等) と記号・全半角差を畳んで別表記を同一キーに寄せ、
かつ別出版社は区別したままにする。stdlib のみ・決定的。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from publisher_norm import normalize_publisher as n  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond, msg):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def test_alias_collapse() -> None:
    base = n("有斐閣")
    for v in ("株式会社有斐閣", "(株)有斐閣", "㈱有斐閣", "（株）有斐閣", "有斐閣株式会社", " 有斐閣 "):
        check(n(v) == base, f"alias 一致: {v} -> {n(v)!r} != {base!r}")
    check(n("商事法務") == n("株式会社商事法務"), "商事法務 alias")
    check(n("テスト") == n("有限会社テスト"), "有限会社 alias")


def test_distinct_kept() -> None:
    check(n("有斐閣") != n("勁草書房"), "別社は区別")
    check(n("日本評論社") != n("日本加除出版"), "別社は区別2")


def test_empty_and_idempotent() -> None:
    check(n("") == "" and n(None) == "", "空入力は空")
    once = n("（株）日本評論社")
    check(n(once) == once, "冪等")


def main() -> int:
    for name, fn in (("test_alias_collapse", test_alias_collapse),
                     ("test_distinct_kept", test_distinct_kept),
                     ("test_empty_and_idempotent", test_empty_and_idempotent)):
        print(f"• {name}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
