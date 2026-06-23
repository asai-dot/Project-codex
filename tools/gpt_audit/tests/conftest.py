"""現行 Box レーン (gpt_ometsuke) の状態を再現するフィクスチャ。

2026-06-06 時点の実 Box 状態を最小内容で写し取る:
  - to_gpt/ : 6 REQUEST (うち answered_not_processed は quasijudicial の 1 件のみ。
              statusregistry v0.2 / legaldb v0.5.1 は再投函済みで active)
  - from_gpt/ : 7 RESULT
  - to_gpt/processed/ : 6 退避済み REQUEST
"""

import os

import pytest


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def write_request(root, sub, filename, request_id, gate, status="queued",
                  result_expected=None, supersedes=None, topic=None, extra=""):
    result_expected = result_expected or filename.replace("_REQUEST.md", "_RESULT.md")
    fm = ["---", "request_id: {}".format(request_id), "gate: {}".format(gate)]
    if topic:
        fm.append("topic: {}".format(topic))
    fm.append("status: {}   # inline comment ignored".format(status))
    if supersedes:
        fm.append("supersedes: {}".format(supersedes))
    fm.append("result_expected_filename: {}".format(result_expected))
    fm.append("---")
    fm.append("")
    fm.append("# {} REQUEST".format(request_id))
    if extra:
        fm.append(extra)
    _write(os.path.join(root, sub, filename), "\n".join(fm) + "\n")


def write_result(root, filename, label, request_id, body_extra=""):
    body = "{}\n\nrequest_id: {}\nreviewer: GPT-5.5 Pro\n".format(label, request_id)
    if body_extra:
        body += body_extra.rstrip("\n") + "\n"
    body += "\n## verdict\nok.\n"
    _write(os.path.join(root, "from_gpt", filename), body)


def build_lane(root):
    # --- to_gpt/ : 6 active-side requests ---------------------------------
    write_request(
        root, "to_gpt",
        "20260605_quasijudicial_v0.4_DDCASESOURCE_REQUEST.md",
        "20260605_quasijudicial_v0.4_DDCASESOURCE", "DDCASESOURCE",
        status="blocked", topic="quasijudicial",
    )
    write_request(
        root, "to_gpt",
        "20260606_caselink_CASELINK_REQUEST.md",
        "20260606_caselink_CASELINK", "CASELINK", topic="caselink",
    )
    write_request(
        root, "to_gpt",
        "20260606_codexgov_v0.1_IMPL_REQUEST.md",
        "20260606_codexgov_v0.1_IMPL", "IMPL", topic="codexgov",
    )
    write_request(
        root, "to_gpt",
        "20260606_legallibbiblio_v0.5_INGEST_REQUEST.md",
        "20260606_legallibbiblio_v0.5_INGEST", "INGEST", topic="legallibbiblio",
    )
    write_request(
        root, "to_gpt",
        "20260606_statusregistry_v0.2_DDSTATUS_REQUEST.md",
        "20260606_statusregistry_v0.2_DDSTATUS", "DDSTATUS", topic="statusregistry",
        supersedes="20260605_statusregistry_v0.1_DDSTATUS",
    )
    write_request(
        root, "to_gpt",
        "20260607_legaldb_v0.5.1_DESIGN_REQUEST.md",
        "20260607_legaldb_v0.5.1_DESIGN", "DESIGN", topic="legaldb",
    )

    # --- from_gpt/ : 7 results --------------------------------------------
    write_result(root, "20260605_ccguard_v0.1.1_G0_RESULT.md",
                 "G0_PASS", "20260605_ccguard_v0.1.1_G0")
    write_result(root, "20260605_claudehead_v1.1_DDCLAUDEHEAD_RESULT.md",
                 "DDCLAUDEHEAD_PASS_WITH_NOTES", "20260605_claudehead_v1.1_DDCLAUDEHEAD")
    write_result(root, "20260605_lawtime_v0.1_DD_RESULT.md",
                 "DD_PASS", "20260605_lawtime_v0.1_DD")
    write_result(root, "20260605_matterevent_v0.5.1_DDMATTEREVENT_RESULT.md",
                 "DDMATTEREVENT_PASS", "20260605_matterevent_v0.5.1_DDMATTEREVENT")
    write_result(root, "20260605_quasijudicial_v0.4_DDCASESOURCE_RESULT.md",
                 "DDCASESOURCE_NEED_MORE", "20260605_quasijudicial_v0.4_DDCASESOURCE")
    write_result(root, "20260605_statusregistry_v0.1_DDSTATUS_RESULT.md",
                 "DDSTATUS_MODIFY_REQUIRED", "20260605_statusregistry_v0.1_DDSTATUS")
    write_result(root, "20260606_legaldb_v0.5_DESIGN_RESULT.md",
                 "DESIGN_MODIFY_REQUIRED", "20260606_legaldb_v0.5_DESIGN")

    # --- to_gpt/processed/ : 6 already-processed requests -----------------
    for fn, rid, gate in [
        ("20260605_ccguard_v0.1.1_G0_REQUEST.md", "20260605_ccguard_v0.1.1_G0", "G0"),
        ("20260605_claudehead_v1.1_DDCLAUDEHEAD_REQUEST.md",
         "20260605_claudehead_v1.1_DDCLAUDEHEAD", "DDCLAUDEHEAD"),
        ("20260605_lawtime_v0.1_DD_REQUEST.md", "20260605_lawtime_v0.1_DD", "DD"),
        ("20260605_matterevent_v0.5.1_DDMATTEREVENT_REQUEST.md",
         "20260605_matterevent_v0.5.1_DDMATTEREVENT", "DDMATTEREVENT"),
        ("20260605_statusregistry_v0.1_DDSTATUS_REQUEST.md",
         "20260605_statusregistry_v0.1_DDSTATUS", "DDSTATUS"),
        ("20260606_legaldb_v0.5_DESIGN_REQUEST.md", "20260606_legaldb_v0.5_DESIGN", "DESIGN"),
    ]:
        write_request(root, "to_gpt/processed", fn, rid, gate)

    return root


