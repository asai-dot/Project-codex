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
from pipeline_probe import (  # noqa: E402
    ManifestError, collect, parse_roots, run_probe, validate_manifest,
)

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


def test_roundtrip_frontmatter(tmp: Path) -> None:
    # v0.2: front-matter request_id / result_expected_filename を優先突合。
    sent = tmp / "to_gpt"; ret = tmp / "from_gpt"
    sent.mkdir(); ret.mkdir()
    # REQUEST: stem を消しても RESULT 名と一致しない (別名)。front-matter で繋ぐ。
    (sent / "20260606_codexprogress_v0.1_DDPROGRESS_REQUEST.md").write_text(
        "---\nrequest_id: 20260606_codexprogress_v0.1_DDPROGRESS\n"
        "result_expected_filename: weird_named_result.md\n---\n本文", encoding="utf-8")
    (ret / "weird_named_result.md").write_text("結果", encoding="utf-8")  # 別名でも expected で一致
    # 版違いは別キー (誤対応しない): v0.2 REQUEST は戻り無し → pending。
    (sent / "20260606_codexprogress_v0.2_DDPROGRESS_REQUEST.md").write_text(
        "---\nrequest_id: 20260606_codexprogress_v0.2_DDPROGRESS\n---\n本文", encoding="utf-8")
    # orphan: どの送信にも対応しない戻り。
    (ret / "20260601_ghost_RESULT.md").write_text("---\nrequest_id: 20260601_ghost\n---\n",
                                                  encoding="utf-8")

    r = run_probe(tmp, {"type": "roundtrip", "sent": "to_gpt/*.md", "returned": "from_gpt/*.md"})
    check(r["sent"] == 2, "送信 2 (v0.1, v0.2)")
    check(r["pending_count"] == 1, "v0.2 のみ未戻り (別名 RESULT は expected で一致)")
    check(r["pending"][0]["key"] == "20260606_codexprogress_v0.2_DDPROGRESS", "pending=v0.2")
    check(r["pending"][0]["age_basis"].startswith("request_id_date"), "age 基準=request_id日付")
    check(r["orphan_count"] == 1 and r["orphan"] == ["20260601_ghost_RESULT.md"], "孤児戻り検出")


def test_manifest_validation() -> None:
    bad = {
        "roots": {"a": "x"},
        "stages": [
            {"id": "S1", "depends_on": ["NOPE"], "probes": [{"type": "exists", "root": "a", "path": "p"}]},
            {"id": "S1", "probes": [{"type": "weird", "path": "p"}]},   # dup id + invalid type
            {"id": "S2", "depends_on": ["S3"], "probes": [{"type": "exists", "root": "zzz", "path": "p"}]},
            {"id": "S3", "depends_on": ["S2"], "probes": []},            # S2<->S3 cycle
        ],
    }
    errs = validate_manifest(bad)
    joined = " | ".join(errs)
    check(any("duplicate stage id: S1" in e for e in errs), "重複 id 検出")
    check(any("unknown dependency: S1 -> NOPE" in e for e in errs), "未知依存 検出")
    check("invalid probe type" in joined and "weird" in joined, "不正 probe type 検出")
    check("unknown root" in joined and "zzz" in joined, "未知 root 検出")
    check(any(e.startswith("cycle:") for e in errs), "循環依存 検出")


def test_orphan_probe(tmp: Path) -> None:
    h = tmp / "handoff"; h.mkdir()
    (h / "report.md").write_text("x", encoding="utf-8")
    (h / "stray.md").write_text("x", encoding="utf-8")  # 未宣言
    r = run_probe(tmp, {"type": "orphan", "scan": "handoff/*.md",
                        "declared": ["handoff/report.md"]})
    check(r["orphan_count"] == 1 and r["orphan"] == ["stray.md"], "未宣言成果物のみ orphan")
    check(not r["done"], "orphan あり→未完")


