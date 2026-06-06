from alo_gpt_audit.cli import main
from conftest import write_request


def test_lint_warns_missing_scope_fields(capsys, design_lane_root):
    rc = main(["--root", design_lane_root, "lint"])
    out = capsys.readouterr().out
    # 4 REQUEST すべて review_scope/target_mode 等を欠くので警告が出る
    assert "missing review_scope" in out
    assert "missing target_mode" in out
    assert rc == 0  # advisory: 既定では exit 0


def test_lint_strict_returns_nonzero(capsys, design_lane_root):
    rc = main(["--root", design_lane_root, "lint", "--strict"])
    assert rc == 1


def test_lint_clean_request_passes(capsys, tmp_path):
    import os

    root = str(tmp_path / "gpt_ometsuke")
    write_request(
        root, "to_gpt", "20260606_clean_v0.1_GATE_REQUEST.md",
        "20260606_clean_v0.1_GATE", "GATE",
    )
    # front-matter に preflight 必須キーを注入してクリーンな REQUEST にする
    p = os.path.join(root, "to_gpt", "20260606_clean_v0.1_GATE_REQUEST.md")
    text = open(p, encoding="utf-8").read().replace(
        "gate: GATE\n",
        "gate: GATE\nsource_hash: sha1:deadbeef\nreview_scope: ok\n"
        "regression_anchors: ok\ndecision_requested: ok\ntarget_mode: box_hash_locked\n",
    )
    open(p, "w", encoding="utf-8").write(text)

    rc = main(["--root", root, "lint", "--strict"])
    out = capsys.readouterr().out
    assert "警告なし" in out
    assert rc == 0
