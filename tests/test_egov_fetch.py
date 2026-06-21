"""e-Gov 各号取得ツールのテスト (合成 fixture・stdlib のみ・ネット非依存).

§5(ドクトリン)の top-down 正準リスト源 = 条文各号 anchor を、法令標準XMLから取り出す検算。
実 e-Gov へはアクセスせず、tests/fixtures の縮小XMLで parse を固定する。
実行: ``python tests/test_egov_fetch.py``。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from egov_fetch import extract_law_xml, parse_items, run_targets  # noqa: E402
from requirement_floor import analyze_floor  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


FIXTURE = (ROOT / "tests" / "fixtures" / "egov_kaishaho_199.xml").read_text(encoding="utf-8")


def test_parse_items_basic():
    items = parse_items(FIXTURE, law_id="405AC0000000086", article="199", paragraph="1")
    check(len(items) == 5, "199条1項=5号を抽出")
    check([i["号"] for i in items] == ["一", "二", "三", "四", "五"], "号ラベルが順に並ぶ")
    check(items[0]["名称"] == "募集株式の数", "一号の本文を取得")
    check(items[0]["id"] == "405AC0000000086/a199/p1/i1", "anchor id=law/article/paragraph/item")
    check(items[0]["article"] == "199" and items[0]["paragraph"] == "1", "条/項を保持")


def test_readonly_l0_invariants():
    """HOLD 不変条件: 出力は L0 observation で、procedure 紐付け/accepted 化を含まない。"""
    items = parse_items(FIXTURE, law_id="405AC0000000086", article="199", paragraph="1")
    check(all(i["layer"] == "L0_observation" for i in items), "全件 L0 observation")
    check(all(i["status"] == "observed" for i in items), "status=observed(accepted化しない)")
    check(all("procedure_id" not in i and "spine_ref" not in i for i in items),
          "procedure へ紐付けない(HOLD)")
    check(all(i["source"].startswith("e-Gov") for i in items), "source=e-Gov を明示")


def test_paragraph_filter():
    # 項で絞ると2項の Item は出ない(2項は号なしだが、絞り込み自体を検査)。
    all_p = parse_items(FIXTURE, article="199")
    p1 = parse_items(FIXTURE, article="199", paragraph="1")
    check(len(p1) == 5 and len(all_p) == 5, "号は1項のみ。項フィルタが効く")
    check(parse_items(FIXTURE, article="999") == [], "存在しない条は空")


def test_extract_law_xml_from_json_envelope():
    # e-Gov の版差(JSON 包み)でも法令XML を取り出せる。
    import json
    env = json.dumps({"law_data": {"law_full_text": FIXTURE}, "attached": None})
    xml = extract_law_xml(env.encode("utf-8"))
    items = parse_items(xml, article="199", paragraph="1")
    check(len(items) == 5, "JSON 包みからXML を復元して抽出")


def test_feeds_requirement_floor_shape():
    """各号 anchor が requirement_floor の canonical 形(id/名称/号/aliases)として渡せる。

    ※ ここで床に accepted されるわけではない。床は N書式の収束で別途決まる(下では1書式=部分被覆)。
    """
    canon = parse_items(FIXTURE, law_id="K", article="199", paragraph="1")
    forms = [{"id": "f1", "source_family": "X",
              "記載事項": ["募集株式の数", "募集株式の払込金額又はその算定方法"]}]
    floor = analyze_floor(canon, forms)
    # 1書式しか被覆しない号は statutory_conditional 側(=全書式一致でないと床にしない)。
    covered = {r["名称"] for r in floor["statutory_floor"]}
    check("募集株式の数" in covered, "1書式=1冊一致でも n=1 なので床に乗る(被覆1/1)")
    # 号 anchor が canonical として例外なく処理できること(形の互換)を主に確認。
    check(floor["n_forms"] == 1, "canonical 形として requirement_floor が消費可能")


def test_run_targets_offline():
    """一括取得の配線を、ネット注入(オフライン fetcher)で検算。raw + anchors を書く。"""
    import tempfile

    raw_bytes = FIXTURE.encode("utf-8")
    calls = []

    def fake_fetch(law_id, *, url=None, timeout=30):  # オフライン: fixture を返す
        calls.append((law_id, url))
        return raw_bytes

    targets = [{"law_id": "405AC0000000086", "article": "199", "paragraph": "1",
                "out": "k199.anchors.json"}]
    with tempfile.TemporaryDirectory() as d:
        raw_dir = Path(d) / "raw"
        res = run_targets(targets, raw_dir=raw_dir, out_dir=raw_dir, fetch_fn=fake_fetch)
        check(len(res) == 1 and res[0]["n_anchors"] == 5, "1対象=5各号を取得")
        check((raw_dir / "405AC0000000086.xml").exists(), "raw XML を保存")
        out = (raw_dir / "k199.anchors.json")
        check(out.exists(), "anchors JSON を出力")
        import json as _j
        payload = _j.loads(out.read_text(encoding="utf-8"))
        check(payload["layer"] == "L0_observation", "出力は L0(床ではない)")
        check(calls == [("405AC0000000086", None)], "law_id で read-only 取得を呼ぶ")


def main() -> int:
    for t in [test_parse_items_basic, test_readonly_l0_invariants, test_paragraph_filter,
              test_extract_law_xml_from_json_envelope, test_feeds_requirement_floor_shape,
              test_run_targets_offline]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