def test_snapshot_metadata(tmp: Path) -> None:
    manifest = {"roots": {"r": "x"}, "tracks": {},
                "stages": [{"id": "A", "track": "t", "probes": [{"type": "exists", "root": "r", "path": "p"}]}]}
    snap = collect({"r": tmp}, manifest)
    check(snap["probe_version"] == "0.2.1", "probe_version")
    check(snap["manifest_hash"].startswith("sha256:"), "manifest_hash")
    check("+0900" in snap["generated_at_jst"], "JST タイムスタンプ")
    check(snap["manifest_errors"] == [], "正常 manifest はエラー無し")


def test_real_manifest_smoke() -> None:
    # 同梱 manifest が parse でき、空 root でも例外なく描画できる。
    import tempfile

    manifest = json.loads((Path(__file__).resolve().parents[1]
                           / "pipeline" / "pipeline.json").read_text(encoding="utf-8"))
    check(validate_manifest(manifest) == [], "同梱 manifest は検証エラー無し")
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


def test_roundtrip_duplicate_request_id(tmp: Path) -> None:
    # N2: 同一 request_id の重複送信を silent dedupe せず surface する。
    sent = tmp / "to_gpt"; ret = tmp / "from_gpt"
    sent.mkdir(); ret.mkdir()
    (sent / "20260607_dup_a_REQUEST.md").write_text(
        "---\nrequest_id: 20260607_dup\n---\n", encoding="utf-8")
    (sent / "20260607_dup_b_REQUEST.md").write_text(
        "---\nrequest_id: 20260607_dup\n---\n", encoding="utf-8")  # 同一 rid (重複投函)
    (sent / "20260607_solo_REQUEST.md").write_text(
        "---\nrequest_id: 20260607_solo\n---\n", encoding="utf-8")

    r = run_probe(tmp, {"type": "roundtrip", "sent": "to_gpt/*.md",
                        "returned": "from_gpt/*.md"})
    check(r["sent"] == 2, "distinct rid は 2 (dup は 1 件に集約)")
    check(r["duplicate_count"] == 1, "重複 rid を 1 件検出")
    check(r["duplicate"][0]["key"] == "20260607_dup", "重複キー")
    check(r["duplicate"][0]["files"] == ["20260607_dup_a_REQUEST.md",
                                         "20260607_dup_b_REQUEST.md"],
          "衝突した送信ファイル 2 件を列挙 (捨てない)")
    check(r["pending_count"] == 2, "未戻りは distinct rid ぶん (dup と solo)")

    # dashboard が重複を明示する (silent でない)。
    manifest = {"tracks": {"t": "T"}, "stages": [
        {"id": "R", "title": "R", "track": "t",
         "probes": [{"type": "roundtrip", "sent": "to_gpt/*.md",
                     "returned": "from_gpt/*.md"}]}]}
    snap = collect(tmp, manifest)
    rows = derive(manifest, snap)
    md = render_markdown(manifest, rows, snap)
    check("重複 request_id" in md and "20260607_dup" in md, "markdown に重複明細")
    check("重1" in md, "サマリに 重1 表示")


def test_collect_refuses_invalid_manifest(tmp: Path) -> None:
    # N1: collect() 自体が不正 manifest を既定で拒否 (両経路の単一ソース)。
    bad = {"roots": {"a": "x"}, "stages": [
        {"id": "S1", "depends_on": ["NOPE"],
         "probes": [{"type": "exists", "root": "a", "path": "p"}]},
        {"id": "S1", "probes": []},  # duplicate id
    ]}
    raised = False
    try:
        collect({"a": tmp}, bad)
    except ManifestError as e:
        raised = True
        check(any("unknown dependency" in err for err in e.errors)
              and any("duplicate stage id" in err for err in e.errors),
              "ManifestError.errors に検証指摘を保持")
    check(raised, "不正 manifest で collect は既定で拒否 (ManifestError)")

    # refuse_on_invalid=False では収集し manifest_errors に記録 (degraded 観測)。
    snap = collect({"a": tmp}, bad, refuse_on_invalid=False)
    check(snap["manifest_errors"], "force 時はエラーを記録しつつ収集")

    # 正常 manifest は当然通る。
    ok = {"roots": {"a": "x"}, "stages": [
        {"id": "A", "probes": [{"type": "exists", "root": "a", "path": "p"}]}]}
    check(collect({"a": tmp}, ok)["manifest_errors"] == [], "正常 manifest は素通り")