@pytest.fixture
def lane_root(tmp_path):
    return build_lane(str(tmp_path / "gpt_ometsuke"))


def build_design_doc_lane(root):
    """設計書 §13 の理想シナリオ: answered_not_processed = 4, processed 空。

    検収テスト (TEST-1〜6) 用。NEED_MORE / PASS_WITH_NOTES の構造化本文も入れて
    反映キュー抽出を検証できるようにする。
    """
    write_request(
        root, "to_gpt", "20260605_statusregistry_v0.1_DDSTATUS_REQUEST.md",
        "20260605_statusregistry_v0.1_DDSTATUS", "DDSTATUS", topic="statusregistry",
    )
    write_request(
        root, "to_gpt", "20260605_claudehead_v1.1_DDCLAUDEHEAD_REQUEST.md",
        "20260605_claudehead_v1.1_DDCLAUDEHEAD", "DDCLAUDEHEAD", topic="claudehead",
    )
    write_request(
        root, "to_gpt", "20260605_quasijudicial_v0.4_DDCASESOURCE_REQUEST.md",
        "20260605_quasijudicial_v0.4_DDCASESOURCE", "DDCASESOURCE",
        status="blocked", topic="quasijudicial",
    )
    write_request(
        root, "to_gpt", "20260606_legaldb_v0.5_DESIGN_REQUEST.md",
        "20260606_legaldb_v0.5_DESIGN", "DESIGN", topic="legaldb",
    )

    write_result(root, "20260605_statusregistry_v0.1_DDSTATUS_RESULT.md",
                 "DDSTATUS_MODIFY_REQUIRED", "20260605_statusregistry_v0.1_DDSTATUS")
    write_result(
        root, "20260605_claudehead_v1.1_DDCLAUDEHEAD_RESULT.md",
        "DDCLAUDEHEAD_PASS_WITH_NOTES", "20260605_claudehead_v1.1_DDCLAUDEHEAD",
        body_extra=(
            "notes:\n"
            "blocking_before_ratify:\n"
            "  - 第二Anthropic を hand/capacity と書く (固定担当にしない)\n"
            "  - head 落ち時の fallback を明記\n"
            "non_blocking_after_ratify:\n"
            "  - cost lane の表現修正\n"
        ),
    )
    write_result(
        root, "20260605_quasijudicial_v0.4_DDCASESOURCE_RESULT.md",
        "DDCASESOURCE_NEED_MORE", "20260605_quasijudicial_v0.4_DDCASESOURCE",
        body_extra=(
            "need_more_type: material_absent\n"
            "missing_materials:\n"
            "  - DD-CASE-SOURCE-CASEID_v0.4_closure_20260604.md\n"
            "  - registry_negative_test.py\n"
        ),
    )
    write_result(root, "20260606_legaldb_v0.5_DESIGN_RESULT.md",
                 "DESIGN_MODIFY_REQUIRED", "20260606_legaldb_v0.5_DESIGN")
    return root


@pytest.fixture
def design_lane_root(tmp_path):
    return build_design_doc_lane(str(tmp_path / "gpt_ometsuke"))
