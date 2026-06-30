"""make_raw_intake.py のテスト: 骨組み生成とテンプレが gate を通らないこと."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import make_raw_intake as mk  # noqa: E402
import manifest_gate as mg  # noqa: E402


def test_creates_tree_and_files(tmp_path):
    rc = mk.main(["--root", str(tmp_path), "--date", "20260618", "--sources", "legallib"])
    assert rc == 0
    d = tmp_path / "legallib" / "20260618"
    assert (d / "manifest.template.json").exists()
    assert (d / "DROP_HERE.md").exists()


def test_template_has_all_required_fields():
    t = mk.manifest_template("legallib")
    for f in mg.REQUIRED:
        assert f in t


def test_template_does_not_pass_gate():
    """TODO テンプレは投入をブロックされるのが正しい挙動 (人が埋めるまで通さない)."""
    for source in mk.ROUTE_HINTS:
        t = mk.manifest_template(source)
        errs = mg.validate(t)
        assert errs, f"{source} template unexpectedly passed gate"


def test_route_hint_values_are_valid_enums():
    """テンプレのヒント値が gate の enum と矛盾しないこと (TODO以外)."""
    for source in mk.ROUTE_HINTS:
        t = mk.manifest_template(source)
        for f, allowed in mg.ENUMS.items():
            v = t.get(f)
            if isinstance(v, str) and not v.startswith("TODO"):
                assert v in allowed, f"{source}.{f}={v} not in {allowed}"


def test_default_creates_all_four_sources(tmp_path):
    mk.main(["--root", str(tmp_path), "--date", "20260618"])
    for source in ["lionbolt", "bengo4", "legallib", "self_scan"]:
        assert (tmp_path / source / "20260618" / "manifest.template.json").exists()