def test_probe_main_refuses_invalid(tmp: Path) -> None:
    # N1: pipeline_probe.py main() の一括収集経路。
    import contextlib
    import io

    from pipeline_probe import main as probe_main

    mpath = tmp / "bad.json"
    mpath.write_text(json.dumps({"stages": [
        {"id": "A", "probes": []}, {"id": "A", "probes": []}]}), encoding="utf-8")
    out = tmp / "snap.json"
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = probe_main(["--manifest", str(mpath), "--root", str(tmp),
                         "--out", str(out)])
    check(rc == 1, "probe main も不正 manifest で exit 1")
    check("duplicate stage id" in err.getvalue(), "stderr に検証エラー")
    check(not out.exists(), "拒否時は snapshot を書かない")


def test_dashboard_root_path_refuses_invalid(tmp: Path) -> None:
    # N1 本丸: dashboard --root の収集+描画一発実行も検証拒否が効く。
    import contextlib
    import io

    from pipeline_dashboard import main as dash_main

    mpath = tmp / "bad.json"
    mpath.write_text(json.dumps({"stages": [
        {"id": "A", "depends_on": ["B"], "probes": []},
        {"id": "A", "probes": []}]}), encoding="utf-8")  # dup id + unknown dep
    out_md = tmp / "o.md"
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = dash_main(["--manifest", str(mpath), "--root", str(tmp),
                        "--out-md", str(out_md)])
    check(rc == 1, "dashboard --root も不正 manifest で exit 1 (N1)")
    check("manifest validation FAILED" in err.getvalue(), "stderr に検証失敗")
    check(not out_md.exists(), "拒否時は出力を書かない")

    # --snapshot 経路 (収集しない) は従来どおりバナー表示で描画は通す。
    snap = collect(tmp, {"roots": {}, "tracks": {}, "stages": [
        {"id": "A", "track": "t", "probes": []}]}, refuse_on_invalid=False)
    snap["manifest_errors"] = ["duplicate stage id: A"]  # 外部 snapshot を模す
    spath = tmp / "snap.json"
    spath.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    mpath.write_text(json.dumps({"tracks": {"t": "T"}, "stages": [
        {"id": "A", "title": "A", "track": "t", "probes": []}]}), encoding="utf-8")
    out_md2 = tmp / "o2.md"
    rc2 = dash_main(["--manifest", str(mpath), "--snapshot", str(spath),
                     "--out-md", str(out_md2)])
    check(rc2 == 0 and out_md2.exists(), "--snapshot 経路は収集しないので描画は通る")


