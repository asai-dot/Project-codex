#!/usr/bin/env python3
"""demo_run.py — alo-gpt-audit のフル lifecycle を実データ相当のシナリオで回し、
artifacts/ に dry-run / 実行 / action-queue / owner-digest / health を書き出す。

シナリオは APPROVAL_RULE §6 / AUDIT_ROADMAP AUDIT-SYS-002 の「今回4件」を再現:
  - statusregistry  DDSTATUS_MODIFY_REQUIRED   -> patch_queue
  - claudehead      DDCLAUDEHEAD_PASS_WITH_NOTES(blocking) -> patch_queue (§F)
  - quasijudicial   DDCASESOURCE_NEED_MORE(material_absent) -> material_queue
  - legaldb         DESIGN_MODIFY_REQUIRED     -> patch_queue
さらに、現在 GPT 未回答の 2 件 (lawtime v0.2 / toclegalref v0.2) を missing_result
として置き、「to_gpt 直下は未回答だけ」になる様子を見せる。
"""

import io
import shutil
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import alo_gpt_audit as A  # noqa: E402

ARTIFACTS = HERE.parents[1] / "artifacts"


def w(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def req(to_gpt, rid, gate, topic, status="queued", extra=""):
    w(to_gpt / f"{rid}_REQUEST.md",
      "---\n"
      f"request_id: {rid}\ntopic: {topic}\ngate: {gate}\nstatus: {status}\n"
      f"result_expected_filename: {rid}_RESULT.md\n{extra}---\n"
      f"# REQUEST {rid}\n")


def res(from_gpt, rid, label, body=""):
    w(from_gpt / f"{rid}_RESULT.md", f"{label}\n\nrequest_id: {rid}\n\n{body}\n")


def build(root: Path):
    to_gpt = root / "to_gpt"
    from_gpt = root / "from_gpt"
    to_gpt.mkdir(parents=True)
    from_gpt.mkdir(parents=True)

    # --- answered 4件 (要 close) ---
    req(to_gpt, "20260605_statusregistry_v0.1_DDSTATUS", "DDSTATUS", "statusregistry")
    res(from_gpt, "20260605_statusregistry_v0.1_DDSTATUS", "DDSTATUS_MODIFY_REQUIRED",
        "required_patches:\n  - lifecycleを7語に限定\n  - statusをrow_dispositionへ改名\n")

    req(to_gpt, "20260605_claudehead_v1.1_DDCLAUDEHEAD", "DDCLAUDEHEAD", "claudehead")
    res(from_gpt, "20260605_claudehead_v1.1_DDCLAUDEHEAD", "DDCLAUDEHEAD_PASS_WITH_NOTES",
        "blocking_before_ratify:\n"
        "  - 第二Anthropicをhand/capacityと明記\n"
        "  - head落ち時のfallback pathを明記\n")

    req(to_gpt, "20260605_quasijudicial_v0.4_DDCASESOURCE", "DDCASESOURCE", "quasijudicial")
    res(from_gpt, "20260605_quasijudicial_v0.4_DDCASESOURCE", "DDCASESOURCE_NEED_MORE",
        "need_more_type: material_absent\n"
        "missing_materials:\n"
        "  - DD-CASE-SOURCE-CASEID_v0.4_closure_20260604.md\n"
        "  - alo_source_registry_seed_v0.1_20260604.jsonl\n"
        "  - registry_negative_test.py\n")

    req(to_gpt, "20260606_legaldb_v0.5_DESIGN", "DESIGN", "legaldb")
    res(from_gpt, "20260606_legaldb_v0.5_DESIGN", "DESIGN_MODIFY_REQUIRED",
        "required_patches:\n  - 海外先例over-reachを抑制\n  - stable_anchor_id mintを定義\n")

    # --- 現在 GPT 未回答の 2件 (missing_result, to_gpt 直下に残るべき) ---
    req(to_gpt, "20260607_lawtime_v0.2_DDLAWTIME", "DDLAWTIME", "lawtime")
    req(to_gpt, "20260607_toclegalref_v0.2_DDTOCLEGALREF", "DDTOCLEGALREF", "toclegalref")


def run(fn, *a, **k):
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*a, **k)
    return buf.getvalue()


def main():
    tmp = tempfile.mkdtemp()
    root = Path(tmp) / "gpt_ometsuke"
    build(root)
    lane = A.Lane(root)
    ns = lambda **kw: type("NS", (), kw)()  # noqa: E731

    sections = []
    sections.append(("status BEFORE",
                     run(A.cmd_status, lane, ns(verbose=True))))
    sections.append(("close-all DRY-RUN",
                     run(A.cmd_close_all, lane, ns(apply=False))))

    dryrun = "\n\n".join(f"$ alo-gpt-audit {name}\n{'='*60}\n{out}"
                         for name, out in sections)
    w(ARTIFACTS / "DRYRUN_demo_4items.txt", dryrun)

    # --- APPLY ---
    exec_sections = []
    exec_sections.append(("close-all --apply",
                          run(A.cmd_close_all, lane, ns(apply=True))))
    exec_sections.append(("close-all --apply (再実行 = idempotency 確認)",
                          run(A.cmd_close_all, lane, ns(apply=True))))
    exec_sections.append(("status AFTER",
                          run(A.cmd_status, lane, ns(verbose=True))))
    exec_sections.append(("action-queue",
                          run(A.cmd_action_queue, lane, ns())))
    exec_sections.append(("owner-digest",
                          run(A.cmd_owner_digest, lane, ns(all=False))))
    # 1件 reflect して queue から消える様子
    exec_sections.append(("reflect statusregistry --apply",
                          run(A.cmd_reflect, lane,
                              ns(request_id="20260605_statusregistry_v0.1_DDSTATUS",
                                 apply=True))))
    exec_sections.append(("action-queue (reflect 後)",
                          run(A.cmd_action_queue, lane, ns())))

    execout = "\n\n".join(f"$ alo-gpt-audit {name}\n{'='*60}\n{out}"
                          for name, out in exec_sections)
    w(ARTIFACTS / "EXEC_demo_4items.txt", execout)

    # health (demo lane)
    health_md = run(A.cmd_health, lane, ns(json=False))
    w(ARTIFACTS / "HEALTH_demo_lane.md", health_md)

    print("artifacts written:")
    for p in ["DRYRUN_demo_4items.txt", "EXEC_demo_4items.txt", "HEALTH_demo_lane.md"]:
        print("  artifacts/" + p)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
