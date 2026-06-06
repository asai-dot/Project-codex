"""パイプライン可視化ツールのテスト (合成 fs・stdlib のみ).

count / exists / roundtrip probe、status 導出 (done/blocked/waiting/todo)、
stale 検出、同梱 manifest のスモークを検証する。
実行: ``python tests/test_pipeline.py``。
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from pipeline_dashboard import derive, render_html, render_markdown  # noqa: E402
from pipeline_probe import collect, parse_roots, run_probe  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def test_probes(tmp: Path) -> None:
    (tmp / "toc").mkdir()
    for i in range(3):
        (tmp / "toc" / f"isbn_{i}.json").write_text("[]", encoding="utf-8")
    c = run_probe(tmp, {"type": "count", "path": "toc/*.json", "expected": 6, "label": "x"})
    check(c["count"] == 3 and c["ratio"] == 0.5 and not c["done"], "count 3/6=0.5 未完")
    c2 = run_probe(tmp, {"type": "count", "path": "toc/*.json", "expected": 3})
    check(c2["done"], "count 3/3 完了")

    e = run_probe(tmp, {"type": "exists", "path": "toc/isbn_0.json"})
    check(e["done"], "exists 有")
    e2 = run_probe(tmp, {"type": "exists", "path": "nope/*.md"})
    check(not e2["done"], "exists 無")


def test_roundtrip(tmp: Path) -> None:
    sent = tmp / "to_gpt"
    ret = tmp / "from_gpt"
    sent.mkdir(); ret.mkdir()
    (sent / "20260605_lawtime_REQUEST.md").write_text("x", encoding="utf-8")
    (sent / "20260606_matter_REQUEST.md").write_text("x", encoding="utf-8")
    (ret / "20260605_lawtime_RESULT.md").write_text("y", encoding="utf-8")
    # 古い未戻りを作る (mtime を 48h 前に)。
    old = sent / "20260601_old_REQUEST.md"
    old.write_text("x", encoding="utf-8")
    import os
    past = time.time() - 48 * 3600
    os.utime(old, (past, past))

    r = run_probe(tmp, {"type": "roundtrip", "sent": "to_gpt/*.md",
                        "returned": "from_gpt/*.md", "max_age_hours": 24})
    check(r["sent"] == 3 and r["returned"] == 1, "送3 戻1")
    check(r["pending_count"] == 2, "未戻り2 (matter, old)")
    pending_keys = {p["key"] for p in r["pending"]}
    check("20260605_lawtime" not in pending_keys, "lawtime は戻り済(キー一致)")
    check(not r["done"], "未戻りあり→未完")


def test_status_derivation(tmp: Path) -> None:
    # A(done) → B(依存A, exists無=todeだが依存満たすので todo) と
    # C(依存D未完=blocked)、roundtrip pending の E(waiting)。
    (tmp / "a.json").write_text("[]", encoding="utf-8")
    (tmp / "to_gpt").mkdir(); (tmp / "from_gpt").mkdir()
    (tmp / "to_gpt" / "x_REQUEST.md").write_text("x", encoding="utf-8")  # 戻りなし

    manifest = {
        "tracks": {"t": "T"},
        "stages": [
            {"id": "A", "title": "A", "track": "t",
             "probes": [{"type": "exists", "path": "a.json"}]},
            {"id": "B", "title": "B", "track": "t", "depends_on": ["A"],
             "probes": [{"type": "exists", "path": "missing.json"}]},
            {"id": "C", "title": "C", "track": "t", "depends_on": ["D"],
             "probes": [{"type": "exists", "path": "a.json"}]},
            {"id": "D", "title": "D", "track": "t",
             "probes": [{"type": "exists", "path": "missing.json"}]},
            {"id": "E", "title": "E", "track": "t",
             "probes": [{"type": "roundtrip", "sent": "to_gpt/*.md",
                         "returned": "from_gpt/*.md"}]},
        ],
    }
    snap = collect(tmp, manifest)
    rows = {r["id"]: r for r in derive(manifest, snap)}
    check(rows["A"]["status"] == "done", "A done")
    check(rows["B"]["status"] == "todo" and not rows["B"]["unmet_deps"], "B todo (依存満たす)")
    check(rows["C"]["status"] == "blocked" and rows["C"]["unmet_deps"] == ["D"], "C blocked←D")
    check(rows["D"]["status"] == "todo", "D todo")
    check(rows["E"]["status"] == "waiting", "E waiting (roundtrip未戻り)")

    md = render_markdown(manifest, list(rows.values()), snap)
    check("要注目" in md and "戻り待ち" in md, "markdown に詰まりセクション")
    check("依存待ちで入れない" in md, "blocked セクション")
    html = render_html(manifest, list(rows.values()), snap)
    check("<!doctype html>" in html and "E" in html, "html 生成")


def test_real_manifest_smoke() -> None:
    # 同梱 manifest が parse でき、空 root でも例外なく描画できる。
    import tempfile

    manifest = json.loads((Path(__file__).resolve().parents[1]
                           / "pipeline" / "pipeline.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        roots = parse_roots([f"bookdx={td}", f"alo={td}", f"repo={td}"])
        snap = collect(roots, manifest)
        rows = derive(manifest, snap)
        check(len(rows) == len(manifest["stages"]), "全ステージ評価")
        # 空 root なので legallib_fetch は todo、依存先 (resolver等) は blocked。
        by = {r["id"]: r for r in rows}
        check(by["legallib_fetch"]["status"] == "todo", "空 root で fetch=todo")
        check(by["legallib_apply"]["status"] == "blocked", "apply は依存未完で blocked")
        md = render_markdown(manifest, rows, snap)
        check(manifest["title"] in md, "実 manifest 描画 OK")


def main() -> int:
    import tempfile

    for t in [test_probes, test_roundtrip, test_status_derivation]:
        print(f"• {t.__name__}")
        with tempfile.TemporaryDirectory() as td:
            t(Path(td))
    for t in [test_real_manifest_smoke]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