def test_structure_section(tmp: Path) -> None:
    # 全体構造セクション: structure 宣言を最上部に描き、live があれば roll-up。
    from pipeline_dashboard import _rollup

    (tmp / "a.json").write_text("[]", encoding="utf-8")  # A=done, B=todo
    manifest = {
        "tracks": {"t": "T"},
        "structure": {
            "static_objects": [
                {"id": "book", "label": "③ 文献", "stages": ["A", "B"], "subs": [
                    {"id": "meta", "label": "書誌メタ", "stages": ["A"]},
                    {"id": "author", "label": "著者", "stages": [], "note": "外部WS#8"},
                ]},
                {"id": "law", "label": "① 法令", "stages": [], "note": "外部WS#8"},
            ],
            "dynamic_sources": [{"id": "sf", "label": "Ⓑ SF系", "stages": ["A"]}],
            "crosscutting": [{"id": "c3", "label": "C3 可視化", "stages": []}],
        },
        "stages": [
            {"id": "A", "title": "A", "track": "t", "probes": [{"type": "exists", "path": "a.json"}]},
            {"id": "B", "title": "B", "track": "t", "probes": [{"type": "exists", "path": "missing.json"}]},
        ],
    }
    snap = collect(tmp, manifest)
    rows = derive(manifest, snap)
    rows_by_id = {r["id"]: r for r in rows}
    ru = _rollup(rows_by_id, ["A", "B"])
    check(ru["done"] == 1 and ru["total"] == 2 and ru["status"] == "in_progress",
          "roll-up 1/2 done = in_progress")
    check(_rollup(rows_by_id, []) is None, "stages 無しは roll-up None")

    md = render_markdown(manifest, rows, snap)
    check("🗺 全体構造" in md, "構造セクション見出し")
    check("③ 文献" in md and "1/2 done" in md, "文献 roll-up 表示")
    check("① 法令" in md and "外部WS#8" in md, "外部WS は — + メモ")
    check("└ 書誌メタ" in md and "1/1 done" in md, "サブ 書誌メタ を割って roll-up")
    check("└ 著者" in md, "サブ 著者 (stages無し→—)")
    html = render_html(manifest, rows, snap)
    check("schip" in html and "③ 文献" in html, "html 構造チップ描画")
    check("subchip" in html and "書誌メタ" in html, "html サブチップ描画")

    # structure 無し manifest では構造セクションを出さない (後方互換)。
    bare = {"tracks": {"t": "T"}, "stages": manifest["stages"]}
    snap2 = collect(tmp, bare)
    check("🗺 全体構造" not in render_markdown(bare, derive(bare, snap2), snap2),
          "structure 無しならセクション無し")


def test_supabase_probe() -> None:
    # オフライン(env未設定)では skipped を返し、ネットを叩かない・collect を壊さない。
    import os

    from pipeline_dashboard import _rollup, derive

    saved = {k: os.environ.pop(k, None)
             for k in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_ANON_KEY")}
    try:
        r = run_probe(Path("."), {"type": "supabase", "table": "case_citations",
                                  "expected": 17259, "label": "判例引用"})
        check(r["type"] == "supabase" and r["skipped"] and not r["available"]
              and not r["done"], "supabase offline = skipped (ネット不要)")

        # validate: supabase は fs root 不要・table 必須。
        ok = {"roots": {"a": "x"},
              "stages": [{"id": "S", "probes": [{"type": "supabase", "table": "t"}]}]}
        check(validate_manifest(ok) == [], "supabase probe は root 無しでも valid")
        bad = {"stages": [{"id": "S", "probes": [{"type": "supabase"}]}]}
        check(any("table が無い" in e for e in validate_manifest(bad)),
              "table 無し supabase は error")

        # 構造 roll-up: skipped のみのオブジェクトは集計から除外 → None(—)。
        manifest = {"structure": {"static_objects": [{"id": "case", "label": "②", "stages": ["C"]}]},
                    "stages": [{"id": "C", "probes": [{"type": "supabase", "table": "t", "expected": 9}]}]}
        snap = collect({"a": Path(".")}, manifest)  # supabase は root 無視
        rows = derive(manifest, snap)
        check(rows[0]["skipped"], "skipped 行フラグ")
        check(_rollup({x["id"]: x for x in rows}, ["C"]) is None, "skipped のみ→roll-up None(—)")
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def main() -> int:
    import tempfile

    fs_tests = [test_probes, test_roundtrip, test_status_derivation,
                test_roundtrip_frontmatter, test_orphan_probe, test_snapshot_metadata,
                test_roundtrip_duplicate_request_id, test_collect_refuses_invalid_manifest,
                test_probe_main_refuses_invalid, test_dashboard_root_path_refuses_invalid,
                test_structure_section]
    for t in fs_tests:
        print(f"• {t.__name__}")
        with tempfile.TemporaryDirectory() as td:
            t(Path(td))
    for t in [test_manifest_validation, test_real_manifest_smoke, test_supabase_probe]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
