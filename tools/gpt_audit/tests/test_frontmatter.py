from alo_gpt_audit.frontmatter import split_frontmatter


def test_parses_scalars_and_strips_inline_comments():
    text = (
        "---\n"
        "request_id: 20260606_statusregistry_v0.2_DDSTATUS\n"
        "gate: DDSTATUS\n"
        "status: blocked   # ← targets が Box 不在のため active 化しない\n"
        "source_hash: sha1:fb37e5883e61720a84a9d11bdbf1c087eae65394    # comment\n"
        "result_expected_filename: 20260606_statusregistry_v0.2_DDSTATUS_RESULT.md\n"
        "source_refs:\n"
        "  - box_id: \"123\"\n"
        "---\n"
        "\n"
        "# body\n"
    )
    meta, body = split_frontmatter(text)
    assert meta["request_id"] == "20260606_statusregistry_v0.2_DDSTATUS"
    assert meta["gate"] == "DDSTATUS"
    assert meta["status"] == "blocked"  # inline comment stripped
    assert meta["source_hash"] == "sha1:fb37e5883e61720a84a9d11bdbf1c087eae65394"
    assert meta["result_expected_filename"].endswith("_DDSTATUS_RESULT.md")
    # nested list item must not leak as a scalar key
    assert "box_id" not in meta
    assert body.strip() == "# body"


def test_no_frontmatter_returns_whole_text():
    meta, body = split_frontmatter("DDSTATUS_PASS\n\nrequest_id: x\n")
    assert meta == {}
    assert body.startswith("DDSTATUS_PASS")
